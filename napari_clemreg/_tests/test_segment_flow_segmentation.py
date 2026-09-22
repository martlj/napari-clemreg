"""Segment-Flow EM segmentation integration (modernisation plan §4a,
issue #5 tighter-integration option).

Most of this is testable without Nextflow: prerequisite checking and the
revision pin. The real end-to-end test needs an actual Nextflow + Conda
install (and, on some systems, a specific JDK -- see the module
docstring), so it's marked slow and additionally skipped outright if
those tools aren't on PATH, rather than failing CI (which has neither).
"""
import shutil
from unittest.mock import patch

import numpy as np
import pytest

from napari_clemreg.clemreg import segment_flow_segmentation as sf
from napari_clemreg.clemreg.segment_flow_segmentation import (
    SEGMENT_FLOW_REPO,
    SEGMENT_FLOW_REVISION,
    SegmentFlowNotAvailable,
    SegmentFlowRunError,
    _check_prerequisites,
    segment_flow_em_segmentation,
)

_HAS_NEXTFLOW = shutil.which("nextflow") is not None and shutil.which("conda") is not None


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
    with patch("shutil.which", return_value=None):
        with pytest.raises(SegmentFlowNotAvailable):
            segment_flow_em_segmentation(np.zeros((2, 2, 2), dtype=np.uint8))


def test_segment_flow_retries_transient_setup_model_race(tmp_path):
    """setupModel and computeImageIds are submitted by Nextflow just
    milliseconds apart (confirmed directly from a real run's
    .nextflow.log) -- genuinely concurrent `conda activate`/`conda info
    --json` invocations, which conda's own activation mechanism isn't
    safe against racing. Confirmed directly this is a race, not a real
    misconfiguration: the exact cached env setupModel needs was checked
    directly and does have aiod_registry correctly installed, and a
    manual, sequential (non-concurrent) run of the identical activation
    command always succeeds. Retrying is cheap (everything's cached) and
    safe (idempotent).
    """
    mask_dir = tmp_path / "aiod_cache" / "empanada" / "MitoNet v1_masks"
    mask_dir.mkdir(parents=True)
    (mask_dir / "input_masks_deadbeef_all.tiff").touch()

    calls = []

    def fake_run_nextflow(cmd, cwd, env):
        calls.append(1)
        if len(calls) < 3:
            return 1, (
                "ERROR ~ Error executing process > 'setupModel'\n"
                "ModuleNotFoundError: No module named 'aiod_registry'"
            )
        return 0, "ok"

    with patch.object(sf, "_run_nextflow", fake_run_nextflow), \
         patch.object(sf, "_check_prerequisites", lambda: None), \
         patch.object(sf.time, "sleep", lambda seconds: None), \
         patch("aiod_utils.io.image_paths_to_csv", lambda *a, **k: None), \
         patch("tifffile.imread", lambda p: np.zeros((2, 2, 2), dtype=np.uint8)):
        result = segment_flow_em_segmentation(np.zeros((2, 4, 4), dtype=np.uint8), root_dir=tmp_path)

    assert result.shape == (2, 2, 2)
    assert len(calls) == 3


def test_segment_flow_does_not_retry_unrelated_failures(tmp_path):
    """A real, non-transient failure should surface immediately, not get
    masked behind retries meant only for the specific known race above.
    """
    calls = []

    def fake_run_nextflow(cmd, cwd, env):
        calls.append(1)
        return 1, "ERROR ~ some other real failure\nValueError: bad model_type"

    with patch.object(sf, "_run_nextflow", fake_run_nextflow), \
         patch.object(sf, "_check_prerequisites", lambda: None), \
         patch("aiod_utils.io.image_paths_to_csv", lambda *a, **k: None):
        with pytest.raises(SegmentFlowRunError):
            segment_flow_em_segmentation(np.zeros((2, 4, 4), dtype=np.uint8), root_dir=tmp_path)

    assert len(calls) == 1


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_NEXTFLOW, reason="needs a real Nextflow + Conda install")
def test_segment_flow_em_segmentation_real_run(tmp_path):
    """Runs the actual pipeline against synthetic noise (no real
    mitochondria expected -- this checks the round trip works and
    returns a correctly-shaped mask, not segmentation quality).
    """
    rng = np.random.default_rng(0)
    volume = rng.integers(0, 255, size=(8, 64, 64), dtype=np.uint8)

    mask = segment_flow_em_segmentation(volume, root_dir=tmp_path)

    assert mask.shape == volume.shape
