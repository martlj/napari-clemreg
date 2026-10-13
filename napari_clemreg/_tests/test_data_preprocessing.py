import numpy as np
import pytest
from qtpy.QtWidgets import QApplication

from napari_clemreg.clemreg.data_preprocessing import (
    get_pixelsize, return_isotropic_image_list, _zoom_values, resample_to_pixelsize,
    _make_isotropic,
)

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


def test_get_pixelsize_parses_decimal_and_fraction_spacing():
    assert get_pixelsize({'ImageDescription': 'unit=micron\nspacing=0.25\n'})[2] == 0.25
    assert get_pixelsize({'ImageDescription': 'unit=micron\nspacing=1/4\n'})[2] == 0.25


def test_get_pixelsize_never_evaluates_metadata(tmp_path):
    marker = tmp_path / 'marker'
    metadata = {'ImageDescription': f'unit=micron\nspacing=__import__("pathlib").Path({str(marker)!r}).touch() or 0.1\n'}

    x, y, z, unit = get_pixelsize(metadata)

    assert not marker.exists()
    assert z == 1


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


def test_resample_to_pixelsize_downsamples_to_coarser_native_grid():
    # A 40**3 array isotropic at 5nm/voxel (the internal warp working
    # grid, keyed to EM's z-pixel-size) covers a 200nm cube. Resampling
    # to a coarser, anisotropic target (20nm z, 10nm xy) should shrink it
    # to a 10 x 20 x 20 array while covering the same physical extent.
    arr = np.random.default_rng(0).integers(0, 255, (40, 40, 40), dtype=np.uint8)
    result = resample_to_pixelsize(arr, working_pxlsz=5.0, target_pxlsz=(20.0, 10.0))
    assert result.shape == (10, 20, 20)


def test_resample_to_pixelsize_is_identity_when_target_matches_working_grid():
    arr = np.random.default_rng(0).integers(0, 255, (12, 12, 12), dtype=np.uint8)
    result = resample_to_pixelsize(arr, working_pxlsz=5.0, target_pxlsz=(5.0, 5.0))
    assert result.shape == arr.shape


# The FM sample's pixel sizes (nm): 130 z, 35 xy, resampled onto a 20 nm
# working grid. A ramp holding each voxel's physical z position shows
# where every output voxel samples from, so a wrong scale shows up as a
# value that drifts away from the output voxel's own position.
@pytest.mark.xfail(strict=True, reason='#98: ndimage.zoom stretches z by (n_out - 1) / (n_in - 1)')
@pytest.mark.parametrize('n_slices', [7, 28])
def test_make_isotropic_keeps_the_requested_z_scale(n_slices):
    ramp = np.broadcast_to(np.arange(n_slices, dtype=float)[:, None, None] * 130, (n_slices, 2, 2))

    result = _make_isotropic(ramp, pxlsz_lm=(130, 35), pxlsz_em=(20, 20), order=1)

    assert result.shape[0] == round(n_slices * 6.5)
    # Beyond the last input slice's centre the value is clamped, not scaled.
    inside = np.arange(result.shape[0]) * 20 <= (n_slices - 1) * 130
    np.testing.assert_allclose(result[inside, 0, 0], np.arange(result.shape[0])[inside] * 20, atol=1e-6)


@pytest.mark.xfail(strict=True, reason='#98: ndimage.zoom stretches z by (n_out - 1) / (n_in - 1)')
def test_resample_to_pixelsize_keeps_the_requested_z_scale():
    ramp = np.broadcast_to(np.arange(182, dtype=float)[:, None, None] * 20, (182, 2, 2))

    result = resample_to_pixelsize(ramp, working_pxlsz=20, target_pxlsz=(130, 20), order=1)

    assert result.shape[0] == 28
    np.testing.assert_allclose(result[:, 0, 0], np.arange(28) * 130, atol=1e-6)
