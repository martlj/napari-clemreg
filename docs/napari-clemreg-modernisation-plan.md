# napari-clemreg modernisation plan

Scope: (1) move the package to Python 3.11+, (2) make it compatible with napari 0.6.6+, (3) add an option to emit a **MoBIE project** (OME-Zarr sources, affine transform stored where possible) instead of, or in addition to, writing a transformed "moving" image TIFF, and (4) **split the codebase into two distributions** — a pure-Python `clemreg` core and a thin `napari-clemreg` widget package (§6).

Underpinning all of the above: **(0) stand up a test suite first**, as the safety net that lets the dependency bumps and the package split proceed without silently changing results (§0).

Repo state referenced: `krentzd/napari-clemreg`, `setup.cfg` version `0.2.1`, npe2 manifest (`napari.yaml`). Plugin already uses npe2, which removes the biggest napari-upgrade risk.

---

## 0. Testing foundation (start here)

Everything else in this plan touches behaviour-adjacent code: dependency bumps (numpy/open3d/probreg/torch can shift numerics), napari 0.6 API moves, and the split relocates code across package boundaries. Without a suite that captures current behaviour, a silent regression is indistinguishable from a successful refactor. So yes — build tests first. This is greenfield: the only test file (`_tests/test_dock_widget.py`) is **entirely commented out**, and `--cov=napari_autolign` measures a package that doesn't exist.

### 0.1 Three layers

1. **Deterministic unit tests (exact)** for pure functions whose output must not drift:
   - thin-plate-spline internals (`_make_warp`, `_make_L_matrix`, `_U`, `_calculate_f`) on tiny hand-checkable inputs
   - rigid/affine matrix construction (`_make_matrix_from_rigid_params`)
   - isotropic scaling factors (`_zoom_values`) and the isotropic→inverse round-trip
   - `get_pixelsize` metadata parsing — reuse the exact ImageJ description strings from `sample_data.py`
   - mask polygon rasterisation (`mask_area`, `mask_roi`)
   - **MoBIE affine conversion** (§3.3) — golden values for a known transform through ZYX→XYZ and nm→µm
   - invariants: identity transform ⇒ image unchanged (within interpolation tolerance)

2. **Characterisation / regression tests (with tolerance)** — pin what the pipeline does *today* on a fixed input as the oracle for the upgrade and split:
   - segmentation: foreground-voxel count / object count within tolerance
   - registration: apply a **known** affine to a synthetic point cloud and assert CPD recovers it — the cleanest oracle, no golden file needed
   - end-to-end quality: Dice/IoU between the warped FM segmentation and the EM segmentation, asserted above a threshold
   - probreg CPD, open3d sampling and MitoNet are **stochastic** — seed every RNG (numpy, torch, open3d) and still assert with tolerances, not equality. Some drift across dependency versions is expected; the tolerance is where you encode "acceptable".

3. **Widget / integration smoke tests (napari)** — replace the commented-out stub: each `magic_factory` widget builds under `make_napari_viewer`, the npe2 manifest loads, and the reader returns a valid layer-data tuple. These stay with `napari-clemreg` after the split (§6.4).

### 0.2 Test data & reproducibility

- Don't hit live Zenodo in unit tests. Add a **small committed synthetic fixture** — e.g. a blob volume plus a copy displaced by a *known* transform — for fast deterministic tests; the existing `notebooks/data/em_mask.tif` can seed one. Cache the real Zenodo sample via **`pooch` + checksum** for a handful of slow end-to-end tests marked `@pytest.mark.slow`.
- MitoNet/empanada is heavy (torch, optional GPU). Allow **injecting a precomputed EM segmentation** so the downstream sample→register→warp path is testable deterministically without running the network; mark full-network runs slow/optional.
- Seed all RNGs centrally in a fixture and record the seed in the golden metadata.

### 0.3 Tooling & CI

- `pytest`, `pytest-qt`, `pytest-cov`; consider `pytest-regressions` for managing golden arrays and (optionally) `hypothesis` for the math invariants.
- Fix `--cov=napari_autolign` → `--cov=napari_clemreg` immediately; set a coverage floor and ratchet upward.
- Capture the characterisation baseline on the **current** working environment (py3.9 + existing pins) *before* bumping anything — that baseline is what the upgrade is measured against. If the old environment is hard to reproduce, capture on first green run and treat it as v0.

### 0.4 How testing reshapes the roadmap

- The characterisation suite (layer 2) is written against current behaviour and then becomes the **acceptance gate** for §1 (deps), §2 (napari) and §6 (split).
- The unit tests (layer 1) are easiest to write for code that is *already* pure — which is most of the maths — so they double as the executable spec for the core `clemreg` API boundary (§6.2). Writing them first surfaces exactly which functions still demand napari layers and need de-napari-fying.
- Caveat: some array-level unit tests can't be written cleanly until the split exposes array-based entry points (many functions currently require napari layers). Bridge this by testing through the current public functions with in-test-constructed napari layers, and let the fully array-based unit tests land alongside the §6 extraction.

---

## 1. Python 3.11+

### 1.1 Packaging metadata (`setup.cfg`)

- `python_requires = >=3.7` → `>=3.11`.
- Replace the `3.7 / 3.8 / 3.9` classifiers with `3.11`, `3.12` (and `3.13` once deps confirm support).
- Bump `Development Status` from `2 - Pre-Alpha` to something honest (`4 - Beta`) if you're cutting a release alongside this.

### 1.2 Dependency pins — the real work

Current `install_requires` hard-pins everything with `==`, and most pins predate 3.11 wheels. These are the ones that block the upgrade or need loosening:

