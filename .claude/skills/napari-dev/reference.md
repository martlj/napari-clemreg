# napari plugin reference

Checked against napari 0.9.2, npe2 0.9.0, superqt 0.8.2 and the plugin template on 2026-10-04. Source-code facts are given as `napari/<file>:<function>` in the installed package; re-check them when the napari version changes.

| Topic | Source |
|---|---|
| Best practices | https://napari.org/stable/plugins/building_a_plugin/best_practices.html |
| First plugin, contribution guides | https://napari.org/stable/plugins/building_a_plugin/first_plugin.html, https://napari.org/stable/plugins/building_a_plugin/guides.html |
| Debugging, notifications | https://napari.org/stable/plugins/building_a_plugin/debug_plugins.html |
| Manifest / contributions reference | https://napari.org/stable/plugins/technical_references/manifest.html, https://napari.org/stable/plugins/technical_references/contributions.html |
| Testing | https://napari.org/stable/plugins/testing_and_publishing/test.html |
| Publishing, hub listing | https://napari.org/stable/plugins/testing_and_publishing/deploy.html, https://napari.org/stable/plugins/testing_and_publishing/hub_customization.html |
| Widget communication | https://napari.org/stable/plugins/advanced_topics/widget_communication.html |
| Threading | https://napari.org/stable/guides/threading.html |
| Plugin template (copier) | https://github.com/napari/napari-plugin-template (`template/`) |
| Hub | https://napari-hub.org, built by https://github.com/napari/hub-lite from https://github.com/napari/npe2api |

## Version notes

