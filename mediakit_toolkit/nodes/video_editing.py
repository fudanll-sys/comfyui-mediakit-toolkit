"""Cloud/local video editing nodes backed by the official MediaKit CLI."""

from __future__ import annotations

import json
from typing import Any

from comfy_api.latest import io

from ..errors import MediaKitInputError
from ..media_bridge import (
    download_audio_output,
    download_animated_image_output,
    download_video_output,
    materialize_audio,
    materialize_media_list,
    materialize_video,
)
from ..orchestrator import (
    add_subtitle_to_video,
    adjust_audio_speed,
    adjust_video_speed,
    adjust_video_volume,
    apply_camera_motion,
    apply_video_filter,
    concat_audios,
    concat_videos,
    crop_video,
    extract_animated_image,
    extract_audio,
    fade_audio,
    fade_video_audio,
    flip_video,
    mix_audios,
    mux_audio_video,
    rotate_video,
    stitch_videos,
    trim_audio,
    trim_video,
)


def _media_inputs(identifier: str, kind: str, maximum: int = 100) -> object:
    native_type = io.Video if kind == "video" else io.Audio
    return io.Autogrow.Input(
        identifier,
        template=io.Autogrow.TemplateNames(
            native_type.Input(kind),
            names=[f"{kind}_{i}" for i in range(1, maximum + 1)],
            min=2 if maximum == 3 else 1,
        ),
        tooltip=f"按编号连接{kind}，最多 {maximum} 个。",
    )


