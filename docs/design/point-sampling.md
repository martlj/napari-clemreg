# Design: continuous point cloud sampling

This document describes the design and the reasons for it. **It doesn't track status**: that's on [#75](https://github.com/martlj/napari-clemreg/issues/75) and the issues its phases get. When a decision changes, update the [decisions log](#decisions-log) rather than adding "update" notes to the text.

It refines the distance-weighted and skeleton methods proposed in #75, and uses the types from [the package split design](package-split.md) (`PixelSize`, `Params`). Where the samplers live is decision D9 there, and doesn't change anything here.

## Goal

1. **Points at continuous positions.** A point can lie anywhere inside or on a 3D object, at any physical coordinate, not only on voxel centres or on the planes of the original z slices.
2. **One control for where points come from.** A single position setting moves the points from the object's surface to its centreline, and a uniform option spreads them through the whole volume.
3. **Physical units throughout.** Sample each segmentation on its own grid in micrometres, so EM and FM clouds have the same point density without first resampling both onto the working grid.
4. **The current method stays the default.** `edge` keeps giving the same output, checked by the pipeline output baseline. The new method is opt-in until the evaluation below shows it should become the default.
5. **numpy, scipy and scikit-image only**, as #75 requires, so other projects can import the sampler without open3d or probreg.

## Why points come out in slices today

The adapter `run_point_cloud_sampling` resamples both segmentations onto a working grid whose voxel size is the EM z pixel size, using nearest-neighbour interpolation (`_make_isotropic`, `order=0`). `point_cloud_sampling` then runs 2D Canny on each z slice, keeps every *k*th edge voxel, downsamples onto a voxel grid and removes statistical outliers.

On the sample data, FM is 35 nm in xy and 130 nm in z, and EM is 20 nm in all three axes. So each FM slice becomes 6.5 identical working slices, and this causes four problems:

- **Terraces.** Canny finds the same contour on each of those 6.5 slices, so an object's side wall becomes a stack of vertical-walled slabs, with a step at each original FM slice. The points follow the slabs, not the real surface between them.
- **No top or bottom faces.** Canny in 2D only finds edges within a slice, so the caps of each object are never sampled (#75 mentions this).
- **Voxel positions.** Every point starts on a voxel centre of the working grid. Voxel-grid downsampling averages them, but the averages still follow the terraces.
- **Anisotropic EM loses resolution.** When EM isn't isotropic (serial-section EM, for example), `_make_isotropic(..., ref_frame='EM')` shrinks xy down to the z pixel size before sampling.

A quick check on a synthetic ellipsoid (semi-axes 0.35 × 0.25 × 0.6 µm, rasterised at the FM sample's pixel size) shows the effect. The "z phase" is where a point lies between two original FM slices, as a fraction of the slice spacing. Without slicing artefacts its histogram is flat:

| Sampler | Points | z phase, 10 bins, relative to flat | Median distance to the true surface |
|---|---|---|---|
| current `edge` | 194 | 2.53, 0.98, 0.05, 1.60, 1.55, 0.00, 1.55, 0.67, 0.15, 0.93 | 34 nm |
| continuous, surface band | 15 651 | 0.80 to 1.13 | 15 nm |
| continuous, uniform | 110 871 | 0.93 to 1.06 | (interior points) |

The current cloud also misses the bottom cap. The continuous rows come from a 40-line prototype of steps 1 to 5 below, without the local normalisation or count control, so only their flatness is meaningful, not their point counts.

**A separate bug found on the way:** `ndimage.zoom` aligns the corners of the input and output grids, so 28 FM slices become 182 working slices at 6.70 working slices per FM slice, not 6.5. That stretches the FM cloud by about 3% in z (15% for a 7-slice crop). The registration and the native-resolution warp then disagree about the z scale. That's [#98](https://github.com/martlj/napari-clemreg/issues/98). The image warp needs an exact resampling either way; the `continuous` method doesn't resample the masks at all (P3).

## Approach: sample a continuous field, not voxels

Treat each object as a continuous shape defined by its signed distance, interpolated between voxels. Then draw points from a probability density over that shape. Where the density puts the points is the tunable part.

### 1. Objects

Label the segmentation (`ndimage.label` for FM's binary mask; EM is already labelled), and crop each object with `ndimage.find_objects`, padded by a few voxels. Everything below works per object crop, which keeps memory small on large EM volumes and lets each object be normalised on its own.

### 2. Signed distance on the native grid

Compute φ = EDT(outside) − EDT(inside) with `ndimage.distance_transform_edt(..., sampling=pixel_size)`, in µm, on the object's own grid. φ is negative inside, positive outside and zero on the boundary. No resampling to the working grid is needed.

### 3. Interpolate between slices

Evaluate φ at any physical position by trilinear interpolation (`ndimage.map_coordinates(..., order=1)`). Between two slices, the boundary φ = 0 then moves smoothly from one slice's contour to the next instead of stepping. This is **shape-based interpolation** (Raya and Udupa 1990; Herman, Zheng and Bucholtz 1992), the standard way to interpolate binary masks between slices. It removes the terraces and gives objects real top and bottom caps. An optional Gaussian smoothing of φ (`smoothing`, in µm) also removes the voxel staircase within each slice.

Interpolation can't add information the data don't have: between slices the shape is a smooth guess. But it's an unbiased guess, which the terraces aren't.

### 4. A depth coordinate from surface to centreline

Define a depth t(x) in [0, 1]: 0 on the surface, 1 on the centreline. Two ways to normalise it:

- **Per object:** t = −φ / max(−φ) over the object. Simple, but on a tubule of varying width only the thickest part reaches t = 1, so "centreline" points pile up there.
- **Local (proposed default):** t = −φ(x) / r(x), where r(x) is the local radius: −φ at the nearest point of the object's medial axis. To find the medial axis, threshold the interpolated φ onto an isotropic grid for the object's crop (at the finest pixel size, so this is shape-based interpolation again), skeletonise it (`skimage.morphology.skeletonize`), then use `distance_transform_edt(..., return_indices=True)` on the skeleton's complement to find each position's nearest skeleton point. Then t = 1 along the whole centreline of a branched network, however thick each branch is.

### 5. Draw points from a density over depth

Sample from the density p(x) ∝ [φ(x) < 0] · w(t(x)), where w is a Gaussian centred at `position` with width `spread`, or w = 1 everywhere for uniform sampling.

Rejection sampling over the bounding box wastes most candidates when the target is a thin shell. Instead, sample voxel-then-jitter:

1. Give each voxel cell a weight equal to an upper bound of w over the cell (from φ at its corners, padded by the cell's half diagonal), and pick cells in proportion to it.
2. Place a candidate uniformly inside each picked cell, in physical coordinates. `scipy.stats.qmc.Sobol` instead of uniform random numbers gives lower variance for the same count.
3. Evaluate φ and t at the candidate by interpolation, and accept it with probability w(t) divided by the cell's bound.

This draws exactly from the continuous density, and the acceptance rate stays high even for a thin surface band.

### 6. Exactly on the surface or on the centreline

`spread = 0` asks for points exactly at one depth:

- **Surface** (`position = 0`): take candidates from a narrow band and move each onto φ = 0 with one or two Newton steps, x ← x − φ ∇φ / |∇φ|², using the interpolated gradient. The alternative is `skimage.measure.marching_cubes(..., spacing=pixel_size)` on φ and sampling triangles in proportion to their area. Both give continuous points, caps included. Phase 0 picks one (P4).
- **Centreline** (`position = 1`): the depth's gradient vanishes on the medial axis, so Newton steps don't work there. Instead, trace the skeleton from step 4 into branches (neighbour walking in numpy, or `skan` if it's worth the dependency), fit a smoothing spline to each branch in physical coordinates, and sample along each spline by arc length. Branch points and end points, which #75 also proposes, fall out of the same tracing. This replaces #75's skeleton method with one whose points aren't confined to voxels.

### 7. How many points, and how evenly spaced

Set the count by a physical `spacing` (µm, the mean distance between neighbouring points) rather than `every_k` and `voxel_size`, which are in working-grid voxels. Each object's count follows from its volume (band or uniform), surface area (surface) or length (centreline). The same `spacing` for EM and FM gives both clouds the same density, which CPD and BCPD assume, since their mixture models weight every point equally.

An optional `min_distance` (µm) thins clumps with Poisson-disk rejection using `scipy.spatial.cKDTree`. This replaces voxel-grid downsampling and statistical outlier removal for this method: the points come from a density, so there are no Canny outliers to remove.

### 8. Edges of the volume and of the Mask ROI

An object cut by the volume's edge or by the FM Mask ROI has an artificial surface there. Drop points whose position is within `border` µm of the cut, by checking the distance to the crop or ROI boundary. The current method samples these cut faces too.

### 9. Output

An (N, 3) array of (z, y, x) positions in µm, and the object label of each point if asked for. Until the core works in physical units throughout, the adapter divides by the working grid's voxel size, so registration and warping stay as they are.

## Why points away from the surface may register better

FM and EM rarely agree on where a surface is. The FM point spread function blurs objects, more in z than in xy, and the FM threshold then decides how much of that blur counts as inside. Both mostly dilate or erode the object. A uniform dilation moves the surface but not the medial axis, so centreline points should depend less on the FM threshold and the PSF. Surface points carry more shape information, though, and an object much longer along z than the PSF still moves its centreline ends. Which works better, and whether something in between does, is a question for the evaluation, and is the reason to keep `position` tunable rather than choose one.

## Interface

The shared interface from #75:

```python
sample_points(labels, pixel_size, method="edge", seed=None, **params) -> np.ndarray  # (N, 3), µm
```

`method="continuous"` takes:

| Parameter | Default | Meaning |
|---|---|---|
| `position` | 0.0 | depth to sample at: 0 surface, 1 centreline |
| `spread` | 0.1 | width of the depth band; 0 for exactly at `position`; `None` for uniform through the volume (ignores `position`) |
| `normalise` | `"local"` | `"local"` (radius at the nearest medial point) or `"object"` (the object's maximum depth) |
| `spacing` | to be set in phase 0 | mean distance between neighbouring points, µm |
| `min_distance` | `None` | Poisson-disk thinning distance, µm |
| `smoothing` | 0.0 | Gaussian σ applied to φ, µm |
| `border` | 0.0 | drop points this close to the volume or ROI edge, µm |
| `seed` | `None` | random seed; `Params` stores one so runs repeat |

In the GUI, a **Sampling method** dropdown in the Point Cloud Sampling section, as #75 proposes. For `continuous`, three presets cover most uses, with **Custom** showing the `position` and `spread` fields:

- **Surface**: `position = 0`, `spread = 0`
- **Centreline**: `position = 1`, `spread = 0`
- **Throughout**: `spread = None`

The parameters become new `Params` fields with these defaults and `sampling_method = "edge"`, so saved parameter files keep loading and give the same results.

## Relation to the methods in #75

| #75 method | Here |
|---|---|
| edge (current) | unchanged, still the default |
| distance-map weighted | `continuous`, with continuous positions, per-object or local normalisation, and sampling on the native grid |
| skeleton, branch and end points | `continuous` with `position = 1, spread = 0` (step 6) |
| object centroids | unchanged: one point per object, as a baseline |

## Phases

0. **Prototype and evaluate** outside the package, in a script or notebook: the synthetic phantoms and metrics under *Tests*, comparing `edge` with the presets. Decides P4 and the default `spacing`.
1. **The sampler in the core**, behind `method="continuous"`, with unit tests. The `edge` baseline is unchanged. Wherever D9 puts it, it imports only numpy, scipy and scikit-image.
2. **Widget and `Params`**: the method dropdown, the presets and the new fields.
3. **Evaluation on real data**: the benchmark sample and the EMPIAR datasets, as #75 describes, including bad starting orientations (#73) and partial overlap. If a preset wins clearly, propose it as the new default. That's a changed default with the old one still available, so a minor bump.

## Tests

On synthetic phantoms (ellipsoids, curved tubes of varying radius, a branched tube) rasterised at z/xy anisotropies of 1, 4 and 10:

- **No slicing:** the z phase of the points is uniform (Kolmogorov–Smirnov test against uniform).
- **Accuracy:** surface points lie within a tolerance of the analytic surface, and centreline points within a tolerance of the analytic axis, including on the thin parts of the varying-radius tube.
- **Physical units:** the same shape rasterised at two pixel sizes gives clouds with the same statistics (count per µm², mean distance to the surface).
- **Tunability:** the mean depth of the points increases with `position`.
- **Reproducible:** the same `seed` gives identical points.
- **Registration:** a synthetic FM/EM pair with a known transform is recovered at each anisotropy, measured by target registration error, for `edge` and each preset.
- **Baseline:** `test_pipeline_baseline.py` passes unchanged.

## Risks and limits

- **Objects one or two slices thick.** Their z extent is a guess, and shape-based interpolation makes them lens-shaped. Flag objects thinner than a set number of slices and either drop them or fall back to their centroid.
- **Touching objects merge** when FM's binary mask is labelled, so their centreline runs through both. The current method has the same limitation.
- **Skeletons on large EM volumes** are the slowest step, since they need an isotropic grid per object. Crops keep this bounded. For `normalise="object"` and for `spread = None`, no skeleton is needed.
- **Random points vary between runs.** The seed makes runs repeatable, and the evaluation should report the spread across seeds, not one run.
- **Large objects get more points**, as they do today. An optional per-object cap may be worth adding if one large object dominates the registration.

## Decisions log

| # | Decision | Options | Proposal | Status |
|---|---|---|---|---|
| P1 | How location is tuned | depth t in [0, 1] with `position` and `spread`; separate methods per location | One depth parameterisation with presets, so surface, centreline and anything between are one method | Proposed |
| P2 | Depth normalisation | per object; local (radius at the nearest medial point) | Local by default, per object as an option, because per object biases centreline points towards the thickest part | Proposed |
| P3 | Grid to sample on | the working grid after `_make_isotropic`; each segmentation's native grid in µm | Native grids: avoids nearest-neighbour terraces, the z stretch and EM xy downsampling, and saves memory | Proposed |
| P4 | Exact surface points | Newton projection onto φ = 0; marching cubes and area-weighted triangle sampling | Decide in phase 0 on accuracy and speed | Open |
| P5 | Point count | `every_k` and `voxel_size` in working-grid voxels; `spacing` and `min_distance` in µm | µm, for the new method only; `edge` keeps its parameters | Proposed |
| P6 | Default method | `edge`; a `continuous` preset | `edge` until phase 3 shows otherwise (from #75) | Accepted |

## References

- Raya, S. P. and Udupa, J. K. (1990). Shape-based interpolation of multidimensional objects. *IEEE Transactions on Medical Imaging* 9(1), 32–42.
- Herman, G. T., Zheng, J. and Bucholtz, C. A. (1992). Shape-based interpolation. *IEEE Computer Graphics and Applications* 12(3), 69–79.
