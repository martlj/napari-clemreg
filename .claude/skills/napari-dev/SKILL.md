---
name: napari-dev
description: Use when writing, reviewing, packaging, testing or publishing a napari plugin — npe2 manifest (napari.yaml), widget, reader, writer or sample-data contributions, dock widgets and what happens when they close, thread_worker, notifications and errors, pyproject dependencies and extras, splitting a headless core from the plugin, napari hub, PyPI or conda-forge releases, or tests with make_napari_viewer.
---

# napari plugin development

napari's plugin manager runs `pip install <dist>` (no extras) into the user's environment; plugins share its napari, Qt binding, viewer, event loop and process. Read `reference.md` (snippets, sources) before packaging, CI, release or clean-up work.

## Rules
1. **Dependencies.** List everything imported at runtime. Never a Qt binding, `napari[all]` or `napari[qt]`; offer `all = ["napari[all]"]`, put a binding in the dev group, import Qt via `qtpy`. List `napari` (floor only) only if imported at runtime; annotate with strings or `TYPE_CHECKING`.
2. **Layout.** One distribution whose headless core never imports napari/Qt (test it), or two: `napari-<x>` (manifest, entry point, `Framework :: napari`, depends on `core>=1.2,<2`) and a Qt-free core, released first. Plugin modules are private (`_widget.py`); `python_name` points at them; public surface = `__init__.py` + manifest.
3. **Identity.** Distribution = manifest `name` = entry-point key = command-id prefix. PyPI names are permanent.
4. **Hub** reads only PyPI metadata and the manifest. No `.napari/`, `.napari-hub/`, `napari-hub-cli`. README images need absolute URLs.
5. **Closing.** *Hide* keeps the widget. *X* un-parents it (`ParentChange`, `parent() is None`), leaving it alive. Closing the viewer deletes it (`destroyed`). Keep resources in a non-widget object with one idempotent `release()` for both plus `aboutToQuit`; stop workers before deleting their files. Never `closeEvent`/`hideEvent`; never discard unsaved results.
6. **Threads.** Slow work in `thread_worker`; update widgets via signals. napari already reports worker exceptions; to handle them pass `connect={"errored": ...}` at creation. Long jobs are generators so `quit()` works. Dask computes in workers use `callbacks=()`.
7. **Messages.** Expected problems: what is wrong and what to do (widget or `show_error`). Caught unexpected errors: `notification_manager.receive_error(type(e), e, e.__traceback__)`. Never only "see the log".
8. **Event loop.** Widget modules import on the GUI thread: defer heavy imports. No sleeps, waits or big `.compute()` in slots.
9. **Viewer.** Injected only into a parameter named `napari_viewer` or annotated `"napari.viewer.Viewer"`; a bare `viewer` gets nothing. Public API only; change only layers you created (tag `metadata`); never hard-code dock names; parent dialogs; colours follow `viewer.theme`.
10. **Files.** Caches in `platformdirs.user_cache_dir`, scratch in `tempfile`, never package dir or CWD. Close handles (Windows uninstall).
11. **Tests.** `make_napari_viewer_proxy` cleans up and fails on leaked viewers; add no cleanup. Smoke-test `dock, widget = viewer.window.add_plugin_dock_widget(<manifest name>, <widget display_name>)`, then `remove_dock_widget(widget)`. Run `npe2 validate <name> --imports`; prefer viewer-free unit tests. Linux CI needs a virtual display; `QT_QPA_PLATFORM=offscreen` segfaults on macOS.

## Red flags
- "napari or qtpy as an extra" · "PyQt6 in dependencies" · "`.napari/config.yml`"
- "clean up in `closeEvent`" · "`self.destroyed.connect(self.cleanup)`" · "`_qt_window`/`_dock_widgets`"
- "`worker.errored.connect(...)` after creation" · "`quit()` stops a function worker"
- "import torch at module top" · "core pinned `==`" · "`def __init__(self, viewer)`"
