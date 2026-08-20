"""Capability orchestration shared by MediaKit cloud nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli import (
    build_analyze_highlights_arguments,
    build_asr_subtitles_arguments,
    build_enhance_arguments,
    build_erase_subtitle_arguments,
    build_generative_enhance_arguments,
    build_matte_video_arguments,
    build_probe_metadata_arguments,
    build_query_arguments,
    build_segment_scenes_arguments,
    build_video_ocr_arguments,
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


async def enhance_video_generative(
    video_path: Path,
    *,
    resolution: str,
    bitrate_level: str,
    fps: float,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    return await _run_cloud_video_task(
        build_generative_enhance_arguments(
            str(video_path),
            resolution=resolution,
            bitrate_level=bitrate_level,
            fps=fps,
        ),
        capability="enhance-video-generative",
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


def _flatten_result(payload: dict[str, Any]) -> dict[str, Any]:
    """CLI flattens query-task result fields; keep both shapes working."""
    nested = payload.get("result")
    if isinstance(nested, dict):
        merged = dict(nested)
        for key, value in payload.items():
            if key != "result" and key not in merged:
                merged[key] = value
        return merged
    return dict(payload)


def find_first_url(
    payload: dict[str, Any],
    *,
    prefer: tuple[str, ...],
) -> str | None:
    """Return the first HTTP(S) URL whose key hints at a preferred field."""
    def walk(node: Any, key: str) -> str | None:
        if isinstance(node, str) and node.startswith(("http://", "https://")):
            if any(token in key.lower() for token in prefer):
                return node
            return None
        if isinstance(node, dict):
            for child_key, child in node.items():
                found = walk(child, child_key)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = walk(item, "")
                if found:
                    return found
        return None
    return walk(payload, "")


def find_subtitle_url(payload: dict[str, Any]) -> str | None:
    """Return a subtitle/file download URL from an ASR or OCR result."""
    found = find_first_url(payload, prefer=("subtitle", "srt", "text"))
    if found:
        return found
    return find_first_url(payload, prefer=("url", "file"))


async def _run_cloud_task(
    submit_arguments: list[str],
    *,
    capability: str,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[dict[str, Any], str]:
    """Submit and poll a cloud task, returning the flattened result payload."""
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
        log_event("task_completed", capability=capability, task_id=task_id)
        return _flatten_result(result.payload), task_id
    except Exception as exc:
        log_event(
            "task_failed",
            capability=capability,
            task_id=task_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise


async def asr_video_subtitles(
    video_path: Path,
    *,
    content_type: str,
    language: str,
    enable_speaker_info: bool,
    enable_confidence: bool,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[dict[str, Any], str]:
    return await _run_cloud_task(
        build_asr_subtitles_arguments(
            str(video_path),
            content_type=content_type,
            language=language,
            enable_speaker_info=enable_speaker_info,
            enable_confidence=enable_confidence,
        ),
        capability="asr-subtitles",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def ocr_video_subtitles(
    video_path: Path,
    *,
    mode: str,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[dict[str, Any], str]:
    return await _run_cloud_task(
        build_video_ocr_arguments(str(video_path), mode=mode),
        capability="video-ocr",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def matte_video(
    video_path: Path,
    *,
    tool: str,
    output_format: str,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    payload, task_id = await _run_cloud_task(
        build_matte_video_arguments(
            str(video_path),
            tool=tool,
            output_format=output_format,
        ),
        capability=tool,
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )
    return _result_video_url(payload), task_id


async def segment_video_scenes(
    video_path: Path,
    *,
    enable_clip_fade: bool,
    segment_threshold: float | None,
    min_duration: float | None,
    max_duration: float | None,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[dict[str, Any], str]:
    return await _run_cloud_task(
        build_segment_scenes_arguments(
            str(video_path),
            enable_clip_fade=enable_clip_fade,
            segment_threshold=segment_threshold,
            min_duration=min_duration,
            max_duration=max_duration,
        ),
        capability="segment-scenes",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def analyze_video_highlights(
    video_path: Path,
    *,
    model: str,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[dict[str, Any], str]:
    return await _run_cloud_task(
        build_analyze_highlights_arguments([str(video_path)], model=model),
        capability="analyze-video-highlights",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def probe_video_metadata(
    video_path: Path,
    *,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[dict[str, Any], str]:
    return await _run_cloud_task(
        build_probe_metadata_arguments(str(video_path)),
        capability="probe-video-metadata",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )
