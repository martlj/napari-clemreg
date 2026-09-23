"""EM segmentation (napari-free core API).

Both backends run the same MitoNet model: through Crick's AI-on-Demand
Segment-Flow pipeline (the default, run by Nextflow in its own
environment), or in-process via `empanada-dl` (the `empanada` extra,
currently blocked on Python 3.11, #5). Each backend's module is only
imported when it's used, so neither is needed unless it's chosen.
"""
import logging

import numpy as np

from .exceptions import ClemregError, NoSegmentationError

logger = logging.getLogger(__name__)

BACKENDS = ('segment-flow', 'empanada')


def segment_em(volume: np.ndarray, backend: str = 'segment-flow', three_axis: bool = False) -> np.ndarray:
    """Segment mitochondria in an EM volume with MitoNet.

    Parameters
    ----------
    volume : np.ndarray
        The EM volume, (z, y, x).
    backend : {'segment-flow', 'empanada'}
        How to run MitoNet.
    three_axis : bool
        Predict along all three axes and combine. Only the 'empanada'
        backend uses this (#48).

    Returns
    -------
    np.ndarray
        The instance labels.

    Raises
    ------
    NoSegmentationError
        If nothing is segmented.
    ClemregError
        If the backend is unknown, or fails (Segment-Flow's own errors
        subclass ClemregError).
    """
    if backend == 'segment-flow':
        from .segment_flow_segmentation import segment_flow_em_segmentation

        logger.info('Running EM segmentation via MitoNet (Segment-Flow); progress is printed to the terminal.')
        seg_volume = segment_flow_em_segmentation(volume)
        logger.info('EM segmentation via Segment-Flow finished.')
    elif backend == 'empanada':
        from .empanada_segmentation import empanada_segmentation

        seg_volume = empanada_segmentation(input=volume, axis_prediction=three_axis)
    else:
        raise ClemregError(f'Unknown EM segmentation backend {backend!r}; expected one of {BACKENDS}')

    if np.all(seg_volume == seg_volume.flat[0]):
        raise NoSegmentationError('No mitochondria found in the EM image')
    return seg_volume
