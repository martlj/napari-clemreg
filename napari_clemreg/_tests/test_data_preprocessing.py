import numpy as np
import pytest
from qtpy.QtWidgets import QApplication

from napari_clemreg.clemreg.data_preprocessing import get_pixelsize, return_isotropic_image_list, _zoom_values

# Exact metadata dicts used by napari_clemreg/clemreg/sample_data.py, reused
# here so the parsing test exercises real-world strings rather than an
# idealised format.
FM_METADATA = {
    'ImageDescription': (
        'ImageJ=1.53t\nimages=112\nchannels=4\nslices=28\nhyperstack=true\n'
        'mode=grayscale\nunit=micron\nspacing=0.13\nloop=false\n'
        'min=0.0\nmax=65535.0\n'
    ),
    'XResolution': 28.349506,
    'YResolution': 28.349506,
}
EM_METADATA = {
    'ImageDescription': '\nunit=micron\nspacing=0.02\n',
    'XResolution': 50,
    'YResolution': 50,
}


def test_get_pixelsize_parses_fm_sample_metadata():
    x, y, z, unit = get_pixelsize(FM_METADATA)
    assert x == pytest.approx(1 / 28.349506)
    assert y == pytest.approx(1 / 28.349506)
    assert z == pytest.approx(0.13)
    assert unit == 'micron'


def test_get_pixelsize_parses_em_sample_metadata():
    x, y, z, unit = get_pixelsize(EM_METADATA)
    assert x == pytest.approx(1 / 50)
    assert y == pytest.approx(1 / 50)
    assert z == pytest.approx(0.02)
    assert unit == 'micron'


def test_get_pixelsize_defaults_when_xy_resolution_missing():
    x, y, z, unit = get_pixelsize({'ImageDescription': 'unit=micron\nspacing=0.02\n'})
    assert x == 1
    assert y == 1
    assert z == pytest.approx(0.02)
    assert unit == 'micron'


def test_get_pixelsize_defaults_when_image_description_missing():
    x, y, z, unit = get_pixelsize({'XResolution': 50, 'YResolution': 50})
    assert x == pytest.approx(1 / 50)
    assert y == pytest.approx(1 / 50)
    assert z == 1
    assert unit == 'micron'


def test_zoom_values():
    xy_zoom, z_zoom = _zoom_values(xy=10, z=20, xy_ref=5, z_ref=4)
    assert xy_zoom == pytest.approx(2.0)
    assert z_zoom == pytest.approx(5.0)


def test_zoom_values_identity_when_matching_reference():
    xy_zoom, z_zoom = _zoom_values(xy=1, z=1, xy_ref=1, z_ref=1)
    assert xy_zoom == pytest.approx(1.0)
    assert z_zoom == pytest.approx(1.0)


def test_return_isotropic_image_list_handles_real_linked_layers():
    """copy.deepcopy(image) on a real, viewer-attached layer (as this
    function used to do) crashes -- confirmed directly: modern napari
    layers carry live Qt/vispy canvas state (down to a QFont, several
    frames deep through overlay callbacks) that can't be pickled. Hit
    live, deep into a real registration run, on exactly this
    linked-layers path (FM channels linked via link_layers()).
    """
    import napari
    from napari_clemreg.clemreg._napari_compat import link_layers

    QApplication.instance() or QApplication([])
    viewer = napari.viewer.ViewerModel()
    img1 = viewer.add_image(
        np.random.default_rng(0).integers(0, 255, (4, 8, 8), dtype=np.uint8),
        name='FM_Mitotracker', colormap='green', blending='additive',
    )
    img2 = viewer.add_image(
        np.random.default_rng(1).integers(0, 255, (4, 8, 8), dtype=np.uint8),
        name='FM_TGN46', colormap='magenta', blending='additive',
    )
    link_layers([img1, img2])

    result = return_isotropic_image_list(
        input_image=img1, pxlsz_lm=(100.0, 50.0), pxlsz_em=(20.0, 20.0),
    )

    assert {r.name for r in result} == {'FM_Mitotracker', 'FM_TGN46'}
    for r in result:
        assert r.data.shape == (20, 20, 20)
