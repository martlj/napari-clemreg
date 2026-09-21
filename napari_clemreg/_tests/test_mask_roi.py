import numpy as np
import pytest
from napari.layers import Shapes
from skimage import draw

from napari_clemreg.clemreg.mask_roi import mask_area, mask_roi


def test_mask_area_unit_square():
    x = np.array([0.0, 1.0, 1.0, 0.0])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    assert mask_area(x, y) == pytest.approx(1.0)


def test_mask_area_triangle():
    # Right triangle with legs 4 and 3 -> area 6
    x = np.array([0.0, 4.0, 0.0])
    y = np.array([0.0, 0.0, 3.0])
    assert mask_area(x, y) == pytest.approx(6.0)


class _FakeImageLayer:
    """Minimal duck-typed stand-in for a napari Image layer's `.data`/`.shape`."""

    def __init__(self, data):
        self.data = data
        self.shape = data.shape


def test_mask_roi_zeroes_outside_rectangle_and_z_range():
    arr = np.ones((10, 8, 8))
    rectangle = np.array(
        [[0, 2, 2], [0, 2, 6], [0, 6, 6], [0, 6, 2]], dtype=float
    )
    crop_mask = Shapes([rectangle], shape_type='rectangle')

    result = mask_roi(_FakeImageLayer(arr), crop_mask, z_min=3, z_max=7)

    # Ground truth built the same way mask_roi assembles its 3D mask, so
    # this isolates mask_roi's z-range/channel assembly logic from
    # skimage.draw.polygon2mask's own boundary-inclusivity conventions.
    mask_2d = draw.polygon2mask(arr.shape[1:], rectangle[:, 1:])
    mask_3d = np.zeros_like(arr, dtype=bool)
    mask_3d[3:7] = mask_2d
    expected = (arr * mask_3d).astype(int)

    np.testing.assert_array_equal(result, expected)
    assert result.shape == arr.shape


def test_mask_roi_raises_for_multiple_shapes():
    arr = np.ones((10, 8, 8))
    rectangle = np.array(
        [[0, 2, 2], [0, 2, 6], [0, 6, 6], [0, 6, 2]], dtype=float
    )
    crop_mask = Shapes([rectangle, rectangle], shape_type='rectangle')

    with pytest.raises(AssertionError):
        mask_roi(_FakeImageLayer(arr), crop_mask, z_min=3, z_max=7)