| Version | What changed for plugins |
|---|---|
| napari 0.6.0 / 0.7 | require Python ≥ 3.10 |
| napari 0.6.2 | public `viewer.window.dock_widgets` (read-only, inner widgets); private `_dock_widgets` now warns ([widget communication](https://napari.org/stable/plugins/advanced_topics/widget_communication.html)) |
| napari 0.8 / 0.9 | require Python ≥ 3.11 (PyPI metadata); 0.9 has *Help → Show logs* for records reaching the root logger (`napari/_qt/_qapp_model/qactions/_help.py`) |

## Dependencies and layout

**Single distribution** (template layout, plus an optional headless core package):

```toml
[project]
name = "napari-example"                  # = manifest name = entry-point key
dynamic = ["version"]                    # setuptools_scm / hatch-vcs, or a static version you bump
description = "One sentence for PyPI and the hub"
readme = "README.md"                     # the hub's description page
requires-python = ">=3.11"               # not below what your napari floor needs
license = "MIT"                          # PEP 639 SPDX expression
license-files = ["LICENSE"]
authors = [{ name = "…", email = "…" }]
classifiers = [
    "Framework :: napari",               # required for the hub and plugin manager
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.11",
    "Topic :: Scientific/Engineering :: Image Processing",
]                                        # no "License ::" classifier with a licence expression
dependencies = [
    "numpy", "qtpy", "superqt",          # everything imported at runtime
    # "napari>=0.6",                     # only if napari is imported at runtime; floor = oldest version CI tests
]

[project.optional-dependencies]
all = ["napari[all]"]                    # napari + default Qt for a fresh environment

[dependency-groups]
dev = ["pytest", "pytest-cov", "pytest-qt", "napari[qt]"]

[project.urls]
"Bug Tracker" = "https://github.com/<org>/<repo>/issues"
"Documentation" = "https://github.com/<org>/<repo>#readme"
"Source Code" = "https://github.com/<org>/<repo>"   # the hub takes the GitHub link from this or Homepage
"User Support" = "https://forum.image.sc/tag/napari"

[project.entry-points."napari.manifest"]
napari-example = "napari_example:napari.yaml"
```

- **napari itself.** The template lists no napari and says it *"can be included in dependencies if napari imports are required"*; the best-practices page says *"Don't require napari if not necessary"* and use string / `TYPE_CHECKING` annotations ([template pyproject](https://github.com/napari/napari-plugin-template/blob/main/template/pyproject.toml.jinja), [best practices](https://napari.org/stable/plugins/building_a_plugin/best_practices.html#best-practice-napari-type)). If you import `napari.qt.threading`, `napari.utils.notifications` etc. at runtime, list plain `napari` with a floor only: a floor above the user's installed napari makes pip *upgrade* napari, which can break conda environments.
- **Qt.** Never PyQt5/PyQt6/PySide2/PySide6, `napari[all]` (includes PyQt6) or `napari[qt]` in base dependencies: the plugin manager installs base dependencies only, and mixing pip and conda Qt breaks environments ([best practices](https://napari.org/stable/plugins/building_a_plugin/best_practices.html)). napari already depends on `qtpy`, `superqt`, `magicgui` (napari METADATA), but list what you import.
- **Dev tools** go in `[dependency-groups] dev` (template; `pip install -e . --group dev` needs pip ≥ 25.1) or a `dev` extra.
- **PEP 639.** `license = "<SPDX>"` + `license-files` needs setuptools ≥ 77 (template pins `setuptools>=77.0.3`) or hatchling ≥ 1.27; don't combine it with `License ::` classifiers (PEP 639 tells tools to reject that). The hub shows it correctly: npe2api fills its `license` field from `License-Expression` (checked: `napari-animation` has PyPI `license=None`, `license_expression="BSD-3-Clause"`, npe2api `license="BSD-3-Clause"`; hub-lite `fetch_napari_data.py:get_license`).
- **Wheels.** Avoid dependencies without wheels for all OSes ([best practices](https://napari.org/stable/plugins/building_a_plugin/best_practices.html)). State big downloads (torch) in the README.
- **Packaging hygiene.** Don't ship a top-level `tests` package; restrict the sdist to what users need; check the manifest is in the wheel (setuptools needs `package-data` `"*" = ["*.yaml"]`, as in the template; hatchling includes package files). Build releases in CI from a clean checkout.
- **Build backend.** Either works: the template's setuptools (`setuptools>=77.0.3` plus `setuptools_scm`, `package-data` for `*.yaml`), or hatchling ≥ 1.27 (plus `hatch-vcs`; includes package files automatically). Pick one per distribution and stay with it.
- **Versioning.** Template: setuptools_scm writing `_version.py`; napari: *"The 'best' versioning and deployment workflow is the one you will actually use!"* ([version management](https://napari.org/stable/plugins/virtual_environment_docs/3-version-management.html)).

**Two distributions** (plugin + reusable headless core):

- `core-example` (import package `example`): no napari, Qt or `Framework :: napari`; no `napari.manifest` entry point. Usable from scripts, notebooks, other GUIs.
- `napari-example` (import package `napari_example`): owns the manifest, entry point and classifier; `dependencies = ["core-example>=1.2,<2", "qtpy", "superqt", …]` (plus `napari` if imported). Use a compatible range, never `==`, so users can take core bug-fix releases.
- Release order: publish the core first, then the plugin that needs it; bump the plugin's lower bound when it starts using new core API. The hub lists only the plugin.
- CI: test the core alone in a Qt-free job (proves no napari/Qt dependency); test the plugin against the core's lowest supported version and its latest (or `main`). In a monorepo, give each distribution its own `pyproject.toml` and tag scheme (e.g. `core-v1.2.0`, `napari-v0.3.0`).
- A test that imports the core in a subprocess and asserts `napari`/`qtpy` are not in `sys.modules` is useful in both layouts.

**conda-forge.** Optional and encouraged for binary dependencies; the plugin manager installs from PyPI and conda-forge ([deploy](https://napari.org/stable/plugins/testing_and_publishing/deploy.html)). Generate a recipe with grayskull and submit to `conda-forge/staged-recipes` (https://conda-forge.org/docs/maintainer/adding_pkgs/). conda-forge splits `napari-base` (required deps only) from `napari` (`conda-forge/napari-feedstock` `recipe.yaml`); a recipe that needs napari should not pull a Qt binding either.

## napari.yaml

```yaml
name: napari-example                 # = distribution name
display_name: Example                # 3–90 chars (npe2 manifest/_validators.py:display_name); shown on the hub
visibility: public                   # hidden = installable, not in search
categories: ["Image Processing"]     # fixed list: npe2 manifest/schema.py:Category
contributions:
  commands:
    - id: napari-example.make_widget
      title: Open the example widget
      python_name: napari_example._widget:ExampleWidget
    - id: napari-example.get_reader
      title: Open example files
      python_name: napari_example._reader:napari_get_reader
  widgets:
    - command: napari-example.make_widget
      display_name: Example widget    # menu shows "Example widget (Example)"
  readers:
    - command: napari-example.get_reader
      filename_patterns: ["*.exm"]
      accepts_directories: false
```

- **Private modules.** Follow the template: `_widget.py`, `_reader.py`, `_writer.py`, `_sample_data.py`, referenced by `python_name`; `__init__.py` exposes `__version__` and an explicit `__all__`. The public API is `__init__.py` plus the manifest (template `src/{{module_name}}/`).
- **Widgets.** `python_name` can be a `QWidget` subclass, a magicgui `Widget`/`Container`, a `magic_factory`, or any function with `autogenerate: true` (npe2 `contributions/_widgets.py`). napari injects the viewer into a parameter named `napari_viewer` or annotated `napari.viewer.Viewer` (string works). Through `add_plugin_dock_widget` it is a `PublicOnlyProxy`; through the Plugins menu it is the real viewer (`napari/_qt/qt_main_window.py:_instantiate_dock_widget` vs `napari/_qt/_qplugins/_qnpe2.py:_toggle_or_get_widget`), so don't rely on either.
- **Menus.** Widgets/commands can also appear in napari menus via `contributions.menus` (e.g. `napari/layers/segment`, as in the template manifest).
- **Readers.** The command receives a path (or list) and must return a callable *or `None`* quickly, without reading the file; returning `None` lets napari try the next reader. The callable returns a list of `(data, kwargs, layer_type)` tuples. Narrow `filename_patterns`; `["*"]` makes you a candidate for every file. Readers are for formats that map to layers.
- **Writers.** `layer_types` constraints like `image`, `image*`, `labels+`; empty `filename_extensions` means any extension; return the list of written paths (npe2 `contributions/_writers.py`).
- **Sample data.** `key` + `display_name` + a `command` returning layer-data tuples, or a `uri` opened by a reader (npe2 `contributions/_sample_data.py`). Download lazily into the cache folder.
- **Tools.** `npe2 validate <name-or-path> [--imports] [--debug]`; `--imports` imports every `python_name` (`npe2/cli.py:validate`). `npe2 fetch <name>` shows a published plugin's manifest; `npe2 compile <src>` builds a manifest from `@npe2.implements` decorators. npe1 (`napari_plugin_engine` hooks) is legacy: write npe2 only.

## Widget lifetime and clean-up

What napari 0.9.2 does (`napari/_qt/widgets/qt_viewer_dock_widget.py`, `napari/_qt/qt_main_window.py`; confirmed by running it with PyQt6):

| User action | What happens to your widget |
|---|---|
| Title-bar *hide* button, or toggling it in the Plugins menu | Dock hidden (`QDockWidget.close()`); widget kept; reopening shows the same instance. |
| Title-bar *close* (X) → `destroyOnClose` → `remove_dock_widget` | `widget.setParent(None)`, dock removed and `deleteLater()`d. Widget stays alive (no `destroyed`), gets `QEvent.ParentChange` with `parent() is None`. Reopening creates a new instance. |
| Closing the viewer window | Main window has `WA_DeleteOnClose`; the widget is deleted as a child: `destroyed` fires, no `ParentChange`. Workers registered as tasks are cancelled first (`_QtMainWindow.closeEvent`). |
| Quitting the app | Windows close; `QApplication.aboutToQuit` fires only if napari owns the app (not in IPython/Jupyter, `napari/_qt/qt_event_loop.py:quit_app`); deferred deletes may never run. |

napari has no public "widget closed" hook. The inner widget gets no `closeEvent` for X or viewer close, and `hideEvent` also fires for the hide button and when the window is minimised or hidden. `destroyed` connected to a method of the widget itself never runs (the Python wrapper is gone); connected to a plain function or a method of another object it does. So keep releasable resources in a small non-widget object:

```python
class _Resources:
    """Workers, temporary files and global connections owned by one widget."""

    def __init__(self):
        self.workers = []
        self.released = False

    def release(self, *_):
        if self.released:
            return
        self.released = True
        for worker in self.workers:
            worker.quit()               # generator workers stop at the next yield
        if any(worker.is_running for worker in self.workers):
            return                      # each worker calls remove_files() when it finishes
        self.remove_files()

    def remove_files(self, *_):
        ...  # idempotent: delete temp files, disconnect global/viewer signals, close handles

    def add_worker(self, worker):
        self.workers.append(worker)
        worker.finished.connect(self.after_worker)

    def after_worker(self, *_):
        if self.released and not any(w.is_running for w in self.workers):
            self.remove_files()     # the last worker to end after release() cleans up


class ExampleWidget(QWidget):
    def __init__(self, napari_viewer: "napari.viewer.Viewer"):
        super().__init__()
        self._resources = _Resources()
        self.destroyed.connect(self._resources.release)           # viewer closed
        QApplication.instance().aboutToQuit.connect(self._resources.release)

    def event(self, event):
        if event.type() == QEvent.Type.ParentChange and self.parent() is None:
            self._resources.release()                              # X button
        return super().event(event)
```

- Order matters: stop workers first, delete their files last. A function worker can't be interrupted, so give long jobs a stop flag or make them generators, and let the worker's `finished` (or a `finally` in the job) call `remove_files()` when it ends after `release()`.
- `ParentChange` → `None` relies on napari un-parenting in `remove_dock_widget` (verified in 0.9.2; re-check on upgrades). It is plain Qt API, no napari private access.
- Never delete results the user hasn't saved on close: keep them on disk, or ask first.
- Disconnect from `viewer.layers.events`/`viewer.events` in `release` if you connected lambdas or partials (bound methods are held weakly by napari's event system and psygnal).

## Threads

- `thread_worker` / `create_worker` from `napari.qt.threading`. Function workers can't be interrupted; generator workers stop at the next `yield` after `quit()` ([threading guide](https://napari.org/stable/guides/threading.html)). A core with its own callback/stop flag is fine when it keeps the core napari-free.
- **Errors.** Unless `ignore_errors=True` or `connect={"errored": …}` is passed *at creation*, superqt connects a `reraise` slot to `errored` (`superqt/utils/_qthreading.py:create_worker`). The re-raised exception reaches napari's `sys.excepthook` → `notification_manager.receive_error` → an error notification with a traceback button (when napari runs the event loop: `napari` CLI or `napari.run()`, `napari/_qt/qt_event_loop.py:run`). Connecting your own handler later with `worker.errored.connect(...)` adds to it, so the user sees two reports. In pytest-qt, the re-raise fails the test.
- **Task registry.** If a viewer exists when the worker is created, napari registers it with `cancel_callback=worker.quit`; closing the window with pending/busy workers asks for confirmation, then cancels them (`napari/_qt/qthreading.py:create_worker`, `_QtMainWindow.closeEvent`). Progress bars: `progress=True` or `{"total": n}`.
- Connect `returned`/`yielded`/`errored` to bound methods of the widget, so a deleted widget isn't called. Only touch widgets and layers on the main thread; `NAPARI_ENSURE_PLUGIN_MAIN_THREAD=1` makes the viewer proxy raise on off-thread access (`napari/utils/_proxies.py`), useful in tests.
- **Dask in workers.** `dask.compute(..., callbacks=())` (or `arr.compute(callbacks=())`). With the default `callbacks=None`, dask temporarily swaps the process-global `Callback.active` set (`dask/callbacks.py:local_callbacks`), racing napari's slicing, which registers its cachey cache there (`napari/utils/_dask_utils.py:configure_dask`).
- Never block the event loop (`time.sleep`, `worker.await_workers()`, `.compute()` of big arrays in a slot).

## Messages and logging

- Breaking problem: raise; handled surprise: `warnings.warn`; pop-ups: `napari.utils.notifications.show_info/show_warning/show_error` ([debugging page](https://napari.org/stable/plugins/building_a_plugin/debug_plugins.html)). Warnings and exceptions are routed to notifications by napari's hooks (`napari/utils/notifications.py:NotificationManager.install_hooks`).
- Exceptions raised in your Qt slots already become notifications. To report an exception you caught (with "View traceback"): `notification_manager.receive_error(type(e), e, e.__traceback__)`.
- Library code: `logging.getLogger(__name__)`, no handlers. In napari 0.9, records that pass the root logger's level appear in *Help → Show logs*, but don't rely on users finding it.
- Developers: `NAPARI_CATCH_ERRORS=0` prints tracebacks instead of notifications; `NAPARI_EXIT_ON_ERROR=1` exits.

## Viewer, layers, memory, theme

- Public API only (`viewer.window.add_dock_widget`, `add_plugin_dock_widget`, `dock_widgets`, `viewer.layers`, `viewer.events`). Never `viewer.window._qt_window`, `_dock_widgets`, `qt_viewer`.
- Dock names are `"<widget display_name> (<plugin>)"`. In 0.9.2 the menu path uses the manifest `display_name` and `add_plugin_dock_widget` the manifest `name` (`napari/plugins/__init__.py:menu_item_template`, `_qnpe2.py:_build_widgets_submenu_actions`, `qt_main_window.py:add_plugin_dock_widget`), so don't hard-code the key; get another widget with `add_plugin_dock_widget(name, widget_display_name)` (returns the existing one) or look it up in `dock_widgets`.
- Layer events: `viewer.layers.events.inserted/removed/moved/reordered`, `viewer.layers.selection.events.active`, `layer.events.data`. Widgets with `reset_choices()` are reconnected to layer changes automatically (`qt_main_window.py:add_dock_widget`).
- Only change layers you created, tagged in `layer.metadata`; per-viewer state on the widget (or a `WeakKeyDictionary` keyed by viewer, per the widget-communication page).
- Large data: pass dask/zarr arrays, not `np.asarray(...)`; give pyramids as a list with `multiscale=True`; napari's dask cache is sized with `napari.utils.resize_dask_cache`. Don't keep extra copies of layer data on the widget.
- Extra windows: `QDialog(parent=dock_widget)` inherits napari's stylesheet ([best practices](https://napari.org/stable/plugins/building_a_plugin/best_practices.html)). Custom colours: read `napari.utils.theme.get_theme(viewer.theme)` and update on `viewer.events.theme`.
- Settings: platformdirs config folder or `QSettings`, never the package folder. Caches: `platformdirs.user_cache_dir`, shown to the user with a way to clear them.
- Import cost: npe2 imports `python_name` modules only when the contribution is used, on the GUI thread; defer heavy imports ([best practices](https://napari.org/stable/plugins/building_a_plugin/best_practices.html)). Keep the core's `__init__` light too. Import inside the function that runs in the worker:

  ```python
  def _extract(paths):            # runs in a thread_worker
      from example.features import extract   # pulls in torch, off the GUI thread
      return extract(paths)
  ```

  Test it in a subprocess: `python -c "import napari_example._widget, sys; assert 'torch' not in sys.modules"`.

## Testing and CI

- napari registers a pytest plugin (`pytest11` entry point → `napari/utils/_testsupport.py`); fixtures need pytest-qt. `make_napari_viewer_proxy` wraps the viewer in `PublicOnlyProxy` (warns on private access) and is what the testing page shows; `make_napari_viewer` for code that needs private attributes. Both close viewers, reset settings, and fail the *next* test if a `QtViewer` leaked (a global keeping your widget or viewer alive). `make_napari_viewer(strict_qt=True)` also warns on leaked top-level widgets. No `qtbot.addWidget` or `viewer.close()` on top.
- Smoke test through the manifest: `dock, widget = viewer.window.add_plugin_dock_widget("<manifest name>", "<widget display_name>")` (it returns the dock and the inner widget; the first argument is the manifest `name`, the second the widget's `display_name`). Test the close path: `dock.destroyOnClose()` is private, so call `viewer.window.remove_dock_widget(widget)` and assert workers stopped / files removed.
- Prefer unit tests of pure functions and widget methods called directly ([testing](https://napari.org/stable/plugins/testing_and_publishing/test.html)). *"Aim for 100%"* coverage is a goal, not a gate.
- GitHub Actions (template `test_and_deploy.yml`): Linux × Python 3.11–3.14, macOS and Windows on one version; `pyvista/setup-headless-display-action@v5.1` with `qt: true` (template adds `wm: herbstluftwm`); tox + tox-gh-actions via uv (calling pytest directly is fine); codecov; `hynek/build-and-inspect-python-package`. Add `npe2 validate <name> --imports`, one job on a second Qt binding (PySide6) to prove qtpy-only code, and scheduled jobs for slow/network tests.
- `QT_QPA_PLATFORM=offscreen` segfaults when creating a napari viewer on macOS (reproduced with napari 0.9.2 / PyQt6); use a real or virtual display.
- Release: push a `v*` tag; `pypa/gh-action-pypi-publish` with PyPI trusted publishing (`id-token: write`, no token), TestPyPI first if unsure. Ship `LICENSE`, `README.md` (install with `pip install <name>` / `[all]`, where the widget appears in the menu, usage, citation, credit and licence for vendored code), `CHANGELOG.md`.
- The hub (hub-lite) rebuilds four times a day from npe2api (`hub-lite/.github/workflows/build_and_deploy.yml`); the docs say allow up to 4 hours. Check the page after release; announce on image.sc (https://forum.image.sc/tag/napari).
