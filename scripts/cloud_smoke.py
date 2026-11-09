#!/usr/bin/env python3
"""Manual, paid smoke through the real Trim node; never retry a submission."""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import secrets
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from mediakit_toolkit.cloud_smoke import require_api_key, require_cli
from mediakit_toolkit.errors import MediaKitConfigurationError, MediaKitTaskError
from mediakit_toolkit.redaction import redact_text


def validate_options(*, confirm_billing, duration_seconds, poll_interval,
                     max_attempts, client_token):
    if not confirm_billing:
        raise MediaKitConfigurationError("必须显式指定 --confirm-billing；本次会提交真实付费任务。")
    if not math.isfinite(duration_seconds) or not 1 < duration_seconds <= 3:
        raise MediaKitConfigurationError("测试素材时长必须大于 1 秒且不超过 3 秒。")
    if not 2 <= poll_interval <= 60 or not 1 <= max_attempts <= 5000:
        raise MediaKitConfigurationError("轮询间隔须为 2～60 秒，次数须为 1～5000。")
    if client_token and (len(client_token) > 64 or any(not 32 <= ord(c) <= 126 for c in client_token)):
        raise MediaKitConfigurationError("client_token 须为不超过 64 字符的可打印 ASCII。")


def _create_fixture(path: Path, duration_seconds: float) -> None:
    completed = subprocess.run([
        "ffmpeg", "-n", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=8000",
        "-t", str(duration_seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(path),
    ], capture_output=True, text=True, check=False, timeout=60, shell=False)
    if completed.returncode != 0:
        raise RuntimeError("无法创建测试素材：" + redact_text(completed.stderr[-2000:]))


def _load_runtime(comfy_root: Path):
    if not (comfy_root / "comfy_api/latest/_io.py").is_file():
        raise MediaKitConfigurationError("--comfy-root 必须指向真实 ComfyUI 源码。")
    sys.path.insert(0, str(comfy_root.resolve()))
    # ComfyUI imports its argument parser and device setup: don't expose smoke
    # arguments to it and force CPU. No server or desktop application is started.
    original_argv = sys.argv
    try:
        sys.argv = [sys.argv[0], "--cpu"]
        # Library imports normally parse [] unless ComfyUI was launched as a
        # server, so argv alone does NOT set CPU. Set the actual runtime args
        # before the downloader lazily imports model_management.
        from comfy.cli_args import args as comfy_args
        comfy_args.cpu = True
        from comfy_api.latest import InputImpl
        from mediakit_toolkit.nodes.video_editing import MediaKitTrimVideo
        from comfy_api_nodes import util
        assert callable(util.download_url_to_video_output)
        import mediakit_toolkit.orchestrator as orchestrator
        import av
    finally:
        sys.argv = original_argv
    return InputImpl.VideoFromFile, MediaKitTrimVideo, orchestrator, av


def _inspect_output(path: Path, av) -> dict:
    if not path.is_file() or path.stat().st_size <= 0:
        raise MediaKitTaskError("节点输出文件为空。")
    with av.open(str(path)) as container:
        if not container.streams.video:
            raise MediaKitTaskError("节点输出没有视频流。")
        stream = container.streams.video[0]
        width, height = stream.codec_context.width, stream.codec_context.height
        duration = float(stream.duration * stream.time_base) if stream.duration is not None else None
        decoded_frames = sum(1 for _ in container.decode(stream))
    if decoded_frames <= 0 or (width, height) != (320, 240):
        raise MediaKitTaskError("节点输出解码或分辨率校验失败。")
    if duration is None or not 0.75 <= duration <= 1.25:
        raise MediaKitTaskError("节点输出不是预期约 1 秒视频。")
    return {"downloaded_bytes": path.stat().st_size, "decoded_frames": decoded_frames,
            "width": width, "height": height, "duration_seconds": duration}


def run_smoke(*, work_dir: Path, comfy_root: Path, confirm_billing: bool,
              duration_seconds: float, poll_interval: int, max_attempts: int,
              client_token: str = "") -> dict:
    validate_options(confirm_billing=confirm_billing, duration_seconds=duration_seconds,
                     poll_interval=poll_interval, max_attempts=max_attempts, client_token=client_token)
    require_api_key()
    require_cli()
    video_from_file, node, orchestrator, av = _load_runtime(comfy_root)
    work_dir.mkdir(parents=True, exist_ok=True)
    state_path = work_dir / "smoke-state.json"
    state = {"status": "prepared", "client_token": client_token or "mediakit-smoke-" + secrets.token_hex(16),
             "task_id": None, "paid_submissions": 0, "node": "MediaKitTrimVideo"}
    # Exclusive creation is a local rerun guard. Never delete this evidence or
    # automatically resubmit after a timeout/lost response. Query the original ID.
    try:
        with state_path.open("x", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise MediaKitConfigurationError(
            "该目录已有 smoke-state.json，拒绝重复提交；请查询原 task_id。"
        ) from exc

    def save_state():
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    fixture = work_dir / "smoke-input.mp4"
    output = work_dir / "smoke-output.mp4"
    original_cli = orchestrator.run_cli_async

    async def guarded_cli(arguments, **kwargs):
        if "trim-video" in arguments:
            kwargs["timeout"] = min(kwargs.get("timeout", 180), 180)
            if state["paid_submissions"]:
                raise MediaKitTaskError("冒烟禁止第二次付费提交。")
            if "--cloud" not in arguments or "--client-token" not in arguments:
                raise MediaKitTaskError("真实节点缺少云端模式或幂等 token。")
            if arguments[arguments.index("--client-token") + 1] != state["client_token"]:
                raise MediaKitTaskError("真实节点未透传预先保存的 token。")
            state.update(status="submitting", paid_submissions=1)
            save_state()  # Persist before sending; lost response must not trigger retry.
        elif "query-task" not in arguments:
            raise MediaKitTaskError("冒烟不允许其它业务调用。")
        result = await original_cli(arguments, **kwargs)
        task_id = result.payload.get("task_id")
        if task_id:
            state["task_id"] = task_id
        if "query-task" in arguments:
            state["task_id"] = arguments[arguments.index("--task-id") + 1]
            state["last_status"] = result.payload.get("status")
        save_state()
        return result

    async def execute():
        with patch.object(orchestrator, "run_cli_async", guarded_cli):
            result = await asyncio.wait_for(node.execute(
                video=video_from_file(str(fixture)), start_time=0.0, end_time=1.0,
                run_mode="cloud", poll_interval_seconds=poll_interval,
                max_poll_attempts=max_attempts, client_token=state["client_token"],
            ), timeout=600)
        # This is the native VIDEO returned by the real node/media bridge.
        await asyncio.to_thread(result[0].save_to, str(output))

    started = time.monotonic()
    try:
        _create_fixture(fixture, duration_seconds)
        asyncio.run(execute())
        report = _inspect_output(output, av)
        state.update(status="passed", elapsed_seconds=round(time.monotonic() - started, 2), **report)
    except Exception as exc:
        state.update(status="failed", error=redact_text(str(exc)),
                     note="Do not resubmit. Query the original task_id; a missing response does not prove no charge.")
        save_state()
        raise
    save_state()
    return state


def resume_smoke(*, work_dir: Path, comfy_root: Path, task_id: str,
                 poll_interval: int, max_attempts: int) -> dict:
    """Query and decode an already-submitted task; never call trim-video."""
    if not task_id or not 2 <= poll_interval <= 60 or not 1 <= max_attempts <= 5000:
        raise MediaKitConfigurationError("恢复任务需要原 task_id 和合法轮询参数。")
    require_api_key()
    require_cli()
    _, _, orchestrator, av = _load_runtime(comfy_root)
    from mediakit_toolkit.media_bridge import download_video_output
    work_dir.mkdir(parents=True, exist_ok=True)
    state_path = work_dir / "smoke-resume-state.json"
    state = {"status": "resuming", "task_id": task_id, "paid_submissions": 0,
             "verification": "query original task + real media bridge download/save/decode"}
    with state_path.open("x", encoding="utf-8") as stream:
        json.dump(state, stream, ensure_ascii=False, indent=2)
    original_cli = orchestrator.run_cli_async

    async def query_only(arguments, **kwargs):
        if "query-task" not in arguments or "trim-video" in arguments:
            raise MediaKitTaskError("恢复模式只允许查询，禁止任何付费提交。")
        return await original_cli(arguments, **kwargs)

    async def recover():
        with patch.object(orchestrator, "run_cli_async", query_only):
            payload = await orchestrator._poll_until_terminal(task_id,
                poll_interval_seconds=poll_interval, max_poll_attempts=max_attempts,
                capability="smoke-resume", flatten=True)
        state["last_status"] = payload.get("status")
        url = orchestrator._result_video_url(payload)
        video = await download_video_output(url)
        await asyncio.to_thread(video.save_to, str(work_dir / "smoke-output.mp4"))

    async def bounded_recover():
        return await asyncio.wait_for(recover(), timeout=600)

    try:
        asyncio.run(bounded_recover())
        state.update(status="passed", **_inspect_output(work_dir / "smoke-output.mp4", av))
    except Exception as exc:
        state.update(status="failed", error=redact_text(str(exc)))
        raise
    finally:
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-billing", action="store_true")
    parser.add_argument("--resume-task-id", default="", help="Query/decode an existing task; never submit.")
    parser.add_argument("--comfy-root", required=True)
    parser.add_argument("--work-dir", default="./cloud-smoke-artifacts")
    parser.add_argument("--duration-seconds", type=float, default=2.0)
    parser.add_argument("--poll-interval-seconds", type=int, default=5)
    parser.add_argument("--max-poll-attempts", type=int, default=60)
    parser.add_argument("--client-token", default="")
    args = parser.parse_args()
    if args.resume_task_id:
        result = resume_smoke(work_dir=Path(args.work_dir).resolve(),
            comfy_root=Path(args.comfy_root).resolve(), task_id=args.resume_task_id,
            poll_interval=args.poll_interval_seconds, max_attempts=args.max_poll_attempts)
    else:
        result = run_smoke(work_dir=Path(args.work_dir).resolve(), comfy_root=Path(args.comfy_root).resolve(),
                           confirm_billing=args.confirm_billing, duration_seconds=args.duration_seconds,
                           poll_interval=args.poll_interval_seconds, max_attempts=args.max_poll_attempts,
                           client_token=args.client_token)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": redact_text(str(exc))}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
