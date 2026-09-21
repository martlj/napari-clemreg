import numpy as np

from napari_clemreg.clemreg.point_cloud_registration import (
    _make_matrix_from_rigid_params,
)


def test_make_matrix_from_rigid_params_translation_only():
    identity_rot = np.eye(3)
    trans = [1.0, 2.0, 3.0]
    mat = _make_matrix_from_rigid_params(identity_rot, trans, s=1.0)

    point = np.array([0.0, 0.0, 0.0, 1.0])
    result = mat @ point
    np.testing.assert_allclose(result[:3], trans)


def test_make_matrix_from_rigid_params_rotation_and_scale():
    # 90 degree rotation about z: (x, y, z) -> (-y, x, z)
    rot_90_z = np.array([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    scale = 2.0
    mat = _make_matrix_from_rigid_params(rot_90_z, trans=[0.0, 0.0, 0.0], s=scale)

    point = np.array([1.0, 0.0, 0.0, 1.0])
    result = mat @ point
    np.testing.assert_allclose(result[:3], [0.0, 2.0, 0.0], atol=1e-12)


def test_make_matrix_from_rigid_params_is_homogeneous():
    mat = _make_matrix_from_rigid_params(np.eye(3), [1.0, 2.0, 3.0], s=1.0)
    assert mat.shape == (4, 4)
    np.testing.assert_allclose(mat[3], [0.0, 0.0, 0.0, 1.0])
