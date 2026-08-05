"""Cloud video AI nodes backed by the official MediaKit CLI."""

from __future__ import annotations

from comfy_api.latest import io

from ..media_bridge import download_video_output, materialize_video
from ..orchestrator import (
    enhance_video,
    enhance_video_generative,
    erase_video_subtitle,
)


class MediaKitVideoEnhance(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoEnhance",
            display_name="MediaKit Video Enhance",
            category="MediaKit/Video AI",
            description="使用火山引擎 AI MediaKit 标准版或专业版增强视频画质。",
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "tool_version",
                    options=["standard", "professional"],
                    default="standard",
                ),
                io.Combo.Input(
                    "scene",
                    options=["common", "ugc", "short_series", "aigc", "old_film"],
                    default="common",
                ),
                io.Combo.Input(
                    "resolution",
                    options=[
                        "keep",
                        "240p",
                        "360p",
                        "480p",
                        "540p",
                        "720p",
                        "1080p",
                        "2k",
                        "4k",
                    ],
                    default="1080p",
                ),
                io.Int.Input(
                    "poll_interval_seconds",
                    default=5,
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
                io.Combo.Input(
                    "bitrate_level",
                    options=["low", "medium", "high"],
                    default="medium",
                ),
                io.Float.Input(
                    "fps",
                    default=0.0,
                    min=0.0,
                    max=120.0,
                    step=1.0,
                    advanced=True,
                    tooltip="0 表示保持源视频帧率。",
                ),
            ],
            outputs=[io.Video.Output(display_name="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        tool_version: str,
        scene: str,
        resolution: str,
        poll_interval_seconds: int = 5,
        max_poll_attempts: int = 720,
        bitrate_level: str = "medium",
        fps: float = 0.0,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await enhance_video(
                video_path,
                tool_version=tool_version,
                scene=scene,
                resolution=resolution,
                bitrate_level=bitrate_level,
                fps=fps,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        output_video = await download_video_output(result_url)
        return io.NodeOutput(output_video)


class MediaKitEraseVideoSubtitle(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitEraseVideoSubtitle",
            display_name="MediaKit Erase Video Subtitle",
            category="MediaKit/Video AI",
            description="使用 MediaKit 标准版智能检测并擦除视频硬字幕。",
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
            outputs=[io.Video.Output(display_name="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await erase_video_subtitle(
                video_path,
                professional=False,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitVideoEnhanceGenerative(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoEnhanceGenerative",
            display_name="MediaKit Video Enhance Generative",
            category="MediaKit/Video AI",
            description=(
                "使用 MediaKit 扩散大模型主动补全视频细节并进行生成式增强修复。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "resolution",
                    options=["720p", "1080p"],
                    default="720p",
                ),
                io.Combo.Input(
                    "bitrate_level",
                    options=["low", "medium", "high"],
                    default="medium",
                ),
                io.Float.Input(
                    "fps",
                    default=0.0,
                    min=0.0,
                    max=120.0,
                    step=1.0,
                    tooltip="0 保持源帧率；指定时必须为 15–120 fps。",
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
        resolution: str,
        bitrate_level: str,
        fps: float,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await enhance_video_generative(
                video_path,
                resolution=resolution,
                bitrate_level=bitrate_level,
                fps=fps,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitEraseVideoSubtitlePro(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitEraseVideoSubtitlePro",
            display_name="MediaKit Erase Video Subtitle Pro",
            category="MediaKit/Video AI",
            description="使用 MediaKit 精细化字幕擦除，可限定擦除类型与画面区域。",
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "erase_mode",
                    options=["Subtitle", "Text"],
                    default="Subtitle",
                    tooltip="Subtitle 仅擦字幕；Text 同时擦除其他渲染文字。",
                ),
                io.Combo.Input(
                    "output_encode_mode",
                    options=["Quality", "Size"],
                    default="Quality",
                ),
                io.Boolean.Input(
                    "restrict_region",
                    default=False,
                    tooltip="启用后只擦除归一化坐标框内的文字。",
                ),
                io.Float.Input(
                    "top_left_x",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    advanced=True,
                ),
                io.Float.Input(
                    "top_left_y",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    advanced=True,
                ),
                io.Float.Input(
                    "bottom_right_x",
                    default=1.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    advanced=True,
                ),
                io.Float.Input(
                    "bottom_right_y",
                    default=1.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    advanced=True,
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
        erase_mode: str,
        output_encode_mode: str,
        restrict_region: bool,
        top_left_x: float,
        top_left_y: float,
        bottom_right_x: float,
        bottom_right_y: float,
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        erase_region = None
        if restrict_region:
            erase_region = {
                "top_left_x": top_left_x,
                "top_left_y": top_left_y,
                "bottom_right_x": bottom_right_x,
                "bottom_right_y": bottom_right_y,
            }
        with materialize_video(video) as video_path:
            result_url, _task_id = await erase_video_subtitle(
                video_path,
                professional=True,
                mode=erase_mode,
                output_encode_mode=output_encode_mode,
                erase_region=erase_region,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))
