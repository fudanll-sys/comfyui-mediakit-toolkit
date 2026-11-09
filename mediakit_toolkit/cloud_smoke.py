"""Manual, paid MediaKit cloud smoke-test helpers.

These helpers contain no secrets. The GitHub Actions workflow injects
``MEDIAKIT_API_KEY`` through GitHub Secrets only when a human explicitly runs
the "Cloud Smoke (paid, manual)" workflow.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .errors import MediaKitConfigurationError, MediaKitTaskError
from .redaction import redact_text

_TERMINAL_SUCCESS = "completed"
_TERMINAL_FAILURE = {"failed", "canceled", "cancelled"}


@dataclass(frozen=True)
class SmokeResult:
    """Structured result of one paid cloud smoke run."""

    submit_payload: dict[str, object]
    terminal_payload: dict[str, object]
    result_url: str
    downloaded_bytes: int
    output_path: Path


def require_cli() -> str:
    """Return the MediaKit CLI path or raise an actionable configuration error."""
    executable = shutil.which("mediakit-cli")
    if not executable:
        raise MediaKitConfigurationError(
            "PATH 中找不到 mediakit-cli；请先安装官方 CLI 再运行云端冒烟。"
        )
    return executable


def require_api_key() -> None:
    """Fail before any paid call when the runtime has no API key."""
    if not os.environ.get("MEDIAKIT_API_KEY"):
        raise MediaKitConfigurationError(
            "缺少 MEDIAKIT_API_KEY；该工作流只能手动触发并从 GitHub Secrets 注入。"
        )


def run_json_command(
    arguments: Sequence[str],
    *,
    timeout: int,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    """Run a CLI command and parse its final JSON object without shell=True."""
    completed = runner(
        [require_cli(), *arguments],
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        raise MediaKitTaskError(
            f"MediaKit CLI 云端冒烟命令失败（退出码 {completed.returncode}）："
            + redact_text(combined[-2000:])
        )
    return parse_final_json(completed.stdout or completed.stderr)


def parse_final_json(output: str) -> dict[str, object]:
    """Return the final top-level JSON object emitted by the CLI."""
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, dict[str, object]]] = []
    for index, character in enumerate(output):
        if character != "{":
            continue
        try:
            value, consumed = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append((index, index + consumed, value))
    if not candidates:
        raise MediaKitTaskError("云端冒烟未解析到 JSON 结果：" + redact_text(output[-1000:]))
    return max(candidates, key=lambda item: (item[1], -item[0]))[2]


def build_trim_arguments(
    input_path: Path,
    *,
    start_time: float,
    end_time: float,
    client_token: str,
) -> list[str]:
    """Build the smallest paid cloud trim command used by the smoke workflow.

    An explicit ``--client-token`` makes the single paid submission idempotent:
    if the submit step is retried with the same token, the backend returns the
    original task instead of charging for a second task (24h default
    idempotency). A brand-new smoke run generates a fresh token.
    """
    if end_time <= start_time:
        raise MediaKitTaskError("冒烟裁剪结束时间必须大于开始时间。")
    if (not client_token or len(client_token) > 64
            or any(not 32 <= ord(c) <= 126 for c in client_token)):
        raise MediaKitTaskError(
            "client_token 必须是非空 ASCII 字符串且长度不超过 64。"
        )
    # CLI 0.2.2's public binary is cloud-only and does not accept a global
    # ``--cloud`` mode flag. The smoke test therefore uses the domain command
    # directly; it still targets the cloud endpoint because no local mode exists.
    return [
        "editing",
        "trim-video",
        "--video-url",
        str(input_path),
        "--start-time",
        str(start_time),
        "--end-time",
        str(end_time),
        "--client-token",
        client_token,
    ]


def build_poll_arguments(
    task_id: str,
    *,
    poll_interval_seconds: int,
    max_poll_attempts: int,
) -> list[str]:
    """Build a bounded query-task command."""
    if not task_id:
        raise MediaKitTaskError("云端冒烟缺少 task_id。")
    if poll_interval_seconds <= 0 or max_poll_attempts <= 0:
        raise MediaKitTaskError("轮询间隔和次数必须为正数。")
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


def extract_task_id(payload: Mapping[str, object]) -> str:
    """Validate the task id returned by an asynchronous submit call."""
    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise MediaKitTaskError("提交结果缺少非空 task_id。")
    return task_id


def assert_terminal_completed(payload: Mapping[str, object]) -> None:
    """Ensure the polled task reached the successful terminal state."""
    status = payload.get("status")
    if status in _TERMINAL_FAILURE or payload.get("success") is False:
        raise MediaKitTaskError(
            "云端任务进入失败终态：" + redact_text(json.dumps(dict(payload), ensure_ascii=False))
        )
    if status != _TERMINAL_SUCCESS:
        raise MediaKitTaskError(f"云端任务未在限定时间内完成，当前状态：{status!r}。")


def extract_result_url(payload: Mapping[str, object]) -> str:
    """Return the output media URL from a completed task payload."""
    for key in ("video_url", "audio_url", "image_url", "url"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    result = payload.get("result")
    if isinstance(result, dict):
        for key in ("video_url", "audio_url", "image_url", "url"):
            value = result.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
    raise MediaKitTaskError("完成态结果中没有可下载的媒体 URL。")


def download_result(
    url: str,
    output_path: Path,
    *,
    opener: Callable[[str], object] = urllib.request.urlopen,
) -> int:
    """Download the result and return its byte count without printing the signed URL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with opener(url) as response, output_path.open("wb") as stream:
        data = response.read()
        stream.write(data)
    if output_path.stat().st_size <= 0:
        raise MediaKitTaskError("下载结果为空文件。")
    return output_path.stat().st_size
