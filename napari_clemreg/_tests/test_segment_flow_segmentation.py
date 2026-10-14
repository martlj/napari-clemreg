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
    _build_model_config,
    _build_subprocess_env,
    _check_prerequisites,
    _default_profile,
    _find_mask,
    _input_key,
    _segment_flow_source,
    segment_flow_em_segmentation,
)

_HAS_NEXTFLOW = shutil.which("nextflow") is not None and shutil.which("conda") is not None
try:
    import aiod_registry  # noqa: F401
    _HAS_AIOD_REGISTRY = True
except ImportError:
    _HAS_AIOD_REGISTRY = False
try:
    import aiod_utils  # noqa: F401
    import yaml  # noqa: F401
    _HAS_AIOD_PACKAGES = _HAS_AIOD_REGISTRY
except ImportError:
    _HAS_AIOD_PACKAGES = False


def test_segment_flow_revision_is_pinned_not_default_branch():
    # Must not be "master"/"main" (the default branch) -- see the module
    # docstring for why: running the bare default branch fails in ways
    # that disappear once pinned to the same revision aiod_napari uses.
    assert SEGMENT_FLOW_REVISION not in ("master", "main")
    assert SEGMENT_FLOW_REPO == "FrancisCrickInstitute/Segment-Flow"


def test_segment_flow_source_defaults_to_pinned_github_release(monkeypatch):
    monkeypatch.delenv("AIOD_NXF_REPO", raising=False)
    assert _segment_flow_source() == [SEGMENT_FLOW_REPO, "-r", SEGMENT_FLOW_REVISION]


def test_segment_flow_source_uses_local_checkout_without_revision(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOD_NXF_REPO", str(tmp_path))
    assert _segment_flow_source() == [str(tmp_path)]


def test_segment_flow_source_rejects_missing_local_checkout(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOD_NXF_REPO", str(tmp_path / "missing"))
    with pytest.raises(SegmentFlowNotAvailable, match="AIOD_NXF_REPO"):
        _segment_flow_source()


def test_default_profile_honours_env(monkeypatch):
    monkeypatch.delenv("AIOD_NXF_PROFILE", raising=False)
    assert _default_profile() == "local"
    monkeypatch.setenv("AIOD_NXF_PROFILE", "berta")
    assert _default_profile() == "berta"


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


@pytest.mark.skipif(not _HAS_AIOD_REGISTRY, reason="needs the aiod_registry package")
def test_build_model_config_patches_only_conf_threshold(tmp_path):
    """aiod_registry's own default conf_threshold for MitoNet v1 (0.5) is
    notably stricter than empanada-dl's own bundled config (0.3, see
    empanada_configs/MitoNet_V1.yaml) -- confirmed directly by generating
    and reading Segment-Flow's actual default config, and a real
    production run against a real EM volume (known, via the bundled
    empanada-dl path, to contain mitochondria) found none at all via
    Segment-Flow. This patches just that one field onto Segment-Flow's
    own generated default (not a hand-written config, which would risk
    an incomplete/wrong schema).
    """
    config_path = _build_model_config("MitoNet v1", "mito", 0.3, tmp_path)

    import yaml
    config = yaml.safe_load(config_path.read_text())

    assert config["conf_threshold"] == 0.3
    # Confirm this really did come from the registry's own generator, not
    # a hand-written stand-in -- these are AIoD's field names, not ours.
    assert config["plane"] == "XY"
    assert config["center_threshold"] == 0.1
    assert config["min_distance"] == 3


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


def test_input_key_depends_on_volume_and_settings():
    source = [SEGMENT_FLOW_REPO, "-r", SEGMENT_FLOW_REVISION]
    volume = np.arange(24, dtype=np.uint8).reshape(2, 3, 4)
    key = _input_key(volume, "MitoNet v1", "mito", 0.3, source)

    # Same content, different memory layout: same key.
    assert _input_key(np.asfortranarray(volume), "MitoNet v1", "mito", 0.3, source) == key
    changed = volume.copy()
    changed[0, 0, 0] += 1
    assert _input_key(changed, "MitoNet v1", "mito", 0.3, source) != key
    assert _input_key(volume.astype(np.uint16), "MitoNet v1", "mito", 0.3, source) != key
    assert _input_key(volume.reshape(3, 2, 4), "MitoNet v1", "mito", 0.3, source) != key
    assert _input_key(volume, "MitoNet v1", "mito", 0.5, source) != key
    assert _input_key(volume, "MitoNet v1", "mito", 0.3, ["/local/checkout"]) != key


def test_find_mask_matches_only_this_image_and_prefers_newest(tmp_path):
    import os

    assert _find_mask(tmp_path / "missing", "clemreg_abc_tif") is None
    old = tmp_path / "clemreg_abc_tif_masks_111_all.tiff"
    new = tmp_path / "clemreg_abc_tif_masks_222_all.tiff"
    other = tmp_path / "clemreg_xyz_tif_masks_333_all.tiff"
    for i, path in enumerate((new, old, other)):
        path.touch()
        os.utime(path, (1000 + i, 1000 + i))
    os.utime(new, (2000, 2000))

    assert _find_mask(tmp_path, "clemreg_abc_tif") == new


@pytest.mark.skipif(not _HAS_AIOD_PACKAGES, reason="needs aiod_utils, aiod_registry and pyyaml")
def test_segment_flow_em_segmentation_reuses_published_mask(tmp_path, monkeypatch):
    """A mask already published for this volume and these settings is
    returned without starting Nextflow."""
    import tifffile
    from aiod_utils.io import get_image_id
    from napari_clemreg.clemreg import segment_flow_segmentation as sf

    monkeypatch.delenv("AIOD_NXF_REPO", raising=False)
    volume = np.arange(24, dtype=np.uint8).reshape(2, 3, 4)
    key = _input_key(volume, "MitoNet v1", "mito", 0.3, _segment_flow_source())
    image_id = get_image_id(f"clemreg_{key}.tif").value
    mask_dir = tmp_path / "aiod_cache" / "empanada" / "MitoNet v1_masks"
    mask_dir.mkdir(parents=True)
    expected = np.ones(volume.shape, dtype=np.uint16)
    tifffile.imwrite(mask_dir / f"{image_id}_masks_deadbeef_all.tiff", expected)

    def refuse(*args, **kwargs):
        raise AssertionError("Nextflow should not run when a mask can be reused")

    monkeypatch.setattr(sf, "_run_nextflow", refuse)
    with patch("shutil.which", return_value="/usr/bin/fake"):
        mask = segment_flow_em_segmentation(volume, root_dir=tmp_path)

    np.testing.assert_array_equal(mask, expected)


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
