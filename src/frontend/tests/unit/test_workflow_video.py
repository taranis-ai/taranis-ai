import shutil
import subprocess

import pytest
from dev.record_workflow_video import join_clips


def test_join_clips_preserves_workflow_order_and_quoted_paths(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg is required for the video export check")
    clips = []
    for color in ("blue", "red"):
        clip = tmp_path / f"{color} ' clip.webm"
        subprocess.run(
            [ffmpeg, "-v", "error", "-f", "lavfi", "-i", f"color=c={color}:s=16x16:r=1:d=1", "-c:v", "libvpx-vp9", str(clip)],
            check=True,
        )
        clips.append(clip)

    output = tmp_path / "taranis-walkthrough-video.webm"
    join_clips(list(reversed(clips)), output, ffmpeg)
    frames = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(output), "-vf", "fps=1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
        check=True,
        capture_output=True,
    ).stdout
    frame_size = 16 * 16 * 3
    assert len(frames) == 2 * frame_size
    assert frames[0] > 200 and frames[2] < 50
    assert frames[frame_size] < 50 and frames[frame_size + 2] > 200
