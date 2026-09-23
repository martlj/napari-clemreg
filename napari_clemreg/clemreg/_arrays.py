"""Helpers for core functions that take arrays but used to take napari layers."""
import numpy as np


def as_array(obj):
    """Return `obj` as a numpy array.

    Core functions take arrays. For backwards compatibility (decision D4
    in docs/design/package-split.md), they also accept anything with a
    `.data` attribute holding the array, such as a napari layer, so that
    copies of the published batch notebook keep working. Checked in this
    order because numpy arrays have a `.data` attribute of their own (a
    memoryview).
    """
    if isinstance(obj, np.ndarray):
        return obj
    return np.asarray(getattr(obj, 'data', obj))
