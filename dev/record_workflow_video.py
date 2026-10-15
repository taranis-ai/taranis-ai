#!/usr/bin/env -S uv run --script
"""Record the analyst workflow and combine its browser clips into one WebM."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "src/frontend"
VIDEO_FILENAME = "taranis-walkthrough-video.webm"


def join_clips(clips: list[Path], output: Path, ffmpeg: str) -> None:
    if not clips:
        raise RuntimeError("The workflow did not record any video clips")
    manifest = output.with_suffix(".txt")
    manifest.write_text(
        "".join(
            "file '" + str(clip.resolve()).replace("'", "'\\''") + "'\n"
            for clip in clips
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
            "-an",
            "-c:v",
            "copy",
            str(output),
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=FRONTEND / "tests/playwright/videos" / VIDEO_FILENAME,
    )
    parser.add_argument(
        "--highlight-delay",
        type=float,
        default=2,
        help="Seconds to highlight each action (default: 2)",
    )
    args = parser.parse_args()
    if args.highlight_delay < 0:
        parser.error("--highlight-delay must be non-negative")
    output = args.output.expanduser().resolve()
    if output.suffix.lower() != ".webm":
        parser.error("--output must end in .webm")
    if os.getenv("TARANIS_E2E_EXTERNAL_BASE_URL") or os.getenv(
        "TARANIS_E2E_EXTERNAL_CORE_API_URL"
    ):
        parser.error(
            "Unset external E2E URLs to record the local workflow with scripted Chat."
        )
    for command in ("uv", "ffmpeg"):
        if not shutil.which(command):
            parser.error(
                f"Missing required command: {command}. Install it before recording."
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".workflow-", dir=output.parent
    ) as temporary:
        recording_dir = Path(temporary)
        subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                "tests/playwright/test_e2e_workflow.py",
                "--e2e-user-workflow",
                "--record-video",
                f"--highlight-delay={args.highlight_delay}",
                "-x",
            ],
            cwd=FRONTEND,
            env={**os.environ, "TARANIS_E2E_VIDEO_DIR": str(recording_dir)},
            check=True,
        )
        clips = [
            Path(json.loads(line))
            for line in (recording_dir / "clips.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        combined = recording_dir / VIDEO_FILENAME
        join_clips(clips, combined, "ffmpeg")
        combined.replace(output)
    print(f"Video created -> it is here: {output}", flush=True)
    print(
        "Now copy to 'taranis.ai' repository under 'static/taranis-walkthrough-video.webm'",
        flush=True,
    )


if __name__ == "__main__":
    main()
