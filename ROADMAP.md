# Roadmap

A lighter-weight, forward-looking summary of what's planned. For detailed technical context on the original modernisation plan items, see [docs/napari-clemreg-modernisation-plan.md](docs/napari-clemreg-modernisation-plan.md) — this document links to the relevant section of that plan where one exists, and additionally covers newer ideas that have come up since it was written, from live GUI testing.

See [CHANGELOG.md](CHANGELOG.md) for what's already landed.

## In progress / open PRs

- **Native-resolution warping** ([#33](https://github.com/martlj/napari-clemreg/issues/33), [PR #34](https://github.com/martlj/napari-clemreg/pull/34)) — done for Rigid/Affine CPD; BCPD still uses the old warp-then-downsample approach rather than a single direct pass, deferred because it touches the same TPS grid-generation code as the pre-existing #9 bug (fixed in 0.3.0, but the area stays delicate).
- **Unify Run Registration and split widgets** ([#35](https://github.com/martlj/napari-clemreg/issues/35), [PR #36](https://github.com/martlj/napari-clemreg/pull/36)) — per-section "Run this step" buttons and auto-set/highlight are in; still open: whether to retire the standalone split widgets (`fixed_segmentation.py`, `moving_segmentation.py`, `point_cloud_sampling.py`, `registration_warping.py`) now that the combined widget covers their use cases, or keep them for anyone who wants a smaller widget instance. Not decided.
- **bioio-based pixel-size metadata** ([#37](https://github.com/martlj/napari-clemreg/issues/37), [PR #38](https://github.com/martlj/napari-clemreg/pull/38)).

## Planned (tracked, not yet started)

From the original modernisation plan (`docs/napari-clemreg-modernisation-plan.md`):

- **Repository & release strategy** ([#1](https://github.com/martlj/napari-clemreg/issues/1), plan §7) — when/how `modernisation` goes back into `main`, actual version tagging, PyPI ownership transfer to the Crick org. See the "Status note" at the top of [CHANGELOG.md](CHANGELOG.md) — no version bump has actually happened yet despite several minor-version-worthy batches of work.
- **`empanada-dl` dependency blocker** ([#5](https://github.com/martlj/napari-clemreg/issues/5)) — still can't install on Python 3.11 (`numpy==1.22` pin, no wheels). Segment-Flow (0.6.0) makes this non-blocking for EM segmentation generally, but the extra itself is still broken for anyone who specifically wants the in-process bundled backend.
- **MoBIE project output option** ([#6](https://github.com/martlj/napari-clemreg/issues/6), plan §3) — export registered/warped volumes as a MoBIE project.
- **Package split: `clemreg` core + `napari-clemreg` widgets** ([#7](https://github.com/martlj/napari-clemreg/issues/7), plan §6) — `packages/clemreg/` currently just reserves the PyPI name. Extracting the algorithmic core (segmentation, point-cloud sampling, registration, warping) into a standalone, napari-free package is a natural point to also reconsider the widget layer's own architecture (see the raw-Qt-vs-magicgui note below).

## Newer ideas (from this week's live testing, not yet in the original plan)

- **OME-Zarr integration** — the underlying motivation for the native-resolution warping work (#33): once real OME-Zarr/NGFF support exists, the current isotropic-resampling-onto-a-common-grid approach becomes unnecessary rather than just lighter. Depends on #6.
- **OME-Zarr sample data, tiff + zarr variants** ([#41](https://github.com/martlj/napari-clemreg/issues/41)) — for once OME-Zarr support lands.
- **Regenerate EM sample data with real embedded pixel-size metadata** ([#42](https://github.com/martlj/napari-clemreg/issues/42)) — confirmed directly that the current EM Zenodo file has no pixel-size metadata embedded at all; the hardcoded override in `sample_data.py` is load-bearing, not decorative, and can't be retired until this happens.
- **Reconsider `ndevio` for broader file-format reading** ([#40](https://github.com/martlj/napari-clemreg/issues/40)) — a bioio-based reader with real "install missing format plugin" prompting, useful once we need formats beyond TIFF (CZI, ND2, LIF, OME-Zarr). Not adopted now: its reader registers for `.tif`/`.tiff` too, which would conflict with our own TIFF reader from #37.
- **magicgui vs. raw Qt for the widget layer** — investigated while building #35's per-section buttons: `make_run_registration()`'s own function body has no reference back to its own widget Container (confirmed directly against magicgui's internals — it's called as a plain function, no self-injection), which forced a workaround (watching `viewer.layers.events.inserted` and matching by layer name) instead of a direct call. AIoD's own `aiod_napari` plugin is built entirely in raw Qt and doesn't hit this class of problem at all, at the cost of losing magicgui's automatic type-based widget generation and layer-list choice syncing. Not worth a full rewrite now — revisit when the core/widget package split (#7) happens anyway, since that's a natural point to reconsider the widget layer's architecture.
- **Push BCPD's warp fully upstream** — see "Native-resolution warping" above; the Rigid/Affine CPD case warps directly from raw data in one pass, but BCPD doesn't yet, since it needs a bigger change to the TPS grid-generation code in an already-fragile area.
