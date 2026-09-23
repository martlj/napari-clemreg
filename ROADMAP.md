# Roadmap

A lighter-weight, forward-looking summary of what's planned. For detailed technical context on the original modernisation plan items, see [docs/napari-clemreg-modernisation-plan.md](docs/napari-clemreg-modernisation-plan.md) — this document links to the relevant section of that plan where one exists, and additionally covers newer ideas that have come up since it was written, from live GUI testing.

See [CHANGELOG.md](CHANGELOG.md) for what's already landed.

## Known GUI bugs

Each is pinned by a strict expected-failure test (in `test_widget_behaviour.py` or `test_pipeline_baseline.py`). Phase 1 of the package split (#58) fixes #47, #50 and #53 by design.

- **Save parameters crashes Register, and Parameters from JSON does nothing** ([#47](https://github.com/martlj/napari-clemreg/issues/47)).
- **Run Registration silently hangs when Segment-Flow fails** ([#53](https://github.com/martlj/napari-clemreg/issues/53)). This affects the default backend, so it's the most urgent.
- **Split EM/FM segmentation widgets crash when no segmentation is found** ([#50](https://github.com/martlj/napari-clemreg/issues/50)).
- **Prediction Across Three Axis is shown with Segment-Flow, where it does nothing** ([#48](https://github.com/martlj/napari-clemreg/issues/48)).
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

- **Retire the split widgets?** Run Registration's per-step buttons (#35) now cover their use cases. This is decision D7 in the [package split design](docs/design/package-split.md#decisions-log), and it doesn't block the split.

## Newer ideas (from live testing, not in the original plan)

- **OME-Zarr integration** — the underlying motivation for the native-resolution warping work (#33): once real OME-Zarr/NGFF support exists, the current isotropic-resampling-onto-a-common-grid approach becomes unnecessary rather than just lighter. Depends on #6.
- **OME-Zarr sample data, tiff + zarr variants** ([#41](https://github.com/martlj/napari-clemreg/issues/41)) — for once OME-Zarr support lands.
- **Regenerate EM sample data with real embedded pixel-size metadata** ([#42](https://github.com/martlj/napari-clemreg/issues/42)) — confirmed directly that the current EM Zenodo file has no pixel-size metadata embedded at all; the hardcoded override in `sample_data.py` is load-bearing, not decorative, and can't be retired until this happens.
- **Reconsider `ndevio` for broader file-format reading** ([#40](https://github.com/martlj/napari-clemreg/issues/40)) — a bioio-based reader with real "install missing format plugin" prompting, useful once we need formats beyond TIFF (CZI, ND2, LIF, OME-Zarr). Not adopted now: its reader registers for `.tif`/`.tiff` too, which would conflict with our own TIFF reader from #37.
- **magicgui vs. raw Qt for the widget layer** — investigated while building #35's per-section buttons: `make_run_registration()`'s own function body has no reference back to its own widget Container (confirmed directly against magicgui's internals — it's called as a plain function, no self-injection), which forced a workaround (watching `viewer.layers.events.inserted` and matching by layer name) instead of a direct call. AIoD's own `aiod_napari` plugin is built entirely in raw Qt and doesn't hit this class of problem at all, at the cost of losing magicgui's automatic type-based widget generation and layer-list choice syncing. Not worth a full rewrite now. It's recorded as decision D8 in the [package split design](docs/design/package-split.md#decisions-log): the split's adapters don't depend on either framework, so this can be decided after the split.
- **Push BCPD's warp fully upstream** (follow-up to [#33](https://github.com/martlj/napari-clemreg/issues/33)) — the Rigid/Affine CPD case warps directly from raw data in one pass, but BCPD doesn't yet, since it needs a bigger change to the TPS grid-generation code in an already-fragile area.
