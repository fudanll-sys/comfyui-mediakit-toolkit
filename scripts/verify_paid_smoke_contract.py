"""Non-billable smoke contract: real ComfyUI/node/media, mocked cloud boundary."""
import argparse
import asyncio
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--comfy-root", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location("smoke_contract", root / "scripts/cloud_smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
video_from_file, node, orchestrator, av = smoke._load_runtime(Path(args.comfy_root))
from mediakit_toolkit.cli import CommandResult
import numpy as np


def make_video(path, duration):
    with av.open(str(path), "w") as container:
        stream = container.add_stream("libx264", rate=15)
        stream.width, stream.height, stream.pix_fmt = 320, 240, "yuv420p"
        for _ in range(round(duration * 15)):
            frame = av.VideoFrame.from_ndarray(np.zeros((240, 320, 3), dtype="uint8"), format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


with tempfile.TemporaryDirectory() as directory:
    output = Path(directory)
    cloud_result = output / "mock-cloud-result.mp4"
    make_video(cloud_result, 1)

    async def fake_cloud(arguments, **kwargs):
        if "trim-video" in arguments:
            source = Path(arguments[arguments.index("--video-url") + 1])
            assert source.is_file(), "Real media bridge did not materialize the input"
            assert arguments[arguments.index("--client-token") + 1] == "contract-only-token"
            return CommandResult({"task_id": "mock-task"}, "", "", 0)
        assert "query-task" in arguments
        assert arguments[arguments.index("--task-id") + 1] == "mock-task"
        return CommandResult({"status": "completed", "video_url": str(cloud_result)}, "", "", 0)

    mocked = AsyncMock(side_effect=fake_cloud)
    with patch.object(smoke, "require_api_key"), patch.object(smoke, "require_cli"), \
         patch.object(smoke, "_create_fixture", side_effect=make_video), \
         patch.object(orchestrator, "run_cli_async", mocked):
        result = smoke.run_smoke(work_dir=output, comfy_root=Path(args.comfy_root),
            confirm_billing=True, duration_seconds=2, poll_interval=5,
            max_attempts=60, client_token="contract-only-token")
    assert result["status"] == "passed" and result["decoded_frames"] == 15, result
    assert mocked.await_count == 2
    with patch.object(smoke, "require_api_key"), patch.object(smoke, "require_cli"), \
         patch.object(orchestrator, "run_cli_async", mocked):
        recovered = smoke.resume_smoke(work_dir=output / "recovery", comfy_root=Path(args.comfy_root),
            task_id="mock-task", poll_interval=5, max_attempts=60)
    assert recovered["paid_submissions"] == 0 and recovered["decoded_frames"] == 15
    assert mocked.await_count == 3
    report = {"passed": True, "actual_comfyui_node": "MediaKitTrimVideo",
              "native_video_decode": True, "frames": result["decoded_frames"],
              "paid_cloud_calls": 0, "mocked_boundary": "orchestrator.run_cli_async",
              "limitations": ["No live auth/upload/cloud/download validation", "No browser or queue test"]}
    print(json.dumps(report, ensure_ascii=False))
