"""Safe subprocess adapter for the official MediaKit CLI."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .errors import (
    MediaKitCommandError,
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


def run_cli(
    arguments: Sequence[str],
    *,
    timeout: int = 14_400,
    env: Mapping[str, str] | None = None,
    expect_json: bool = True,
) -> CommandResult:
    """Run MediaKit CLI without invoking a shell."""
    executable = find_cli()
    command = [executable, *map(str, arguments)]
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
