"""Safe subprocess adapter for the official MediaKit CLI."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .errors import (
    MediaKitCommandError,
    MediaKitCompatibilityError,
    MediaKitConfigurationError,
    MediaKitDependencyError,
    MediaKitInputError,
    MediaKitTaskError,
)
from .redaction import redact_text


@dataclass(frozen=True)
class CommandResult:
    payload: dict[str, Any]
    stdout: str
    stderr: str
    returncode: int


def find_cli() -> str:
    """Return the MediaKit executable or raise an actionable error."""
    executable = shutil.which("mediakit-cli")
    if executable:
        return executable
    raise MediaKitDependencyError(
        "找不到 mediakit-cli。请先安装官方 CLI："
        "npx @volcengine/mediakit-cli install -y，然后重启 ComfyUI。"
    )


def extract_json_objects(output: str) -> list[dict[str, Any]]:
    """Extract JSON objects from mixed human-readable CLI output."""
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    for index, character in enumerate(output):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append(value)
    return objects


def parse_final_json(output: str) -> dict[str, Any]:
    """Return the final JSON object emitted by a CLI command."""
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    for index, character in enumerate(output):
        if character != "{":
            continue
        try:
            value, consumed = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append((index, index + consumed, value))
    if candidates:
        # The final top-level object ends furthest to the right. Choosing by
        # start offset would incorrectly return a nested `result` object.
        return max(candidates, key=lambda item: (item[1], -item[0]))[2]
    raise MediaKitCommandError(
        "无法解析 MediaKit CLI 返回结果。输出末尾：\n"
        + redact_text(output[-3000:])
    )


def _classify_failure(payload: Mapping[str, Any], combined: str) -> None:
    error = payload.get("error")
    status = str(payload.get("status", "")).lower()
    searchable = f"{error!s}\n{combined}".lower()
    if any(token in searchable for token in ("authentication", "unauthorized", "api key", "apikey")):
        raise MediaKitConfigurationError(
            "MediaKit 鉴权失败。请运行 mediakit-cli init --api-key <YOUR_API_KEY> --yes，"
            "或为 ComfyUI 进程设置 MEDIAKIT_API_KEY。"
        )
    if (
        error
        or status in {"failed", "canceled", "cancelled"}
        or payload.get("success") is False
    ):
        detail = error if error else payload
        raise MediaKitTaskError(
            "MediaKit 任务失败：" + redact_text(json.dumps(detail, ensure_ascii=False))
        )


def normalize_mode_arguments(executable: str, arguments: Sequence[str]) -> list[str]:
    """Probe help before a business call; never retry a paid submission.

    Older binaries expose --cloud/--local. The current cloud-only binary
    removed both flags. Only strip --cloud when help positively identifies
    the cloud-only interface. Never downgrade a requested local call to cloud.
    """
    args = list(map(str, arguments))
    if not args or args[0] not in ("--cloud", "--local"):
        return args
    try:
        help_result = subprocess.run(
            [executable, "--help"], capture_output=True, text=True,
            timeout=30, shell=False, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MediaKitCompatibilityError("无法读取 CLI 模式合同；未提交任务。") from exc
    text = help_result.stdout + "\n" + help_result.stderr
    if help_result.returncode != 0:
        raise MediaKitCompatibilityError("CLI help 读取失败；未提交任务。")
    flag = args[0]
    if re.search(r"(?m)^\s*" + re.escape(flag) + r"(?:[ =\t]|$)", text):
        return args
    cloud_only = "Cloud media-processing commands" in text
    if flag == "--cloud" and cloud_only:
        return args[1:]
    raise MediaKitCompatibilityError(
        f"当前 CLI 未声明支持 {flag}；未提交任务，也不会自动改为付费云端调用。"
    )


def run_cli(
    arguments: Sequence[str],
    *,
    timeout: int = 14_400,
    env: Mapping[str, str] | None = None,
    expect_json: bool = True,
) -> CommandResult:
    """Run MediaKit CLI without invoking a shell."""
    executable = find_cli()
    command = [executable, *normalize_mode_arguments(executable, arguments)]
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    # MediaKit requires integrations to identify their request surface. Do not
    # inherit a stale `skill` value from the parent shell when running as a
    # ComfyUI plugin.
    process_env["MEDIAKIT_SURFACE"] = "plugin"
    process_env["MEDIAKIT_RUNTIME"] = "comfyui"

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=process_env,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaKitCommandError(
            f"MediaKit CLI 超时（{timeout} 秒）。云端任务可能仍在运行。"
        ) from exc
    except OSError as exc:
        raise MediaKitCommandError(f"无法启动 MediaKit CLI：{exc}") from exc

    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    if expect_json:
        payload = parse_final_json(combined)
    else:
        payload = {}

    if completed.returncode != 0:
        if payload:
            _classify_failure(payload, combined)
        raise MediaKitCommandError(
            f"MediaKit CLI 执行失败（退出码 {completed.returncode}）：\n"
            + redact_text(combined[-4000:])
        )

    if payload:
        _classify_failure(payload, combined)

    return CommandResult(
        payload=payload,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


async def run_cli_async(
    arguments: Sequence[str],
    *,
    timeout: int = 14_400,
    expect_json: bool = True,
) -> CommandResult:
    """Execute the blocking CLI adapter outside ComfyUI's event loop."""
    return await asyncio.to_thread(
        run_cli,
        arguments,
        timeout=timeout,
        expect_json=expect_json,
    )


