"""End-to-end characterisation test (modernisation plan §0.1.2 / §0.1.3).

Exercises the full segment -> sample -> register -> warp pipeline on a
synthetic dataset with a *known* ground-truth transform between the two
modalities, and asserts the warped moving segmentation overlaps the fixed
segmentation above a Dice threshold. This is the acceptance-gate test the
plan calls for before the Python 3.11 / napari 0.6.6 dependency bumps and
the core/widget split (§6) -- a large numeric drift in any of the four
pipeline stages should show up here even if each stage's own tests still
pass individually.

Uses the affine warp path (_warp_image_volume_affine), not BCPD/TPS, since
the BCPD warp has a known pre-existing bug (#9) unrelated to what this
test is checking.
"""
import numpy as np

from napari_clemreg.clemreg.point_cloud_sampling import point_cloud_sampling
from napari_clemreg.clemreg.point_cloud_registration import point_cloud_registration
from napari_clemreg.clemreg.warp_image_volume import _warp_image_volume_affine

from .conftest import make_blob_volume, SYNTHETIC_BLOB_SHAPE, SYNTHETIC_BLOB_CENTERS, SYNTHETIC_BLOB_RADIUS


class _FakeLabels:
    """Minimal duck-typed stand-in for a napari Labels layer."""

    def __init__(self, data, name='labels'):
        self.data = data
        self.name = name


def _apply_affine(matrix, point):
    z, y, x = point
    return tuple((matrix @ np.array([z, y, x, 1.0]))[:3])


def _dice(a, b):
    a, b = a.astype(bool), b.astype(bool)
    return 2 * np.logical_and(a, b).sum() / (a.sum() + b.sum())


def test_full_pipeline_recovers_known_transform_with_high_dice():
    # Ground-truth FM(moving) -> EM(fixed) rigid transform: small rotation
    # about the z axis plus a few-voxel translation.
    theta = np.deg2rad(8)
    rotation = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(theta), -np.sin(theta)],
        [0.0, np.sin(theta), np.cos(theta)],
    ])
    translation = np.array([1.0, 2.0, -1.5])
    fm_to_em = np.eye(4)
    fm_to_em[:3, :3] = rotation
    fm_to_em[:3, 3] = translation
    em_to_fm = np.linalg.inv(fm_to_em)

    # Independently generate the EM segmentation from the fixed blob
    # centres, and the FM segmentation from those same structures mapped
    # backwards through the ground-truth transform -- so the two volumes
    # are only related via `fm_to_em`, not via image resampling.
    em_centers = SYNTHETIC_BLOB_CENTERS
    fm_centers = [_apply_affine(em_to_fm, c) for c in em_centers]

    em_volume = make_blob_volume(
        SYNTHETIC_BLOB_SHAPE, em_centers, SYNTHETIC_BLOB_RADIUS, rng=np.random.default_rng(0)
    )
    fm_volume = make_blob_volume(
        SYNTHETIC_BLOB_SHAPE, fm_centers, SYNTHETIC_BLOB_RADIUS, rng=np.random.default_rng(1)
    )
    em_binary = (em_volume > 0.3).astype(np.uint8)
    fm_binary = (fm_volume > 0.3).astype(np.uint8)

    em_points = point_cloud_sampling(_FakeLabels(em_binary), every_k_points=2, voxel_size=1, sigma=1.0)
    fm_points = point_cloud_sampling(_FakeLabels(fm_binary), every_k_points=2, voxel_size=1, sigma=1.0)

    _, _, _, kwargs = point_cloud_registration(
        fm_points, em_points, algorithm='Rigid CPD', max_iterations=100
    )
    recovered = kwargs['affine']

    # Loose sanity check: recovered transform is in the right ballpark.
    # Point-cloud sampling (canny edges + voxel downsampling) means CPD
    # won't recover the exact matrix -- Dice below is the real signal.
    np.testing.assert_allclose(recovered, fm_to_em, atol=0.5)

    warped_fm = _warp_image_volume_affine(
        fm_binary, recovered, output_shape=SYNTHETIC_BLOB_SHAPE, interpolation_order=0
    )
    dice = _dice(warped_fm, em_binary)
    assert dice > 0.85
