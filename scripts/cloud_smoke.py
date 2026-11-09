#!/usr/bin/env python3
"""Run exactly one minimal, paid MediaKit cloud smoke test.

This script is intended for manual local verification and the
workflow_dispatch GitHub Actions job. It never stores or prints the API key
or the signed result URL's query parameters.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Allow ``python scripts/cloud_smoke.py`` from a fresh checkout without
# installing the package into the CI runner's site-packages.
_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from mediakit_toolkit.cloud_smoke import (
    SmokeResult,
    assert_terminal_completed,
    build_poll_arguments,
    build_trim_arguments,
    download_result,
    extract_result_url,
    extract_task_id,
    require_api_key,
    run_json_command,
)
from mediakit_toolkit.redaction import redact_text


def _create_fixture(path: Path, duration_seconds: float) -> None:
    """Create a tiny synthetic MP4 using ffmpeg; fail clearly if unavailable."""
    completed = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=15",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=8000",
            "-t",
            str(duration_seconds),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "无法使用 ffmpeg 创建测试视频：\n"
            + redact_text((completed.stderr or completed.stdout)[-2000:])
        )


def run_smoke(*, work_dir: Path, duration_seconds: float, poll_interval: int, max_attempts: int) -> SmokeResult:
    require_api_key()
    fixture = work_dir / "smoke-input.mp4"
    output = work_dir / "smoke-output.mp4"
    _create_fixture(fixture, duration_seconds)

    # Trim a 2s clip to 1s: the smallest valid cloud editing task.
    submit_payload = run_json_command(
        build_trim_arguments(fixture, start_time=0.0, end_time=1.0),
        timeout=300,
    )
    task_id = extract_task_id(submit_payload)

    # Poll in bounded loops: one CLI --poll-complete window is capped at
    # 9 minutes, and a long task can return running at the window boundary.
    # Reuse the same task_id; never resubmit the paid task. The same terminal
    # guard as the production orchestrator is used so a window-boundary
    # ``running`` response cannot be mistaken for completion.
    terminal_payload: dict[str, object] = {}
    for _ in range(max(1, 600 // (poll_interval or 5))):
        terminal_payload = run_json_command(
            build_poll_arguments(
                task_id,
                poll_interval_seconds=poll_interval,
                max_poll_attempts=max_attempts,
            ),
            timeout=900,
        )
        if terminal_payload.get("status") in (
            "completed",
            "failed",
            "canceled",
            "cancelled",
        ) or terminal_payload.get("success") is False:
            break
    assert_terminal_completed(terminal_payload)
    result_url = extract_result_url(terminal_payload)
    downloaded_bytes = download_result(result_url, output)
    return SmokeResult(
        submit_payload=submit_payload,
        terminal_payload=terminal_payload,
        result_url=result_url,
        downloaded_bytes=downloaded_bytes,
        output_path=output,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one paid MediaKit cloud smoke test.")
    parser.add_argument("--work-dir", default="")
    parser.add_argument("--duration-seconds", type=float, default=2.0)
    parser.add_argument("--poll-interval-seconds", type=int, default=5)
    parser.add_argument("--max-poll-attempts", type=int, default=60)
    args = parser.parse_args()

    if args.duration_seconds <= 1.0:
        parser.error("--duration-seconds must be greater than 1.0")

    if args.work_dir:
        work_dir = Path(args.work_dir).expanduser().resolve()
        work_dir.mkdir(parents=True, exist_ok=True)
        context = None
    else:
        context = tempfile.TemporaryDirectory(prefix="mediakit-smoke-")
        work_dir = Path(context.name)

    try:
        result = run_smoke(
            work_dir=work_dir,
            duration_seconds=args.duration_seconds,
            poll_interval=args.poll_interval_seconds,
            max_attempts=args.max_poll_attempts,
        )
    finally:
        if context is not None:
            context.cleanup()

    summary = {
        "status": "passed",
        "task_id": result.terminal_payload.get("task_id"),
        "downloaded_bytes": result.downloaded_bytes,
        "output_exists": result.output_path.is_file(),
        "billing_usage": result.terminal_payload.get("usage"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # Surface one readable, redacted failure line.
        print(json.dumps({"status": "failed", "error": redact_text(str(exc))}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
