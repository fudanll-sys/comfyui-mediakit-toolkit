"""Bridge ComfyUI native media objects to file-backed CLI inputs."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Iterator

from .errors import MediaKitCompatibilityError, MediaKitInputError


def _stream_source(video: object) -> object:
    getter = getattr(video, "get_stream_source", None)
    if not callable(getter):
        raise MediaKitInputError(
            "输入不是兼容的 ComfyUI VIDEO 对象：缺少 get_stream_source()。"
        )
    return getter()


@contextmanager
def materialize_video(video: object) -> Iterator[Path]:
    """Yield a local path for a native ComfyUI video and clean temp files."""
    source = _stream_source(video)
    if isinstance(source, (str, os.PathLike)):
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise MediaKitInputError(f"输入视频文件不存在：{path}")
        yield path
        return

    if isinstance(source, BytesIO) or callable(getattr(source, "read", None)):
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temporary:
                temporary_path = Path(temporary.name)
                seek = getattr(source, "seek", None)
                if callable(seek):
                    seek(0)
                shutil.copyfileobj(source, temporary)
            yield temporary_path
        except OSError as exc:
            raise MediaKitInputError(f"无法准备临时视频文件：{exc}") from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return

    raise MediaKitInputError(
        f"不支持的视频流来源类型：{type(source).__name__}"
    )


async def download_video_output(url: str) -> object:
    """Convert a MediaKit result URL to ComfyUI's native VIDEO output."""
    try:
        from comfy_api_nodes.util import download_url_to_video_output
    except ImportError as exc:
        raise MediaKitCompatibilityError(
            "当前 ComfyUI 缺少原生视频下载接口。请升级到支持 V3 VIDEO API 的版本。"
        ) from exc
    return await download_url_to_video_output(url)


async def download_text_output(url: str) -> str:
    """Download a MediaKit result file and return its decoded text."""
    try:
        return await asyncio.to_thread(_download_text_sync, url)
    except OSError as exc:
        raise MediaKitInputError(f"无法下载结果文件：{exc}") from exc


def _download_text_sync(url: str) -> str:
    import urllib.request

    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310
        data = response.read()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
