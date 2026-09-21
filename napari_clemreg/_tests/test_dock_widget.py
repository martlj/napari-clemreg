"""Widget / integration smoke tests (modernisation plan §0.1.3).

These build the magicgui widgets and the npe2 manifest, but stop short of
`napari.viewer.Viewer()` (the `make_napari_viewer` fixture from napari's
own pytest plugin): on this machine, constructing a real Viewer under
`QT_QPA_PLATFORM=offscreen` segfaults inside vispy's OpenGL canvas setup
(napari/_vispy/canvas.py -> get_max_texture_sizes), which is an
environment/driver limitation, not something napari-clemreg controls.
CI (tox's `pytest-xvfb` on ubuntu-latest) has a real X server and GL
context, so a `make_napari_viewer`-based test belongs there -- this file
covers what's reliable locally: that each `magic_factory` widget builds
(exercises `on_init_specs.py` and every `on_init` callback) and that the
npe2 manifest + reader hook are wired correctly.
"""
import numpy as np
import pytest
import tifffile
from qtpy.QtWidgets import QApplication

from napari_clemreg._reader import napari_get_reader
from napari_clemreg.widgets.fixed_segmentation import fixed_segmentation_widget
from napari_clemreg.widgets.moving_segmentation import moving_segmentation_widget
from napari_clemreg.widgets.point_cloud_sampling import point_cloud_sampling_widget
from napari_clemreg.widgets.registration_warping import registration_warping_widget
from napari_clemreg.widgets.run_registration import make_run_registration

WIDGET_FACTORIES = [
    fixed_segmentation_widget,
    moving_segmentation_widget,
    point_cloud_sampling_widget,
    registration_warping_widget,
    make_run_registration,
]


@pytest.fixture
def qapp():
    """A QApplication, needed to construct any Qt/magicgui widget."""
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("factory", WIDGET_FACTORIES, ids=[f.__name__ for f in WIDGET_FACTORIES])
def test_widget_factory_builds(factory, qapp):
    widget = factory()
    assert widget is not None


def test_npe2_manifest_loads():
    from npe2 import PluginManifest

    manifest = PluginManifest.from_file('napari_clemreg/napari.yaml')

    assert manifest.name == 'napari-clemreg'
    widget_commands = {w.command for w in manifest.contributions.widgets}
    declared_commands = {c.id for c in manifest.contributions.commands}
    # Every widget must reference a command that's actually declared.
    assert widget_commands <= declared_commands


def test_reader_recognises_tiff_and_rejects_other_extensions():
    assert napari_get_reader('somefile.tif') is not None
    assert napari_get_reader('somefile.tiff') is not None
    assert napari_get_reader('somefile.png') is None


def test_reader_returns_valid_layer_data_tuple(tmp_path):
    array = np.random.default_rng(0).integers(0, 255, size=(5, 10, 10), dtype=np.uint8)
    path = tmp_path / 'test.tif'
    tifffile.imwrite(path, array)

    reader = napari_get_reader(str(path))
    layer_data = reader(str(path))

    assert isinstance(layer_data, list)
    data, layer_kwargs, layer_type = layer_data[0]
    np.testing.assert_array_equal(data, array)
    assert layer_type == 'image'
    assert 'metadata' in layer_kwargs
