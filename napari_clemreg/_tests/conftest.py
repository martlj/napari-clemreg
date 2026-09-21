import os

# torch (pip wheel, bundled libiomp5) and napari's conda-forge dependency
# stack (libomp) can load two OpenMP runtimes in the same process and
# segfault on import on macOS. Harmless on Linux CI, where this is a no-op.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pytest


@pytest.fixture
def seed():
    """A fixed seed for tests that need reproducible randomness."""
    value = 0
    np.random.seed(value)
    return value


@pytest.fixture
def rng():
    """A seeded numpy Generator for tests that need reproducible randomness."""
    return np.random.default_rng(0)
