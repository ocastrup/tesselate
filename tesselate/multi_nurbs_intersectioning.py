# Retry: simplified run (smaller sample sizes) of the pipeline using geomdl NURBS trim if available,
# otherwise use emulated trim. This version reduces sampling/resolution to avoid timeouts.
# Refer to ChatGPT Common error norms chat
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Try geomdl import
use_geomdl = False
try:
    from geomdl import BSpline, NURBS, utilities
    use_geomdl = True
except Exception as e:
    use_geomdl = False

def bernstein_poly(i, n, t):
    from math import comb
    return comb(n, i) * (t**i) * ((1 - t)**(n - i))

def make_bezier_surface(ctrlpts):
    ctrlpts = np.asarray(ctrlpts)
    m, n = np.array(ctrlpts.shape[:2]) - 1
    def surface_eval(u, v):
        B_u = np.array([bernstein_poly(i, m, u) for i in range(m + 1)])
        B_v = np.array([bernstein_poly(j, n, v) for j in range(n + 1)])
        return np.tensordot(B_u, np.tensordot(B_v, ctrlpts, (0, 1)), (0, 0))
    return surface_eval

class MultiBezierSurface:
    def __init__(self, ctrlgrid, patch_size=4):
        self.ctrlgrid = np.asarray(ctrlgrid)
        self.patch_size = patch_size
        self.step = patch_size - 1
        nx, ny, _ = ctrlgrid.shape
        self.px = (nx - 1) // self.step
        self.py = (ny - 1) // self.step
        self.patches = []
        self.idx_by_coord = {}
        for pi in range(self.px):
            for pj in range(self.py):
                i = pi * self.step
                j = pj * self.step
                patch_ctrl = ctrlgrid[i:i+patch_size, j:j+patch_size, :]
                surf = make_bezier_surface(patch_ctrl)
                patch_index = len(self.patches)
                self.patches.append(((pi, pj), (surf, None, None)))
                self.idx_by_coord[(pi, pj)] = patch_index
    def patch_from_coord(self, pi, pj):
        return self.idx_by_coord.get((pi, pj), None)
    def eval_patch(self, idx, u, v):
        return self.patches[idx][1][0](u, v)

class GlobalUVSpline:
    def __init__(self, uv_curve, geomdl_surface=None):
        self.uv_curve = uv_curve
        self.surface = geomdl_surface
        self._is_geomdl_uv = hasattr(uv_curve, "evaluate_single") and hasattr(uv_curve, "derivatives")
        if not self._is_geomdl_uv:
            self.uv_pts = np.asarray(uv_curve, dtype=float)
            if self.uv_pts.ndim != 2 or self.uv_pts.shape[1] != 2:
                raise ValueError("uv_curve array must be shape (N,2)")
    def evaluate_uv(self, t):
        scalar = np.isscalar(t) or (isinstance(t, np.ndarray) and t.ndim == 0)
        t_arr = np.atleast_1d(t)
        if self._is_geomdl_uv:
            out = np.array([self.uv_curve.evaluate_single(float(tt)) for tt in t_arr])
        else:
            n = len(self.uv_pts)
            if n == 1:
                out = np.tile(self.uv_pts[0], (len(t_arr), 1))
            else:
                u_ctrl = np.linspace(0.0, 1.0, n)
                U = np.interp(t_arr, u_ctrl, self.uv_pts[:, 0])
                V = np.interp(t_arr, u_ctrl, self.uv_pts[:, 1])
                out = np.column_stack((U, V))
        return out[0] if scalar else out
    def derivative_uv(self, t):
        t = float(t)
        if self._is_geomdl_uv:
            derivs = self.uv_curve.derivatives(t, order=1)
            duv = np.array(derivs[1], dtype=float)
            return duv.reshape(2,)
        else:
            h = 1e-6
            t0 = max(0.0, t - h); t1 = min(1.0, t + h)
            p0 = np.asarray(self.evaluate_uv(t0)).reshape(2,)
            p1 = np.asarray(self.evaluate_uv(t1)).reshape(2,)
            return (p1 - p0) / (t1 - t0)
    def evaluate3D(self, t, multi_surf):
        uv = self.evaluate_uv(t)
        arr = np.atleast_2d(uv)
        pts = []
        for Ux, Vx in arr:
            pi = int(np.floor(Ux)); pj = int(np.floor(Vx))
            u_local = float(np.clip(Ux - pi, 0.0, 1.0)); v_local = float(np.clip(Vx - pj, 0.0, 1.0))
            pidx = multi_surf.patch_from_coord(pi, pj)
            if pidx is None:
                pts.append([np.nan, np.nan, np.nan])
            else:
                pts.append(multi_surf.eval_patch(pidx, u_local, v_local))
        return pts[0] if np.isscalar(t) else np.array(pts)
    def derivative3D(self, t, multi_surf):
        h = 1e-6
        P0 = np.asarray(self.evaluate3D(max(0.0, t-h), multi_surf)).reshape(3,)
        P1 = np.asarray(self.evaluate3D(min(1.0, t+h), multi_surf)).reshape(3,)
        return (P1 - P0) / (2*h)

