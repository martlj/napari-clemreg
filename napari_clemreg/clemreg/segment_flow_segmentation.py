"""EM segmentation via Crick's AI-on-Demand (Segment-Flow), as an
alternative to the bundled empanada-dl path -- which is currently
blocked entirely on Python 3.11 (empanada-dl hard-pins numpy==1.22,
see issue #5). Shells out to `nextflow run FrancisCrickInstitute/Segment-Flow`
as a subprocess; the model itself runs in Segment-Flow's own isolated
per-model conda env, never in this process, so it needs no napari-clemreg
dependency changes at all.

Requires Nextflow and Conda on PATH. Verified end-to-end, not just by
inspection: `segment_flow_em_segmentation` was run directly against a
small synthetic test volume, through a real Nextflow/Segment-Flow
install, producing a correctly-shaped mask back. See the inline notes
below for the real, non-obvious gotchas hit getting there -- none of
them were guessed.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import tifffile

# Segment-Flow's default branch (`master`) is not the tested/stable
# target -- aiod_napari (the reference frontend) pins to a specific
# release tag instead (see its DEFAULT_NXF_REV in
# aiod_napari/inference/nxf.py) and this must match. Confirmed directly:
# running against bare `master` HEAD failed two different ways (a Groovy
# parse error in a newer commit, then a channel-wiring bug even once that
# was worked around) that both disappeared once pinned to this tag.
SEGMENT_FLOW_REVISION = "0.2.1"

SEGMENT_FLOW_REPO = "FrancisCrickInstitute/Segment-Flow"


class SegmentFlowNotAvailable(RuntimeError):
    """Raised when Nextflow (or Conda) isn't available on PATH."""


class SegmentFlowRunError(RuntimeError):
    """Raised when the Nextflow pipeline itself fails."""


def _build_subprocess_env() -> dict:
    """Environment for the Nextflow subprocess call.

    NXF_VER pins to a Nextflow release known to work with
    SEGMENT_FLOW_REVISION (see its comment above) -- newer Nextflow
    releases hit a real Groovy parse regression against Segment-Flow's
    pipeline script, confirmed directly. Left alone if the caller's own
    environment already sets NXF_VER.

    JAVA_HOME: Nextflow needs a JDK, and very recent ones (confirmed: 26)
    fail with "Unsupported class file major version". macOS's own
    `/usr/libexec/java_home -v <N>` isn't reliable here -- confirmed
    directly that it happily returns a *newer* JDK than requested instead
    of failing, so it can't tell us whether a compatible one is actually
    available. Instead, look directly for a Homebrew-installed
    openjdk@17/21 (the two versions the prerequisite-check error message
    below recommends), under both the Apple Silicon and Intel Homebrew
    prefixes. Left alone if the caller already set JAVA_HOME, or if no
    such install is found -- guessing further would risk pointing at a
    path that doesn't exist.
    """
    import os
    import platform

    env = os.environ.copy()
    env.setdefault("NXF_VER", "25.04.7")

    if platform.system() == "Darwin" and "JAVA_HOME" not in os.environ:
        for homebrew_prefix in ("/opt/homebrew/opt", "/usr/local/opt"):
            for jdk_version in ("21", "17"):
                candidate = Path(homebrew_prefix) / f"openjdk@{jdk_version}"
                if candidate.is_dir():
                    env["JAVA_HOME"] = str(candidate)
                    break
            else:
                continue
            break

    return env


def _run_nextflow(cmd: list, cwd: Path, env: dict) -> tuple[int, str]:
    """Run the Nextflow subprocess, printing its output line-by-line as it
    arrives instead of swallowing it until the process exits.

    Nextflow's own output is what previously gave visible progress in the
    terminal for the (now-optional) empanada-dl path's tqdm bars; a plain
    `subprocess.run(..., capture_output=True)` here produced zero terminal
    feedback for the entire run (confirmed directly: nothing printed at all
    while a real run was in progress) -- unhelpful for a pipeline that can
    run for minutes, especially on a first call against a given root_dir
    while a model environment/checkpoint downloads. Still returns the full
    output so a failure can be reported with complete context.
    """
    process = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    lines = []
    for line in process.stdout:
        # flush=True: stdout is only line-buffered by default when
        # attached to a real terminal -- when napari's own output is
        # redirected to a log file (or, as found while testing this,
        # to any non-TTY pipe), Python falls back to block buffering,
        # which would silently defeat the whole point of streaming here.
        print(line, end="", flush=True)
        lines.append(line)
    process.wait()
    return process.returncode, "".join(lines)


def _check_prerequisites() -> None:
    missing = [tool for tool in ("nextflow", "conda") if shutil.which(tool) is None]
    if missing:
        raise SegmentFlowNotAvailable(
            f"Segment-Flow EM segmentation needs {' and '.join(missing)} on PATH. "
            "See https://www.nextflow.io/ and https://docs.conda.io/ to install. "
            "Note: Nextflow also needs a JDK -- very recent JDKs (tested: 26) can "
            "fail with 'Unsupported class file major version'; a JDK around 17-21 "
            "is the safer bet (e.g. `brew install openjdk@21` on macOS -- this is "
            "auto-detected and used even without setting JAVA_HOME yourself; on "
            "other platforms, set JAVA_HOME to point at a 17-21 JDK if your "
            "default is newer)."
        )
    try:
        import aiod_utils  # noqa: F401
    except ImportError as e:
        raise SegmentFlowNotAvailable(
            "Segment-Flow EM segmentation needs the `aiod_utils` package "
            "(`pip install aiod_utils`) to build the image manifest CSV in the "
            "format Segment-Flow expects."
        ) from e


