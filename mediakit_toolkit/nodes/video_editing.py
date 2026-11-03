"""Cloud/local video editing nodes backed by the official MediaKit CLI."""

from __future__ import annotations

from comfy_api.latest import io

from ..media_bridge import (
    download_audio_output,
    download_video_output,
    materialize_video,
)
from ..orchestrator import extract_audio, trim_video


class MediaKitTrimVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitTrimVideo",
            display_name="Trim · 视频裁剪",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 按时间范围裁剪视频；CLI 支持本地模式时本地执行（免费），"
                "否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Float.Input(
                    "start_time",
                    default=0.0,
                    min=0.0,
                    max=86400.0,
                    step=0.1,
                    tooltip="裁剪开始时间（秒）。",
                ),
                io.Float.Input(
                    "end_time",
                    default=30.0,
                    min=0.0,
                    max=86400.0,
                    step=0.1,
                    tooltip="裁剪结束时间（秒）；留空裁剪到视频末尾。",
                ),
                io.Combo.Input(
                    "run_mode",
                    options=["auto", "cloud"],
                    default="auto",
                    tooltip=(
                        "auto 使用本地模式（如 CLI 支持）；cloud 强制提交云端任务。"
                    ),
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
        start_time: float,
        end_time: float,
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        if end_time <= start_time:
            end_time = None
        with materialize_video(video) as video_path:
            result_url, _task_id = await trim_video(
                video_path,
                start_time=start_time,
                end_time=end_time,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitExtractAudio(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitExtractAudio",
            display_name="Extract Audio · 提取音频",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 从视频中分离音轨，输出原生 AUDIO；CLI 支持本地模式时"
                "本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "output_format",
                    options=["mp3", "m4a", "ogg", "flac", "wav"],
                    default="m4a",
                    tooltip="输出音频格式。",
                ),
                io.Combo.Input(
                    "run_mode",
                    options=["auto", "cloud"],
                    default="auto",
                    tooltip=(
                        "auto 使用本地模式（如 CLI 支持）；cloud 强制提交云端任务。"
                    ),
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
            outputs=[io.Audio.Output(display_name="audio")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        output_format: str,
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await extract_audio(
                video_path,
                output_format=output_format,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_audio_output(result_url))
