# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Remotes

This is a personal fork (`martlj/napari-clemreg`) of `krentzd/napari-clemreg`. `origin` is the fork; `upstream` is the original. Push work to `origin`; only pull from `upstream` to sync in changes from the original project.

## Commands

Install the plugin locally (Python 3.9 recommended, per README):

```
conda create -n clemreg_env python=3.9
conda activate clemreg_env
pip install "napari[all]"
pip install -e .
```

Run the test suite (uses tox, matching CI's per-Python/per-OS matrix):

```
tox
```

Run tests directly with pytest against the active environment:

```
pytest -v --color=yes --cov=napari_clemreg --cov-report=xml
```

Run a single test file or test:

```
pytest napari_clemreg/_tests/test_warp_image_volume.py
pytest napari_clemreg/_tests/test_warp_image_volume.py::test_name
```

Note: `napari_clemreg/_tests/test_dock_widget.py` is currently a commented-out placeholder (from the cookiecutter template) — there is no active widget-level test coverage yet, but unit tests for the pure math in `clemreg/` exist under `napari_clemreg/_tests/` (see §0 of the modernisation plan below).

**macOS: torch + napari can segfault on import** (two OpenMP runtimes loaded in one process — torch's bundled `libiomp5` vs. the conda-forge `libomp` napari's stack pulls in). `napari_clemreg/_tests/conftest.py` sets `KMP_DUPLICATE_LIB_OK=TRUE` and `OMP_NUM_THREADS=1` before those imports, so pytest runs are unaffected; if you import `napari_clemreg` (or `torch` then `napari`) directly in a script or REPL, set those env vars first. No-op on Linux CI.

There are pre-existing local conda envs for this repo:
- `clemreg_env` (python 3.9) — matches the **pre-#3** `setup.cfg` pins the repo actually ships and installs cleanly today (has `napari-clemreg` installed editable from this checkout via `pip install -e . --no-deps`). Use this for day-to-day work and for the §0 characterisation baseline, since `setup.cfg`'s `python_requires` now says `>=3.11` but a real `pip install` still can't resolve on 3.11 until #5 (`empanada-dl`) is unblocked.
- `clemreg-py311-verify` (python 3.11) — built to empirically verify the #3 (Python 3.11) dependency bump. Has every `setup.cfg` dependency installed at its latest available version **except `empanada-dl`** (deliberately excluded, since it's the #5 blocker) — `napari-clemreg` is installed editable via `pip install -e . --no-deps` here too. The full test suite passes here (30 passed, 1 xfailed) as of the #3 work. Reuse this env rather than rebuilding it for further Python 3.11 verification; extend it if you need to test a newer pin.
- `napari-clemreg-311` and `napari-clemreg` (no suffix) — both broken (numpy/scikit-image ABI mismatches from earlier, less careful upgrade attempts). Not worth fixing; superseded by `clemreg-py311-verify`.

**macOS: open3d's wheel needs `libusb`** (`brew install libusb`) or it fails to import with a `dlopen`/`Library not loaded` error. Not a napari-clemreg issue — open3d's compiled binary links against it unconditionally.

## Architecture

The plugin has two layers under `napari_clemreg/`:

- **`widgets/`** — thin `magicgui`-based napari GUI entry points (`run_registration.py`, `fixed_segmentation.py`, `moving_segmentation.py`, `point_cloud_sampling.py`, `registration_warping.py`). These are registered as napari commands/widgets in `napari_clemreg/napari.yaml`, the plugin manifest read by napari's plugin engine (npe2). Widget functions handle UI wiring, parameter forms (`clemreg/on_init_specs.py` defines widget layout specs), and threading via napari's `thread_worker`/`GeneratorWorker`.
- **`clemreg/`** — the actual algorithm/glue code, napari-independent aside from layer types and threading helpers:
  - `widget_components.py` — glue functions (e.g. `run_moving_segmentation`) called by the widgets, chaining together the pipeline steps below.
  - `log_segmentation.py`, `empanada_segmentation.py` — FM (Laplacian-of-Gaussian) and EM (MitoNet/empanada-dl) segmentation.
  - `mask_roi.py`, `data_preprocessing.py` — ROI masking and isotropic resampling.
  - `point_cloud_sampling.py`, `point_cloud_registration.py` — point-cloud extraction from segmentations and registration (Rigid/Affine CPD, BCPD via `probreg`).
  - `warp_image_volume.py` — warps the moving image volume using the resulting point-cloud transform.
  - `sample_data.py` — provides the built-in napari sample dataset.
- `napari_clemreg/_reader.py` — napari file reader hook (`.tif`/`.tiff`, directories).

The full pipeline (EM segmentation → FM segmentation → point-cloud sampling → point-cloud registration → image warping) can be run end-to-end via the `Run registration` widget, or each stage run independently via the numbered "split registration" widgets — both paths call into the same `clemreg/` functions.

### In-progress package split

`packages/clemreg/` is a placeholder for extracting the `clemreg/` core (segmentation, point-cloud sampling, registration, warping, plus a planned MoBIE export) into a standalone, napari-free PyPI package (`clemreg`, requires Python ≥3.11, built with hatchling — separate from the root package's setuptools/Python ≥3.7 config). It currently only reserves the PyPI name (version `0.0.0`, no functionality). The napari plugin in this repo will eventually depend on that core package rather than containing the algorithms directly. This is being tracked on the `feature/split-clemreg-core` branch.

The full plan (testing foundation, Python 3.11 + napari 0.6.6 upgrade, MoBIE export, the core/widget split, and the repo/PyPI/release strategy) is in [docs/napari-clemreg-modernisation-plan.md](docs/napari-clemreg-modernisation-plan.md) — read it before starting work related to any of those areas.

## Packaging

The root package (`napari-clemreg`, the napari plugin) is defined via `setup.cfg`/`setup.py` (no `pyproject.toml`). `python_requires = >=3.11` as of the #3 modernisation work, with most pins loosened to `>=` per the plan's §1.2 table. **`empanada-dl` stays hard-pinned at `==0.1.7`** (its own `numpy==1.22` pin blocks Python 3.11 installs entirely — see [issue #5](https://github.com/martlj/napari-clemreg/issues/5)), so `pip install napari-clemreg` will not actually resolve on Python 3.11 until that's unblocked, even though the rest of the stack (verified empirically in `clemreg-py311-verify`, see above) already works. Heavy dependencies (`napari`, `torch`, `open3d`, `probreg`) make installs slow.