def sample_parametric_curve(curve_func, n=200):
    s = np.linspace(0.0, 1.0, n)
    pts = np.array([curve_func(si) for si in s])
    return s, pts

def segment_intersection_2d(p1, p2, q1, q2):
    p = np.array(p1); r = np.array(p2) - p
    q = np.array(q1); s = np.array(q2) - q
    r_cross_s = r[0]*s[1] - r[1]*s[0]
    if abs(r_cross_s) < 1e-12:
        return None
    q_p = q - p
    t = (q_p[0]*s[1] - q_p[1]*s[0]) / r_cross_s
    u = (q_p[0]*r[1] - q_p[1]*r[0]) / r_cross_s
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return float(t), float(u)
    return None

def point_in_polygon(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i+1)%n]
        if ((y0 > y) != (y1 > y)) and (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-30) + x0):
            inside = not inside
    return inside

def refine_intersection_analytic(spline_uv: GlobalUVSpline, trim_curve, t0, s0, tol=1e-9, max_iter=25):
    t = float(np.clip(t0, 0.0, 1.0)); s = float(np.clip(s0, 0.0, 1.0))
    for _ in range(max_iter):
        P = np.asarray(spline_uv.evaluate_uv(t)).reshape(2,)
        Q = np.asarray(trim_curve.evaluate_single(s)).reshape(2,)
        F = P - Q
        res = np.linalg.norm(F)
        if res < tol:
            return t, s, True, res
        dP_dt = np.asarray(spline_uv.derivative_uv(t)).reshape(2,)
        derivs = trim_curve.derivatives(s, order=1)
        dQ_ds = np.asarray(derivs[1], dtype=float).reshape(2,)
        J = np.column_stack((dP_dt, -dQ_ds))
        try:
            delta = np.linalg.solve(J, -F)
        except np.linalg.LinAlgError:
            return t, s, False, res
        t += float(delta[0]); s += float(delta[1])
        t = float(np.clip(t, 0.0, 1.0)); s = float(np.clip(s, 0.0, 1.0))
        if np.linalg.norm(delta) < tol:
            P_final = np.asarray(spline_uv.evaluate_uv(t)).reshape(2,)
            Q_final = np.asarray(trim_curve.evaluate_single(s)).reshape(2,)
            return t, s, True, np.linalg.norm(P_final - Q_final)
    P_final = np.asarray(spline_uv.evaluate_uv(t)).reshape(2,)
    Q_final = np.asarray(trim_curve.evaluate_single(s)).reshape(2,)
    return t, s, np.linalg.norm(P_final - Q_final) < tol, np.linalg.norm(P_final - Q_final)

