"""Cloud video AI nodes backed by the official MediaKit CLI."""

from __future__ import annotations

from comfy_api.latest import io

from ..media_bridge import download_video_output, materialize_video
from ..orchestrator import enhance_video


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
                    default="aigc",
                ),
                io.Combo.Input(
                    "resolution",
                    options=["keep", "720p", "1080p", "2k", "4k", "8k"],
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
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await enhance_video(
                video_path,
                tool_version=tool_version,
                scene=scene,
                resolution=resolution,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        output_video = await download_video_output(result_url)
        return io.NodeOutput(output_video)
