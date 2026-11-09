"""Capability orchestration shared by MediaKit cloud nodes."""

from __future__ import annotations

import asyncio
from time import monotonic
from pathlib import Path
from typing import Any, Mapping, Sequence

from .cli import (
    build_add_subtitle_arguments,
    build_adjust_audio_speed_arguments,
    build_adjust_video_speed_arguments,
    build_adjust_video_volume_arguments,
    build_analyze_highlights_arguments,
    build_apply_camera_motion_arguments,
    build_apply_video_filter_arguments,
    build_asr_subtitles_arguments,
    build_concat_audio_arguments,
    build_concat_video_arguments,
    build_crop_video_arguments,
    build_enhance_arguments,
    build_erase_subtitle_arguments,
    build_extract_animated_image_arguments,
    build_extract_audio_arguments,
    build_fade_audio_arguments,
    build_fade_video_audio_arguments,
    build_flip_video_arguments,
    build_generative_enhance_arguments,
    build_matte_video_arguments,
    build_mix_audio_arguments,
    build_mux_audio_video_arguments,
    build_probe_metadata_arguments,
    build_query_arguments,
    build_rotate_video_arguments,
    build_segment_scenes_arguments,
    build_stitch_video_arguments,
    build_trim_audio_arguments,
    build_trim_video_arguments,
    build_video_ocr_arguments,
    run_cli_async,
    supported_modes,
)
from .errors import MediaKitTaskError
from .logging_utils import log_event


def resolve_run_mode(domain: str, tool: str, requested: str) -> str:
    """Decide between ``local`` and ``cloud`` execution.

    ``requested`` is ``auto`` (use local when the installed CLI supports it,
    otherwise cloud) or ``cloud`` (force cloud). ``local`` is never forced
    from node parameters: older CLI builds do not implement local mode, so a
    forced selection would fail at runtime.
    """
    if requested == "cloud":
        return "cloud"
    modes = supported_modes(domain, tool)
    if "Local" in modes or "local" in modes:
        return "local"
    return "cloud"


def _local_result_path(payload: dict[str, Any]) -> Path:
    """Extract the output path of a synchronous local-mode CLI result."""
    value = _result_media_url(payload, error="本地任务完成，但未返回输出路径。")
    return Path(value).expanduser().resolve()


def _task_id(payload: dict[str, Any]) -> str:
    value = payload.get("task_id")
    if not isinstance(value, str) or not value:
        raise MediaKitTaskError("MediaKit CLI 未返回 task_id。")
    return value


#: Result URL keys a MediaKit task may return, in preference order.
_MEDIA_URL_KEYS: tuple[str, ...] = ("video_url", "audio_url", "image_url", "url")


def _result_media_url(
    payload: dict[str, Any],
    *,
    error: str = "MediaKit 任务完成，但未返回媒体 URL。",
) -> str:
    """Return the first media URL in a task result payload.

    MediaKit editing/understanding tasks may return ``video_url``,
    ``audio_url``, or ``image_url`` depending on the capability; the CLI also
    flattens ``result`` fields, so both shapes are supported.
    """
    value: Any = None
    for key in _MEDIA_URL_KEYS:
        if payload.get(key):
            value = payload[key]
            break
    if not value and isinstance(payload.get("result"), dict):
        for key in _MEDIA_URL_KEYS:
            if payload["result"].get(key):
                value = payload["result"][key]
                break
    if not isinstance(value, str) or not value:
        raise MediaKitTaskError(error)
    return value


def _result_video_url(payload: dict[str, Any]) -> str:
    """Return the primary media URL of a finished task (backward-compatible)."""
    return _result_media_url(payload)


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


_TERMINAL_STATUSES = ("completed", "failed", "canceled", "cancelled")