def clip_spline_by_geomdl_trim(spline_uv, trim_curve, multi_surf,
                               n_spline_samples=200, n_trim_samples=200,
                               refine_tol=1e-9, sample_per_segment=80):
    ts = np.linspace(0,1,n_spline_samples+1); spine = spline_uv.evaluate_uv(ts)
    ss, trim_pts = sample_parametric_curve(lambda s: trim_curve.evaluate_single(s), n=n_trim_samples+1)
    intersections = []
    for i in range(len(spine)-1):
        p1 = spine[i]; p2 = spine[i+1]
        for j in range(len(trim_pts)-1):
            q1 = trim_pts[j]; q2 = trim_pts[j+1]
            res = segment_intersection_2d(p1[:2], p2[:2], q1[:2], q2[:2])
            if res is not None:
                t_local, u_local = res
                t_init = ts[i] + t_local*(ts[i+1]-ts[i])
                s_init = ss[j] + u_local*(ss[j+1]-ss[j])
                t_ref, s_ref, ok, err = refine_intersection_analytic(spline_uv, trim_curve, t_init, s_init, tol=refine_tol)
                intersections.append((t_ref, s_ref, ok, err))
    intersections = sorted(intersections, key=lambda x: x[0])
    clustered = []
    for item in intersections:
        if not clustered:
            clustered.append(item)
        else:
            if abs(item[0] - clustered[-1][0]) < 1e-6:
                if item[3] < clustered[-1][3]:
                    clustered[-1] = item
            else:
                clustered.append(item)
    intersections = clustered
    t_vals = [0.0] + [t for (t, s, ok, err) in intersections] + [1.0]
    t_vals = sorted(list(set([float(max(0.0,min(1.0,t))) for t in t_vals])))
    segments = []
    for k in range(len(t_vals)-1):
        a = t_vals[k]; b = t_vals[k+1]
        if b - a < 1e-12:
            continue
        mid = 0.5*(a+b)
        Umid, Vmid = spline_uv.evaluate_uv(mid)
        inside = point_in_polygon((Umid, Vmid), trim_pts[:, :2])
        if inside:
            seg_t = np.linspace(a, b, sample_per_segment)
            seg_uv = spline_uv.evaluate_uv(seg_t)
            seg_pts3d = spline_uv.evaluate3D(seg_t, multi_surf)
            segments.append({'t0':a, 't1':b, 't':seg_t, 'UV':seg_uv, 'pts3d':seg_pts3d})
    return segments, intersections, (spine, ts), (trim_pts, ss)

# Build multi-surf
nx, ny = 7, 7
ctrlgrid = np.zeros((nx, ny, 3))
for i in range(nx):
    for j in range(ny):
        x = i; y = j
        z = 0.25 * np.sin(np.pi * i / (nx-1)) * np.cos(np.pi * j / (ny-1))
        ctrlgrid[i,j] = (x, y, z)
multi_surf = MultiBezierSurface(ctrlgrid, patch_size=4)

# Build UV spline
if use_geomdl:
    uv_curve = BSpline.Curve()
    uv_curve.degree = 3
    uv_curve.ctrlpts = [[0.2,0.2],[0.9,0.4],[1.6,0.3],[2.8,0.6],[3.2,0.7]]
    uv_curve.knotvector = utilities.generate_knot_vector(uv_curve.degree, len(uv_curve.ctrlpts))
    spline_uv = GlobalUVSpline(uv_curve, geomdl_surface=None)
else:
    uv_pts = np.array([[0.2,0.2],[0.9,0.4],[1.6,0.3],[2.8,0.6],[3.2,0.7]])
    spline_uv = GlobalUVSpline(uv_pts, geomdl_surface=None)

# Build trim
if use_geomdl:
    trim = NURBS.Curve()
    trim.degree = 3
    trim.ctrlpts = [
        [2.5,0.5],[2.5,0.6],[2.4,0.75],[2.5,0.9],
        [2.3,1.1],[1.8,1.2],[1.4,1.2],[1.0,1.2],
        [0.6,1.1],[0.4,0.9],[0.5,0.75],[0.4,0.6],
        [0.5,0.5]
    ]
    trim.knotvector = utilities.generate_knot_vector(trim.degree, len(trim.ctrlpts))
    spline_trim = trim
