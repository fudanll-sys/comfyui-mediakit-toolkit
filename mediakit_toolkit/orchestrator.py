"""Capability orchestration shared by MediaKit cloud nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli import (
    build_enhance_arguments,
    build_query_arguments,
    run_cli_async,
)
from .errors import MediaKitTaskError


def _task_id(payload: dict[str, Any]) -> str:
    value = payload.get("task_id")
    if not isinstance(value, str) or not value:
        raise MediaKitTaskError("MediaKit CLI 未返回 task_id。")
    return value


def _result_video_url(payload: dict[str, Any]) -> str:
    value = payload.get("video_url")
    if not value and isinstance(payload.get("result"), dict):
        value = payload["result"].get("video_url")
    if not isinstance(value, str) or not value:
        raise MediaKitTaskError("MediaKit 任务完成，但未返回 video_url。")
    return value


async def enhance_video(
    video_path: Path,
    *,
    tool_version: str,
    scene: str,
    resolution: str,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    submit = await run_cli_async(
        build_enhance_arguments(
            str(video_path),
            tool_version=tool_version,
            scene=scene,
            resolution=resolution,
        )
    )
    task_id = _task_id(submit.payload)
    wait_timeout = max(600, poll_interval_seconds * max_poll_attempts + 300)
    result = await run_cli_async(
        build_query_arguments(
            task_id,
            poll_interval_seconds=poll_interval_seconds,
            max_poll_attempts=max_poll_attempts,
        ),
        timeout=wait_timeout,
    )
    return _result_video_url(result.payload), task_id

