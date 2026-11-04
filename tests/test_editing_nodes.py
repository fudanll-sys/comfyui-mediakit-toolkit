"""Tests for P1 MediaKit Video Editing nodes (builders and orchestration)."""

import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mediakit_toolkit.cli import (
    CommandResult,
    build_add_subtitle_arguments,
    build_adjust_audio_speed_arguments,
    build_adjust_video_speed_arguments,
    build_adjust_video_volume_arguments,
    build_apply_camera_motion_arguments,
    build_apply_video_filter_arguments,
    build_concat_audio_arguments,
    build_concat_video_arguments,
    build_crop_video_arguments,
    build_extract_animated_image_arguments,
    build_fade_audio_arguments,
    build_fade_video_audio_arguments,
    build_flip_video_arguments,
    build_mix_audio_arguments,
    build_mux_audio_video_arguments,
    build_rotate_video_arguments,
    build_stitch_video_arguments,
    build_trim_audio_arguments,
)
from mediakit_toolkit.errors import MediaKitInputError
from mediakit_toolkit.orchestrator import (
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
    fade_audio,
    fade_video_audio,
    flip_video,
    mix_audios,
    mux_audio_video,
    rotate_video,
    stitch_videos,
    trim_audio,
)


class EditingBuilderTests(unittest.TestCase):
    def test_adjust_video_speed_defaults(self):
        args = build_adjust_video_speed_arguments("/tmp/in.mp4")
        self.assertEqual(
            args, ["--cloud", "editing", "adjust-video-speed", "--video-url", "/tmp/in.mp4"]
        )

    def test_adjust_video_speed_custom(self):
        args = build_adjust_video_speed_arguments("/tmp/in.mp4", speed=2.0)
        self.assertEqual(args[args.index("--speed") + 1], "2.0")

    def test_adjust_video_speed_rejects_out_of_range(self):
        with self.assertRaises(MediaKitInputError):
            build_adjust_video_speed_arguments("/tmp/in.mp4", speed=9.0)

    def test_adjust_video_volume_defaults(self):
        args = build_adjust_video_volume_arguments("/tmp/in.mp4")
        self.assertEqual(
            args,
            ["--cloud", "editing", "adjust-video-volume", "--video-url", "/tmp/in.mp4"],
        )

    def test_adjust_video_volume_custom(self):
        args = build_adjust_video_volume_arguments("/tmp/in.mp4", volume=0.5)
        self.assertEqual(args[args.index("--volume") + 1], "0.5")

    def test_apply_camera_motion_flags(self):
        args = build_apply_camera_motion_arguments(
            "/tmp/in.mp4", motion_style="bounce", start_time=1.5, end_time=10
        )
        self.assertEqual(args[args.index("--motion-style") + 1], "bounce")
        self.assertEqual(args[args.index("--start-time") + 1], "1.5")
        self.assertEqual(args[args.index("--end-time") + 1], "10")

    def test_apply_camera_motion_local_prefix(self):
        args = build_apply_camera_motion_arguments("/tmp/in.mp4", run_mode="local")
        self.assertEqual(args[0], "--local")

    def test_apply_video_filter_defaults(self):
        args = build_apply_video_filter_arguments("/tmp/in.mp4")
        self.assertNotIn("--filter-style", args)

    def test_apply_video_filter_custom(self):
        args = build_apply_video_filter_arguments("/tmp/in.mp4", filter_style="sunset")
        self.assertEqual(args[args.index("--filter-style") + 1], "sunset")

    def test_apply_video_filter_rejects_unknown(self):
        with self.assertRaises(MediaKitInputError):
            build_apply_video_filter_arguments("/tmp/in.mp4", filter_style="vaporwave")

    def test_flip_video_horizontal(self):
        args = build_flip_video_arguments("/tmp/in.mp4", is_flip_horizontal=True)
        self.assertIn("--is-flip-horizontal", args)
        self.assertNotIn("--is-flip-vertical", args)

    def test_flip_video_both(self):
        args = build_flip_video_arguments(
            "/tmp/in.mp4", is_flip_horizontal=True, is_flip_vertical=True
        )
        self.assertIn("--is-flip-horizontal", args)
        self.assertIn("--is-flip-vertical", args)

    def test_flip_video_rejects_no_direction(self):
        with self.assertRaises(MediaKitInputError):
            build_flip_video_arguments("/tmp/in.mp4")

    def test_rotate_video_required_direction(self):
        args = build_rotate_video_arguments("/tmp/in.mp4", rotate_direction="rotate_180")
        self.assertEqual(args[args.index("--rotate-direction") + 1], "rotate_180")

    def test_rotate_video_rejects_unknown(self):
        with self.assertRaises(MediaKitInputError):
            build_rotate_video_arguments("/tmp/in.mp4", rotate_direction="rotate_45")

    def test_concat_video_repeats_urls(self):
        args = build_concat_video_arguments(["/tmp/a.mp4", "/tmp/b.mp4"])
        self.assertEqual(
            [args[i + 1] for i, a in enumerate(args) if a == "--video-urls"],
            ["/tmp/a.mp4", "/tmp/b.mp4"],
        )

    def test_concat_video_transitions(self):
        args = build_concat_video_arguments(
            ["/tmp/a.mp4"], transitions=["1182359", "1182360"]
        )
        self.assertEqual(args.count("--transitions"), 2)

    def test_concat_video_rejects_empty(self):
        with self.assertRaises(MediaKitInputError):
            build_concat_video_arguments([])

    def test_concat_audio_repeats_urls(self):
        args = build_concat_audio_arguments(["/tmp/a.mp3", "/tmp/b.mp3"], output_format="wav")
        self.assertEqual(args.count("--audio-urls"), 2)
        self.assertEqual(args[args.index("--format") + 1], "wav")

    def test_mix_audio_repeats_urls(self):
        args = build_mix_audio_arguments(["/tmp/a.mp3", "/tmp/b.mp3"])
        self.assertEqual(args[0], "--cloud")
        self.assertEqual(args[1], "editing")
        self.assertEqual(args[2], "mix-audio")
        self.assertEqual(args.count("--audio-urls"), 2)

    def test_mux_audio_video_defaults(self):
        args = build_mux_audio_video_arguments("/tmp/v.mp4", "/tmp/a.mp3")
        self.assertEqual(
            args,
            [
                "--cloud",
                "editing",
                "mux-audio-video",
                "--video-url",
                "/tmp/v.mp4",
                "--audio-url",
                "/tmp/a.mp3",
            ],
        )

    def test_mux_audio_video_replace_and_sync(self):
        args = build_mux_audio_video_arguments(
            "/tmp/v.mp4",
            "/tmp/a.mp3",
            is_audio_reserve=False,
            is_video_audio_sync=True,
            sync_method="speed",
            sync_mode="audio",
        )
        self.assertIn("--is-audio-reserve=false", args)
        self.assertIn("--is-video-audio-sync=true", args)
        self.assertEqual(args[args.index("--sync-method") + 1], "speed")
        self.assertEqual(args[args.index("--sync-mode") + 1], "audio")

    def test_add_subtitle_subtitle_url(self):
        args = build_add_subtitle_arguments(
            "/tmp/in.mp4", subtitle_url="/tmp/sub.srt"
        )
        self.assertEqual(args[2], "add-subtitle-to-video")
        self.assertEqual(args[args.index("--subtitle-url") + 1], "/tmp/sub.srt")
        self.assertNotIn("--subtitles", args)

    def test_add_subtitle_inline_json(self):
        args = build_add_subtitle_arguments(
            "/tmp/in.mp4",
            subtitles=[{"subtitle_text": "你好", "start_time": 0, "end_time": 3}],
        )
        self.assertIn("--subtitles", args)
        self.assertIn("你好", args[args.index("--subtitles") + 1])

    def test_add_subtitle_rejects_missing_both(self):
        with self.assertRaises(MediaKitInputError):
            build_add_subtitle_arguments("/tmp/in.mp4")

    def test_add_subtitle_rejects_bad_item(self):
        with self.assertRaises(MediaKitInputError):
            build_add_subtitle_arguments(
                "/tmp/in.mp4",
                subtitles=[{"subtitle_text": "x"}],
            )

    def test_add_subtitle_style_flags(self):
        args = build_add_subtitle_arguments(
            "/tmp/in.mp4",
            subtitle_url="/tmp/sub.srt",
            subtitle_font_type="pm_zhengdao",
            subtitle_pos_preset="top_center",
            subtitle_font_size=80,
            subtitle_font_color="#FF0000FF",
            subtitle_text_effect="fx123",
        )
        self.assertIn("--subtitle-font-type", args)
        self.assertIn("--subtitle-pos-preset", args)
        self.assertEqual(args[args.index("--subtitle-font-size") + 1], "80")
        self.assertEqual(args[args.index("--subtitle-font-color") + 1], "#FF0000FF")
        self.assertEqual(args[args.index("--subtitle-text-effect") + 1], "fx123")

    def test_stitch_video_json(self):
        args = build_stitch_video_arguments(
            ["/tmp/a.mp4", "/tmp/b.mp4", "/tmp/c.mp4"],
            stitch_direction="vertical",
        )
        self.assertEqual(args[2], "stitch-video")
        payload = json.loads(args[args.index("--videos") + 1])
        self.assertEqual(len(payload), 3)
        self.assertEqual(payload[0], {"video_url": "/tmp/a.mp4"})
        self.assertEqual(args[args.index("--stitch-direction") + 1], "vertical")

    def test_stitch_video_rejects_out_of_range(self):
        with self.assertRaises(MediaKitInputError):
            build_stitch_video_arguments(["/tmp/a.mp4"], stitch_direction="horizontal")
        with self.assertRaises(MediaKitInputError):
            build_stitch_video_arguments(
                ["/tmp/a.mp4"], stitch_direction="diagonal"
            )

    def test_crop_video_flags(self):
        args = build_crop_video_arguments(
            "/tmp/in.mp4",
            top_left_x=100,
            top_left_y=200,
            bottom_right_x=1100,
            bottom_right_y=700,
        )
        self.assertEqual(args[2], "crop-video")
        self.assertEqual(
            [args[i + 1] for i, a in enumerate(args) if a == "--top-left-x"],
            ["100"],
        )
        self.assertEqual(
            [args[i + 1] for i, a in enumerate(args) if a == "--bottom-right-y"],
            ["700"],
        )

    def test_crop_video_validations(self):
        with self.assertRaises(MediaKitInputError):
            build_crop_video_arguments(
                "/tmp/in.mp4",
                top_left_x=10,
                top_left_y=0,
                bottom_right_x=10,
                bottom_right_y=100,
            )
        with self.assertRaises(MediaKitInputError):
            build_crop_video_arguments(
                "/tmp/in.mp4",
                top_left_x=0,
                top_left_y=0,
                bottom_right_x=10,
                bottom_right_y=10,
            )

    def test_adjust_audio_speed_flags(self):
        args = build_adjust_audio_speed_arguments("/tmp/in.m4a", speed=1.5)
        self.assertEqual(args[2], "adjust-audio-speed")
        self.assertEqual(args[args.index("--speed") + 1], "1.5")
        self.assertNotIn("--format", args)
        args = build_adjust_audio_speed_arguments(
            "/tmp/in.m4a", speed=1.0, output_format="wav"
        )
        self.assertEqual(args[args.index("--format") + 1], "wav")

    def test_adjust_audio_speed_validations(self):
        with self.assertRaises(MediaKitInputError):
            build_adjust_audio_speed_arguments("/tmp/in.m4a", speed=4.5)
        with self.assertRaises(MediaKitInputError):
            build_adjust_audio_speed_arguments("/tmp/in.m4a", output_format="mp4")

    def test_trim_audio_flags(self):
        args = build_trim_audio_arguments(
            "/tmp/in.m4a", start_time=1.5, end_time=10.0, output_format="ogg"
        )
        self.assertEqual(args[2], "trim-audio")
        self.assertEqual(args[args.index("--start-time") + 1], "1.5")
        self.assertEqual(args[args.index("--end-time") + 1], "10.0")
        self.assertEqual(args[args.index("--format") + 1], "ogg")

    def test_trim_audio_validations(self):
        with self.assertRaises(MediaKitInputError):
            build_trim_audio_arguments("/tmp/in.m4a", start_time=5.0, end_time=2.0)

    def test_fade_audio_default_format_is_mp3(self):
        args = build_fade_audio_arguments("/tmp/in.m4a")
        self.assertEqual(args[2], "fade-audio")
        self.assertNotIn("--format", args)
        args = build_fade_audio_arguments(
            "/tmp/in.m4a", fade_in_duration=0.5, output_format="m4a"
        )
        self.assertEqual(args[args.index("--fade-in-duration") + 1], "0.5")
        self.assertEqual(args[args.index("--format") + 1], "m4a")

    def test_fade_video_audio_flags(self):
        args = build_fade_video_audio_arguments(
            "/tmp/in.mp4", fade_in_duration=2.0, fade_out_duration=3.0
        )
        self.assertEqual(args[2], "fade-video-audio")
        self.assertEqual(args[args.index("--fade-in-duration") + 1], "2.0")
        self.assertEqual(args[args.index("--fade-out-duration") + 1], "3.0")

    def test_extract_animated_image_flags(self):
        args = build_extract_animated_image_arguments(
            "/tmp/in.mp4", start_time=1.0, end_time=4.0, output_format="webp"
        )
        self.assertEqual(args[2], "extract-animated-image")
        self.assertEqual(args[args.index("--start-time") + 1], "1.0")
        self.assertEqual(args[args.index("--end-time") + 1], "4.0")
        self.assertEqual(args[args.index("--output-format") + 1], "webp")

    def test_extract_animated_image_validations(self):
        with self.assertRaises(MediaKitInputError):
            build_extract_animated_image_arguments(
                "/tmp/in.mp4", start_time=4.0, end_time=4.0
            )
        with self.assertRaises(MediaKitInputError):
            build_extract_animated_image_arguments(
                "/tmp/in.mp4", start_time=0.0, end_time=1.0, output_format="png"
            )