def cli_version() -> str:
    """Return a single-line CLI version suitable for diagnostics."""
    result = run_cli(["version"], timeout=30, expect_json=False)
    text = (result.stdout or result.stderr).strip()
    return redact_text(text) or "已安装（未返回版本文本）"


def build_enhance_arguments(
    video_path: str,
    *,
    tool_version: str,
    scene: str,
    resolution: str,
    bitrate_level: str = "medium",
    fps: float = 0.0,
) -> list[str]:
    arguments = [
        "--cloud",
        "video",
        "enhance-video",
        "--video-url",
        video_path,
        "--tool-version",
        tool_version,
    ]
    if tool_version == "standard":
        arguments.extend(["--scene", scene])
    if resolution != "keep":
        arguments.extend(["--resolution", resolution])
    if bitrate_level not in {"low", "medium", "high"}:
        raise MediaKitInputError(f"不支持的码率档位：{bitrate_level}")
    arguments.extend(["--bitrate-level", bitrate_level])
    if fps < 0 or fps > 120:
        raise MediaKitInputError("目标帧率必须为 0（保持原值）或不超过 120。")
    if fps > 0:
        arguments.extend(["--fps", str(fps)])
    return arguments


def build_generative_enhance_arguments(
    video_path: str,
    *,
    resolution: str,
    bitrate_level: str,
    fps: float = 0.0,
) -> list[str]:
    """Build the official generative video restoration command."""
    if resolution not in {"720p", "1080p"}:
        raise MediaKitInputError(
            f"大模型画质增强仅支持 720p 或 1080p，当前为：{resolution}"
        )
    if bitrate_level not in {"low", "medium", "high"}:
        raise MediaKitInputError(f"不支持的码率档位：{bitrate_level}")
    if fps != 0 and not 15 <= fps <= 120:
        raise MediaKitInputError(
            "大模型画质增强帧率必须为 0（保持原值）或 15 到 120。"
        )

    arguments = [
        "--cloud",
        "video",
        "enhance-video-generative",
        "--video-url",
        video_path,
        "--resolution",
        resolution,
        "--bitrate-level",
        bitrate_level,
    ]
    if fps > 0:
        arguments.extend(["--fps", str(fps)])
    return arguments


