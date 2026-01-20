
# Trimmed NURBS Surface Clipping Pipeline  
**Production-Ready Mathematical and Algorithmic Overview**

This document outlines a full pipeline for intersecting and clipping a global-UV spline against trimmed NURBS surfaces using analytic derivatives from `geomdl`.

---

## 1. Overview of the Pipeline

1. **Global UV Spline Construction**  
   - Represent the projected curve as a `geomdl` B‑spline or NURBS curve in **global UV coordinates**.  
   - The curve supports  
     C(t), C'(t)  
     using closed-form evaluations from `geomdl`.

2. **Trim Curve Representation**  
   - A trim curve is a NURBS or BSpline curve  
     T(s), T'(s)  
     provided by `geomdl.evaluator` using `derivatives(s, order=1)`.

3. **Intersection Detection (Seed Stage)**  
   - Sample both the global UV spline and trim curve.  
   - Use polyline–polyline intersection in UV space.  
   - Each intersection candidate provides a seed pair (t0, s0).

4. **Analytic Newton Refinement**  
   We solve the 2×2 system:
   F(t,s) = C(t) - T(s) = 0  
   Its Jacobian is  
   J(t,s) = [ dC/dt   -dT/ds ].  
   The Newton update is  
   [Δt, Δs]^T = -J^{-1} F.

5. **Clipping the Spline**  
   - Use ordered refined intersection parameters (t1 < ... < tk).  
   - Alternate inside/outside states to determine kept UV segments.

6. **Mapping UV Segments to 3D**  
   - Use the surface Jacobian: S(u,v), Su, Sv.  
   - Combined with C'(t) = (u'(t), v'(t)), compute:  
     d/dt S(C(t)) = Su * u'(t) + Sv * v'(t).

7. **Output**  
   - Clipped curve pieces in UV.  
   - Corresponding 3D segments.  
   - Exact intersection pairs (t, s).

---

## 2. Mathematical Details

### 2.1 Global UV Curve
A curve in UV-space is defined as:
C(t) = (U(t), V(t)).

If represented as a B‑spline:
C(t) = Σ Ni,p(t) * Pi.

### 2.2 Trim Curve
The trim curve is another spline:
T(s) = Σ Mj,q(s) * Qj.

### 2.3 Surface Mapping
A NURBS surface is:
S(u,v) = (Σ Ni(u) Mj(v) w_ij P_ij) / (Σ Ni(u) Mj(v) w_ij).

Surface partial derivatives:
Su = ∂S/∂u  
Sv = ∂S/∂v

### 2.4 Intersection Conditions
We require C(t) = T(s).  
This yields two equations:
U(t) - UT(s) = 0  
V(t) - VT(s) = 0

Newton refinement uses the Jacobian:
J = [[U'(t), -UT'(s)], [V'(t), -VT'(s)]]

---

## 3. Pseudocode for the Pipeline

function clip_spline(surface, C, trim):
    seeds = sample_intersections(C, trim)
    refined = []
    for (t0, s0) in seeds:
        (t, s) = newton_refine(C, trim, t0, s0)
        refined.append((t, s))
    refined.sort by t
    pieces = extract_intervals(refined)
    for p in pieces:
        sample t -> UV -> 3D
    return pieces

---

## 4. Implementation Notes

- Newton refinement requires invertible Jacobian.  
- If singular, fallback to damped Newton or bisection.  
- Sorting intersections is crucial for correct in/out logic.  
- Surface evaluation must match global UV coordinates precisely.

---

## 5. Files & Deliverables

This Markdown file summarizes:

- Mathematical foundations  
- Algorithmic pipeline  
- Newton refinement  
- Clipping and 3D mapping  

Meant to accompany the production-ready `TrimmedSurfaceClipper` class.

---

## 6. License

MIT License (proposed for GitHub repo).
