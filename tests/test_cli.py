import json
import subprocess
import unittest
from unittest.mock import patch

from mediakit_toolkit.cli import (
    build_analyze_highlights_arguments,
    build_asr_subtitles_arguments,
    build_enhance_arguments,
    build_erase_subtitle_arguments,
    build_generative_enhance_arguments,
    build_matte_video_arguments,
    build_probe_metadata_arguments,
    build_query_arguments,
    build_segment_scenes_arguments,
    build_video_ocr_arguments,
    parse_final_json,
    run_cli,
)
from mediakit_toolkit.errors import (
    MediaKitConfigurationError,
    MediaKitInputError,
    MediaKitTaskError,
)


class CliParsingTests(unittest.TestCase):
    def test_parses_plain_json(self):
        self.assertEqual(parse_final_json('{"task_id":"task-1"}')["task_id"], "task-1")

    def test_parses_final_top_level_object_not_nested_result(self):
        output = 'progress\n{"status":"completed","result":{"video_url":"https://x/y?secret=1"}}\n'
        parsed = parse_final_json(output)
        self.assertEqual(parsed["status"], "completed")
        self.assertEqual(parsed["result"]["video_url"], "https://x/y?secret=1")

    def test_parses_last_of_multiple_top_level_objects(self):
        output = '{"task_id":"one"}\nworking\n{"task_id":"two","status":"completed"}'
        self.assertEqual(parse_final_json(output)["task_id"], "two")


class CommandBuilderTests(unittest.TestCase):
    def test_standard_enhance_includes_scene(self):
        args = build_enhance_arguments(
            "/tmp/input.mp4",
            tool_version="standard",
            scene="aigc",
            resolution="1080p",
        )
        self.assertIn("--scene", args)
        self.assertIn("--resolution", args)
        self.assertIn("--bitrate-level", args)
        self.assertEqual(args[:3], ["--cloud", "video", "enhance-video"])

    def test_professional_ignores_scene_and_keep_resolution(self):
        args = build_enhance_arguments(
            "/tmp/input.mp4",
            tool_version="professional",
            scene="aigc",
            resolution="keep",
        )
        self.assertNotIn("--scene", args)
        self.assertNotIn("--resolution", args)

    def test_enhance_includes_optional_fps(self):
        args = build_enhance_arguments(
            "/tmp/input.mp4",
            tool_version="standard",
            scene="common",
            resolution="720p",
            bitrate_level="high",
            fps=60,
        )
        self.assertEqual(args[args.index("--fps") + 1], "60")
        self.assertEqual(args[args.index("--bitrate-level") + 1], "high")

    def test_generative_enhance_uses_dedicated_tool(self):
        args = build_generative_enhance_arguments(
            "/tmp/input.mp4",
            resolution="1080p",
            bitrate_level="high",
            fps=30,
        )
        self.assertEqual(
            args[:3], ["--cloud", "video", "enhance-video-generative"]
        )
        self.assertEqual(args[args.index("--resolution") + 1], "1080p")
        self.assertEqual(args[args.index("--fps") + 1], "30")

    def test_generative_enhance_rejects_unsupported_resolution(self):
        with self.assertRaises(MediaKitInputError):
            build_generative_enhance_arguments(
                "/tmp/input.mp4",
                resolution="4k",
                bitrate_level="medium",
            )

    def test_generative_enhance_rejects_low_nonzero_fps(self):
        with self.assertRaises(MediaKitInputError):
            build_generative_enhance_arguments(
                "/tmp/input.mp4",
                resolution="720p",
                bitrate_level="medium",
                fps=10,
            )

    def test_query_is_blocking_and_bounded(self):
        args = build_query_arguments(
            "task-1", poll_interval_seconds=5, max_poll_attempts=12
        )
        self.assertIn("--poll-complete", args)
        self.assertEqual(args[-1], "12")

    def test_standard_subtitle_erase_has_no_pro_parameters(self):
        args = build_erase_subtitle_arguments(
            "/tmp/input.mp4", professional=False
        )
        self.assertEqual(
            args,
            [
                "--cloud",
                "video",
                "erase-video-subtitle",
                "--video-url",
                "/tmp/input.mp4",
            ],
        )

    def test_pro_subtitle_erase_encodes_valid_region_as_json(self):
        args = build_erase_subtitle_arguments(
            "/tmp/input.mp4",
            professional=True,
            mode="Text",
            output_encode_mode="Size",
            erase_region={
                "top_left_x": 0,
                "top_left_y": 0.5,
                "bottom_right_x": 1,
                "bottom_right_y": 1,
            },
        )
        self.assertEqual(args[:3], ["--cloud", "video", "erase-video-subtitle-pro"])
        region_json = args[args.index("--erase-ratio-location") + 1]
        self.assertEqual(json.loads(region_json)[0]["top_left_y"], 0.5)

    def test_pro_subtitle_erase_rejects_inverted_region(self):
        with self.assertRaises(MediaKitInputError):
            build_erase_subtitle_arguments(
                "/tmp/input.mp4",
                professional=True,
                erase_region={
                    "top_left_x": 0.8,
                    "top_left_y": 0.5,
                    "bottom_right_x": 0.2,
                    "bottom_right_y": 1,
                },
            )