| Package | Current pin | Action / reason |
|---|---|---|
| `numpy` | `== 1.22.0` | No 3.11 wheels (numpy added cp311 in 1.23.2), and incompatible with modern napari/scikit-image. Move to `>=1.26,<3` (or `>=2` once probreg/open3d are 2.0-safe). **But this pin is forced from below by `empanada-dl` (see its row) — relaxing it here is not enough on its own.** |
| `magicgui` | `== 0.7.3` (listed twice) | Too old for napari 0.6.x. Bump to `>=0.8.3`; **remove the duplicate line**. |
| `scipy` | `== 1.10.1` | Loosen to `>=1.11`. |
| `scikit-image` | `== 0.21.0` | Loosen to `>=0.22` (0.24/0.25 for py3.12). |
| `open3d` | `== 0.17.0` | Main risk. 0.17 has no 3.11 wheels; needs `>=0.18`. Verify point-cloud API (`point_cloud_sampling.py`) still matches. |
| `probreg` | `== 0.3.6` | Depends on old open3d/transforms3d; test CPD + BCPD paths after the numpy/open3d bump. Highest-risk dependency — see §4. |
| `torch` | `== 2.0.1` | Bump to `>=2.2` for 3.11/3.12 wheels; keep `empanada-dl` happy. |
| `empanada-dl` | `== 0.1.7` | **The hard blocker for Python 3.11 — see §4a.** `empanada-dl` 0.1.7 (latest on PyPI, unchanged) itself pins **`numpy==1.22`**, which has no cp311 wheels. So `empanada-dl` transitively forces `numpy==1.22` and prevents any Python 3.11 install regardless of what clemreg's own pins say. Resolve via §4a before anything else in §1 can land. |
| `h5py`, `imageio`, `tifffile`, `matplotlib`, `tqdm`, `connected-components-3d`, `transforms3d` | `==` pins | Convert to `>=` lower bounds; these are low-risk. |
| `napari` | unpinned | Pin `>=0.6.6` (see §2). |

Recommendation: convert `==` to compatible-range pins (`>=x,<y`) so the plugin installs cleanly in a modern napari environment rather than fighting the solver. Consider moving packaging to `pyproject.toml` (PEP 621) while you're here, but that's optional.

### 1.3 `tox.ini` / CI

- `envlist = py{37,38,39}` → `py{311,312}` (add `313` when deps allow).
- Update the `[gh-actions]` python map.
- `.github/workflows/plugin_preview.yml` — bump the Python matrix.
- `commands = pytest ... --cov=napari_autolign` is a **bug**: the package is `napari_clemreg`, so coverage is measuring nothing. Fix to `--cov=napari_clemreg`.

### 1.4 Code-level 3.11 checks (low risk, but grep for)

- No use of removed stdlib (nothing obvious in the tree).
- `1 // point_freq` integer-division in `widget_components.run_point_cloud_sampling` — behaviour unchanged in 3.11, but worth a test.
- `__init__.py` hard-codes `__version__ = "0.1.0"` while `setup.cfg` says `0.2.1`. Wire version from metadata (`importlib.metadata.version`) to stop the drift.

---

## 2. napari 0.6.6+ compatibility