else:
    class MockTrim:
        def evaluate_single(self, s):
            cx, cy = 1.5, 0.75; w, h, r = 2.0, 1.0, 0.25
            t = s % 1.0
            if t < 0.25:
                th = (t/0.25) * (np.pi/2)
                u = cx + (w/2 - r) + r*np.cos(th); v = cy + (h/2 - r) + r*np.sin(th)
            elif t < 0.5:
                th = ((t-0.25)/0.25) * (np.pi/2)
                u = cx - (w/2 - r) + r*np.cos(th+np.pi/2); v = cy + (h/2 - r) + r*np.sin(th+np.pi/2)
            elif t < 0.75:
                th = ((t-0.5)/0.25) * (np.pi/2)
                u = cx - (w/2 - r) + r*np.cos(th+np.pi); v = cy - (h/2 - r) + r*np.sin(th+np.pi)
            else:
                th = ((t-0.75)/0.25) * (np.pi/2)
                u = cx + (w/2 - r) + r*np.cos(th+3*np.pi/2); v = cy - (h/2 - r) + r*np.sin(th+3*np.pi/2)
            return [u, v]
        def derivatives(self, s, order=1):
            p = np.array(self.evaluate_single(s))
            h = 1e-6
            p1 = np.array(self.evaluate_single(min(1.0,s+h)))
            dp = (p1 - p) / h
            return [p.tolist(), dp.tolist()]
    spline_trim = MockTrim()

# Run clipping
segments, intersections, (spine, ts), (trim_pts, ss) = clip_spline_by_geomdl_trim(
    spline_uv, spline_trim, multi_surf,
    n_spline_samples=200, n_trim_samples=200, refine_tol=1e-8, sample_per_segment=80
)

print("Intersections:", intersections)

# Visualization (simple)
fig = plt.figure(figsize=(12,5))
ax1 = fig.add_subplot(1,2,1)
for (pi,pj), _ in multi_surf.patches:
    rect = np.array([[pi, pj],[pi+1,pj],[pi+1,pj+1],[pi,pj+1],[pi,pj]])
    ax1.plot(rect[:,0], rect[:,1], 'k-', alpha=0.2)
ax1.plot(spine[:,0], spine[:,1], '-', lw=1, label='Spline (sampled)')
ax1.plot(trim_pts[:,0], trim_pts[:,1], 'm-', lw=1.5, label='Trim (sampled)')
for (t,s,ok,err) in intersections:
    uv = spline_uv.evaluate_uv(t)
    ax1.plot(uv[0], uv[1], 'ro')
for seg in segments:
    ax1.plot(seg['UV'][:,0], seg['UV'][:,1], 'g-', lw=2)
ax1.set_title('Global UV-space'); ax1.axis('equal'); ax1.legend()

ax2 = fig.add_subplot(1,2,2, projection='3d')
# plot patches
Ugrid, Vgrid = np.meshgrid(np.linspace(0,1,8), np.linspace(0,1,8))
for (pi,pj), (surf_eval,_,_) in multi_surf.patches:
    pts = np.array([surf_eval(u,v) for u,v in zip(Ugrid.flatten(), Vgrid.flatten())])
    X = pts[:,0].reshape(Ugrid.shape); Y = pts[:,1].reshape(Ugrid.shape); Z = pts[:,2].reshape(Ugrid.shape)
    ax2.plot_surface(X, Y, Z, alpha=0.5, color='lightblue', linewidth=0)
samp_t = np.linspace(0,1,200)
samp_pts3d = spline_uv.evaluate3D(samp_t, multi_surf)
ax2.plot(samp_pts3d[:,0], samp_pts3d[:,1], samp_pts3d[:,2], 'r--', lw=1.2, label='Spline mapped')
trim_3d = []
for Ux,Vx in trim_pts:
    pi = int(np.floor(Ux)); pj = int(np.floor(Vx))
    u_local = float(np.clip(Ux - pi, 0.0, 1.0)); v_local = float(np.clip(Vx - pj, 0.0, 1.0))
    pidx = multi_surf.patch_from_coord(pi, pj)
    if pidx is None:
        trim_3d.append([np.nan, np.nan, np.nan])
    else:
        trim_3d.append(multi_surf.eval_patch(pidx, u_local, v_local))
trim_3d = np.array(trim_3d)
ax2.plot(trim_3d[:,0], trim_3d[:,1], trim_3d[:,2], 'm-', lw=1.5, label='Trim mapped')
for seg in segments:
    pts = seg['pts3d']; valid = ~np.isnan(pts[:,0])
    if np.any(valid):
        ax2.plot(pts[valid,0], pts[valid,1], pts[valid,2], 'g-', lw=2)
ax2.set_title('3D mapping'); ax2.legend()
plt.show()

{'n_segments': len(segments), 'n_intersections': len(intersections)}

