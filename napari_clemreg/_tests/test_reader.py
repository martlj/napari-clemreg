"""bioio-based reader (issue #37): pixel data + physical pixel size
extraction that works for real file metadata, not just ImageJ-written
TIFFs.

The shape/dtype checks below need no network (they run against
whatever's already cached, or trigger the same ~275MB/~337MB Zenodo
download `test_sample_data.py`'s slow test does) -- marked slow and
skipped unless `pytest --run-slow` is passed, same convention.
"""
import numpy as np
import pytest

from napari_clemreg._reader import napari_get_reader, bioio_reader
from napari_clemreg.clemreg.data_preprocessing import get_pixelsize
from napari_clemreg.clemreg.sample_data import POOCH


def test_napari_get_reader_matches_tif_extensions():
    assert napari_get_reader("some/path/image.tif") is bioio_reader
    assert napari_get_reader("some/path/image.tiff") is bioio_reader
    assert napari_get_reader("some/path/image.czi") is None
    assert napari_get_reader(["a.tif", "b.tif"]) is None


@pytest.mark.slow
def test_bioio_reader_extracts_real_pixel_size_when_present():
    """EM04468_2_63x_pos8T_LM_raw.tif (the FM sample file) has complete,
    correct embedded ImageJ metadata -- confirmed directly with
    tifffile against the real file: spacing=0.13 (z, micron),
    XResolution/YResolution matching 28.349506 (xy, pixels/micron).
    """
    path = POOCH.fetch("EM04468_2_63x_pos8T_LM_raw.tif", progressbar=True)
    layers = bioio_reader(path)

    assert len(layers) == 1
    data, layer_kwargs, layer_type = layers[0]
    assert layer_type == "image"
    assert data.shape == (4, 28, 1226, 1226)  # C, Z, Y, X

    pps = layer_kwargs["metadata"]["physical_pixel_sizes"]
    assert pps.Z == pytest.approx(0.13)
    assert pps.Y == pytest.approx(1 / 28.349506, rel=1e-3)
    assert pps.X == pytest.approx(1 / 28.349506, rel=1e-3)

    x, y, z, unit = get_pixelsize(layer_kwargs["metadata"])
    assert (x, y, z) == (pps.X, pps.Y, pps.Z)
    assert unit == "micron"


@pytest.mark.slow
def test_bioio_reader_reports_missing_pixel_size_as_none_not_a_wrong_default():
    """em_20nm_z_40_145.tif (the EM sample file) has no pixel size
    metadata embedded at all -- confirmed directly with tifffile
    against the real file: no spacing/unit, no XResolution/YResolution
    tags. bioio should report this as None, not silently invent a
    value -- and get_pixelsize() should fall through to its documented
    pixel-size-1 default (the same one sample_data.py's own hardcoded
    metadata override exists to avoid) rather than raise.
    """
    path = POOCH.fetch("em_20nm_z_40_145.tif", progressbar=True)
    layers = bioio_reader(path)

    assert len(layers) == 1
    data, layer_kwargs, layer_type = layers[0]
    assert data.shape == (106, 1750, 1484)  # Z, Y, X (single channel, squeezed)

    pps = layer_kwargs["metadata"]["physical_pixel_sizes"]
    assert (pps.X, pps.Y, pps.Z) == (None, None, None)

    x, y, z, unit = get_pixelsize(layer_kwargs["metadata"])
    assert (x, y, z, unit) == (1, 1, 1, "micron")
