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

from napari_clemreg.clemreg.segment_flow_segmentation import (
    SEGMENT_FLOW_REPO,
    SEGMENT_FLOW_REVISION,
    SegmentFlowNotAvailable,
    _build_subprocess_env,
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


def test_build_subprocess_env_strips_venv_from_path():
    """`uv run` (and a plain venv activation) prepends the venv's own
    bin/ to PATH and sets VIRTUAL_ENV, *without* deactivating an
    already-active conda env. Confirmed directly this breaks Nextflow's
    own per-process conda activation for entirely unrelated envs (e.g.
    setupModel's, which needs aiod_registry): conda's activation script
    has no knowledge of the venv's bin/ entry and never removes it, so
    it keeps winning over whatever conda env conda just "activated" --
    `python` (and everything else) kept resolving to the venv's own
    interpreter regardless. This was previously misdiagnosed as a
    transient concurrency race (see git history); the real cause is
    deterministic and is this.
    """
    fake_venv = "/Users/fake/some-project/.venv"
    fake_env = {
        "VIRTUAL_ENV": fake_venv,
        "PATH": f"{fake_venv}/bin:/usr/bin:/bin",
    }
    with patch("os.environ", fake_env):
        env = _build_subprocess_env()

    assert "VIRTUAL_ENV" not in env
    assert f"{fake_venv}/bin" not in env["PATH"].split(":")
    assert env["PATH"] == "/usr/bin:/bin"


def test_build_subprocess_env_leaves_path_alone_without_a_venv():
    with patch("os.environ", {"PATH": "/usr/bin:/bin"}):
        env = _build_subprocess_env()

    assert env["PATH"] == "/usr/bin:/bin"


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
