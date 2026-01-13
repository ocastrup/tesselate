# TrimmedSplineProjector  
**Theory and Pseudocode for Multi‑Patch Trimmed Surfaces**

---

## 1. Purpose

`TrimmedSplineProjector` is a geometric utility for projecting a curve onto a **multi‑patch parametric surface** (Bézier or NURBS), handling:

- Multiple surface patches (non‑wrapped global UV space)
- Trimmed domains (NURBS trim curves)
- Analytic derivatives from `geomdl`
- Robust clipping of the projected curve against trims
- Exact handling of patch boundaries

The primary output is a **set of curve segments** that lie on the surface and inside its trimmed domain.

---

## 2. Conceptual Model

### 2.1 Multi‑Patch Surface

We assume the surface is composed of patches:

S = ⋃ᵢ Sᵢ(u,v),   (u,v) ∈ [0,1]²

Each patch has:
- A local parametric domain [0,1]²
- A global UV embedding:

(U,V) = (iᵤ + u, iᵥ + v)

---

### 2.2 Global UV Space

All curve operations are performed in **global UV coordinates**.

Benefits:
- Continuous curve representation across patches
- Single intersection and clipping logic
- Deferred mapping to per‑patch parameterizations

---

## 3. Inputs and Outputs

### Inputs

- Multi‑patch surface (list or grid of Bézier/NURBS patches)
- Trim curves (NURBS curves in UV space)
- Input curve (3D or UV‑space)
- Projection direction (constant or field)

### Outputs

- List of clipped curve segments:
  - Global UV representation
  - Corresponding 3D points
  - Patch‑local parameter intervals

---

## 4. Mathematical Foundations

### 4.1 Projection to Surface

Given:
- Curve C(t) ∈ ℝ³
- Direction d

We solve for each patch:

S(u,v) = C(t) + λ d

Solved using Newton iteration with analytic Jacobians:

J = [Sᵤ  Sᵥ  −d]

---

### 4.2 Surface–Curve Differential Mapping

Once the projected UV curve is known:

d/dt S(u(t),v(t)) = Sᵤ u'(t) + Sᵥ v'(t)

All surface derivatives are obtained analytically from `geomdl`.

---

### 4.3 Trimming and Clipping

Trim curves define a domain D ⊂ ℝ².

Clipping is performed by:
1. Intersecting the global UV spline with trim curves
2. Refining intersections with Newton solves:

C(t) = T(s)

3. Alternating inside/outside states to extract valid intervals

---

## 5. Algorithm Overview

### High‑Level Pipeline

1. Project curve onto each surface patch
2. Convert patch‑local UV results into global UV
3. Merge all projected UV samples
4. Fit a global UV spline
5. Intersect spline with trim curves
6. Clip spline to trimmed domain
7. Split clipped spline by patch boundaries
8. Map final segments to 3D

---

## 6. Pseudocode

### 6.1 Main Entry Point

```text
function project_curve(curve, surface, trims):
    uv_samples = []

    for patch in surface.patches:
        local_uv = project_onto_patch(curve, patch)
        global_uv = map_to_global_uv(local_uv, patch)
        uv_samples.extend(global_uv)

    uv_spline = fit_bspline(uv_samples)

    clipped_segments = clip_against_trims(uv_spline, trims)

    result = []
    for seg in clipped_segments:
        patch_segments = split_by_patch(seg)
        for pseg in patch_segments:
            xyz = map_uv_to_3d(pseg)
            result.append((pseg, xyz))

    return result
```

---

### 6.2 Projection onto a Single Patch

```text
function project_onto_patch(curve, patch):
    for each sample t on curve:
        solve S(u,v) = C(t) + λ d
        using Newton with analytic derivatives
        if converged and (u,v) in [0,1]²:
            store (u,v,t)
    return samples
```

---

### 6.3 Clipping Against Trim Curves

```text
function clip_against_trims(uv_spline, trims):
    intersections = []
    for trim in trims:
        seeds = polyline_intersections(uv_spline, trim)
        refined = newton_refine(seeds)

    sort intersections by t
    segments = extract_inside_intervals(intersections)
    return segments
```

---

### 6.4 Newton Refinement (Curve–Curve)

```text
solve C(t) - T(s) = 0

repeat:
    F = C(t) - T(s)
    J = [C'(t), -T'(s)]
    Δ = -J⁻¹ F
    (t,s) += Δ
until ||F|| < tol
```

---

## 7. Robustness Considerations

- Patch boundaries handled explicitly in global UV
- Degenerate Jacobians handled via damping
- Trim tangencies handled with adaptive stepping
- Multiple trim loops supported

---

## 8. Advantages of the Approach

- No surface tessellation
- Analytic derivatives throughout
- Exact trim handling
- Patch‑independent curve logic
- CAD‑kernel‑style robustness

---

## 9. Intended Use Cases

- CAD/CAM toolpath projection
- Surface annotation curves
- Isoparametric feature extraction
- Reverse‑engineering workflows
- Multi‑patch surface processing

---

## 10. License

MIT License (recommended)
