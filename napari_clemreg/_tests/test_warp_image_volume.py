import numpy as np

from napari_clemreg.clemreg.warp_image_volume import (
    _U,
    _make_L_matrix,
    _calculate_f,
    _make_warp,
)


def test_U_at_zero_is_zero():
    assert _U(np.array(0.0)) == 0.0


def test_U_matches_r_squared_log_r():
    x = np.array([1.0, 2.0, np.e])
    expected = (x**2) * np.log(x)
    np.testing.assert_allclose(_U(x), expected)


def test_make_L_matrix_shape_and_blocks(rng):
    points = rng.uniform(0, 10, size=(5, 3))
    n = len(points)
    L = _make_L_matrix(points)

    assert L.shape == (n + 4, n + 4)
    # K block (top-left) has zero diagonal: U(0) == 0 for coincident points
    np.testing.assert_allclose(np.diag(L[:n, :n]), 0.0)
    # K block is symmetric (interpoint distances are symmetric)
    np.testing.assert_allclose(L[:n, :n], L[:n, :n].T)
    # P block (top-right): column of ones followed by the points themselves
    np.testing.assert_allclose(L[:n, n], 1.0)
    np.testing.assert_allclose(L[:n, n + 1:], points)
    # O block (bottom-right) is zero
    np.testing.assert_allclose(L[n:, n:], 0.0)


def test_calculate_f_reduces_to_affine_when_weights_are_zero(rng):
    """With all point-weights zero, f(x,y,z) = a1 + ax*x + ay*y + az*z."""
    points = rng.uniform(0, 10, size=(6, 3))
    a1, ax, ay, az = 1.0, 2.0, -3.0, 0.5
    coeffs = np.array([0.0] * len(points) + [a1, ax, ay, az])

    x = rng.uniform(0, 10, size=(4,))
    y = rng.uniform(0, 10, size=(4,))
    z = rng.uniform(0, 10, size=(4,))

    result = _calculate_f(coeffs, points, x, y, z)
    expected = a1 + ax * x + ay * y + az * z
    np.testing.assert_allclose(result, expected)


def test_make_warp_identity_transform_is_unchanged(rng):
    """Identity transform => image unchanged (within interpolation tolerance).

    When from_points == to_points, _make_warp should be the identity
    everywhere -- see the modernisation plan's testing-foundation
    invariants, docs/napari-clemreg-modernisation-plan.md §0.1.1.

    Regression test for a bug (#9) where the TPS right-hand side zeroed
    only 3 of the 4 rows needed to satisfy the affine-orthogonality
    constraint (`V[-3:, :] = 0` instead of `V[-4:, :] = 0`), corrupting
    the affine part of every solve.
    """
    points = rng.uniform(0, 10, size=(6, 3))
    query = rng.uniform(0, 10, size=(5,))
    x_vals, y_vals, z_vals = query, query[::-1].copy(), query * 0.5

    x_warp, y_warp, z_warp = _make_warp(points, points, x_vals, y_vals, z_vals)
    actual = np.stack([x_warp, y_warp, z_warp], axis=1)
    expected = np.stack([x_vals, y_vals, z_vals], axis=1)

    np.testing.assert_allclose(actual, expected, atol=1e-6)


def test_make_warp_recovers_a_known_affine_transform(rng):
    """When from_points/to_points are related by an affine map, the TPS
    solution should have zero non-affine (bending) component and recover
    that same affine map exactly at arbitrary query points, not just at
    the control points themselves -- a stronger check than the identity
    invariant above, and another regression test for #9.
    """
    from_points = rng.uniform(0, 10, size=(6, 3))
    matrix = np.array([
        [1.2, 0.1, -0.05],
        [0.0, 0.9, 0.2],
        [0.1, 0.0, 1.1],
    ])
    offset = np.array([2.0, -1.0, 0.5])
    to_points = from_points @ matrix.T + offset

    query = rng.uniform(0, 10, size=(5,))
    x_vals, y_vals, z_vals = query, query[::-1].copy(), query * 0.5

    x_warp, y_warp, z_warp = _make_warp(from_points, to_points, x_vals, y_vals, z_vals)
    actual = np.stack([x_warp, y_warp, z_warp], axis=1)
    expected = np.stack([x_vals, y_vals, z_vals], axis=1) @ matrix.T + offset

    np.testing.assert_allclose(actual, expected, atol=1e-6)
