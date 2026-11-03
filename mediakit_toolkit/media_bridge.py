"""Bridge ComfyUI native media objects to file-backed CLI inputs."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterator, Sequence

from .errors import MediaKitCompatibilityError, MediaKitInputError

# Temporary file suffixes by media kind. The exact extension does not drive
# ffprobe/ffmpeg (they sniff content), but a plausible one avoids confusing
# the CLI's upload path and downstream tooling.
_KIND_SUFFIX = {
    "video": ".mp4",
    "audio": ".m4a",
    "image": ".png",
}


def _stream_source(media: object, kind: str) -> object:
    getter = getattr(media, "get_stream_source", None)
    if not callable(getter):
        raise MediaKitInputError(
            f"输入不是兼容的 ComfyUI {kind.upper()} 对象：缺少 get_stream_source()。"
        )
    return getter()


def _prepare_media(media: object, kind: str) -> tuple[Path, Callable[[], None]]:
    """Return (local_path, cleanup) for a native media object.

    Path-backed inputs yield the original file with a no-op cleanup; stream
    inputs are copied to a temporary file that cleanup removes.
    """
    source = _stream_source(media, kind)
    if isinstance(source, (str, os.PathLike)):
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise MediaKitInputError(f"输入{kind}文件不存在：{path}")
        return path, (lambda: None)

    if isinstance(source, BytesIO) or callable(getattr(source, "read", None)):
        temporary: tempfile._TemporaryFileWrapper | None = None
        try:
            temporary = tempfile.NamedTemporaryFile(
                suffix=_KIND_SUFFIX[kind], delete=False
            )
            temporary_path = Path(temporary.name)
            seek = getattr(source, "seek", None)
            if callable(seek):
                seek(0)
            shutil.copyfileobj(source, temporary)
            temporary.close()
        except OSError as exc:
            if temporary is not None:
                temporary.close()
            raise MediaKitInputError(f"无法准备临时{kind}文件：{exc}") from exc
        return temporary_path, (lambda: temporary_path.unlink(missing_ok=True))

    raise MediaKitInputError(
        f"不支持的{kind}流来源类型：{type(source).__name__}"
    )


@contextmanager
def materialize_video(video: object) -> Iterator[Path]:
    """Yield a local path for a native ComfyUI video and clean temp files."""
    path, cleanup = _prepare_media(video, "video")
    try:
        yield path
    finally:
        cleanup()


@contextmanager
def materialize_audio(audio: object) -> Iterator[Path]:
    """Yield a local path for a native ComfyUI audio object and clean up."""
    path, cleanup = _prepare_media(audio, "audio")
    try:
        yield path
    finally:
        cleanup()


@contextmanager
def materialize_image(image: object) -> Iterator[Path]:
    """Yield a local path for a native ComfyUI image and clean up."""
    path, cleanup = _prepare_media(image, "image")
    try:
        yield path
    finally:
        cleanup()


@contextmanager
def materialize_media_list(
    media_list: Sequence[object], kind: str = "video"
) -> Iterator[list[Path]]:
    """Materialize multiple native media objects into a list of local paths.

    All temporary files are cleaned up on exit, including on failure.
    """
    if not media_list:
        raise MediaKitInputError("需要至少一个输入媒体。")
    prepared: list[tuple[Path, Callable[[], None]]] = []
    try:
        for media in media_list:
            prepared.append(_prepare_media(media, kind))
        yield [path for path, _cleanup in prepared]
    finally:
        for _path, cleanup in reversed(prepared):
            cleanup()


async def _download_output(url: str, kind: str, util_names: Sequence[str]) -> object:
    """Convert a MediaKit result URL to a native ComfyUI output object.

    HTTP(S) results are downloaded through ComfyUI's media utility; local path
    results (e.g. local-mode CLI output) are handed over via ``file://``.
    """
    try:
        from comfy_api_nodes import util
    except ImportError as exc:
        raise MediaKitCompatibilityError(
            "当前 ComfyUI 缺少原生媒体下载接口。请升级到支持 V3 媒体 API 的版本。"
        ) from exc

    for name in util_names:
        downloader = getattr(util, name, None)
        if callable(downloader):
            break
    else:
        raise MediaKitCompatibilityError(
            f"当前 ComfyUI 缺少 {kind} 下载接口（{', '.join(util_names)}）。"
        )

    if url.startswith(("http://", "https://")):
        return await downloader(url)

    path = Path(url).expanduser().resolve()
    if not path.is_file():
        raise MediaKitInputError(f"结果媒体文件不存在：{path}")
    return await downloader(path.as_uri())


async def download_video_output(url: str) -> object:
    """Convert a MediaKit result URL to ComfyUI's native VIDEO output."""
    return await _download_output(
        url,
        "video",
        ("download_url_to_video_output",),
    )


async def download_audio_output(url: str) -> object:
    """Convert a MediaKit result URL to ComfyUI's native AUDIO output."""
    return await _download_output(
        url,
        "audio",
        ("download_url_to_audio_output", "download_url_to_video_output"),
    )


async def download_image_output(url: str) -> object:
    """Convert a MediaKit result URL to ComfyUI's native IMAGE output."""
    return await _download_output(
        url,
        "image",
        ("download_url_to_image_output",),
    )


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
