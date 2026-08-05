"""Capability orchestration shared by MediaKit cloud nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli import (
    build_enhance_arguments,
    build_erase_subtitle_arguments,
    build_query_arguments,
    run_cli_async,
)
from .errors import MediaKitTaskError
from .logging_utils import log_event


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
    bitrate_level: str = "medium",
    fps: float = 0.0,
) -> tuple[str, str]:
    return await _run_cloud_video_task(
        build_enhance_arguments(
            str(video_path),
            tool_version=tool_version,
            scene=scene,
            resolution=resolution,
            bitrate_level=bitrate_level,
            fps=fps,
        ),
        capability="enhance-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def erase_video_subtitle(
    video_path: Path,
    *,
    professional: bool,
    mode: str = "Subtitle",
    output_encode_mode: str = "Quality",
    erase_region: dict[str, float] | None = None,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    capability = (
        "erase-video-subtitle-pro" if professional else "erase-video-subtitle"
    )
    return await _run_cloud_video_task(
        build_erase_subtitle_arguments(
            str(video_path),
            professional=professional,
            mode=mode,
            output_encode_mode=output_encode_mode,
            erase_region=erase_region,
        ),
        capability=capability,
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def _run_cloud_video_task(
    submit_arguments: list[str],
    *,
    capability: str,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    log_event("task_submit_started", capability=capability)
    task_id: str | None = None
    try:
        submit = await run_cli_async(submit_arguments)
        task_id = _task_id(submit.payload)
        log_event("task_submitted", capability=capability, task_id=task_id)
        wait_timeout = max(600, poll_interval_seconds * max_poll_attempts + 300)
        result = await run_cli_async(
            build_query_arguments(
                task_id,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            ),
            timeout=wait_timeout,
        )
        result_url = _result_video_url(result.payload)
        log_event("task_completed", capability=capability, task_id=task_id)
        return result_url, task_id
    except Exception as exc:
        log_event(
            "task_failed",
            capability=capability,
            task_id=task_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise
