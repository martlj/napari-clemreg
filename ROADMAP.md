# Roadmap

A lighter-weight, forward-looking summary of what's planned. For detailed technical context on the original modernisation plan items, see [docs/napari-clemreg-modernisation-plan.md](docs/napari-clemreg-modernisation-plan.md) — this document links to the relevant section of that plan where one exists, and additionally covers newer ideas that have come up since it was written, from live GUI testing.

See [CHANGELOG.md](CHANGELOG.md) for what's already landed.

## Known GUI bugs

Each is pinned by a strict expected-failure test (in `test_widget_behaviour.py` or `test_pipeline_baseline.py`). Phase 1 of the package split (#58) fixes #47 by design.

- **Save parameters crashes Register, and Parameters from JSON does nothing** ([#47](https://github.com/martlj/napari-clemreg/issues/47)).
- **Voxel Size sits in the wrong section** ([#49](https://github.com/martlj/napari-clemreg/issues/49)).
- **Registration direction EM → FM always crashes** ([#68](https://github.com/martlj/napari-clemreg/issues/68)), in every release so far. Fixing it needs a decision on what EM → FM output should look like.
- **README screenshots are out of date** ([#51](https://github.com/martlj/napari-clemreg/issues/51)).

## Planned

From the original modernisation plan (`docs/napari-clemreg-modernisation-plan.md`):

- **Repository & release strategy** ([#1](https://github.com/martlj/napari-clemreg/issues/1), plan §7) — when/how `modernisation` goes back into `main` (it's the fork's default branch meanwhile), actual version tagging, PyPI ownership transfer to the Crick org. See the "Status note" at the top of [CHANGELOG.md](CHANGELOG.md) — no version bump has actually happened yet despite several release-worthy batches of work (proposed numbering in the CHANGELOG).
- **`empanada-dl` dependency blocker** ([#5](https://github.com/martlj/napari-clemreg/issues/5)) — still can't install on Python 3.11 (`numpy==1.22` pin, no wheels). Segment-Flow (0.5.0) makes this non-blocking for EM segmentation generally, but the extra itself is still broken for anyone who specifically wants the in-process bundled backend.
- **MoBIE project output option** ([#6](https://github.com/martlj/napari-clemreg/issues/6), plan §3) — export registered/warped volumes as a MoBIE project.
- **Package split: `clemreg` core + `napari-clemreg` widgets** ([#7](https://github.com/martlj/napari-clemreg/issues/7), [milestone *clemreg 0.1.0*](https://github.com/martlj/napari-clemreg/milestone/1)): design in [docs/design/package-split.md](docs/design/package-split.md), with phases #58–#61 (decisions agreed in #57). MoBIE export (#6) is written directly in the core and can start once phase 1 (#58) merges. Get the upstream owner's agreement to the new layout before phase 2 (#59).

## Testing follow-ups

- **Run the real Segment-Flow test by hand before each release.** It skips on CI, because the runners have no Nextflow.
- **A manual release checklist** for what tests can't judge: overlay correctness, the readability of the auto-set highlight, dock sizing, and light and dark themes.

## Open decisions

Issues waiting on a decision are labelled [`needs-decision`](https://github.com/martlj/napari-clemreg/issues?q=is%3Aopen+label%3Aneeds-decision), and issues waiting on someone or something outside this repo are labelled [`blocked`](https://github.com/martlj/napari-clemreg/issues?q=is%3Aopen+label%3Ablocked). Decisions without an issue of their own:

- **Retire the split widgets?** Run Registration's per-step buttons (#35) now cover their use cases. This is decision D7 in the [package split design](docs/design/package-split.md#decisions-log), and it doesn't block the split.
- **Keep magicgui for the widgets, or move to raw Qt?** Decision D8; see the magicgui note under *Newer ideas*. It can wait until after the split.

## Newer ideas (from live testing, not in the original plan)

- **Selectable point cloud sampling methods** ([#75](https://github.com/martlj/napari-clemreg/issues/75)). Today points come only from the outside edge of each mask (2D Canny per z-slice). The current method stays the default, with unchanged results. Additions to investigate:
  - distance-map weighted sampling, with a tunable weight so points can come from near the edge, near object centres, or anywhere, using physical pixel sizes and per-object normalised distance
  - skeleton sampling, optionally only at branch points or end points, which is useful for filament-like structures in other projects
  - object centroids, as a baseline

  Package the samplers so other projects can import them with only numpy, scipy and scikit-image, i.e. without open3d or the registration stack. Where they live is open decision D9 in the [package split design](docs/design/package-split.md#decisions-log).

- **Automatic initial orientation for point cloud registration** ([#73](https://github.com/martlj/napari-clemreg/issues/73)). Registration works much better when the clouds start within about 90° of the right orientation, and today users pick the nearest orthogonal orientation by hand. To investigate:
  - running the registration from several starting orientations (e.g. the 24 axis-aligned rotations, on downsampled clouds) and keeping the best by a metric such as inlier fraction or Chamfer distance
  - handling a z flip between EM and FM, as a user setting, as extra candidates in the multi-start, or by a heuristic checked against typical data
  - open3d's feature-based global registration as a cheaper initialiser

  It fits the core's `register_point_clouds`, and is easier after package split phase 1 (#58).

- **2D registration** ([#79](https://github.com/martlj/napari-clemreg/issues/79)). A single EM section with a single FM plane, including multichannel FM. Today every step assumes (z, y, x): the FM filter and TPS warp hardcode three axes, segmentation thresholds each z slice, sampling runs Canny per slice and builds open3d 3D clouds, and resampling, warp matrices and output shapes are all 3D. A 2D pair should run through the same widgets and core API, with transforms limited to the plane: rigid is a rotation about z plus translation (and scale), affine is 2×3, and BCPD deforms only within the plane. Plan:
  - **Dimensionality is explicit, not guessed from `ndim`.** The reader squeezes size-1 axes, so a (c, y, x) FM image looks like a (z, y, x) stack. Keep bioio's dimension names in layer metadata and decide 2D or 3D from those, with a widget override when the metadata is missing. `PixelSize` allows no `z` for 2D.
  - **Design the phase 1 types (#58) to cover 2D**, so this doesn't break the API later: `Transform` has an `ndim` and holds a 3×3 or 4×4 homogeneous matrix (or 2D or 3D control points), and `Result` and the MoBIE exporter (#6) take it from there.
  - **Segmentation:** use a 2D difference of Gaussians (`_diff_of_gauss_2d` already exists), threshold the whole image rather than each row, and let `MaskRoi` have no z range. MitoNet is a 2D model, so both EM backends should accept one section.
  - **Sampling:** run Canny on the image directly. Pad clouds with z = 0 for open3d's downsampling and outlier removal, then drop the column, or replace those with numpy/scipy as part of #75.
  - **Registration:** register 2D clouds natively instead of as flat 3D clouds, which can rotate out of the plane. Checked against probreg: BCPD and affine CPD work on (N, 2) points (affine needs 2×2 initial parameters passed in), but rigid CPD crashes in 2D because its reflection fix hardcodes three dimensions. Options are an upstream fix, a small local 2D rigid step, or embedding in 3D and projecting the result back onto an in-plane rotation.
  - **Warping:** 3×3 matrices through `ndimage.affine_transform`, a 2D version of `_rescale_affine_matrix`, and a TPS warp written for any number of dimensions. The working grid becomes the EM xy pixel size, since there's no EM z pixel size to use.
  - **Widgets:** hide the z range and z pixel sizes for 2D inputs, and show 2D points and outputs.
  - **Tests:** synthetic 2D pairs with a known rotation, translation and shear that each algorithm must recover, plus a 2D slice of the sample data as a smoke test. The 3D output baseline must stay unchanged.
  - **Later:** automatic initial orientation (#73) in 2D has 8 candidates (4 rotations, with and without a flip), not 24. Registering a 2D EM section to a 3D FM stack (slice-to-volume) is a separate problem and out of scope; until then, mixed 2D and 3D inputs should fail with a clear error.

  Best done after package split phase 1 (#58), since it changes every core function's signature, but the types should be decided in phase 1.
- **OME-Zarr integration** — the underlying motivation for the native-resolution warping work (#33): once real OME-Zarr/NGFF support exists, the current isotropic-resampling-onto-a-common-grid approach becomes unnecessary rather than just lighter. Depends on #6.
- **OME-Zarr sample data, tiff + zarr variants** ([#41](https://github.com/martlj/napari-clemreg/issues/41)) — for once OME-Zarr support lands.
- **Regenerate EM sample data with real embedded pixel-size metadata** ([#42](https://github.com/martlj/napari-clemreg/issues/42)) — confirmed directly that the current EM Zenodo file has no pixel-size metadata embedded at all; the hardcoded override in `sample_data.py` is load-bearing, not decorative, and can't be retired until this happens.
- **Reconsider `ndevio` for broader file-format reading** ([#40](https://github.com/martlj/napari-clemreg/issues/40)) — a bioio-based reader with real "install missing format plugin" prompting, useful once we need formats beyond TIFF (CZI, ND2, LIF, OME-Zarr). Not adopted now: its reader registers for `.tif`/`.tiff` too, which would conflict with our own TIFF reader from #37.
- **magicgui vs. raw Qt for the widget layer** — investigated while building #35's per-section buttons: `make_run_registration()`'s own function body has no reference back to its own widget Container (confirmed directly against magicgui's internals — it's called as a plain function, no self-injection), which forced a workaround (watching `viewer.layers.events.inserted` and matching by layer name) instead of a direct call. AIoD's own `aiod_napari` plugin is built entirely in raw Qt and doesn't hit this class of problem at all, at the cost of losing magicgui's automatic type-based widget generation and layer-list choice syncing. Not worth a full rewrite now. It's recorded as decision D8 in the [package split design](docs/design/package-split.md#decisions-log): the split's adapters don't depend on either framework, so this can be decided after the split.
- **Push BCPD's warp fully upstream** (follow-up to [#33](https://github.com/martlj/napari-clemreg/issues/33)) — the Rigid/Affine CPD case warps directly from raw data in one pass, but BCPD doesn't yet, since it needs a bigger change to the TPS grid-generation code in an already-fragile area.