def build_erase_subtitle_arguments(
    video_path: str,
    *,
    professional: bool,
    mode: str = "Subtitle",
    output_encode_mode: str = "Quality",
    erase_region: Mapping[str, float] | None = None,
) -> list[str]:
    """Build a cloud subtitle-erasure command from validated values."""
    tool = "erase-video-subtitle-pro" if professional else "erase-video-subtitle"
    arguments = ["--cloud", "video", tool, "--video-url", video_path]
    if not professional:
        return arguments

    if mode not in {"Subtitle", "Text"}:
        raise MediaKitInputError(f"不支持的字幕擦除模式：{mode}")
    if output_encode_mode not in {"Quality", "Size"}:
        raise MediaKitInputError(f"不支持的输出编码模式：{output_encode_mode}")
    arguments.extend(
        ["--mode", mode, "--output-encode-mode", output_encode_mode]
    )

    if erase_region is not None:
        required = (
            "top_left_x",
            "top_left_y",
            "bottom_right_x",
            "bottom_right_y",
        )
        try:
            region = {key: float(erase_region[key]) for key in required}
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaKitInputError("字幕擦除框缺少有效的坐标值。") from exc
        if any(value < 0 or value > 1 for value in region.values()):
            raise MediaKitInputError("字幕擦除框坐标必须位于 0 到 1 之间。")
        if not (
            region["top_left_x"] < region["bottom_right_x"]
            and region["top_left_y"] < region["bottom_right_y"]
        ):
            raise MediaKitInputError("字幕擦除框的右下角必须位于左上角右下方。")
        arguments.extend(
            [
                "--erase-ratio-location",
                json.dumps([region], ensure_ascii=False, separators=(",", ":")),
            ]
        )
    return arguments


