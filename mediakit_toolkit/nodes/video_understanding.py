"""Cloud video understanding and analysis nodes backed by the MediaKit CLI."""

from __future__ import annotations

import json
from typing import Any

from comfy_api.latest import io

from ..media_bridge import (
    download_text_output,
    download_video_output,
    materialize_video,
)
from ..orchestrator import (
    analyze_video_highlights,
    asr_video_subtitles,
    find_subtitle_url,
    matte_video,
    ocr_video_subtitles,
    probe_video_metadata,
    segment_video_scenes,
)
from ..redaction import redact_text


def _raw_json(payload: dict[str, Any]) -> str:
    return redact_text(json.dumps(payload, ensure_ascii=False, indent=2))


class MediaKitVideoASR(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoASR",
            display_name="ASR · 语音转字幕",
            category="MediaKit/Video AI",
            description="使用 MediaKit 识别视频语音，输出带时间戳的字幕。",
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "content_type",
                    options=["auto", "speech", "singing"],
                    default="auto",
                    tooltip="auto 由算法自动探测识别类型。",
                ),
                io.Combo.Input(
                    "language",
                    options=["auto", "cmn-Hans-CN", "eng-US"],
                    default="auto",
                    tooltip="识别提示语言；auto 自动探测语种。",
                ),
                io.Boolean.Input(
                    "enable_speaker_info",
                    default=False,
                    tooltip="开启说话人识别。",
                ),
                io.Boolean.Input(
                    "enable_confidence",
                    default=False,
                    tooltip="返回识别置信度。",
                ),
                io.Int.Input(
                    "poll_interval_seconds",
                    default=10,
                    min=2,
                    max=60,
                    advanced=True,
                ),
                io.Int.Input(
                    "max_poll_attempts",
                    default=720,
                    min=1,
                    max=5000,
                    advanced=True,
                ),
            ],
            outputs=[
                io.String.Output(display_name="subtitle"),
                io.String.Output(display_name="raw_json"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        content_type: str,
        language: str,
        enable_speaker_info: bool,
        enable_confidence: bool,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            payload, _task_id = await asr_video_subtitles(
                video_path,
                content_type=content_type,
                language=language,
                enable_speaker_info=enable_speaker_info,
                enable_confidence=enable_confidence,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        subtitle_url = find_subtitle_url(payload)
        subtitle = await download_text_output(subtitle_url) if subtitle_url else ""
        return io.NodeOutput(subtitle, _raw_json(payload))


class MediaKitVideoOCR(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoOCR",
            display_name="OCR · 视频识别字幕",
            category="MediaKit/Video AI",
            description="使用 MediaKit 识别视频画面中的字幕和文字。",
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "mode",
                    options=["Subtitle", "Detailed"],
                    default="Subtitle",
                    tooltip="Subtitle 识别字幕文本；Detailed 识别更详细信息。",
                ),
                io.Int.Input(
                    "poll_interval_seconds",
                    default=10,
                    min=2,
                    max=60,
                    advanced=True,
                ),
                io.Int.Input(
                    "max_poll_attempts",
                    default=720,
                    min=1,
                    max=5000,
                    advanced=True,
                ),
            ],
            outputs=[
                io.String.Output(display_name="subtitle"),
                io.String.Output(display_name="raw_json"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        mode: str,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            payload, _task_id = await ocr_video_subtitles(
                video_path,
                mode=mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        subtitle_url = find_subtitle_url(payload)
        subtitle = await download_text_output(subtitle_url) if subtitle_url else ""
        return io.NodeOutput(subtitle, _raw_json(payload))


class MediaKitVideoMattePortrait(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoMattePortrait",
            display_name="Matte · 人像抠图",
            category="MediaKit/Video AI",
            description="自动识别人物主体并移除背景，输出透明背景视频。",
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "output_format",
                    options=["WEBM", "MOV"],
                    default="WEBM",
                    tooltip="透明视频输出格式。",
                ),
                io.Int.Input(
                    "poll_interval_seconds",
                    default=10,
                    min=2,
                    max=60,
                    advanced=True,
                ),
                io.Int.Input(
                    "max_poll_attempts",
                    default=720,
                    min=1,
                    max=5000,
                    advanced=True,
                ),
            ],
            outputs=[io.Video.Output(display_name="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        output_format: str,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await matte_video(
                video_path,
                tool="matte-portrait-video",
                output_format=output_format,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitVideoMatteGreenscreen(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoMatteGreenscreen",
            display_name="Matte · 绿幕抠图",
            category="MediaKit/Video AI",
            description="对绿幕或纯色背景视频抠图并移除背景，输出透明视频。",
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "output_format",
                    options=["WEBM", "MOV"],
                    default="WEBM",
                    tooltip="透明视频输出格式。",
                ),
                io.Int.Input(
                    "poll_interval_seconds",
                    default=10,
                    min=2,
                    max=60,
                    advanced=True,
                ),
                io.Int.Input(
                    "max_poll_attempts",
                    default=720,
                    min=1,
                    max=5000,
                    advanced=True,
                ),
            ],
            outputs=[io.Video.Output(display_name="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        output_format: str,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await matte_video(
                video_path,
                tool="matte-greenscreen-video",
                output_format=output_format,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitVideoSegmentScenes(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoSegmentScenes",
            display_name="Scene · 场景切分",
            category="MediaKit/Video AI",
            description="依据转场与画面变化自动切分视频场景，输出切片时间轴。",
            inputs=[
                io.Video.Input("video"),
                io.Boolean.Input(
                    "enable_clip_fade",
                    default=False,
                    tooltip="将检测到的淡入淡出片段作为独立切片。",
                ),
                io.Float.Input(
                    "segment_threshold",
                    default=0.0,
                    min=0.0,
                    max=99.0,
                    step=1.0,
                    tooltip="切分敏感度阈值；0 表示使用算法默认值。",
                ),
                io.Float.Input(
                    "min_duration",
                    default=0.0,
                    min=0.0,
                    max=7200.0,
                    step=1.0,
                    tooltip="单个切片最小时长（秒）；0 表示默认。",
                ),
                io.Float.Input(
                    "max_duration",
                    default=0.0,
                    min=0.0,
                    max=7200.0,
                    step=1.0,
                    tooltip="单个切片最大时长（秒）；0 表示默认。",
                ),
                io.Int.Input(
                    "poll_interval_seconds",
                    default=10,
                    min=2,
                    max=60,
                    advanced=True,
                ),
                io.Int.Input(
                    "max_poll_attempts",
                    default=720,
                    min=1,
                    max=5000,
                    advanced=True,
                ),
            ],
            outputs=[
                io.String.Output(display_name="scenes_json"),
                io.String.Output(display_name="raw_json"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        enable_clip_fade: bool,
        segment_threshold: float,
        min_duration: float,
        max_duration: float,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            payload, _task_id = await segment_video_scenes(
                video_path,
                enable_clip_fade=enable_clip_fade,
                segment_threshold=segment_threshold or None,
                min_duration=min_duration or None,
                max_duration=max_duration or None,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(_raw_json(payload), _raw_json(payload))


class MediaKitVideoAnalyzeHighlights(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoAnalyzeHighlights",
            display_name="Highlight · 高光片段提取",
            category="MediaKit/Video AI",
            description="捕捉视频情绪波峰与关键动作，输出高光时间戳和打分等元数据。",
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "model",
                    options=["Miniseries", "Game"],
                    default="Miniseries",
                    tooltip="Miniseries 短剧；Game 小游戏。",
                ),
                io.Int.Input(
                    "poll_interval_seconds",
                    default=10,
                    min=2,
                    max=60,
                    advanced=True,
                ),
                io.Int.Input(
                    "max_poll_attempts",
                    default=720,
                    min=1,
                    max=5000,
                    advanced=True,
                ),
            ],
            outputs=[
                io.String.Output(display_name="highlights_json"),
                io.String.Output(display_name="raw_json"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        model: str,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            payload, _task_id = await analyze_video_highlights(
                video_path,
                model=model,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(_raw_json(payload), _raw_json(payload))


class MediaKitVideoProbeMetadata(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoProbeMetadata",
            display_name="Metadata · 视频元信息",
            category="MediaKit/Video AI",
            description="探测视频容器、视频流与音频流元信息。",
            inputs=[
                io.Video.Input("video"),
                io.Int.Input(
                    "poll_interval_seconds",
                    default=10,
                    min=2,
                    max=60,
                    advanced=True,
                ),
                io.Int.Input(
                    "max_poll_attempts",
                    default=720,
                    min=1,
                    max=5000,
                    advanced=True,
                ),
            ],
            outputs=[
                io.String.Output(display_name="metadata_json"),
                io.String.Output(display_name="raw_json"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            payload, _task_id = await probe_video_metadata(
                video_path,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(_raw_json(payload), _raw_json(payload))
