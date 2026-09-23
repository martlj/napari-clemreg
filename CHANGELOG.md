# Changelog

All notable changes to this fork's modernisation work are documented here, in reverse chronological order. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**Status note:** `setup.cfg` has stayed at `0.2.1` (inherited from upstream) throughout the modernisation work below — none of it has actually been version-bumped or tagged yet. The version numbers here are a *proposal* for how that work breaks into release batches, grouped by theme and merge date, not a record of real releases. Each batch is numbered by the bump rules in [CLAUDE.md § Versioning](CLAUDE.md#versioning): minor for new features or (while pre-1.0) breaking changes, patch for fixes only. See [ROADMAP.md](ROADMAP.md) and [issue #1](https://github.com/martlj/napari-clemreg/issues/1) for the actual release/versioning decision, which hasn't been made yet.

This changelog covers the modernisation fork's own work only (starting from the testing-foundation pass below). It doesn't itemise upstream `krentzd/napari-clemreg`'s pre-fork history.

## [Unreleased]

Merged into `modernisation` since 0.5.0, not yet released. Proposed as **0.6.0**, a minor bump: it adds features (per-step buttons, `bioio` metadata) and changes the default warped-LM output resolution.

### Added
- The TIFF reader now uses `bioio` to read pixel sizes, instead of hand-parsing ImageJ-specific TIFF tags, so pixel sizes are picked up from TIFFs that weren't written by ImageJ ([#37](https://github.com/martlj/napari-clemreg/issues/37), [PR #38](https://github.com/martlj/napari-clemreg/pull/38)).
- Each stage of the combined "Run Registration" widget (EM Segmentation, LoG Segmentation, Point Cloud Sampling, Point Cloud Registration + Warping) has its own "Run this step" button, independent of the master "Register" button — lets a pre-existing layer be substituted to start from an intermediate step. Completing a step auto-sets and amber-highlights the next step's input ([#35](https://github.com/martlj/napari-clemreg/issues/35), [PR #36](https://github.com/martlj/napari-clemreg/pull/36)).
- Terminal prints the total elapsed time (`mm:ss`) for a full "Register" run, for benchmarking ([PR #36](https://github.com/martlj/napari-clemreg/pull/36)).

### Changed
- Warped LM (moving image) output now defaults to LM's own native pixel resolution instead of being forced onto EM's (much finer) pixel grid, placed correctly via the layer's `scale` rather than matching pixel counts. An "EM pixel grid (legacy)" option keeps the old behaviour. For Rigid/Affine CPD, the registration matrix is rescaled so the warp runs in a single interpolation pass directly from raw data ([#33](https://github.com/martlj/napari-clemreg/issues/33), [PR #34](https://github.com/martlj/napari-clemreg/pull/34)).
- README: the install instructions now use the extras (`pip install -e ".[segment-flow]" pyqt6`) instead of a hand-written dependency list, a new section explains the current state of EM segmentation (Segment-Flow by default, `empanada-dl` blocked on Python 3.11), and the Run Registration parameter list matches the current widget ([PR #52](https://github.com/martlj/napari-clemreg/pull/52)).

### Fixed
- `pint` is now a declared dependency (`pint >= 0.21`). The plugin imports it directly for the pixel-size fields, but it was only installed because napari requires it, and napari's floor (`pint>=0.17`) allows versions without `Quantity.to_preferred`, which the plugin calls when reading pixel sizes ([PR #65](https://github.com/martlj/napari-clemreg/pull/65)).
- README: the **Voxel Size** description had its effect backwards: larger values give *fewer* points and use less memory. The size filter is now correctly described as percentiles ([PR #52](https://github.com/martlj/napari-clemreg/pull/52)). PR #52 also reversed the **Sampling Frequency** description by mistake. Higher values give *more* points, as the original README said, and that's corrected again ([PR #66](https://github.com/martlj/napari-clemreg/pull/66)).

### Development
Changes to tests, CI and project docs, with no effect on the installed package.
- Widget behaviour tests: every widget and **Run this step** button is run against a napari `ViewerModel` with stubbed pipeline functions. Open GUI bugs (#47, #48, #49, #50, #53) are pinned as strict expected failures ([PR #54](https://github.com/martlj/napari-clemreg/pull/54)).
- Real-Viewer smoke tests on Linux CI, a slow end-to-end test of Run Registration on the real sample data, and a `slow tests` workflow that runs `--run-slow` after merges, weekly and on demand ([PR #55](https://github.com/martlj/napari-clemreg/pull/55), [PR #63](https://github.com/martlj/napari-clemreg/pull/63)).
- `modernisation` is now the fork's default branch, so "Fixes #N" closes issues on merge and scheduled workflows run ([PR #56](https://github.com/martlj/napari-clemreg/pull/56)).
- Package split design in [docs/design/package-split.md](docs/design/package-split.md), replacing §6 of the plan, with phases tracked in #57–#61 ([PR #62](https://github.com/martlj/napari-clemreg/pull/62)). Decisions D1–D6 accepted, with D1 and D4 amended and D5 reversed ([PR #67](https://github.com/martlj/napari-clemreg/pull/67)).
- Versioning rules (patch, minor, major, and when to declare 1.0.0), with this changelog's batches renumbered to match ([PR #44](https://github.com/martlj/napari-clemreg/pull/44), [PR #45](https://github.com/martlj/napari-clemreg/pull/45), [PR #46](https://github.com/martlj/napari-clemreg/pull/46)).

## [0.5.0] — AI-on-Demand Segment-Flow integration (2026-09-22 — 2026-09-23)

### Added
- New EM segmentation backend: Crick's AI-on-Demand (AIoD) [Segment-Flow](https://github.com/FrancisCrickInstitute/Segment-Flow) pipeline, shelling out to Nextflow rather than running MitoNet in-process. Works on Python 3.11, unlike the bundled `empanada-dl` extra (blocked by its `numpy==1.22` pin — [#5](https://github.com/martlj/napari-clemreg/issues/5)) ([PR #16](https://github.com/martlj/napari-clemreg/pull/16)).
- **EM Segmentation Backend** dropdown: `MitoNet (Segment-Flow)` / `MitoNet (empanada-dl)`, naming both explicitly as the same underlying model accessed two different ways.

### Changed
- **Breaking (install):** `empanada-dl` moved out of `install_requires` into its own `empanada` extra (`pip install napari-clemreg[empanada]`), so the base install resolves on Python 3.11. Users of the in-process MitoNet backend need the extra.
- Default EM segmentation backend flipped to `MitoNet (Segment-Flow)` — verified end-to-end against real production data, while `empanada-dl` currently can't even install on Python 3.11 ([#31](https://github.com/martlj/napari-clemreg/issues/31), [PR #32](https://github.com/martlj/napari-clemreg/pull/32)).

### Fixed
- `conf_threshold` mismatch between Segment-Flow's default (0.5) and `empanada-dl`'s bundled config (0.3) — was causing Segment-Flow to under-detect mitochondria relative to the bundled backend on identical input.
- Segment-Flow subprocess failures caused by `uv run` leaving its venv's `bin/` on `PATH` ahead of the target conda env activated inside the generated Nextflow script, so the wrong Python kept resolving regardless of which env was "activated".

## [0.4.1] — Live-testing bug-fixing pass (2026-09-22)

Bugs found and fixed while running the "Run Registration" widget end-to-end against real data. A patch release: fixes only, with no new features and no change to the public widget/API surface. (The Qt-binding switch below only touches the README and CI config, not the package's dependencies.)

### Fixed
- Sample data's FM channels displaying as corrupted/flattened stripes ([#17](https://github.com/martlj/napari-clemreg/issues/17), [PR #18](https://github.com/martlj/napari-clemreg/pull/18)).
- "Run Registration" silently hanging (no error, no progress) if FM or EM segmentation failed — root cause: `RegistrationThreadJoiner`'s `finished` signal fires on error as well as success, and unguarded code read kwargs that were never set ([#23](https://github.com/martlj/napari-clemreg/issues/23), [PR #24](https://github.com/martlj/napari-clemreg/pull/24)).
- Confusing `AttributeError` (`'str' object has no attribute 'astype'`) instead of a clear message when no segmentation was found — `run_moving_segmentation`/`run_fixed_segmentation` return the string `'No segmentation'`, not an array, and the combined widget didn't check for it ([#25](https://github.com/martlj/napari-clemreg/issues/25), [PR #26](https://github.com/martlj/napari-clemreg/pull/26)).
- `Points` layer construction crash — modern napari renamed the `edge_color` constructor argument to `border_color` ([#27](https://github.com/martlj/napari-clemreg/issues/27), [PR #28](https://github.com/martlj/napari-clemreg/pull/28)).
- Warping crash (`TypeError: cannot pickle 'QFont' object`) when warping real, viewer-attached layers — `copy.deepcopy(image)` was carrying live Qt/vispy canvas state; replaced with building a fresh, unattached `Image` layer from just the fields actually used downstream ([#29](https://github.com/martlj/napari-clemreg/issues/29), [PR #30](https://github.com/martlj/napari-clemreg/pull/30)).
- Dock panel growing when an "advanced settings" checkbox reveals more widgets, but never shrinking back down when unchecked — Qt widgets don't auto-shrink once resized larger; needed an explicit `adjustSize()` ([#21](https://github.com/martlj/napari-clemreg/issues/21)).

### Changed
- Recommended Qt binding switched from PyQt5 to PyQt6 in the README's install commands and CI config — verified the full widget suite and test suite behave identically under both bindings first ([#19](https://github.com/martlj/napari-clemreg/issues/19)).

## [0.4.0] — Sample data & dev-experience (2026-09-22)

### Added
- Precomputed EM segmentation mask (mitochondria instances) as bundled sample data, so the pipeline can be exercised from Point Cloud Sampling onward without a GPU or the bundled MitoNet/`empanada-dl` widget ([#12](https://github.com/martlj/napari-clemreg/issues/12), [PR #15](https://github.com/martlj/napari-clemreg/pull/15)).

### Fixed
- README's dev-install instructions (`source .venv/bin/activate`) losing to conda base's own `PATH` handling — switched to `uv run` throughout ([#13](https://github.com/martlj/napari-clemreg/issues/13), [PR #14](https://github.com/martlj/napari-clemreg/pull/14)).

## [0.3.0] — Modernisation foundations (2026-09-21)

### Added
- Real test suite (previously none) covering the pure-math/algorithmic core (`clemreg/`), plus a synthetic end-to-end characterisation test with a known ground-truth transform ([#2](https://github.com/martlj/napari-clemreg/issues/2)).
- GitHub Actions CI workflow (none existed before) ([#10](https://github.com/martlj/napari-clemreg/issues/10)).
- Zenodo sample data and MitoNet weights now cached locally (OS-appropriate app-cache dir via `pooch`) instead of re-downloading on every run ([#11](https://github.com/martlj/napari-clemreg/issues/11)).

### Changed
- **Breaking (install):** now requires Python 3.11+ (`python_requires = >=3.11`, previously 3.7+), with most dependency pins loosened from `==` to `>=` ([#3](https://github.com/martlj/napari-clemreg/issues/3)). The widget/API surface is unchanged, so while pre-1.0 this is a minor bump, not a major one (plan §7.7).
- Target napari version bumped from a `<=0.6.6` ceiling to latest stable (0.9.1 at the time) — the ceiling was driven by an assumption about coexisting with `empanada-napari` that no longer applies now Segment-Flow runs EM segmentation in its own isolated environment ([#4](https://github.com/martlj/napari-clemreg/issues/4)).

### Fixed
- Thin-plate-spline (TPS) warp affine solve corrupted by incomplete zero-padding in `_make_warp` — `np.resize` cyclically tiled `to_points` into the constraint rows instead of zero-padding all four, corrupting the affine part of every non-rigid (BCPD) warp solve, not just pathological inputs. Found via the new identity-transform invariant test ([#9](https://github.com/martlj/napari-clemreg/issues/9)).