> **Update, checked 2026-09-21 — target version revised (see [§4a's AIoD update](#4a-empanada-dependency--critical-blocker--watch-item) and [issue #4](https://github.com/martlj/napari-clemreg/issues/4)):** the `napari<=0.6.6` ceiling below was driven by `empanada-napari`'s own pin, under the assumption clemreg would need to coexist with it in one environment. Since the recommended EM-segmentation path is now AIoD (`aiod_napari` + Segment-Flow, empanada isolated in its own conda env — see §4a), that ceiling no longer applies: `aiod_napari` itself declares `napari>=0.6` with **no upper bound**. **Target the latest stable napari (currently 0.9.1) instead of pinning to exactly 0.6.6.** The verification work below (private imports, magicgui, threading signals) is unchanged and still needs doing against whatever version is targeted — already partly de-risked: `napari_clemreg` imports and the full test suite passes under napari 0.9.1 in the `clemreg-py311-verify` env (§1 checked 2026-09-21), including the private `_link_layers` import (§2.1), which still resolves fine at 0.9.1. Note `aiod_napari` pins `numpy<2`, so an environment with both plugins installed will land on a numpy just under 2.0 (e.g. `1.26.x`) rather than clemreg's own full `<3` ceiling — not a blocker, just worth knowing.

Good news: the plugin is already npe2 (`napari.yaml` + `napari.manifest` entry point), so the npe1→npe2 deprecation that dominates 0.6 upgrades does not apply. The work is mostly private-API and magicgui.

### 2.1 Private / internal napari imports (highest risk)

The code reaches into `napari.layers.utils._link_layers` (underscore-private) in three files:

- `widgets/run_registration.py`: `from napari.layers.utils._link_layers import link_layers`
- `clemreg/widget_components.py`: `link_layers`
- `clemreg/warp_image_volume.py`: `from napari.layers.utils._link_layers import get_linked_layers`

Action: verify these still exist/behave in 0.6.6. `link_layers` has a public alias — `from napari.experimental import link_layers` — so switch to that. `get_linked_layers` has **no** public equivalent and stays a private underscore import; keep it but add a smoke test so a future break is caught, and isolate both behind a small helper module so there's one place to patch when napari moves them.

### 2.2 magicgui / `magic_factory`

- Both widgets use `@magic_factory(widget_init=on_init, ...)` with a large `specs` dict from `on_init_specs.py`. magicgui ≥0.8 changed some type-inference and `ForwardRef`/annotation handling. Test that every `specs[...]` widget still builds, especially the `pint`-quantity pixel-size fields (`moving_image_pixelsize_xy`, etc.) and the `Label` header widgets.
- `napari.qt.threading.thread_worker` / `GeneratorWorker` (used heavily in `run_registration.py`'s joiner pattern) is still supported in 0.6, but confirm the `worker.returned` / `worker.yielded` / `worker.finished` signal names are unchanged.
- Confirm nothing depends on the 0.6.0 removals: `CallDefault`, `as_dict`, `chunk_receiver`, old async, `color` in iterables, `running_as_bundle`. A grep of the tree shows none of these are used — low risk, but include in the verification pass.

### 2.3 Reader plugin

- `_reader.py` imports `tifffile` and PIL (`Image.open`). Fine, but confirm the returned layer-data-tuple shape still matches napari 0.6 (`[(data, meta, layer_type)]`).

### 2.4 Tests / Qt

- `tox.ini` deps pin `pyqt5`; napari 0.6 supports PyQt5/6 and PySide6. Keep pyqt5 for CI but confirm it resolves on 3.11/3.12.
- `_tests/test_dock_widget.py` — update to instantiate widgets via the new factory and assert they build under a `make_napari_viewer` fixture.

---

## 3. MoBIE project output option

### 3.1 What MoBIE gives you (and why it beats a flat TIFF)

A MoBIE project is a directory (`project.json` + one or more `dataset/` dirs with `dataset.json`) holding **sources** (image / segmentation / spots) as chunked, multiscale **OME-Zarr**, plus **views** that describe viewer state and `sourceTransforms`. Crucially, MoBIE views support **affine `sourceTransforms`** applied in physical space — MoBIE's own CLEM example project stores a registration as an affine named `"CLEMRegistration"`. This is the key to avoiding resampling.

Python API (`mobie_utils`, `pip install mobie_utils` / conda `mobie_utils`):

```python
import mobie
mobie.add_image(data_path, data_key,
                mobie_root, dataset_name, image_name,
                resolution, chunks, scale_factors,
                file_format="ome.zarr")
mobie.add_segmentation(...)   # for EM/FM segmentations
```

`resolution` is in µm (ZYX), `chunks` and `scale_factors` control the pyramid. `mobie.add_image` initialises the dataset/project if absent. There is also a `mobie.add_registered_source` (elastix-format transforms) and view-creation helpers for custom `sourceTransforms`.

### 3.2 Design: affine when possible, resample only for BCPD

CLEM-Reg exposes three registration algorithms (`clemreg/point_cloud_registration.py` + `widget_components.run_point_cloud_registration_and_warping`):

- **Rigid CPD** and **Affine CPD** → the transform is a single affine matrix. Today the code *resamples* the moving volume with `scipy.ndimage.affine_transform` (`_warp_image_volume_affine`). For MoBIE we can instead write the **raw moving image unchanged** as an OME-Zarr source and store the affine as a `sourceTransform` in the view. No resampling, no interpolation loss, tiny extra disk.
- **BCPD** (non-linear thin-plate-spline, `_warp_image_volume` / `_make_inverse_warp`) → MoBIE `sourceTransforms` only cover affine/crop/grid, **not** a dense non-linear field. So for BCPD we must still resample the moving volume (existing warp code), but write the **result as multiscale OME-Zarr** into the MoBIE project rather than a flat TIFF.

So the output branch is: affine/rigid → store transform; BCPD → resample then store voxels. Both produce a browsable multimodal project.

### 3.3 Matrix conversion (the fiddly bit)

- CLEM-Reg affine lives at `transformed_points.affine.affine_matrix` (a napari `Affine`), in **ZYX** voxel order.
- MoBIE/BDV `affine` parameters are a flat 12-element list in **XYZ** order and in **physical (µm)** units, following the BigDataViewer convention.
- Conversion therefore needs: (a) axis flip ZYX→XYZ, (b) incorporate the moving/fixed pixel sizes (the code already carries these as `pint` quantities → nanometres; MoBIE wants µm), and (c) flatten to the 12-value row-major form MoBIE expects. Build this as a small, unit-tested `clemreg_affine_to_mobie(affine, pxlsz_moving, pxlsz_fixed)` helper — it's the single highest-bug-risk piece and deserves a golden-value test against a known transform.

### 3.4 Suggested project layout produced

One dataset with sources:

- `em` (fixed image) — `add_image`
- `fm` / `fm_ch{c}` (moving image, one source per channel; the warp code already splits linked channel layers)
- `em-segmentation`, `fm-segmentation` — `add_segmentation` (optional, from the intermediate Labels layers)
- optionally the point clouds as `spots` sources (moving/fixed/transformed) for QC
- a `default` view that displays EM + FM together with the registration affine applied to the FM sources (affine mode) or with FM already in the EM frame (BCPD mode).

### 3.5 Where it plugs into the code

- New module `mobie_export.py` with `create_mobie_project(mobie_root, dataset_name, fixed_image, moving_image_list, transform, transform_type, pxlsz_fixed, pxlsz_moving, segmentations=None, points=None)`. It operates purely on numpy arrays + a transform + pixel sizes, so it belongs in the **`clemreg` core package** (§6), not the napari layer — build it there from the start if the split is on the roadmap, so it isn't moved twice.
- In `run_registration.make_run_registration`, the results currently flow through `_add_data(return_value)`, which adds warped Image layers to the viewer. Add:
  - a widget toggle `output_mode` (choices: `napari layers` (current) / `MoBIE project`) plus a `mobie_project_path` `FileEdit` (mirror the existing `save_json` / `save_json_path` show/hide pattern in `on_init`).
  - when `MoBIE project` is chosen, branch **before** the expensive BCPD warp: for affine/rigid, skip `warp_image_volume` entirely and pass the raw moving list + matrix to the exporter; for BCPD, run the warp as today but hand the arrays to the exporter instead of `viewer.add_layer`.
  - a separate `materialise_and_display: bool` checkbox, independent of `output_mode` (added 2026-09-21, per user request): when `MoBIE project` is chosen and this is checked, *also* run the resample/warp (even for affine/rigid, where the MoBIE path otherwise skips it) and add the result as a napari layer for immediate visual QC, in addition to writing the disk-efficient MoBIE project. Unchecked (the default for `MoBIE project` mode) keeps the no-resampling fast path. This only matters for affine/rigid — the BCPD path already resamples unconditionally, so for BCPD it's just "also add the layer napari already has to hand."
- The refactor is cleanest if `run_point_cloud_registration_and_warping` returns the transform object and the (optionally un-warped) moving images, letting the caller decide whether to resample. Today it always resamples inside `warp_image_volume_from_list`; introduce a `resample: bool` / output-mode param so the affine path can short-circuit.

### 3.6 Dependencies for MoBIE

- Add optional extra: `[options.extras_require] mobie = mobie_utils; zarr; ome-zarr`. Keep it optional so the core plugin install stays lean; import lazily inside `mobie_export.py` and raise a clear "pip install napari-clemreg[mobie]" error if missing.
- Note `mobie_utils` is most reliably installed via **conda-forge**; document that for users.

---

## 4. Risks & unknowns (verify before committing to versions)

1. **probreg + open3d + numpy** is the tightest knot. probreg 0.3.6 was built against old open3d/numpy; the CPD/BCPD math must be regression-tested on the sample dataset after bumping. If probreg won't move to numpy≥2, cap numpy at `<2` initially.
2. **empanada-dl** under new torch — confirm MitoNet weights load and `empanada_segmentation.py` runs (secondary to the numpy blocker in §4a).
3. **MoBIE non-linear limitation** — confirm current MoBIE spec (0.3.0) still has no dense-displacement `sourceTransform`; if that's ever added, BCPD could also skip resampling. As of now it can't.
4. **Affine convention** — the ZYX↔XYZ + physical-unit conversion (§3.3) must be validated visually in the MoBIE viewer against a known-good overlay, not just unit-tested.
5. **magicgui specs** — the `pint`-quantity pixel-size widgets are the most likely magicgui-upgrade casualty.

## 4a. empanada dependency — critical blocker + watch item

The MitoNet EM segmentation comes from `empanada-dl`, and it is the single hardest external constraint on this whole effort. State as checked (Aug 2026):

- **`empanada-dl` on PyPI is stuck at 0.1.7** (no newer release) and it **hard-pins `numpy==1.22`**. numpy 1.22 has no Python 3.11 wheels, so `empanada-dl` transitively **makes a Python 3.11 install impossible** — this, not clemreg's own pins, is what actually blocks §1. Its other pins are permissive (`torch>=1.10`, `requires_python>=3.7`); numpy is the problem.
- **Development has moved off the published core package.** The core repo `volume-em/empanada` is active (169 commits, README warns "breaking changes should be expected") but is **not being released to `empanada-dl` on PyPI**. Meanwhile `empanada-napari` keeps releasing (latest 1.2.4) with *looser* deps (`numpy>=1.22`, py3.10–3.13) — but it still uses the **npe1** `napari-plugin-engine` and caps **`napari<=0.6.6`**.
- ~~The napari≤0.6.6 cap across the EM-napari ecosystem reinforces targeting exactly napari 0.6.6 (§2) rather than chasing anything newer.~~ **Superseded, see the 2026-09-21 updates below and in §2**: this assumed coexistence with `empanada-napari` specifically; the recommended AIoD path (`aiod_napari`, which caps at nothing — `napari>=0.6`) removes that ceiling.

> **Update, checked 2026-09-21 (see [issue #5](https://github.com/martlj/napari-clemreg/issues/5)):** `empanada-dl` on PyPI is unchanged (still `0.1.7`, `numpy==1.22`). But **`volume-em/empanada` is not actually active** — its last code push was 2023-02-25; the README's "development is active" line is stale boilerplate, not a live status. The real movement happened in `volume-em/empanada-napari` instead, which *is* actively maintained (pushed within the last month) and has **vendored its own copy of the core inference code** directly in an `empanada/` subdirectory of that repo, with loose pins (`numpy>=1.22`, Python `>=3.10`) — no dependency on the stale `empanada-dl` package at all. This is effectively the "models out of the GUI, numpy-2-capable" core the section below hopes for; it already exists, just isn't published standalone. Licensing is an open discrepancy: `volume-em/empanada`'s `LICENSE` file is GPL-2.0, `empanada-dl`'s PyPI metadata self-declares BSD-3-Clause, and `empanada-napari`'s repo-root `LICENSE` (covering its vendored `empanada/` copy) is BSD-3-Clause — needs maintainer confirmation before relying on any of it. This supersedes "install from empanada git main" below (dead end, same vintage as the stale PyPI release) and reframes the outreach ask (§4a "Interim options", option 4).

### API compatibility & coexistence, verified 2026-09-21 (see [issue #5](https://github.com/martlj/napari-clemreg/issues/5))

**A straight swap looks real.** Every symbol `napari_clemreg/clemreg/empanada_segmentation.py` imports and calls (`config_loaders.load_config`, `data.VolumeDataset`, `inference.filters.{remove_small_objects,remove_pancakes}`, `inference.engines.PanopticDeepLabRenderEngine3d`, and the full `inference.patterns` set) exists in `empanada-napari`'s vendored `empanada/` core with a matching signature — including `update_trackers(rle_seg, index, trackers)`, exactly the 3-arg form clemreg's own code already calls (with a comment noting a prior API adaptation: `# Updated empanada only requires 3 arguments`). So `empanada_segmentation.py` likely needs **zero source changes** if the dependency is swapped. Not verified: actual segmentation-quality numerics against real EM data (needs a real model run, not just an import/signature check).

**Coexistence with `empanada-dl` is currently broken — reproduced directly, not inferred.** `empanada-dl` and `empanada-napari` are different PyPI distributions that **both claim to own the same top-level `empanada/` import path** (`pip show -f` lists `empanada/__init__.py` under both). Installing `empanada-napari` cleanly (modern numpy) and then `empanada-dl` in the same env: pip raised no error about the clash (it can't see it — only declared version deps, not file ownership) and silently downgraded numpy to `1.22.0` to satisfy `empanada-dl`'s pin, which broke scipy's compiled extensions — the same crash signature as the already-broken `napari-clemreg-311` local env, now understood to be this exact mechanism. **Practical implication:** if napari-clemreg keeps depending on `empanada-dl` while a user separately installs `empanada-napari` (plausible — it's the actively maintained, popular plugin people doing EM segmentation in napari would likely already have), their environment breaks, silently and install-order-dependently.

**This reframes the fallback options below into three concrete choices, not a vague "vendor or depend on":**

1. Depend on `empanada-napari` directly (swap `install_requires`) — simplest, API-compatible, but pulls in its entire unrelated dependency tree (mlflow, sphinx, flask, databricks-sdk, simpleitk, openpyxl, ...), forces napari `<=0.6.6`, and the collision above still bites if `empanada-dl` is present from anything else.
2. **Vendor just the needed empanada core files into clemreg's own namespace** (not `empanada/`) — the only option that *structurally* guarantees coexistence, since clemreg would no longer claim the shared `empanada` import name at all. Requires the licensing question resolved first.
3. Make EM segmentation an optional runtime integration — no hard dependency on any empanada distribution; `import empanada` at call time (whatever the user has) with a clear error if missing. Solves coexistence trivially, but shifts install UX onto the user.

**Recommendation: option 2.** It's the only one that solves coexistence structurally rather than by luck.

### Why the "models out of the GUI" work matters to us

An empanada effort that splits the models/inference core cleanly out of the GUI and **publishes a maintained, GUI-free, numpy-2 / py3.11-capable inference package is exactly what clemreg needs** — it would dissolve the numpy blocker above and give the `clemreg` core (§6) a clean dependency for EM segmentation. So this is on clemreg's critical path, not a nice-to-have.

### What to monitor

- New **`empanada-dl` releases on PyPI** (anything past 0.1.7) — specifically whether the `numpy==1.22` pin is relaxed and cp311/cp312 wheels appear. This is the trigger that unblocks §1.
- **`volume-em/empanada` repo** tags/releases and any refactor separating inference from training/GUI; the git version already has looser pins than the stale PyPI 0.1.7.
- Whether a new package name emerges for the split-out core, or `empanada-napari` formally re-depends on a modern `empanada-dl`.

### Interim options if empanada-dl doesn't move in time

Revised 2026-09-21 per the update above — option 1 (git main) is now known to be a dead end, and option 2 is retargeted at the actually-maintained source:

1. ~~Install from the empanada git main~~ — **dead end**: `volume-em/empanada` main hasn't moved since 2023-02-25, same vintage as the stale 0.1.7 PyPI release.
2. **Vendor (or depend on) the `empanada/` package bundled inside `volume-em/empanada-napari`** rather than the dormant `volume-em/empanada` core repo — this is the actively-maintained, loose-numpy-pin copy. **Confirm licensing with the maintainers first**: their repo-root `LICENSE` is BSD-3-Clause, but the original core repo's `LICENSE` is GPL-2.0 and `empanada-dl`'s PyPI metadata claims BSD-3-Clause — three different signals, needs an explicit answer, not an assumption.
3. Install `empanada-dl` with `--no-deps` and satisfy its runtime imports with clemreg-managed modern pins — quickest, but fragile and unsupported.
4. Coordinate directly with the empanada maintainers (volume-em) — revised ask: they've already modernised and vendored the core inside `empanada-napari`; ask them to either publish it standalone as a fresh `empanada-dl` release, or confirm its license so clemreg can depend on/vendor it directly. This is a smaller ask than reviving a dead package.

Recommendation: raise the revised ask with the empanada maintainers early (option 4) while keeping option 2 as fallback once licensing is confirmed; treat "modern empanada core available under a confirmed license" as an explicit dependency of the §1 milestone.

> **Update, checked 2026-09-21 — supersedes the recommendation above (see [issue #5](https://github.com/martlj/napari-clemreg/issues/5)):** Crick's AI-on-Demand (AIoD) infrastructure makes this whole dependency question moot. [`FrancisCrickInstitute/Segment-Flow`](https://github.com/FrancisCrickInstitute/Segment-Flow) (a Nextflow pipeline for deep-learning segmentation) runs empanada/MitoNet in its **own isolated per-model conda env** (`empanada-dl==0.1.6`, `numpy==1.26.4`), invoked as a subprocess — never in the same Python process or environment as napari-clemreg. That makes the namespace-collision problem above irrelevant, and moves the licensing question onto Segment-Flow rather than something clemreg vendors or distributes. Its companion [`FrancisCrickInstitute/aiod_napari`](https://github.com/FrancisCrickInstitute/aiod_napari) plugin is mature, actively maintained, **MIT-licensed**, and targets **Python 3.11/3.12 natively** — it already provides an "Inference" widget (point at images, pick model, press go, masks load back as napari Labels layers).
>
> Two integration options, in order of effort:
> - **A. Installed alongside (no code changes).** Users install `aiod_napari` alongside `napari-clemreg`, run its Inference widget with the empanada/MitoNet model to get an EM segmentation Labels layer, then feed that layer into clemreg's existing `Point Cloud Sampling` split-registration widget (already accepts a Labels layer). Effort: a docs section, ~1-2 hours.
> - **B. Tighter integration.** clemreg's own EM-segmentation widget shells out to Segment-Flow (`nextflow run FrancisCrickInstitute/Segment-Flow --model empanada --model_type mitonet ...`, via the `thread_worker` pattern already used elsewhere) instead of calling `empanada_segmentation()` in-process. ~1-3 days. Would permanently retire the `empanada-dl` dependency and #5 itself.
>
> Recommendation: do A now; treat B as the real long-term fix, ahead of vendoring (option 2 above) or reviving the maintainer outreach (option 4 above) — it outsources the dependency mess entirely rather than clemreg owning a vendored copy.

## 5. Suggested sequencing

Testing leads, because everything after it is measured against the baseline it captures.

1. Move the repo into the Crick org (§7, transfer preferred) and claim `clemreg` on PyPI — do this early so history/CI/releases accrue in the right place. Branch, then fix the `--cov` typo (§0.3) and version drift (§1.4) — cheap wins that unblock CI.
2. **Stand up the test suite (§0)** against the current environment: unit tests for the pure maths + a characterisation baseline (segmentation counts, known-transform recovery, end-to-end Dice) + widget smoke tests. This is the safety net for everything below.
3. Bump packaging (§1.1–1.3) and get a clean install on Python 3.11 in a napari 0.6.6 env; run the suite and adjust tolerances where dependency-driven numerical drift is acceptable.
4. Fix private-import and magicgui issues (§2) until the suite and a manual run pass on the sample data.
5. Add the MoBIE exporter as a self-contained, array-based module + optional extra (§3), affine path first (simpler, no resampling), BCPD path second; add the affine-conversion golden test and a tiny end-to-end that writes a project and runs `mobie.validate_project`.
6. Extract the `clemreg` core package and repoint `napari-clemreg` at it (§6); the suite from step 2 is the acceptance gate. Split the tests: pure tests to core, widget tests to the plugin.
7. Docs: update README/tutorial with the new output option, the `[mobie]` extra, and the two-package install.

## 6. Splitting into two packages: `clemreg` core + `napari-clemreg` widget

Goal: two installable distributions.

- **`clemreg`** (import name `clemreg`) — pure-Python pipeline: FM/EM segmentation, point-cloud sampling, registration, warping, MoBIE export. Operates on numpy arrays + lightweight metadata; **no napari, Qt or magicgui**. Enables headless/batch use (the existing `notebooks/clemreg_batch_mode.ipynb` is evidence this is already wanted), scripting, and fast tests.
- **`napari-clemreg`** (import name `napari_clemreg`) — the napari plugin: widgets, npe2 manifest, reader, sample data, `on_init_specs`, and thin adapters that unwrap layers → arrays, call `clemreg`, and rewrap results. Depends on `clemreg`.

### 6.1 Coupling assessment — why this is feasible

The numerics are already numpy/scipy/open3d/probreg based. napari types are used as **thin wrappers** — reading `.data`/`.metadata`/`.colormap`/`.blending`, constructing `Image`/`Labels`/`Points`, and `get_linked_layers`. So this is a boundary-relocation exercise, not a rewrite. Every `clemreg/` module except the empanada segmenter and `on_init_specs` currently imports napari, but almost always superficially.

Per-module disposition (`napari_clemreg/clemreg/`):

| Module | Napari usage today | Target |
|---|---|---|
| `warp_image_volume.py` — private math (`_make_warp`, `_warp_images`, `_make_inverse_warp`, `_trilinear_interpolation`, `_warp_image_volume_affine`) | none (pure numpy/scipy) | **core**, drop `Image`/`Points` type hints |
| `warp_image_volume.py` — public `warp_image_volume` / `..._from_list` | takes `Image`/`Points`, uses `.colormap`/`.blending`/`get_linked_layers`, builds `Image` | split: array warp → core; layer/link handling → widget |
| `point_cloud_registration.py` — `point_cloud_registration` | `PointsData` (= ndarray alias) | **core** (trivial) |
| `point_cloud_registration.py` — `_add_data(return_value, viewer)` | uses viewer | **widget** |
| `point_cloud_sampling.py` | takes `Labels`, reads `.data` | **core**, take array |
| `log_segmentation.py` | takes `Image`, reads `.data`; imports `thread_worker` (unused for the pure fn) | **core**, take array, drop the Qt import |
| `empanada_segmentation.py` | already array-based (`input=Fixed_Image.data`) | **core** as-is |
| `mask_roi.py` | takes `Shapes` crop mask, reads `crop_mask.data` | **core**, pass polygon vertices array + z range (widget extracts from `Shapes`) |
| `data_preprocessing.py` — `_make_isotropic`, `_zoom_values`, `get_pixelsize` | array/dict based | **core** |
| `data_preprocessing.py` — `make_isotropic`, `return_isotropic_image_list`, `_make_isotropic_v1` | take `Image`, mutate `.data`, use `get_linked_layers` | de-napari-fy: core takes arrays; channel/link assembly → widget |
| `widget_components.py` | heavy: `thread_worker`, `link_layers`, `Labels`/`Points`, magicgui | orchestration → a napari-free `run_pipeline(...)` in core; threading/layer glue stays in **widget** |
| `on_init_specs.py`, `sample_data.py`, `_reader.py`, `widgets/*`, `napari.yaml` | UI/plugin | **widget** |

### 6.2 Proposed napari-free API boundary (what the widget calls)

```python
# clemreg — no napari imports anywhere
segment_fm(array, sigma, threshold, filter=...) -> label_array
segment_em(array, axis) -> label_array
sample_point_cloud(labels, every_k, voxel_size, sigma) -> ndarray
register_point_clouds(moving, fixed, algorithm, max_iter, ...) -> Transform   # affine matrix OR TPS control points
warp_volume(array, transform, output_shape, order, ...) -> ndarray
run_clemreg(fm, em, params) -> Result        # one-shot headless pipeline
to_mobie_project(result, path, ...)          # §3
```

The widget's remaining job shrinks to: unwrap layers → arrays, drive the `thread_worker` orchestration, rewrap results into layers, add to viewer, and handle `get_linked_layers` (an inherently napari concept — core instead receives an explicit list of per-channel arrays). Represent pixel size as an explicit numeric type in core (e.g. a `PixelSize(z, y, x, unit)` dataclass); keep the `pint`-string parsing that `on_init` does in the widget.

### 6.3 Repo / distribution layout

Recommend a **monorepo with two packages** (src layout) initially — one issue tracker, shared CI, coordinated changes, no version-lockstep pain while APIs are still moving:

```
napari-clemreg/              # keep repo name + URL for continuity
  packages/
    clemreg/                 # -> distribution "clemreg"
      pyproject.toml
      src/clemreg/...
    napari-clemreg/          # -> distribution "napari-clemreg"
      pyproject.toml          #   depends on clemreg>=X,<Y
      src/napari_clemreg/...
```

Two separate repos are an option if release cadences genuinely diverge, but that's a decision to defer. Either way, move packaging to `pyproject.toml` (PEP 621) as part of this.

### 6.4 Packaging & tests

- **Core deps:** numpy, scipy, scikit-image, open3d, probreg, transforms3d, connected-components-3d, torch, empanada-dl, tifffile, h5py, tqdm (+ pint if unit handling stays in core). MoBIE as an extra: `clemreg[mobie]`.
- **Widget deps:** `clemreg`, `napari>=0.6.6`, `magicgui>=0.8.3`, `qtpy`. The npe2 entry point and `napari.yaml` live here.
- **Tests split:** pure-numpy tests move to core (fast, no Qt/xvfb — big CI win); widget tests stay with `napari-clemreg` (`pytest-qt`, `make_napari_viewer`).
- Update the batch notebook to `import clemreg` directly — the clearest demonstration of the headless payoff.

### 6.5 Backwards compatibility

Import paths change: `napari_clemreg.clemreg.*` → `clemreg.*`. For one release, keep shim re-exports in `napari_clemreg.clemreg` that import from `clemreg` and emit a `DeprecationWarning`, so anyone importing internals isn't broken immediately.

### 6.6 Where it sits in the roadmap

Do the split **after** the Python 3.11 / napari 0.6.6 compat work (§1–2) lands and tests pass — refactor known-good code rather than debugging two things at once. But build the MoBIE exporter (§3) directly in the core package so it isn't relocated later. Suggested revised order: §1–2 (modernise) → §3 affine-path MoBIE exporter written in a core-shaped module → §6 extract the core package and repoint the widget → §3 BCPD path + validation.

### 6.7 Risks specific to the split

- **Multi-channel / linked layers:** `get_linked_layers` semantics must be reproduced by having the widget assemble the channel list before calling core; get this wrong and multi-channel FM warps silently drop channels.
- **Unit handling:** decide once whether nm/µm conversion lives in core (recommended: core takes explicit numbers) or the widget; the current `pint`-string approach is widget-flavoured.
- **`sample_data`:** downloads + ImageJ-style metadata construction are napari-flavoured; keep in the widget or a napari-free `clemreg.data` submodule.
- **Two version streams** to keep in step via the `>=,<` pin from `napari-clemreg` on `clemreg`.

## 7. Repository & release strategy

Objective: the canonical repository should live in the **Crick GitHub org** for long-term maintenance, while preserving the full commit history (the characterisation baseline in §0 and `git blame` on the dependency pins both depend on it — do **not** start from a clean slate).

### 7.1 Getting the repo into the Crick org — three routes, in order of preference

1. **GitHub repository transfer (recommended).** If the current owner (`krentzd`) agrees to hand over the canonical repo, GitHub's *Transfer ownership* moves the repository — commit history, issues, PRs, releases, stars, watchers — into the Crick org in one step, and automatically sets up redirects from the old `krentzd/napari-clemreg` URL. CLEM-Reg originated at the Crick, so this is the natural home. Keep Daniel Krentzel as an admin/maintainer on the transferred repo. Requires admin on the source repo and repo-creation rights in the Crick org.
2. **Fork into the Crick org.** GitHub can fork into an org you belong to. Preserves history and the upstream link (easy to pull future upstream changes), but the fork is subordinate: issues/stars/releases stay on `krentzd/...`, and it's awkward to treat a fork as the canonical project. Use this only if `krentzd` wants to remain the upstream owner.
3. **Mirror / re-home (clean break).** Bare-clone and push to a fresh `crick/...` repo (optionally `git filter-repo` first). Preserves commit history but **loses** issues, PRs, stars and the fork relationship. Only if a deliberate break from the old repo is wanted; least preferred.

Recommendation: pursue transfer (1); fall back to fork (2) if transfer isn't agreed.

**Interim working model (current plan).** While the upstream owner (Daniel) is away: **fork `napari-clemreg` to the `martlj` account** and do the modernization and testing (§0–§2) there. When Daniel is back, open a **PR from the fork to upstream** to bring the canonical repo up to date, then transfer ownership to the Crick org. The transfer route, given a personal-account source, is **Daniel → `martlj` → `FrancisCrickInstitute`** (a personal repo can only be transferred by its owning account, and admin-collaborator rights do not include transfer; the two-hop puts the org-side step with a Crick member who has repo-creation rights). Treat the fork as a working copy only — keep *canonical* actions (the authoritative release tag, Zenodo archiving, the paper DOI — §7.7) on the upstream/eventual-Crick repo, never the fork.

### 7.2 Monorepo, so no repo split needed

Because the two packages live in one monorepo (§6.3), moving to the Crick org is a single repository operation — the `clemreg` / `napari-clemreg` split is a directory restructure inside it, not a second repo move. If separate repos are ever justified later, split with `git filter-repo` so each carries its relevant history.

### 7.3 PyPI naming & ownership

- `napari-clemreg` is **already published** on PyPI (the existing project) — add Crick maintainers as owners/collaborators on the PyPI project so releases don't depend on one person.
- `clemreg` is **available** on PyPI (checked) — claim it for the new core package before someone else does, even ahead of the split.
- **Ownership decision (recorded):** there is currently **no Francis Crick Institute PyPI organization or shared account**. So `clemreg` will be reserved under the **`martlj` personal PyPI account** for now. This does not lock the institute out — PyPI project ownership is a list of accounts, so once a Crick PyPI org (free for community/OSS, verified via a `crick.ac.uk` email) or shared role account exists, add it as an **Owner** and/or move the project under the org, then remove the personal owner. Revisit as part of the org move (§7.1).
- **Migration path to institute ownership (do later):** (1) create/join a "Francis Crick Institute" PyPI Organization or shared account; (2) add it as Owner on both `clemreg` and `napari-clemreg` (Manage project → Collaborators); (3) configure **Trusted Publishing** so releases come from the `FrancisCrickInstitute/napari-clemreg` GitHub Actions (no stored token); (4) remove the personal-account token/ownership once the org path works.
- Keep both under the same MIT licence; retain the original author's copyright line and add the Crick where appropriate.
- Consider PyPI **Trusted Publishing** (OIDC from GitHub Actions in the Crick org) so releases are automated and not tied to a personal token.

### 7.4 Post-move cleanup

- Update URLs everywhere: `setup.cfg`/new `pyproject.toml` `project_urls` and `url`, README badges, `docs/conf.py`, and any hard-coded `github.com/krentzd/...` links. The GitHub redirect covers old links but canonical references should point at the Crick org.
- Move/duplicate CI so branch protection, required checks and secrets are configured at the org level.
- Preserve the citation/DOI linkage (CLEM-Reg and MoBIE publications, Zenodo sample-data records) — keep `CITATION.cff`/README citation intact through the move.
- napari hub listing follows the PyPI project + `napari.yaml`; no change needed beyond the URL updates.

### 7.5 Where it sits in the roadmap

Do the org move **early** — ideally right after branching (§5 step 1), before large restructuring — so all subsequent history, CI and releases accrue in the Crick org rather than being migrated mid-flight. It's independent of the code work, so it can proceed in parallel with §0 testing.

Note: branching does not depend on the org move, and reserving the PyPI name (§7.6) does not depend on merging — the placeholder can be built and uploaded from a feature branch. Neither blocks the other.

### 7.6 Publishing the `clemreg` placeholder to PyPI

Goal: reserve the `clemreg` name with a `0.0.0` placeholder (built from `packages/clemreg/`, staged on `modernisation`). Reserving the name does **not** require merging the PR — build and upload can happen from the branch.

**Steps** (run from `packages/clemreg/`):

```bash
python -m build            # -> dist/clemreg-0.0.0.tar.gz and dist/clemreg-0.0.0-py3-none-any.whl
twine check dist/*         # validate metadata/README render; purely local, no upload
twine upload --repository testpypi dist/*   # optional rehearsal on test.pypi.org
twine upload dist/*        # real upload; when prompted: username = __token__, password = API token
```

Confirm at `https://pypi.org/project/clemreg/`.

**Account prerequisites (for the `martlj` account).** Before a token can be created: (1) the `martlj` account must exist on PyPI — a registration separate from GitHub, and the name must be free there; (2) **2FA must be enabled** — PyPI requires it on all accounts and *will not issue an API token until it is on*. Do these first, or the upload step blocks.

**Authentication.** Use an API token, not a password. Generate at PyPI → Account settings → API tokens → Add token. The first token must be *account*-scoped (a project-scoped token can't exist before the project does); after `clemreg` is created, issue a narrower project-scoped token for CI. Either paste the token when twine prompts, or store it in `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEI...            # account- or project-scoped token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEI...            # a separate TestPyPI token
```

Keep `~/.pypirc` out of git (it holds secrets). Better still, once the repo is org-hosted, move releases to **Trusted Publishing** (OIDC from GitHub Actions) so no long-lived token is stored anywhere (§7.3).

**Ownership.** The account that does the first real upload becomes the sole owner. Run it from the **org-owned/shared account**, not a personal one. If that account isn't ready, don't rush — the name is unknown to anyone until first upload, so reserving it a few days later is fine. Ownership is fixable after the fact (Manage project → Collaborators → add owners, remove yourself), but starting correct is cleaner.

**Reversibility — the one-way doors.** Most mistakes are recoverable (delete a release, fix metadata in the next version, adjust owners, or `yank` a release to soft-hide it). Two things are permanent: (1) an uploaded **filename/version can never be reused**, even after deletion — so a botched `0.0.0` just means moving on to `0.0.1` (the real core will be `0.1.0` regardless); (2) holding the name, which is the intended outcome. Nothing here can corrupt or forfeit the name. De-risk with `twine check` and a TestPyPI rehearsal before the real upload.

### 7.7 Versioning, paper release & Zenodo DOI

**Current state (checked):** `setup.cfg` says `0.2.1`, but the repo has **no git tags, no GitHub releases, and no code DOI** — only the sample *dataset* is on Zenodo (record 7936982). The software is published: Krentzel et al., *"CLEM-Reg: an automated point cloud-based registration algorithm for volume correlative light and electron microscopy"*, **Nature Methods, 2025**. There is no `CITATION.cff`.

**SemVer policy.** The project is pre-1.0, i.e. in the "major version zero" regime where the API is not yet declared stable and **breaking changes bump the minor, not the major**:

- Modernization PR (Python 3.11 + napari 0.6.6 + dependency overhaul, no split yet): `0.2.1 → 0.3.0`. Breaking for the install environment, but the public widget/API surface is unchanged, so a minor bump is correct — **not** a major (1.0) bump.
- Package split (§6), which changes import paths `napari_clemreg.clemreg.* → clemreg.*`: another breaking change → `0.4.0` while still pre-1.0.
- **Declaring `1.0.0`** is a *commitment to API stability*, not a measure of change size. Don't do it mid-restructure; the natural moment is once the two-package split has settled — a good version to anchor the project's stable era.
- After the split the two distributions version **independently**: `clemreg` begins real releases at `0.1.0` (after the `0.0.0` placeholder, §7.6); `napari-clemreg` continues its own line.

**Paper-associated release (do on the canonical repo, with Daniel).** Because nothing is tagged, create the release that represents the published code: identify the commit matching the paper, tag it (e.g. `v0.2.1`), and cut a GitHub Release. This is the authoritative historical record, so it belongs on the upstream/eventual-Crick repo — **not the `martlj` fork**. Overdue but valuable, and best handled alongside Daniel when he's back.

**Zenodo archiving.** Use the **GitHub–Zenodo integration** (connect the repo on Zenodo, enable it, then each GitHub Release auto-mints a versioned DOI plus a permanent *concept DOI* resolving to the latest). Enable it on the **canonical repo, not the fork** — Zenodo archives whichever repo is connected, so a fork would produce a DOI pointing at a personal copy. A manual `.zip` upload also works for a one-off DOI, but the integration is reproducible for future releases. Then:

- Add a **`CITATION.cff`** to the repo (renders a "Cite this repository" button on GitHub) carrying the Nature Methods citation and, once minted, the Zenodo concept DOI.
- Put the concept DOI badge in the README next to the paper citation.
- Keep this distinct from the sample-data Zenodo record (7936982), which archives data, not code.

## 8. Sample data & caching

Added 2026-09-21, per user request. Two gaps, both grounded in the current code rather than assumed:

### 8.1 Cache the Zenodo sample data and MitoNet model weights

**Current state, checked against the actual code:** `sample_data.py`'s `make_sample_data()` calls `skimage.io.imread(url, plugin='tifffile')` directly on two Zenodo URLs (record 7936982, one EM tiff + one 4-channel FM tiff) — this re-downloads **both files on every call**, straight into memory, with no caching or checksum verification at all. Separately, `empanada_segmentation.py`'s `load_model_to_device` already does its own ad hoc caching for the MitoNet checkpoint: it resolves a cache directory via `torch.hub.get_dir()` (PyTorch's own convention: `$TORCH_HOME/hub`, else `$XDG_CACHE_HOME/torch/hub`, else `~/.cache/torch/hub`), checks `os.path.exists(cached_file)` before downloading, and skips the download if already cached. Functional, but no checksum verification, and it's a second, uncoordinated caching scheme separate from the sample data.

**Best practice for this (scientific-Python / napari ecosystem convention): [`pooch`](https://www.fatiando.org/pooch/).** It's what napari itself and most napari plugins already use for downloadable sample data — `pooch.create()` with a registry of known files + SHA256 hashes, cache directory via `pooch.os_cache("napari-clemreg")` (resolves the correct per-OS location automatically via `platformdirs` under the hood: `~/.cache/napari-clemreg` on Linux, `~/Library/Caches/napari-clemreg` on macOS, `%LOCALAPPDATA%\napari-clemreg\Cache` on Windows). Gives: no repeat downloads, checksum verification (catches corrupted/interrupted downloads silently reused otherwise), a predictable/discoverable/clearable cache location, and matches what contributors coming from other napari plugins will already expect.

**Open decision, not resolved here:** whether to also move the MitoNet checkpoint caching onto `pooch` for one unified cache/verification story, or leave `empanada_segmentation.py`'s existing `torch.hub`-based caching as-is (it already works, needs no new dependency, and matches standard PyTorch-tooling convention). Either is defensible; worth an explicit call before implementing rather than defaulting silently.

### 8.2 Bundle the existing EM segmentation mask as sample data, for GPU-less users

**Already in the repo:** `notebooks/data/em_mask.tif` — a precomputed EM segmentation, ~971 KB, already TIFF-internally-compressed (deflate), shape `[106, 1750, 1484]`, 8-bit. Currently only used in `notebooks/clemreg_batch_mode.ipynb` (loaded as a `Labels` layer there). It's the only existing compressed EM mask found anywhere in the repo.

**Add it as a second `napari.yaml` `sample_data` entry**, alongside the existing `benchmark_dataset.1` (raw EM/FM images), loading `em_mask.tif` directly as a `Labels` layer. This lets users without a GPU — who can't run the empanada/MitoNet EM-segmentation step at all — still exercise the rest of the pipeline (point-cloud sampling → registration → warping) starting from this precomputed mask. Since the file is small and already in the repo, bundle it directly via `[options.package_data]` (no download needed) rather than adding it to the Zenodo-hosted sample-data set — simpler, and it's already sitting there unused outside the one notebook.

## Sources

- napari 0.6.0 release notes (removed APIs): https://napari.org/stable/release/release_0_6_0.html
- napari 0.6.4 release index: https://napari.org/0.6.4/release/index.html
- MoBIE Python tools (README, `add_image` / CLI, formats): https://github.com/mobie/mobie-utils-python
- MoBIE specification (sources, views, affine sourceTransforms, OME-Zarr, spec 0.3.0): https://mobie.github.io/specs/mobie_spec.html
- MoBIE CLEM example project (affine "CLEMRegistration" view): https://github.com/mobie/clem-example-project
- napari linked layers (public `napari.experimental.link_layers`): https://napari.org/gallery/linked_layers.html
- Repo under change: https://github.com/krentzd/napari-clemreg
- empanada core library (active, "breaking changes expected"): https://github.com/volume-em/empanada
- empanada-dl on PyPI (0.1.7, pins numpy==1.22): https://pypi.org/project/empanada-dl/
- empanada-napari on PyPI (1.2.4, napari<=0.6.6, npe1): https://pypi.org/project/empanada-napari/
- PyPI Organization accounts (free for community projects): https://docs.pypi.org/organization-accounts/
- CLEM-Reg paper: Krentzel et al., "CLEM-Reg: an automated point cloud-based registration algorithm for volume correlative light and electron microscopy", Nature Methods (2025) — per the citation in the repo README (verify the exact DOI on the canonical record).