class CliExecutionTests(unittest.TestCase):
    @patch("mediakit_toolkit.cli.shutil.which", return_value="/usr/bin/mediakit-cli")
    @patch("mediakit_toolkit.cli.subprocess.run")
    def test_shell_is_disabled(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            ["mediakit-cli"], 0, '{"task_id":"task-1"}', ""
        )
        result = run_cli(["video", "enhance-video"])
        self.assertEqual(result.payload["task_id"], "task-1")
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(
            run.call_args.kwargs["env"]["MEDIAKIT_SURFACE"], "plugin"
        )
        self.assertEqual(
            run.call_args.kwargs["env"]["MEDIAKIT_RUNTIME"], "comfyui"
        )

    @patch("mediakit_toolkit.cli.shutil.which", return_value="/usr/bin/mediakit-cli")
    @patch("mediakit_toolkit.cli.subprocess.run")
    def test_authentication_error_is_actionable(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            ["mediakit-cli"], 0, '{"error":{"code":"AuthenticationFailed"}}', ""
        )
        with self.assertRaises(MediaKitConfigurationError):
            run_cli(["doctor"])

    @patch("mediakit_toolkit.cli.shutil.which", return_value="/usr/bin/mediakit-cli")
    @patch("mediakit_toolkit.cli.subprocess.run")
    def test_failed_status_raises(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            ["mediakit-cli"], 0, '{"status":"failed","error":{"message":"bad input"}}', ""
        )
        with self.assertRaises(MediaKitTaskError):
            run_cli(["shared", "query-task"])

    @patch("mediakit_toolkit.cli.shutil.which", return_value="/usr/bin/mediakit-cli")
    @patch("mediakit_toolkit.cli.subprocess.run")
    def test_canceled_status_raises(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            ["mediakit-cli"], 0, '{"status":"canceled"}', ""
        )
        with self.assertRaises(MediaKitTaskError):
            run_cli(["shared", "query-task"])


if __name__ == "__main__":
    unittest.main()


class VideoUnderstandingCommandBuilderTests(unittest.TestCase):
    def test_asr_defaults_are_minimal(self):
        args = build_asr_subtitles_arguments("/tmp/in.mp4")
        self.assertEqual(
            args,
            ["--cloud", "video", "asr-subtitles", "--video-url", "/tmp/in.mp4"],
        )

    def test_asr_includes_optional_flags(self):
        args = build_asr_subtitles_arguments(
            "/tmp/in.mp4",
            content_type="speech",
            language="cmn-Hans-CN",
            enable_speaker_info=True,
            enable_confidence=True,
        )
        self.assertEqual(args[args.index("--content-type") + 1], "speech")
        self.assertEqual(args[args.index("--language") + 1], "cmn-Hans-CN")
        self.assertIn("--enable-speaker-info", args)
        self.assertIn("--enable-confidence", args)

    def test_asr_rejects_unknown_content_type(self):
        with self.assertRaises(MediaKitInputError):
            build_asr_subtitles_arguments("/tmp/in.mp4", content_type="lecture")

    def test_ocr_uses_default_mode(self):
        args = build_video_ocr_arguments("/tmp/in.mp4")
        self.assertNotIn("--mode", args)

    def test_ocr_detailed_mode_is_passed(self):
        args = build_video_ocr_arguments("/tmp/in.mp4", mode="Detailed")
        self.assertEqual(args[args.index("--mode") + 1], "Detailed")

    def test_matte_builds_portrait_command(self):
        args = build_matte_video_arguments(
            "/tmp/in.mp4", tool="matte-portrait-video"
        )
        self.assertEqual(
            args[:3], ["--cloud", "video", "matte-portrait-video"]
        )
        self.assertNotIn("--format", args)

    def test_matte_accepts_mov_format(self):
        args = build_matte_video_arguments(
            "/tmp/in.mp4", tool="matte-greenscreen-video", output_format="MOV"
        )
        self.assertEqual(args[args.index("--format") + 1], "MOV")

    def test_matte_rejects_unknown_tool(self):
        with self.assertRaises(MediaKitInputError):
            build_matte_video_arguments("/tmp/in.mp4", tool="matte-unknown")

    def test_scene_segmentation_passes_all_optional_values(self):
        args = build_segment_scenes_arguments(
            "/tmp/in.mp4",
            enable_clip_fade=True,
            segment_threshold=10,
            min_duration=3,
            max_duration=30,
        )
        self.assertEqual(args[args.index("--segment-threshold") + 1], "10")
        self.assertEqual(args[args.index("--min-duration") + 1], "3")
        self.assertEqual(args[args.index("--max-duration") + 1], "30")
        self.assertIn("--enable-clip-fade", args)

    def test_scene_segmentation_rejects_threshold_at_100(self):
        with self.assertRaises(MediaKitInputError):
            build_segment_scenes_arguments("/tmp/in.mp4", segment_threshold=100)

    def test_scene_segmentation_rejects_inverted_durations(self):
        with self.assertRaises(MediaKitInputError):
            build_segment_scenes_arguments(
                "/tmp/in.mp4", min_duration=30, max_duration=3
            )

    def test_highlight_analysis_uses_storyline_cuts_for_miniseries(self):
        args = build_analyze_highlights_arguments(
            ["/tmp/in.mp4"], model="Miniseries"
        )
        self.assertEqual(
            args[:3], ["--cloud", "video", "analyze-video-highlights"]
        )
        self.assertEqual(args[args.index("--mode") + 1], "StorylineCuts")
        urls = json.loads(args[args.index("--video-urls") + 1])
        self.assertEqual(urls, ["/tmp/in.mp4"])

    def test_highlight_analysis_uses_extract_for_game(self):
        args = build_analyze_highlights_arguments(
            ["/tmp/in.mp4"], model="Game"
        )
        self.assertEqual(args[args.index("--mode") + 1], "HighlightExtract")

    def test_highlight_analysis_rejects_empty_list(self):
        with self.assertRaises(MediaKitInputError):
            build_analyze_highlights_arguments([], model="Game")

    def test_probe_metadata_command(self):
        args = build_probe_metadata_arguments("/tmp/in.mp4")
        self.assertEqual(
            args,
            ["--cloud", "video", "probe-video-metadata", "--video-url", "/tmp/in.mp4"],
        )
