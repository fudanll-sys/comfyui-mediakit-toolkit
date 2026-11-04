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
    if kind not in _KIND_SUFFIX:
        raise MediaKitInputError(f"不支持的媒体类型：{kind}")
    if kind == "audio" and isinstance(media, dict):
        return _prepare_audio_tensor(media)
    if kind == "image" and callable(getattr(media, "detach", None)):
        return _prepare_image_tensor(media)
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
                Path(temporary.name).unlink(missing_ok=True)
            raise MediaKitInputError(f"无法准备临时{kind}文件：{exc}") from exc
        return temporary_path, (lambda: temporary_path.unlink(missing_ok=True))

    raise MediaKitInputError(
        f"不支持的{kind}流来源类型：{type(source).__name__}"
    )


def _prepare_audio_tensor(audio: dict) -> tuple[Path, Callable[[], None]]:
    """Serialize ComfyUI's AUDIO dict, not a VideoInput, to PCM16 WAV."""
    import numpy as np
    import wave

    waveform, rate = audio.get("waveform"), audio.get("sample_rate")
    if not callable(getattr(waveform, "detach", None)) or not isinstance(rate, int) or isinstance(rate, bool) or rate <= 0:
        raise MediaKitInputError("AUDIO 需要 waveform Tensor 和正整数 sample_rate。")
    if waveform.ndim != 3 or waveform.shape[0] != 1 or waveform.shape[1] not in (1, 2) or waveform.shape[2] == 0:
        raise MediaKitInputError("AUDIO waveform 必须为非空 [1, 1或2声道, samples]；请先拆分批次。")
    samples = waveform.detach().cpu().float().numpy()[0]
    if not np.isfinite(samples).all():
        raise MediaKitInputError("音频包含 NaN 或无穷值。")
    pcm = (np.clip(samples, -1, 1).T * 32767).round().astype("<i2")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as stream:
        path = Path(stream.name)
    try:
        with wave.open(str(path), "wb") as output:
            output.setnchannels(samples.shape[0])
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes(pcm.tobytes())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path, lambda: path.unlink(missing_ok=True)


def _prepare_image_tensor(image: object) -> tuple[Path, Callable[[], None]]:
    import numpy as np
    from PIL import Image

    if image.ndim != 4 or image.shape[0] != 1 or image.shape[-1] not in (3, 4):
        raise MediaKitInputError("IMAGE 必须是单张 [1,H,W,3或4] Tensor；请先拆分批次。")
    pixels = image.detach().cpu().float().numpy()[0]
    if not np.isfinite(pixels).all():
        raise MediaKitInputError("图片包含 NaN 或无穷值。")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as stream:
        path = Path(stream.name)
    try:
        Image.fromarray((np.clip(pixels, 0, 1) * 255).round().astype("uint8")).save(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path, lambda: path.unlink(missing_ok=True)


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
    candidate = Path(url).expanduser()
    if candidate.is_file():
        from comfy_api.latest import InputImpl
        return InputImpl.VideoFromFile(str(candidate.resolve()))
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

    from urllib.parse import urlparse
    if urlparse(url).scheme not in ("", "http", "https"):
        raise MediaKitInputError("结果只支持 HTTP(S) URL 或本地路径。")
    path = Path(url).expanduser().resolve()
    if not path.is_file():
        raise MediaKitInputError(f"结果媒体文件不存在：{path}")
    from comfy_api.latest import InputImpl
    return InputImpl.VideoFromFile(str(path))


async def download_video_output(url: str) -> object:
    """Convert a MediaKit result URL to ComfyUI's native VIDEO output."""
    return await _download_output(
        url,
        "video",
        ("download_url_to_video_output",),
    )


async def download_audio_output(url: str) -> object:
    """Decode a result into native AUDIO; never fall back to VIDEO."""
    data = await asyncio.to_thread(_read_media_bytes, url)
    return await asyncio.to_thread(_decode_audio_bytes, data)


def _read_media_bytes(url: str) -> bytes:
    from urllib.parse import urlparse
    import urllib.request
    scheme = urlparse(url).scheme
    if scheme in ("http", "https"):
        with urllib.request.urlopen(url, timeout=120) as response:
            return response.read()
    if scheme:
        raise MediaKitInputError("结果只支持 HTTP(S) URL 或本地路径。")
    path = Path(url).expanduser().resolve()
    if not path.is_file():
        raise MediaKitInputError(f"结果媒体文件不存在：{path}")
    return path.read_bytes()


def _decode_audio_bytes(data: bytes) -> object:
    """PyAV resampling handles planar and interleaved PCM consistently."""
    import av
    import numpy as np
    import torch
    try:
        with av.open(BytesIO(data)) as container:
            if not container.streams.audio:
                raise MediaKitInputError("结果文件没有音轨。")
            stream = container.streams.audio[0]
            rate = stream.codec_context.sample_rate
            resampler = av.AudioResampler(format="fltp", layout=stream.codec_context.layout, rate=rate)
            chunks = []
            for frame in container.decode(stream):
                chunks.extend(out.to_ndarray() for out in resampler.resample(frame))
            chunks.extend(out.to_ndarray() for out in resampler.resample(None))
        if not chunks:
            raise MediaKitInputError("结果音轨没有可解码的采样。")
        tensor = torch.from_numpy(np.concatenate(chunks, axis=1).copy()).unsqueeze(0)
        return {"waveform": tensor, "sample_rate": rate}
    except MediaKitInputError:
        raise
    except Exception as exc:
        raise MediaKitInputError(f"音频解码失败：{exc}") from exc


async def download_image_output(url: str) -> object:
    """Decode all frames to native IMAGE [B,H,W,C], not a made-up helper."""
    frames, _durations = await download_animated_image_output(url)
    return frames


async def download_animated_image_output(url: str) -> tuple[object, str]:
    """Preserve every frame and its original duration (milliseconds JSON)."""
    data = await asyncio.to_thread(_read_media_bytes, url)
    return await asyncio.to_thread(_decode_image_bytes, data)


def _decode_image_bytes(data: bytes) -> tuple[object, str]:
    import json
    import numpy as np
    import torch
    from PIL import Image, ImageOps, ImageSequence
    try:
        with Image.open(BytesIO(data)) as image:
            durations, frames = [], []
            for frame in ImageSequence.Iterator(image):
                durations.append(frame.info.get("duration", 0))
                frames.append(np.asarray(ImageOps.exif_transpose(frame).convert("RGB"), dtype=np.float32) / 255.0)
        return torch.from_numpy(np.stack(frames)), json.dumps(durations)
    except Exception as exc:
        raise MediaKitInputError(f"图片解码失败：{exc}") from exc


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