class EditingOrchestratorTests(unittest.TestCase):
    async def _run(self, coro):
        import asyncio

        return await asyncio.ensure_future(coro)

    def test_adjust_video_speed_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t1"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    adjust_video_speed(
                        Path("/tmp/in.mp4"),
                        speed=2.0,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t1")
                self.assertEqual(url, "https://x/out.mp4")
                self.assertIn("adjust-video-speed", run.await_args_list[0].args[0])

    def test_adjust_video_speed_local(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes",
            return_value={"Cloud", "Local"},
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.return_value = CommandResult(
                    {"video_url": "/tmp/out.mp4"}, "", "", 0
                )
                import asyncio

                url, task_id = asyncio.run(
                    adjust_video_speed(
                        Path("/tmp/in.mp4"),
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "")
                self.assertEqual(run.await_args.args[0][0], "--local")
                self.assertTrue(url.endswith("out.mp4"))

    def test_adjust_video_volume_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t2"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    adjust_video_volume(
                        Path("/tmp/in.mp4"),
                        volume=0.5,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t2")
                self.assertIn("adjust-video-volume", run.await_args_list[0].args[0])

    def test_apply_camera_motion_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t3"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    apply_camera_motion(
                        Path("/tmp/in.mp4"),
                        motion_style="bounce",
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t3")
                self.assertIn("apply-camera-motion", run.await_args_list[0].args[0])

    def test_apply_video_filter_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t4"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    apply_video_filter(
                        Path("/tmp/in.mp4"),
                        filter_style="food",
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t4")
                self.assertIn("apply-video-filter", run.await_args_list[0].args[0])

    def test_flip_video_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t5"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    flip_video(
                        Path("/tmp/in.mp4"),
                        is_flip_horizontal=True,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t5")
                self.assertIn("flip-video", run.await_args_list[0].args[0])

    def test_rotate_video_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t6"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    rotate_video(
                        Path("/tmp/in.mp4"),
                        rotate_direction="rotate_right_90",
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t6")
                self.assertIn("rotate-video", run.await_args_list[0].args[0])

    def test_concat_videos_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t7"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    concat_videos(
                        [Path("/tmp/a.mp4"), Path("/tmp/b.mp4")],
                        transitions=["1182359"],
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t7")
                submit = run.await_args_list[0].args[0]
                self.assertIn("concat-video", submit)
                self.assertEqual(submit.count("--video-urls"), 2)

    def test_concat_audios_local(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes",
            return_value={"Cloud", "Local"},
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.return_value = CommandResult(
                    {"audio_url": "/tmp/out.m4a"}, "", "", 0
                )
                import asyncio

                url, task_id = asyncio.run(
                    concat_audios(
                        [Path("/tmp/a.mp3"), Path("/tmp/b.mp3")],
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "")
                self.assertEqual(run.await_args.args[0][0], "--local")

    def test_mix_audios_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t8"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "audio_url": "https://x/out.m4a"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    mix_audios(
                        [Path("/tmp/a.mp3"), Path("/tmp/b.mp3")],
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t8")
                self.assertIn("mix-audio", run.await_args_list[0].args[0])

    def test_mux_audio_video_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t9"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    mux_audio_video(
                        Path("/tmp/v.mp4"),
                        Path("/tmp/a.mp3"),
                        is_audio_reserve=False,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t9")
                submit = run.await_args_list[0].args[0]
                self.assertIn("mux-audio-video", submit)
                self.assertIn("--is-audio-reserve=false", submit)

    def test_add_subtitle_to_video_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t10"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    add_subtitle_to_video(
                        Path("/tmp/in.mp4"),
                        subtitle_url="/tmp/sub.srt",
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t10")
                self.assertIn(
                    "add-subtitle-to-video", run.await_args_list[0].args[0]
                )

    def test_stitch_videos_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t11"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    stitch_videos(
                        [Path("/tmp/a.mp4"), Path("/tmp/b.mp4")],
                        stitch_direction="vertical",
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t11")
                self.assertIn("stitch-video", run.await_args_list[0].args[0])

    def test_crop_video_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t12"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    crop_video(
                        Path("/tmp/in.mp4"),
                        top_left_x=100,
                        top_left_y=100,
                        bottom_right_x=1100,
                        bottom_right_y=700,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t12")
                submit = run.await_args_list[0].args[0]
                self.assertIn("crop-video", submit)
                self.assertIn("--top-left-x", submit)

    def test_adjust_audio_speed_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t13"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "audio_url": "https://x/out.m4a"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    adjust_audio_speed(
                        Path("/tmp/in.m4a"),
                        speed=1.5,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t13")
                self.assertIn("adjust-audio-speed", run.await_args_list[0].args[0])

    def test_trim_audio_local(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes",
            return_value={"Cloud", "Local"},
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.return_value = CommandResult(
                    {"audio_url": "/tmp/out.m4a"}, "", "", 0
                )
                import asyncio

                url, task_id = asyncio.run(
                    trim_audio(
                        Path("/tmp/in.m4a"),
                        start_time=1.0,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "")
                self.assertEqual(run.await_args.args[0][0], "--local")

    def test_fade_audio_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t14"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "audio_url": "https://x/out.mp3"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    fade_audio(
                        Path("/tmp/in.m4a"),
                        fade_out_duration=2.0,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t14")
                self.assertIn("fade-audio", run.await_args_list[0].args[0])

    def test_fade_video_audio_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t15"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "video_url": "https://x/out.mp4"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    fade_video_audio(
                        Path("/tmp/in.mp4"),
                        fade_in_duration=2.0,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t15")
                self.assertIn("fade-video-audio", run.await_args_list[0].args[0])

    def test_extract_animated_image_cloud(self):
        with patch(
            "mediakit_toolkit.orchestrator.supported_modes", return_value={"Cloud"}
        ):
            with patch(
                "mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock
            ) as run:
                run.side_effect = [
                    CommandResult({"task_id": "t16"}, "", "", 0),
                    CommandResult(
                        {"status": "completed", "image_url": "https://x/out.gif"}, "", "", 0
                    ),
                ]
                import asyncio

                url, task_id = asyncio.run(
                    extract_animated_image(
                        Path("/tmp/in.mp4"),
                        start_time=1.0,
                        end_time=4.0,
                        poll_interval_seconds=10,
                        max_poll_attempts=20,
                    )
                )
                self.assertEqual(task_id, "t16")
                self.assertIn(
                    "extract-animated-image", run.await_args_list[0].args[0]
                )
                self.assertEqual(url, "https://x/out.gif")


if __name__ == "__main__":
    unittest.main()