def _ordered_media(value: object, kind: str, maximum: int = 100) -> list[object]:
    if not isinstance(value, dict):
        raise MediaKitInputError("多输入须由 ComfyUI Autogrow 插槽提供。")
    allowed = [f"{kind}_{i}" for i in range(1, maximum + 1)]
    if any(key not in allowed for key in value):
        raise MediaKitInputError("多输入包含未知插槽。")
    items = [value[key] for key in allowed if key in value and value[key] is not None]
    minimum = 2 if maximum == 3 else 1
    if not minimum <= len(items) <= maximum:
        raise MediaKitInputError(f"需要 {minimum}～{maximum} 个输入。")
    return items


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
            outputs=[io.Video.Output(id="video")],
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
        client_token: str | None = None,
    ) -> io.NodeOutput:
        if end_time <= start_time:
            end_time = None
        with materialize_video(video) as video_path:
            token_args = {"client_token": client_token} if client_token is not None else {}
            result_url, _task_id = await trim_video(
                video_path,
                start_time=start_time,
                end_time=end_time,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
                **token_args,
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
            outputs=[io.Audio.Output(id="audio")],
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


class MediaKitAdjustVideoSpeed(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitAdjustVideoSpeed",
            display_name="Speed · 视频变速",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 调整视频播放速度（0.1～4.0 倍速）；CLI 支持本地模式时"
                "本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Float.Input(
                    "speed",
                    default=1.0,
                    min=0.1,
                    max=4.0,
                    step=0.1,
                    tooltip="播放速度倍数；大于 1 快放，小于 1 慢放。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        speed: float = 1.0,
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await adjust_video_speed(
                video_path,
                speed=speed,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitAdjustVideoVolume(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitAdjustVideoVolume",
            display_name="Volume · 音量调整",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 调整视频音量（0～4 倍）；CLI 支持本地模式时本地执行"
                "（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Float.Input(
                    "volume",
                    default=1.0,
                    min=0.0,
                    max=4.0,
                    step=0.1,
                    tooltip="音量倍数；0 静音，1 原音量，小于 1 减小音量。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        volume: float = 1.0,
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await adjust_video_volume(
                video_path,
                volume=volume,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitCameraMotion(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitCameraMotion",
            display_name="Camera Motion · 镜头运动",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 为视频应用预设运镜效果（推拉/平移推拉/环绕/弹动）；"
                "CLI 支持本地模式时本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "motion_style",
                    options=["zoom", "pan-zoom", "orbit-360", "bounce"],
                    default="zoom",
                    tooltip="运镜风格。",
                ),
                io.Float.Input(
                    "start_time",
                    default=0.0,
                    min=0.0,
                    max=86400.0,
                    step=0.1,
                    tooltip="运镜开始时间（秒）；0 表示从片头开始。",
                ),
                io.Float.Input(
                    "end_time",
                    default=0.0,
                    min=0.0,
                    max=86400.0,
                    step=0.1,
                    tooltip="运镜结束时间（秒）；0 表示到视频结尾。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        motion_style: str = "zoom",
        start_time: float = 0.0,
        end_time: float = 0.0,
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await apply_camera_motion(
                video_path,
                motion_style=motion_style,
                start_time=start_time,
                end_time=end_time if end_time > 0 else None,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitVideoFilter(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitVideoFilter",
            display_name="Filter · 视频滤镜",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 为视频应用预设滤镜风格（春日/晚霞/鲜亮/白皙/美食）；"
                "CLI 支持本地模式时本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "filter_style",
                    options=["spring", "sunset", "vivid", "fair_skin", "food"],
                    default="spring",
                    tooltip="滤镜风格。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        filter_style: str = "spring",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await apply_video_filter(
                video_path,
                filter_style=filter_style,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitFlipVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitFlipVideo",
            display_name="Flip · 视频翻转",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 水平或垂直翻转视频；CLI 支持本地模式时本地执行"
                "（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Boolean.Input(
                    "is_flip_horizontal",
                    default=False,
                    tooltip="水平翻转（左右镜像）。",
                ),
                io.Boolean.Input(
                    "is_flip_vertical",
                    default=False,
                    tooltip="垂直翻转（上下镜像）。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        is_flip_horizontal: bool = False,
        is_flip_vertical: bool = False,
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await flip_video(
                video_path,
                is_flip_horizontal=is_flip_horizontal,
                is_flip_vertical=is_flip_vertical,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitConcatVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitConcatVideo",
            display_name="Concat · 视频拼接",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 将多个视频按顺序拼接为一个完整视频，可选转场；CLI 支持"
                "本地模式时本地执行（免费），否则回退云端。"
            ),
            inputs=[
                _media_inputs("videos", "video"),
                io.Combo.Input(
                    "transitions",
                    options=[
                        "",
                        "1182359",
                        "1182360",
                        "1182358",
                        "1182365",
                        "1182367",
                        "1182368",
                        "1182369",
                        "1182370",
                        "1182373",
                        "1182374",
                        "1182375",
                        "1182378",
                    ],
                    default="",
                    tooltip="转场效果 ID；空表示硬切。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        videos: dict[str, object],
        transitions: str = "",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_media_list(_ordered_media(videos, "video"), kind="video") as video_paths:
            result_url, _task_id = await concat_videos(
                video_paths,
                transitions=[transitions] * (len(video_paths) - 1) if transitions else None,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitConcatAudio(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitConcatAudio",
            display_name="Concat Audio · 音频拼接",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 将多个音频按顺序拼接为一个音频；CLI 支持本地模式时"
                "本地执行（免费），否则回退云端。"
            ),
            inputs=[
                _media_inputs("audios", "audio"),
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
            outputs=[io.Audio.Output(id="audio")],
        )

    @classmethod
    async def execute(
        cls,
        audios: dict[str, object],
        output_format: str = "m4a",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_media_list(_ordered_media(audios, "audio"), kind="audio") as audio_paths:
            result_url, _task_id = await concat_audios(
                audio_paths,
                output_format=output_format,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_audio_output(result_url))


class MediaKitMixAudio(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitMixAudio",
            display_name="Mix · 混音",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 将多个音频混音为一个音频；CLI 支持本地模式时本地执行"
                "（免费），否则回退云端。"
            ),
            inputs=[
                _media_inputs("audios", "audio"),
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
            outputs=[io.Audio.Output(id="audio")],
        )

    @classmethod
    async def execute(
        cls,
        audios: dict[str, object],
        output_format: str = "m4a",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_media_list(_ordered_media(audios, "audio"), kind="audio") as audio_paths:
            result_url, _task_id = await mix_audios(
                audio_paths,
                output_format=output_format,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_audio_output(result_url))


class MediaKitMuxAudioVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitMuxAudioVideo",
            display_name="Mux · 音视频合流",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 将音频流与视频流合流为新视频，可保留或替换原音轨并对齐"
                "时长；CLI 支持本地模式时本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video", tooltip="输入视频。"),
                io.Audio.Input("audio", tooltip="待合流的输入音频。"),
                io.Boolean.Input(
                    "is_audio_reserve",
                    default=True,
                    tooltip="保留原视频音轨并与新音频混音；关闭则用新音频替换。",
                ),
                io.Boolean.Input(
                    "is_video_audio_sync",
                    default=False,
                    tooltip="开启音视频时长对齐。",
                ),
                io.Combo.Input(
                    "sync_method",
                    options=["trim", "speed"],
                    default="trim",
                    tooltip="对齐方式；trim 裁剪较长媒体流，speed 变速对齐。",
                ),
                io.Combo.Input(
                    "sync_mode",
                    options=["video", "audio"],
                    default="video",
                    tooltip="对齐基准；以视频或音频时长为准。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        audio: object,
        is_audio_reserve: bool = True,
        is_video_audio_sync: bool = False,
        sync_method: str = "trim",
        sync_mode: str = "video",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path, materialize_audio(
            audio
        ) as audio_path:
            result_url, _task_id = await mux_audio_video(
                video_path,
                audio_path,
                is_audio_reserve=is_audio_reserve,
                is_video_audio_sync=is_video_audio_sync,
                sync_method=sync_method,
                sync_mode=sync_mode,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitRotateVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitRotateVideo",            display_name="Rotate · 视频旋转",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 旋转视频（左转 90°/右转 90°/旋转 180°）；CLI 支持本地"
                "模式时本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video"),
                io.Combo.Input(
                    "rotate_direction",
                    options=["rotate_left_90", "rotate_right_90", "rotate_180"],
                    default="rotate_left_90",
                    tooltip="旋转方向。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        rotate_direction: str = "rotate_left_90",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await rotate_video(
                video_path,
                rotate_direction=rotate_direction,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitAddSubtitle(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitAddSubtitle",
            display_name="Subtitle · 视频加字幕",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 将字幕文件或文本内容按自定义样式压制到视频画面；CLI 支持"
                "本地模式时本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video", tooltip="待添加字幕的视频。"),
                io.String.Input(
                    "subtitle_url",
                    default="",
                    multiline=False,
                    tooltip=(
                        "字幕文件路径或 URL（SRT/VTT/ASS）；与字幕内容列表至少提供一项。"
                    ),
                ),
                io.String.Input(
                    "subtitles_json",
                    default="",
                    multiline=True,
                    tooltip=(
                        "字幕内容列表 JSON，例如："
                        '[{"subtitle_text":"你好","start_time":0,"end_time":3}]'
                    ),
                ),
                io.Combo.Input(
                    "subtitle_font_type",
                    options=["sy_black", "pm_zhengdao", "zhanku_kuaile"],
                    default="sy_black",
                    tooltip="字幕字体。",
                ),
                io.Combo.Input(
                    "subtitle_pos_preset",
                    options=["bottom_center", "top_center", "center", "lower_third"],
                    default="bottom_center",
                    tooltip="字幕位置预设。",
                ),
                io.Int.Input(
                    "subtitle_font_size",
                    default=50,
                    min=1,
                    max=1000,
                    tooltip="字幕字号（px）。",
                ),
                io.String.Input(
                    "subtitle_font_color",
                    default="#FFFFFFFF",
                    multiline=False,
                    tooltip="字幕颜色（RGBA 十六进制）。",
                ),
                io.String.Input(
                    "subtitle_text_effect",
                    default="",
                    multiline=False,
                    tooltip="花字效果资源 ID；设置后颜色参数不生效。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        subtitle_url: str = "",
        subtitles_json: str = "",
        subtitle_font_type: str = "sy_black",
        subtitle_pos_preset: str = "bottom_center",
        subtitle_font_size: int = 50,
        subtitle_font_color: str = "#FFFFFFFF",
        subtitle_text_effect: str = "",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        subtitles: list[dict[str, Any]] | None = None
        if subtitles_json.strip():
            try:
                parsed = json.loads(subtitles_json)
            except json.JSONDecodeError as exc:
                raise MediaKitInputError(f"字幕内容列表不是合法 JSON：{exc}") from exc
            if not isinstance(parsed, list):
                raise MediaKitInputError("字幕内容列表必须是 JSON 数组。")
            subtitles = parsed
        with materialize_video(video) as video_path:
            result_url, _task_id = await add_subtitle_to_video(
                video_path,
                subtitle_url=subtitle_url or None,
                subtitles=subtitles,
                subtitle_font_type=subtitle_font_type,
                subtitle_pos_preset=subtitle_pos_preset,
                subtitle_font_size=subtitle_font_size,
                subtitle_font_color=subtitle_font_color,
                subtitle_text_effect=subtitle_text_effect or None,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitStitchVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitStitchVideo",
            display_name="Stitch · 视频拼合",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 将 2～3 个视频在同一画布按左右或上下方向拼合，适用于多视角"
                "对比；CLI 支持本地模式时本地执行（免费），否则回退云端。"
            ),
            inputs=[
                _media_inputs("videos", "video", maximum=3),
                io.Combo.Input(
                    "stitch_direction",
                    options=["horizontal", "vertical"],
                    default="horizontal",
                    tooltip="horizontal 左右拼接；vertical 上下拼接。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        videos: dict[str, object],
        stitch_direction: str = "horizontal",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_media_list(_ordered_media(videos, "video"), kind="video") as video_paths:
            result_url, _task_id = await stitch_videos(
                video_paths,
                stitch_direction=stitch_direction,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitCropVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitCropVideo",
            display_name="Crop · 画面裁剪",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 按指定矩形区域裁剪视频画面；CLI 支持本地模式时本地执行"
                "（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video", tooltip="待裁剪的视频。"),
                io.Int.Input(
                    "top_left_x",
                    default=0,
                    min=0,
                    max=100000,
                    tooltip="裁剪矩形左上角 X 坐标（像素）。",
                ),
                io.Int.Input(
                    "top_left_y",
                    default=0,
                    min=0,
                    max=100000,
                    tooltip="裁剪矩形左上角 Y 坐标（像素）。",
                ),
                io.Int.Input(
                    "bottom_right_x",
                    default=1920,
                    min=0,
                    max=100000,
                    tooltip="裁剪矩形右下角 X 坐标（像素）。",
                ),
                io.Int.Input(
                    "bottom_right_y",
                    default=1080,
                    min=0,
                    max=100000,
                    tooltip="裁剪矩形右下角 Y 坐标（像素）。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        top_left_x: int = 0,
        top_left_y: int = 0,
        bottom_right_x: int = 1920,
        bottom_right_y: int = 1080,
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await crop_video(
                video_path,
                top_left_x=top_left_x,
                top_left_y=top_left_y,
                bottom_right_x=bottom_right_x,
                bottom_right_y=bottom_right_y,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitAdjustAudioSpeed(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitAdjustAudioSpeed",
            display_name="Audio Speed · 音频变速",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 调整音频播放速度（0.1～4.0 倍）；CLI 支持本地模式时本地"
                "执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Audio.Input("audio", tooltip="待变速的音频。"),
                io.Float.Input(
                    "speed",
                    default=1.0,
                    min=0.1,
                    max=4.0,
                    tooltip="变速倍速。",
                ),
                io.Combo.Input(
                    "format",
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
            outputs=[io.Audio.Output(id="audio")],
        )

    @classmethod
    async def execute(
        cls,
        audio: object,
        speed: float = 1.0,
        format: str = "m4a",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_audio(audio) as audio_path:
            result_url, _task_id = await adjust_audio_speed(
                audio_path,
                speed=speed,
                output_format=format,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_audio_output(result_url))


class MediaKitTrimAudio(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitTrimAudio",
            display_name="Audio Trim · 音频裁剪",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 按时间范围裁剪音频；CLI 支持本地模式时本地执行（免费），"
                "否则回退云端。"
            ),
            inputs=[
                io.Audio.Input("audio", tooltip="待裁剪的音频。"),
                io.Float.Input(
                    "start_time",
                    default=0.0,
                    min=0,
                    tooltip="裁剪起点（秒）。",
                ),
                io.Float.Input(
                    "end_time",
                    default=0.0,
                    min=0,
                    tooltip="裁剪终点（秒）；0 表示裁剪到音频末尾。",
                ),
                io.Combo.Input(
                    "format",
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
            outputs=[io.Audio.Output(id="audio")],
        )

    @classmethod
    async def execute(
        cls,
        audio: object,
        start_time: float = 0.0,
        end_time: float = 0.0,
        format: str = "m4a",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_audio(audio) as audio_path:
            result_url, _task_id = await trim_audio(
                audio_path,
                start_time=start_time,
                end_time=end_time if end_time > 0 else None,
                output_format=format,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_audio_output(result_url))


class MediaKitFadeAudio(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitFadeAudio",
            display_name="Fade Audio · 音频淡入淡出",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 为音频添加淡入与淡出效果；CLI 支持本地模式时本地执行"
                "（免费），否则回退云端。"
            ),
            inputs=[
                io.Audio.Input("audio", tooltip="待处理音频。"),
                io.Float.Input(
                    "fade_in_duration",
                    default=1.0,
                    min=0,
                    tooltip="淡入时长（秒）。",
                ),
                io.Float.Input(
                    "fade_out_duration",
                    default=1.0,
                    min=0,
                    tooltip="淡出时长（秒）。",
                ),
                io.Combo.Input(
                    "format",
                    options=["mp3", "m4a", "ogg", "flac", "wav"],
                    default="mp3",
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
            outputs=[io.Audio.Output(id="audio")],
        )

    @classmethod
    async def execute(
        cls,
        audio: object,
        fade_in_duration: float = 1.0,
        fade_out_duration: float = 1.0,
        format: str = "mp3",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_audio(audio) as audio_path:
            result_url, _task_id = await fade_audio(
                audio_path,
                fade_in_duration=fade_in_duration,
                fade_out_duration=fade_out_duration,
                output_format=format,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_audio_output(result_url))


class MediaKitFadeVideoAudio(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitFadeVideoAudio",
            display_name="Fade · 视频声音淡入淡出",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 为视频中的声音添加淡入与淡出效果；CLI 支持本地模式时"
                "本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video", tooltip="待处理视频。"),
                io.Float.Input(
                    "fade_in_duration",
                    default=1.0,
                    min=0,
                    tooltip="淡入时长（秒）。",
                ),
                io.Float.Input(
                    "fade_out_duration",
                    default=1.0,
                    min=0,
                    tooltip="淡出时长（秒）。",
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
            outputs=[io.Video.Output(id="video")],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        fade_in_duration: float = 1.0,
        fade_out_duration: float = 1.0,
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        with materialize_video(video) as video_path:
            result_url, _task_id = await fade_video_audio(
                video_path,
                fade_in_duration=fade_in_duration,
                fade_out_duration=fade_out_duration,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        return io.NodeOutput(await download_video_output(result_url))


class MediaKitExtractAnimatedImage(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitExtractAnimatedImage",
            display_name="Animated · 提取动图",
            category="MediaKit/Video Editing",
            description=(
                "使用 MediaKit 将视频指定时间段提取为 GIF/WebP 动图；CLI 支持本地模式时"
                "本地执行（免费），否则回退云端。"
            ),
            inputs=[
                io.Video.Input("video", tooltip="待提取动图的视频。"),
                io.Float.Input(
                    "start_time",
                    default=0.0,
                    min=0,
                    tooltip="动图起始时间（秒）。",
                ),
                io.Float.Input(
                    "end_time",
                    default=0.0,
                    min=0,
                    tooltip="动图结束时间（秒），必须大于起始时间。",
                ),
                io.Combo.Input(
                    "output_format",
                    options=["gif", "webp"],
                    default="gif",
                    tooltip="动图输出格式。",
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
            outputs=[
                io.Image.Output(id="image"),
                io.String.Output(id="frame_durations_ms"),
                io.String.Output(id="animated_url"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        video: object,
        start_time: float = 0.0,
        end_time: float = 0.0,
        output_format: str = "gif",
        run_mode: str = "auto",
        poll_interval_seconds: int = 10,
        max_poll_attempts: int = 720,
    ) -> io.NodeOutput:
        if end_time <= start_time:
            raise MediaKitInputError("动图结束时间必须大于起始时间。")
        with materialize_video(video) as video_path:
            result_url, _task_id = await extract_animated_image(
                video_path,
                start_time=start_time,
                end_time=end_time,
                output_format=output_format,
                run_mode=run_mode,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_attempts=max_poll_attempts,
            )
        frames, durations = await download_animated_image_output(result_url)
        return io.NodeOutput(frames, durations, result_url)