async def _poll_until_terminal(
    task_id: str,
    *,
    poll_interval_seconds: int,
    max_poll_attempts: int,
    capability: str,
    flatten: bool,
) -> dict[str, Any]:
    """Poll one task_id across CLI 9-minute windows without resubmitting.

    A single ``query-task --poll-complete`` call can return ``running`` when the
    window ends. Re-issue the *same* task_id until a terminal state arrives so a
    long-running task is never mistaken for completion and never duplicated.
    """
    if poll_interval_seconds <= 0 or max_poll_attempts <= 0:
        raise MediaKitTaskError("轮询间隔和次数必须为正数。")
    # max_poll_attempts is a total waiting budget, not multiplied by 120
    # independent CLI windows. Queries are read-only and never resubmit.
    deadline = monotonic() + poll_interval_seconds * max_poll_attempts
    for _ in range(120):
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        window_attempts = max(1, min(
            max_poll_attempts,
            int(min(540, remaining) / poll_interval_seconds),
        ))
        try:
            result = await asyncio.wait_for(
                run_cli_async(
                    build_query_arguments(
                        task_id,
                        poll_interval_seconds=poll_interval_seconds,
                        max_poll_attempts=window_attempts,
                    ),
                    timeout=min(600, remaining),
                ),
                timeout=remaining,
            )
        except (asyncio.TimeoutError, TimeoutError):
            break
        payload = _flatten_result(result.payload) if flatten else result.payload
        status = payload.get("status")
        if status in _TERMINAL_STATUSES or payload.get("success") is False:
            return payload
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(poll_interval_seconds, remaining))
    raise MediaKitTaskError(
        f"MediaKit 任务 {capability} 未在总轮询时间内进入终态，"
        f"请查询原 task_id={task_id}，不要重新提交。"
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
        payload = await _poll_until_terminal(
            task_id,
            poll_interval_seconds=poll_interval_seconds,
            max_poll_attempts=max_poll_attempts,
            capability=capability,
            flatten=True,
        )
        result_url = _result_video_url(payload)
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
        payload = await _poll_until_terminal(
            task_id,
            poll_interval_seconds=poll_interval_seconds,
            max_poll_attempts=max_poll_attempts,
            capability=capability,
            flatten=True,
        )
        log_event("task_completed", capability=capability, task_id=task_id)
        return payload, task_id
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
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[dict[str, Any], str]:
    mode = resolve_run_mode("video", "probe-video-metadata", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="probe-video-metadata")
        result = await run_cli_async(
            build_probe_metadata_arguments(str(video_path), run_mode="local"),
            timeout=600,
        )
        return _flatten_result(result.payload), ""
    return await _run_cloud_task(
        build_probe_metadata_arguments(str(video_path)),
        capability="probe-video-metadata",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def trim_video(
    video_path: Path,
    *,
    start_time: float,
    end_time: float | None,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
    client_token: str | None = None,
) -> tuple[str, str]:
    """Trim a video locally when supported, otherwise through the cloud."""
    mode = resolve_run_mode("editing", "trim-video", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-trim-video")
        result = await run_cli_async(
            build_trim_video_arguments(
                str(video_path),
                start_time=start_time,
                end_time=end_time,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_trim_video_arguments(
            str(video_path),
            start_time=start_time,
            end_time=end_time,
            run_mode="cloud",
            client_token=client_token,
        ),
        capability="editing-trim-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def extract_audio(
    video_path: Path,
    *,
    output_format: str,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Extract an audio track locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "extract-audio", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-extract-audio")
        result = await run_cli_async(
            build_extract_audio_arguments(
                str(video_path),
                output_format=output_format,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_extract_audio_arguments(
            str(video_path),
            output_format=output_format,
            run_mode="cloud",
        ),
        capability="editing-extract-audio",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def adjust_video_speed(
    video_path: Path,
    *,
    speed: float = 1.0,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Adjust video playback speed locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "adjust-video-speed", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-adjust-video-speed")
        result = await run_cli_async(
            build_adjust_video_speed_arguments(
                str(video_path), speed=speed, run_mode="local"
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_adjust_video_speed_arguments(str(video_path), speed=speed),
        capability="editing-adjust-video-speed",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def adjust_video_volume(
    video_path: Path,
    *,
    volume: float = 1.0,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Adjust video volume locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "adjust-video-volume", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-adjust-video-volume")
        result = await run_cli_async(
            build_adjust_video_volume_arguments(
                str(video_path), volume=volume, run_mode="local"
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_adjust_video_volume_arguments(str(video_path), volume=volume),
        capability="editing-adjust-video-volume",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def apply_camera_motion(
    video_path: Path,
    *,
    motion_style: str = "zoom",
    start_time: float = 0.0,
    end_time: float | None = None,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Apply a camera-motion effect locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "apply-camera-motion", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-apply-camera-motion")
        result = await run_cli_async(
            build_apply_camera_motion_arguments(
                str(video_path),
                motion_style=motion_style,
                start_time=start_time,
                end_time=end_time,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_apply_camera_motion_arguments(
            str(video_path),
            motion_style=motion_style,
            start_time=start_time,
            end_time=end_time,
        ),
        capability="editing-apply-camera-motion",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def apply_video_filter(
    video_path: Path,
    *,
    filter_style: str = "spring",
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Apply a video filter locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "apply-video-filter", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-apply-video-filter")
        result = await run_cli_async(
            build_apply_video_filter_arguments(
                str(video_path), filter_style=filter_style, run_mode="local"
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_apply_video_filter_arguments(str(video_path), filter_style=filter_style),
        capability="editing-apply-video-filter",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def flip_video(
    video_path: Path,
    *,
    is_flip_horizontal: bool = False,
    is_flip_vertical: bool = False,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Flip a video locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "flip-video", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-flip-video")
        result = await run_cli_async(
            build_flip_video_arguments(
                str(video_path),
                is_flip_horizontal=is_flip_horizontal,
                is_flip_vertical=is_flip_vertical,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_flip_video_arguments(
            str(video_path),
            is_flip_horizontal=is_flip_horizontal,
            is_flip_vertical=is_flip_vertical,
        ),
        capability="editing-flip-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def rotate_video(
    video_path: Path,
    *,
    rotate_direction: str,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Rotate a video locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "rotate-video", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-rotate-video")
        result = await run_cli_async(
            build_rotate_video_arguments(
                str(video_path), rotate_direction=rotate_direction, run_mode="local"
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_rotate_video_arguments(str(video_path), rotate_direction=rotate_direction),
        capability="editing-rotate-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def concat_videos(
    video_paths: Sequence[Path],
    *,
    transitions: Sequence[str] | None = None,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Concat videos locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "concat-video", run_mode)
    paths = [str(path) for path in video_paths]
    if mode == "local":
        log_event("local_task_started", capability="editing-concat-video")
        result = await run_cli_async(
            build_concat_video_arguments(
                paths, transitions=transitions, run_mode="local"
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_concat_video_arguments(paths, transitions=transitions),
        capability="editing-concat-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def concat_audios(
    audio_paths: Sequence[Path],
    *,
    output_format: str = "m4a",
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Concat audio locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "concat-audio", run_mode)
    paths = [str(path) for path in audio_paths]
    if mode == "local":
        log_event("local_task_started", capability="editing-concat-audio")
        result = await run_cli_async(
            build_concat_audio_arguments(
                paths, output_format=output_format, run_mode="local"
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_concat_audio_arguments(paths, output_format=output_format),
        capability="editing-concat-audio",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def mix_audios(
    audio_paths: Sequence[Path],
    *,
    output_format: str = "m4a",
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Mix audio locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "mix-audio", run_mode)
    paths = [str(path) for path in audio_paths]
    if mode == "local":
        log_event("local_task_started", capability="editing-mix-audio")
        result = await run_cli_async(
            build_mix_audio_arguments(
                paths, output_format=output_format, run_mode="local"
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_mix_audio_arguments(paths, output_format=output_format),
        capability="editing-mix-audio",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def mux_audio_video(
    video_path: Path,
    audio_path: Path,
    *,
    is_audio_reserve: bool = True,
    is_video_audio_sync: bool = False,
    sync_method: str = "trim",
    sync_mode: str = "video",
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Mux audio and video locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "mux-audio-video", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-mux-audio-video")
        result = await run_cli_async(
            build_mux_audio_video_arguments(
                str(video_path),
                str(audio_path),
                is_audio_reserve=is_audio_reserve,
                is_video_audio_sync=is_video_audio_sync,
                sync_method=sync_method,
                sync_mode=sync_mode,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_mux_audio_video_arguments(
            str(video_path),
            str(audio_path),
            is_audio_reserve=is_audio_reserve,
            is_video_audio_sync=is_video_audio_sync,
            sync_method=sync_method,
            sync_mode=sync_mode,
        ),
        capability="editing-mux-audio-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def add_subtitle_to_video(
    video_path: Path,
    *,
    subtitle_url: str | None = None,
    subtitles: Sequence[Mapping[str, Any]] | None = None,
    subtitle_font_type: str = "sy_black",
    subtitle_pos_preset: str = "bottom_center",
    subtitle_font_size: int = 50,
    subtitle_font_color: str = "#FFFFFFFF",
    subtitle_text_effect: str | None = None,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Burn subtitles locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "add-subtitle-to-video", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-add-subtitle-to-video")
        result = await run_cli_async(
            build_add_subtitle_arguments(
                str(video_path),
                subtitle_url=subtitle_url,
                subtitles=subtitles,
                subtitle_font_type=subtitle_font_type,
                subtitle_pos_preset=subtitle_pos_preset,
                subtitle_font_size=subtitle_font_size,
                subtitle_font_color=subtitle_font_color,
                subtitle_text_effect=subtitle_text_effect,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_add_subtitle_arguments(
            str(video_path),
            subtitle_url=subtitle_url,
            subtitles=subtitles,
            subtitle_font_type=subtitle_font_type,
            subtitle_pos_preset=subtitle_pos_preset,
            subtitle_font_size=subtitle_font_size,
            subtitle_font_color=subtitle_font_color,
            subtitle_text_effect=subtitle_text_effect,
        ),
        capability="editing-add-subtitle-to-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def stitch_videos(
    video_paths: Sequence[Path],
    *,
    stitch_direction: str,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Stitch videos locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "stitch-video", run_mode)
    paths = [str(path) for path in video_paths]
    if mode == "local":
        log_event("local_task_started", capability="editing-stitch-video")
        result = await run_cli_async(
            build_stitch_video_arguments(
                paths, stitch_direction=stitch_direction, run_mode="local"
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_stitch_video_arguments(paths, stitch_direction=stitch_direction),
        capability="editing-stitch-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def crop_video(
    video_path: Path,
    *,
    top_left_x: int,
    top_left_y: int,
    bottom_right_x: int,
    bottom_right_y: int,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Crop a video locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "crop-video", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-crop-video")
        result = await run_cli_async(
            build_crop_video_arguments(
                str(video_path),
                top_left_x=top_left_x,
                top_left_y=top_left_y,
                bottom_right_x=bottom_right_x,
                bottom_right_y=bottom_right_y,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_crop_video_arguments(
            str(video_path),
            top_left_x=top_left_x,
            top_left_y=top_left_y,
            bottom_right_x=bottom_right_x,
            bottom_right_y=bottom_right_y,
        ),
        capability="editing-crop-video",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def adjust_audio_speed(
    audio_path: Path,
    *,
    speed: float = 1.0,
    output_format: str = "m4a",
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Change audio speed locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "adjust-audio-speed", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-adjust-audio-speed")
        result = await run_cli_async(
            build_adjust_audio_speed_arguments(
                str(audio_path),
                speed=speed,
                output_format=output_format,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_adjust_audio_speed_arguments(
            str(audio_path), speed=speed, output_format=output_format
        ),
        capability="editing-adjust-audio-speed",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def trim_audio(
    audio_path: Path,
    *,
    start_time: float = 0.0,
    end_time: float | None = None,
    output_format: str = "m4a",
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Trim audio locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "trim-audio", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-trim-audio")
        result = await run_cli_async(
            build_trim_audio_arguments(
                str(audio_path),
                start_time=start_time,
                end_time=end_time,
                output_format=output_format,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_trim_audio_arguments(
            str(audio_path),
            start_time=start_time,
            end_time=end_time,
            output_format=output_format,
        ),
        capability="editing-trim-audio",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def fade_audio(
    audio_path: Path,
    *,
    fade_in_duration: float = 1.0,
    fade_out_duration: float = 1.0,
    output_format: str = "mp3",
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Fade audio in/out locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "fade-audio", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-fade-audio")
        result = await run_cli_async(
            build_fade_audio_arguments(
                str(audio_path),
                fade_in_duration=fade_in_duration,
                fade_out_duration=fade_out_duration,
                output_format=output_format,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_fade_audio_arguments(
            str(audio_path),
            fade_in_duration=fade_in_duration,
            fade_out_duration=fade_out_duration,
            output_format=output_format,
        ),
        capability="editing-fade-audio",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def fade_video_audio(
    video_path: Path,
    *,
    fade_in_duration: float = 1.0,
    fade_out_duration: float = 1.0,
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Fade a video's audio locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "fade-video-audio", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-fade-video-audio")
        result = await run_cli_async(
            build_fade_video_audio_arguments(
                str(video_path),
                fade_in_duration=fade_in_duration,
                fade_out_duration=fade_out_duration,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_fade_video_audio_arguments(
            str(video_path),
            fade_in_duration=fade_in_duration,
            fade_out_duration=fade_out_duration,
        ),
        capability="editing-fade-video-audio",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )


async def extract_animated_image(
    video_path: Path,
    *,
    start_time: float,
    end_time: float,
    output_format: str = "gif",
    run_mode: str = "auto",
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> tuple[str, str]:
    """Extract an animated image locally when supported, otherwise via cloud."""
    mode = resolve_run_mode("editing", "extract-animated-image", run_mode)
    if mode == "local":
        log_event("local_task_started", capability="editing-extract-animated-image")
        result = await run_cli_async(
            build_extract_animated_image_arguments(
                str(video_path),
                start_time=start_time,
                end_time=end_time,
                output_format=output_format,
                run_mode="local",
            ),
            timeout=600,
        )
        return str(_local_result_path(result.payload)), ""
    return await _run_cloud_video_task(
        build_extract_animated_image_arguments(
            str(video_path),
            start_time=start_time,
            end_time=end_time,
            output_format=output_format,
        ),
        capability="editing-extract-animated-image",
        poll_interval_seconds=poll_interval_seconds,
        max_poll_attempts=max_poll_attempts,
    )