def segment_flow_em_segmentation(
    volume: np.ndarray,
    model_type: str = "MitoNet v1",
    task: str = "mito",
    profile: str = "local",
    root_dir: str | Path | None = None,
) -> np.ndarray:
    """Run EM segmentation via Crick's AI-on-Demand Segment-Flow pipeline.

    Parameters
    ----------
    volume : np.ndarray
        EM image volume to segment.
    model_type : str
        Segment-Flow / AIoD registry model version name (e.g. "MitoNet v1"
        -- see the "versions" keys in aiod_registry's empanada.json
        manifest for the full list, not the model's own casual name).
    task : str
        AIoD registry task key for the chosen model_type (e.g. "mito" --
        again, taken from the registry manifest, not guessed; this does
        NOT match empanada_segmentation.py's own axis_prediction concept).
    profile : str
        Nextflow execution profile: "local", "crick", or "rosalind".
    root_dir : str or Path, optional
        AIoD cache/output root (holds conda envs, model checkpoints, and
        results -- reused across calls so models aren't re-downloaded).
        Defaults to ``~/.nextflow/aiod``, matching aiod_napari's own
        default, so a cache built via aiod_napari or a previous call is
        reused rather than duplicated.

    Returns
    -------
    np.ndarray
        The segmentation mask, same shape as ``volume``.
    """
    _check_prerequisites()

    # Match Segment-Flow's own default (nextflow.config:
    # root_dir = "${System.getProperty('user.home')}/.nextflow/aiod") so a
    # cache built by a previous call, or by aiod_napari itself, is reused
    # rather than duplicated -- and so we know where to look for the output
    # below regardless of whether the caller passed root_dir explicitly.
    if root_dir is None:
        root_dir = Path.home() / ".nextflow" / "aiod"
    root_dir = Path(root_dir)

    # aiod_utils.io.image_paths_to_csv builds the image-manifest CSV in the
    # exact format Segment-Flow expects (img_path, num_slices, height, width,
    # channels, dtype) -- a hand-written CSV with just img_path fails with
    # "Column 'height' not found" partway through the pipeline (split_stacks),
    # confirmed directly. Dimension auto-detection from file metadata isn't
    # implemented upstream (raises NotImplementedError), so dims must be
    # passed explicitly.
    from aiod_utils.io import image_paths_to_csv

    with tempfile.TemporaryDirectory(prefix="napari_clemreg_segment_flow_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        img_path = tmpdir / "input.tif"
        tifffile.imwrite(img_path, volume)

        csv_path = tmpdir / "images.csv"
        depth, height, width = volume.shape
        image_paths_to_csv(
            [img_path],
            csv_path,
            dimensions={"Z": depth, "Y": height, "X": width},
            dtypes=str(volume.dtype),
            overwrite=True,
            index=False,
        )

        cmd = [
            "nextflow", "run", SEGMENT_FLOW_REPO,
            "-r", SEGMENT_FLOW_REVISION,
            "-profile", profile,
            "--img_dir", str(csv_path),
            "--model", "empanada",
            "--model_type", model_type,
            "--task", task,
            "--output_format", "tiff",
            "--root_dir", str(root_dir),
        ]

        print(
            f"Running Segment-Flow EM segmentation (model_type={model_type!r}, "
            f"task={task!r})... this shells out to a real Nextflow pipeline and "
            "can take a while, especially on first run against a given "
            "root_dir while the model environment/checkpoint downloads. Note: "
            "Nextflow may print an 'ERROR ~' block for an individual failed "
            "process attempt (e.g. a transient conda-environment-setup issue) "
            "and still go on to complete the run successfully -- confirmed "
            "directly. That block alone isn't a reliable failure signal; this "
            "function only raises once Nextflow's own final exit code says the "
            "whole run failed, so let it keep running rather than assuming "
            "failure from an ERROR block partway through.",
            flush=True,
        )
        returncode, output = _run_nextflow(cmd, cwd=tmpdir, env=_build_subprocess_env())

        # .nextflow.log lands in cwd (tmpdir), which is deleted with the
        # `with` block above -- so without this, the one file that would
        # help debug exactly this kind of transient mid-run error is gone
        # before anyone can look at it. Keep it on failure, when it's
        # actually needed; skip on success to avoid piling up clutter.
        log_path = tmpdir / ".nextflow.log"
        saved_log_path = None
        if returncode != 0 and log_path.exists():
            log_dir = root_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            saved_log_path = log_dir / f"nextflow_{time.strftime('%Y%m%d_%H%M%S')}.log"
            shutil.copy(log_path, saved_log_path)

        if returncode != 0:
            log_note = f"\n\nFull Nextflow log saved to {saved_log_path}" if saved_log_path else ""
            raise SegmentFlowRunError(
                f"Segment-Flow failed (exit {returncode}):\n{output}{log_note}"
            )
        print("Segment-Flow EM segmentation finished.", flush=True)

        # combineStacks publishes the result as
        # <root_dir>/aiod_cache/<model>/<model_type>_masks/<image-id>_masks_<hash>_all.<format>
        # -- confirmed against a real run. The <hash> is a resolved-param
        # hash we don't compute ourselves, so glob for it rather than
        # predict the exact filename (robust to that hash's computation
        # changing upstream, and there's exactly one match for a
        # single-image run).
        mask_dir = root_dir / "aiod_cache" / "empanada" / f"{model_type}_masks"
        matches = sorted(mask_dir.glob("*_all.tiff"))
        if not matches:
            raise SegmentFlowRunError(
                f"Segment-Flow reported success but no output mask was found in "
                f"{mask_dir} (looked for *_all.tiff). Nextflow output:\n{output}"
            )
        return tifffile.imread(matches[-1])