def build_query_arguments(
    task_id: str,
    *,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> list[str]:
    return [
        "shared",
        "query-task",
        "--task-id",
        task_id,
        "--poll-complete",
        "--poll-interval-seconds",
        str(poll_interval_seconds),
        "--max-poll-attempts",
        str(max_poll_attempts),
    ]


def build_asr_subtitles_arguments(
    video_path: str,
    *,
    content_type: str = "auto",
    language: str = "auto",
    enable_speaker_info: bool = False,
    enable_confidence: bool = False,
) -> list[str]:
    """Build the official cloud ASR (speech-to-subtitle) command."""
    if content_type not in {"auto", "speech", "singing"}:
        raise MediaKitInputError(f"不支持的识别类型：{content_type}")
    if language not in {"auto", "cmn-Hans-CN", "eng-US"}:
        raise MediaKitInputError(f"不支持的识别语言：{language}")
    arguments = [
        "--cloud",
        "video",
        "asr-subtitles",
        "--video-url",
        video_path,
    ]
    if content_type != "auto":
        arguments.extend(["--content-type", content_type])
    if language != "auto":
        arguments.extend(["--language", language])
    if enable_speaker_info:
        arguments.append("--enable-speaker-info")
    if enable_confidence:
        arguments.append("--enable-confidence")
    return arguments


def build_video_ocr_arguments(
    video_path: str,
    *,
    mode: str = "Subtitle",
) -> list[str]:
    """Build the official cloud video OCR command."""
    if mode not in {"Subtitle", "Detailed"}:
        raise MediaKitInputError(f"不支持的 OCR 模式：{mode}")
    arguments = ["--cloud", "video", "video-ocr", "--video-url", video_path]
    if mode != "Subtitle":
        arguments.extend(["--mode", mode])
    return arguments


def build_matte_video_arguments(
    video_path: str,
    *,
    tool: str,
    output_format: str = "WEBM",
) -> list[str]:
    """Build a cloud matting command (portrait or greenscreen)."""
    if tool not in {"matte-portrait-video", "matte-greenscreen-video"}:
        raise MediaKitInputError(f"不支持的抠图工具：{tool}")
    if output_format not in {"MOV", "WEBM"}:
        raise MediaKitInputError(f"不支持的输出格式：{output_format}")
    arguments = ["--cloud", "video", tool, "--video-url", video_path]
    if output_format != "WEBM":
        arguments.extend(["--format", output_format])
    return arguments


def build_segment_scenes_arguments(
    video_path: str,
    *,
    enable_clip_fade: bool = False,
    segment_threshold: float | None = None,
    min_duration: float | None = None,
    max_duration: float | None = None,
) -> list[str]:
    """Build the official cloud scene-segmentation command."""
    if segment_threshold is not None and not 0 <= segment_threshold < 100:
        raise MediaKitInputError("场景切分阈值必须在 [0, 100) 范围内。")
    if min_duration is not None and min_duration < 0:
        raise MediaKitInputError("切片最小时长不能为负数。")
    if max_duration is not None and max_duration < 0:
        raise MediaKitInputError("切片最大时长不能为负数。")
    if (
        min_duration is not None
        and max_duration is not None
        and min_duration > max_duration
    ):
        raise MediaKitInputError("切片最小时长不能大于最大时长。")
    arguments = ["--cloud", "video", "segment-scenes", "--video-url", video_path]
    if enable_clip_fade:
        arguments.append("--enable-clip-fade")
    if segment_threshold is not None:
        arguments.extend(["--segment-threshold", str(segment_threshold)])
    if min_duration is not None:
        arguments.extend(["--min-duration", str(min_duration)])
    if max_duration is not None:
        arguments.extend(["--max-duration", str(max_duration)])
    return arguments


def build_analyze_highlights_arguments(
    video_paths: Sequence[str],
    *,
    model: str,
) -> list[str]:
    """Build the official cloud highlight-analysis command."""
    if model not in {"Miniseries", "Game"}:
        raise MediaKitInputError(f"不支持的高光分析模型：{model}")
    if not video_paths:
        raise MediaKitInputError("高光片段提取至少需要一个视频。")
    mode = "StorylineCuts" if model == "Miniseries" else "HighlightExtract"
    return [
        "--cloud",
        "video",
        "analyze-video-highlights",
        "--video-urls",
        json.dumps(list(video_paths), ensure_ascii=False, separators=(",", ":")),
        "--model",
        model,
        "--mode",
        mode,
    ]


def build_probe_metadata_arguments(
    video_path: str,
    *,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-metadata probe command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    return prefix + ["video", "probe-video-metadata", "--video-url", video_path]


def supported_modes(domain: str, tool: str) -> set[str]:
    """Return the modes a capability supports, e.g. {"Cloud", "Local"}.

    Parsed from ``<domain> <tool> --help`` output. An empty set means the
    information is unavailable (unknown CLI version or a transient error),
    and callers must fall back to cloud-only behavior.
    """
    try:
        result = run_cli([domain, tool, "--help"], timeout=60, expect_json=False)
    except (MediaKitCommandError, MediaKitDependencyError):
        return set()
    text = result.stdout or result.stderr
    modes: set[str] = set()
    for line in text.splitlines():
        if "支持模式" in line:
            _head, _sep, rest = line.partition(":")
            for token in rest.split(","):
                token = token.strip()
                if token:
                    modes.add(token)
    return modes


def build_trim_video_arguments(
    video_path: str,
    *,
    start_time: float,
    end_time: float | None = None,
    run_mode: str = "cloud",
    client_token: str | None = None,
) -> list[str]:
    """Build a video trim command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if start_time < 0:
        raise MediaKitInputError("裁剪开始时间不能为负数。")
    if end_time is not None and end_time <= start_time:
        raise MediaKitInputError("裁剪结束时间必须大于开始时间。")
    if client_token is not None and (
        not client_token or len(client_token) > 64
        or any(not 32 <= ord(c) <= 126 for c in client_token)
    ):
        raise MediaKitInputError(
            "client_token 必须是非空 ASCII 字符串且长度不超过 64。"
        )
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "trim-video", "--video-url", video_path]
    arguments.extend(["--start-time", str(start_time)])
    if end_time is not None:
        arguments.extend(["--end-time", str(end_time)])
    if client_token is not None:
        arguments.extend(["--client-token", client_token])
    return arguments


def build_extract_audio_arguments(
    video_path: str,
    *,
    output_format: str = "m4a",
    run_mode: str = "cloud",
) -> list[str]:
    """Build an audio-extraction command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if output_format not in {"mp3", "m4a", "ogg", "flac", "wav"}:
        raise MediaKitInputError(f"不支持的输出音频格式：{output_format}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "extract-audio", "--video-url", video_path]
    if output_format != "m4a":
        arguments.extend(["--format", output_format])
    return arguments


def build_adjust_video_speed_arguments(
    video_path: str,
    *,
    speed: float = 1.0,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-speed command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if not 0.1 <= speed <= 4.0:
        raise MediaKitInputError("播放速度倍数需在 0.1～4.0 之间。")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "adjust-video-speed", "--video-url", video_path]
    if speed != 1.0:
        arguments.extend(["--speed", str(speed)])
    return arguments


def build_adjust_video_volume_arguments(
    video_path: str,
    *,
    volume: float = 1.0,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-volume command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if not 0 <= volume <= 4:
        raise MediaKitInputError("音量调整倍数需在 0～4 之间。")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "adjust-video-volume", "--video-url", video_path]
    if volume != 1.0:
        arguments.extend(["--volume", str(volume)])
    return arguments


def build_apply_camera_motion_arguments(
    video_path: str,
    *,
    motion_style: str = "zoom",
    start_time: float = 0.0,
    end_time: float | None = None,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a camera-motion command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if motion_style not in {"zoom", "pan-zoom", "orbit-360", "bounce"}:
        raise MediaKitInputError(f"不支持的运镜风格：{motion_style}")
    if start_time < 0:
        raise MediaKitInputError("运镜开始时间不能为负数。")
    if end_time is not None and end_time <= start_time:
        raise MediaKitInputError("运镜结束时间必须大于开始时间。")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "apply-camera-motion", "--video-url", video_path]
    if motion_style != "zoom":
        arguments.extend(["--motion-style", motion_style])
    if start_time != 0.0:
        arguments.extend(["--start-time", str(start_time)])
    if end_time is not None:
        arguments.extend(["--end-time", str(end_time)])
    return arguments


def build_apply_video_filter_arguments(
    video_path: str,
    *,
    filter_style: str = "spring",
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-filter command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if filter_style not in {"spring", "sunset", "vivid", "fair_skin", "food"}:
        raise MediaKitInputError(f"不支持的滤镜风格：{filter_style}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "apply-video-filter", "--video-url", video_path]
    if filter_style != "spring":
        arguments.extend(["--filter-style", filter_style])
    return arguments


def build_flip_video_arguments(
    video_path: str,
    *,
    is_flip_horizontal: bool = False,
    is_flip_vertical: bool = False,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-flip command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if not is_flip_horizontal and not is_flip_vertical:
        raise MediaKitInputError("水平翻转和垂直翻转至少需要开启一项。")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "flip-video", "--video-url", video_path]
    if is_flip_horizontal:
        arguments.append("--is-flip-horizontal")
    if is_flip_vertical:
        arguments.append("--is-flip-vertical")
    return arguments


def build_rotate_video_arguments(
    video_path: str,
    *,
    rotate_direction: str,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-rotate command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if rotate_direction not in {"rotate_left_90", "rotate_right_90", "rotate_180"}:
        raise MediaKitInputError(f"不支持的旋转方向：{rotate_direction}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + [
        "editing",
        "rotate-video",
        "--video-url",
        video_path,
        "--rotate-direction",
        rotate_direction,
    ]
    return arguments


def build_concat_video_arguments(
    video_paths: Sequence[str],
    *,
    transitions: Sequence[str] | None = None,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-concat command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if not 1 <= len(video_paths) <= 100:
        raise MediaKitInputError("拼接视频数量需在 1～100 之间。")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "concat-video"]
    for path in video_paths:
        arguments.extend(["--video-urls", path])
    if transitions:
        for transition in transitions:
            arguments.extend(["--transitions", transition])
    return arguments


def build_concat_audio_arguments(
    audio_paths: Sequence[str],
    *,
    output_format: str = "m4a",
    run_mode: str = "cloud",
) -> list[str]:
    """Build an audio-concat command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if not 1 <= len(audio_paths) <= 100:
        raise MediaKitInputError("拼接音频数量需在 1～100 之间。")
    if output_format not in {"mp3", "m4a", "ogg", "flac", "wav"}:
        raise MediaKitInputError(f"不支持的输出音频格式：{output_format}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "concat-audio"]
    for path in audio_paths:
        arguments.extend(["--audio-urls", path])
    if output_format != "m4a":
        arguments.extend(["--format", output_format])
    return arguments


def build_mix_audio_arguments(
    audio_paths: Sequence[str],
    *,
    output_format: str = "m4a",
    run_mode: str = "cloud",
) -> list[str]:
    """Build an audio-mix command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if not 1 <= len(audio_paths) <= 100:
        raise MediaKitInputError("混音音频数量需在 1～100 之间。")
    if output_format not in {"mp3", "m4a", "ogg", "flac", "wav"}:
        raise MediaKitInputError(f"不支持的输出音频格式：{output_format}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "mix-audio"]
    for path in audio_paths:
        arguments.extend(["--audio-urls", path])
    if output_format != "m4a":
        arguments.extend(["--format", output_format])
    return arguments


def build_mux_audio_video_arguments(
    video_path: str,
    audio_path: str,
    *,
    is_audio_reserve: bool = True,
    is_video_audio_sync: bool = False,
    sync_method: str = "trim",
    sync_mode: str = "video",
    run_mode: str = "cloud",
) -> list[str]:
    """Build an audio-video mux command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if sync_method not in {"trim", "speed"}:
        raise MediaKitInputError(f"不支持的对齐方式：{sync_method}")
    if sync_mode not in {"video", "audio"}:
        raise MediaKitInputError(f"不支持的对齐基准：{sync_mode}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + [
        "editing",
        "mux-audio-video",
        "--video-url",
        video_path,
        "--audio-url",
        audio_path,
    ]
    if not is_audio_reserve:
        arguments.append("--is-audio-reserve=false")
    if is_video_audio_sync:
        arguments.append("--is-video-audio-sync=true")
        if sync_method != "trim":
            arguments.extend(["--sync-method", sync_method])
        if sync_mode != "video":
            arguments.extend(["--sync-mode", sync_mode])
    return arguments


def build_add_subtitle_arguments(
    video_path: str,
    *,
    subtitle_url: str | None = None,
    subtitles: Sequence[Mapping[str, Any]] | None = None,
    subtitle_font_type: str = "sy_black",
    subtitle_pos_preset: str = "bottom_center",
    subtitle_font_size: int = 50,
    subtitle_font_color: str = "#FFFFFFFF",
    subtitle_text_effect: str | None = None,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a burn-subtitle command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if subtitle_font_type not in {"sy_black", "pm_zhengdao", "zhanku_kuaile"}:
        raise MediaKitInputError(f"不支持的字体：{subtitle_font_type}")
    if subtitle_pos_preset not in {
        "bottom_center",
        "top_center",
        "center",
        "lower_third",
    }:
        raise MediaKitInputError(f"不支持的字幕位置预设：{subtitle_pos_preset}")
    if subtitle_font_size <= 0:
        raise MediaKitInputError("字幕字号必须为正数。")
    import math
    if subtitle_url is not None and (not isinstance(subtitle_url, str) or not subtitle_url.strip()):
        raise MediaKitInputError("字幕文件地址不能为空。")
    if not subtitle_url and not subtitles:
        raise MediaKitInputError("字幕文件 URL 与非空字幕列表至少需要提供一项。")
    if subtitles is not None:
        if not isinstance(subtitles, (list, tuple)) or not subtitles:
            raise MediaKitInputError("字幕列表必须是非空数组。")
        for item in subtitles:
            if not isinstance(item, Mapping) or not all(key in item for key in ("subtitle_text", "start_time", "end_time")):
                raise MediaKitInputError("字幕对象需包含 subtitle_text、start_time、end_time 字段。")
            if not isinstance(item["subtitle_text"], str):
                raise MediaKitInputError("字幕文本必须为字符串。")
            start, end = item["start_time"], item["end_time"]
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (start, end)):
                raise MediaKitInputError("字幕时间必须是有限数值。")
            if start < 0 or end <= start:
                raise MediaKitInputError("字幕开始时间须非负，结束时间必须大于开始时间。")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "add-subtitle-to-video", "--video-url", video_path]
    if subtitle_url:
        arguments.extend(["--subtitle-url", subtitle_url])
    if subtitles:
        arguments.extend(
            ["--subtitles", json.dumps(list(subtitles), ensure_ascii=False)]
        )
    if subtitle_font_type != "sy_black":
        arguments.extend(["--subtitle-font-type", subtitle_font_type])
    if subtitle_pos_preset != "bottom_center":
        arguments.extend(["--subtitle-pos-preset", subtitle_pos_preset])
    if subtitle_font_size != 50:
        arguments.extend(["--subtitle-font-size", str(subtitle_font_size)])
    if subtitle_font_color != "#FFFFFFFF":
        arguments.extend(["--subtitle-font-color", subtitle_font_color])
    if subtitle_text_effect:
        arguments.extend(["--subtitle-text-effect", subtitle_text_effect])
    return arguments


def build_stitch_video_arguments(
    video_paths: Sequence[str],
    *,
    stitch_direction: str,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-stitch command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if not 2 <= len(video_paths) <= 3:
        raise MediaKitInputError("拼合视频数量需在 2～3 之间。")
    if stitch_direction not in {"horizontal", "vertical"}:
        raise MediaKitInputError(f"不支持的拼合方向：{stitch_direction}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    videos = json.dumps(
        [{"video_url": path} for path in video_paths], ensure_ascii=False
    )
    arguments = prefix + [
        "editing",
        "stitch-video",
        "--videos",
        videos,
        "--stitch-direction",
        stitch_direction,
    ]
    return arguments


def build_crop_video_arguments(
    video_path: str,
    *,
    top_left_x: int,
    top_left_y: int,
    bottom_right_x: int,
    bottom_right_y: int,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-crop command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if top_left_x < 0 or top_left_y < 0:
        raise MediaKitInputError("裁剪区域左上角坐标不能为负数。")
    if bottom_right_x <= top_left_x or bottom_right_y <= top_left_y:
        raise MediaKitInputError("裁剪区域右下角坐标必须大于左上角坐标。")
    if bottom_right_x - top_left_x < 16 or bottom_right_y - top_left_y < 16:
        raise MediaKitInputError("裁剪区域的宽和高不得小于 16 像素。")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + [
        "editing",
        "crop-video",
        "--video-url",
        video_path,
        "--top-left-x",
        str(top_left_x),
        "--top-left-y",
        str(top_left_y),
        "--bottom-right-x",
        str(bottom_right_x),
        "--bottom-right-y",
        str(bottom_right_y),
    ]
    return arguments


#: Output formats accepted by the audio editing tools.
_AUDIO_FORMATS = ("mp3", "m4a", "ogg", "flac", "wav")


def build_adjust_audio_speed_arguments(
    audio_path: str,
    *,
    speed: float = 1.0,
    output_format: str = "m4a",
    run_mode: str = "cloud",
) -> list[str]:
    """Build an audio speed-change command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if not 0.1 <= speed <= 4.0:
        raise MediaKitInputError("音频变速倍速需在 0.1～4.0 之间。")
    if output_format not in _AUDIO_FORMATS:
        raise MediaKitInputError(f"不支持的输出格式：{output_format}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "adjust-audio-speed", "--audio-url", audio_path]
    if speed != 1.0:
        arguments.extend(["--speed", str(speed)])
    if output_format != "m4a":
        arguments.extend(["--format", output_format])
    return arguments


def build_trim_audio_arguments(
    audio_path: str,
    *,
    start_time: float = 0.0,
    end_time: float | None = None,
    output_format: str = "m4a",
    run_mode: str = "cloud",
) -> list[str]:
    """Build an audio-trim command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if start_time < 0:
        raise MediaKitInputError("裁剪起点不能为负数。")
    if end_time is not None and end_time <= start_time:
        raise MediaKitInputError("裁剪终点必须大于起点。")
    if output_format not in _AUDIO_FORMATS:
        raise MediaKitInputError(f"不支持的输出格式：{output_format}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "trim-audio", "--audio-url", audio_path]
    if start_time != 0.0:
        arguments.extend(["--start-time", str(start_time)])
    if end_time is not None:
        arguments.extend(["--end-time", str(end_time)])
    if output_format != "m4a":
        arguments.extend(["--format", output_format])
    return arguments


def build_fade_audio_arguments(
    audio_path: str,
    *,
    fade_in_duration: float = 1.0,
    fade_out_duration: float = 1.0,
    output_format: str = "mp3",
    run_mode: str = "cloud",
) -> list[str]:
    """Build an audio fade command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if fade_in_duration < 0 or fade_out_duration < 0:
        raise MediaKitInputError("淡入淡出时长不能为负数。")
    if output_format not in _AUDIO_FORMATS:
        raise MediaKitInputError(f"不支持的输出格式：{output_format}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + ["editing", "fade-audio", "--audio-url", audio_path]
    if fade_in_duration != 1.0:
        arguments.extend(["--fade-in-duration", str(fade_in_duration)])
    if fade_out_duration != 1.0:
        arguments.extend(["--fade-out-duration", str(fade_out_duration)])
    if output_format != "mp3":
        arguments.extend(["--format", output_format])
    return arguments


def build_fade_video_audio_arguments(
    video_path: str,
    *,
    fade_in_duration: float = 1.0,
    fade_out_duration: float = 1.0,
    run_mode: str = "cloud",
) -> list[str]:
    """Build a video-audio fade command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if fade_in_duration < 0 or fade_out_duration < 0:
        raise MediaKitInputError("淡入淡出时长不能为负数。")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + [
        "editing",
        "fade-video-audio",
        "--video-url",
        video_path,
    ]
    if fade_in_duration != 1.0:
        arguments.extend(["--fade-in-duration", str(fade_in_duration)])
    if fade_out_duration != 1.0:
        arguments.extend(["--fade-out-duration", str(fade_out_duration)])
    return arguments


def build_extract_animated_image_arguments(
    video_path: str,
    *,
    start_time: float,
    end_time: float,
    output_format: str = "gif",
    run_mode: str = "cloud",
) -> list[str]:
    """Build an animated-image extraction command for cloud or local execution."""
    if run_mode not in {"cloud", "local"}:
        raise MediaKitInputError(f"不支持的运行模式：{run_mode}")
    if start_time < 0:
        raise MediaKitInputError("动图起始时间不能为负数。")
    if end_time <= start_time:
        raise MediaKitInputError("动图结束时间必须大于起始时间。")
    if output_format not in {"gif", "webp"}:
        raise MediaKitInputError(f"不支持的动图格式：{output_format}")
    prefix = ["--local"] if run_mode == "local" else ["--cloud"]
    arguments = prefix + [
        "editing",
        "extract-animated-image",
        "--video-url",
        video_path,
        "--start-time",
        str(start_time),
        "--end-time",
        str(end_time),
    ]
    if output_format != "gif":
        arguments.extend(["--output-format", output_format])
    return arguments
