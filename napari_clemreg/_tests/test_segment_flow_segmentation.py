"""Segment-Flow EM segmentation integration (modernisation plan §4a,
issue #5 tighter-integration option). Only what's testable without a
real Nextflow/Segment-Flow run: prerequisite checking and the revision
pin. The actual pipeline invocation is exercised manually against a
real Nextflow install -- see the module docstring for the findings from
doing that.
"""
from unittest.mock import patch

import pytest

from napari_clemreg.clemreg.segment_flow_segmentation import (
    SEGMENT_FLOW_REPO,
    SEGMENT_FLOW_REVISION,
    SegmentFlowNotAvailable,
    _check_prerequisites,
    segment_flow_em_segmentation,
)


def test_segment_flow_revision_is_pinned_not_default_branch():
    # Must not be "master"/"main" (the default branch) -- see the module
    # docstring for why: running the bare default branch fails in ways
    # that disappear once pinned to the same revision aiod_napari uses.
    assert SEGMENT_FLOW_REVISION not in ("master", "main")
    assert SEGMENT_FLOW_REPO == "FrancisCrickInstitute/Segment-Flow"


def test_check_prerequisites_raises_clearly_when_nextflow_missing():
    with patch("shutil.which", return_value=None):
        with pytest.raises(SegmentFlowNotAvailable, match="nextflow"):
            _check_prerequisites()


def test_check_prerequisites_passes_when_tools_present():
    with patch("shutil.which", return_value="/usr/bin/fake"):
        _check_prerequisites()  # should not raise


def test_segment_flow_em_segmentation_raises_clearly_without_prerequisites():
    import numpy as np

    with patch("shutil.which", return_value=None):
        with pytest.raises(SegmentFlowNotAvailable):
            segment_flow_em_segmentation(np.zeros((2, 2, 2), dtype=np.uint8))
