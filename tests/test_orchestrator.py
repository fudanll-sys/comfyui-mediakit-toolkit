import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mediakit_toolkit.cli import CommandResult
from mediakit_toolkit.orchestrator import (
    analyze_video_highlights,
    asr_video_subtitles,
    enhance_video,
    enhance_video_generative,
    erase_video_subtitle,
    find_subtitle_url,
    matte_video,
    ocr_video_subtitles,
    probe_video_metadata,
    segment_video_scenes,
)


class OrchestratorTests(unittest.IsolatedAsyncioTestCase):
    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_submit_then_poll(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-1"}, "", "", 0),
            CommandResult(
                {"status": "completed", "video_url": "https://example.com/out.mp4"},
                "",
                "",
                0,
            ),
        ]
        url, task_id = await enhance_video(
            Path("/tmp/input.mp4"),
            tool_version="standard",
            scene="aigc",
            resolution="1080p",
            poll_interval_seconds=5,
            max_poll_attempts=10,
        )
        self.assertEqual(task_id, "task-1")
        self.assertEqual(url, "https://example.com/out.mp4")
        self.assertEqual(run_cli_async.await_count, 2)

    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_pro_subtitle_erase_submit_then_poll(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-erase"}, "", "", 0),
            CommandResult(
                {"status": "completed", "video_url": "https://example.com/clean.mp4"},
                "",
                "",
                0,
            ),
        ]
        url, task_id = await erase_video_subtitle(
            Path("/tmp/input.mp4"),
            professional=True,
            mode="Subtitle",
            output_encode_mode="Quality",
            erase_region=None,
            poll_interval_seconds=10,
            max_poll_attempts=20,
        )
        self.assertEqual(task_id, "task-erase")
        self.assertEqual(url, "https://example.com/clean.mp4")
        submit_arguments = run_cli_async.await_args_list[0].args[0]
        self.assertIn("erase-video-subtitle-pro", submit_arguments)

    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_generative_enhance_submit_then_poll(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-generative"}, "", "", 0),
            CommandResult(
                {"status": "completed", "video_url": "https://example.com/ai.mp4"},
                "",
                "",
                0,
            ),
        ]
        url, task_id = await enhance_video_generative(
            Path("/tmp/input.mp4"),
            resolution="1080p",
            bitrate_level="medium",
            fps=0,
            poll_interval_seconds=10,
            max_poll_attempts=20,
        )
        self.assertEqual(task_id, "task-generative")
        self.assertEqual(url, "https://example.com/ai.mp4")
        self.assertIn(
            "enhance-video-generative", run_cli_async.await_args_list[0].args[0]
        )


if __name__ == "__main__":
    unittest.main()


class VideoUnderstandingOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_asr_returns_flattened_payload(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-asr"}, "", "", 0),
            CommandResult(
                {
                    "status": "completed",
                    "result": {
                        "subtitle_url": "https://example.com/out.srt",
                        "language": "cmn-Hans-CN",
                    },
                },
                "",
                "",
                0,
            ),
        ]
        payload, task_id = await asr_video_subtitles(
            Path("/tmp/in.mp4"),
            content_type="speech",
            language="cmn-Hans-CN",
            enable_speaker_info=True,
            enable_confidence=False,
            poll_interval_seconds=10,
            max_poll_attempts=20,
        )
        self.assertEqual(task_id, "task-asr")
        self.assertEqual(payload["subtitle_url"], "https://example.com/out.srt")
        self.assertEqual(payload["language"], "cmn-Hans-CN")
        submit_arguments = run_cli_async.await_args_list[0].args[0]
        self.assertIn("asr-subtitles", submit_arguments)

    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_ocr_submit_then_poll(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-ocr"}, "", "", 0),
            CommandResult(
                {
                    "status": "completed",
                    "srt_url": "https://example.com/out.srt",
                },
                "",
                "",
                0,
            ),
        ]
        payload, task_id = await ocr_video_subtitles(
            Path("/tmp/in.mp4"),
            mode="Detailed",
            poll_interval_seconds=10,
            max_poll_attempts=20,
        )
        self.assertEqual(task_id, "task-ocr")
        self.assertEqual(payload["srt_url"], "https://example.com/out.srt")
        self.assertIn("video-ocr", run_cli_async.await_args_list[0].args[0])

    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_matte_returns_video_url(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-matte"}, "", "", 0),
            CommandResult(
                {"status": "completed", "video_url": "https://example.com/out.webm"},
                "",
                "",
                0,
            ),
        ]
        url, task_id = await matte_video(
            Path("/tmp/in.mp4"),
            tool="matte-portrait-video",
            output_format="WEBM",
            poll_interval_seconds=10,
            max_poll_attempts=20,
        )
        self.assertEqual(task_id, "task-matte")
        self.assertEqual(url, "https://example.com/out.webm")
        self.assertIn("matte-portrait-video", run_cli_async.await_args_list[0].args[0])

    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_scene_segmentation_passes_threshold(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-scene"}, "", "", 0),
            CommandResult(
                {"status": "completed", "segments": [{"start": 0, "end": 5}]},
                "",
                "",
                0,
            ),
        ]
        payload, _ = await segment_video_scenes(
            Path("/tmp/in.mp4"),
            enable_clip_fade=True,
            segment_threshold=10,
            min_duration=3,
            max_duration=30,
            poll_interval_seconds=10,
            max_poll_attempts=20,
        )
        self.assertEqual(payload["segments"][0]["end"], 5)
        submit_arguments = run_cli_async.await_args_list[0].args[0]
        self.assertIn("segment-scenes", submit_arguments)
        self.assertEqual(
            submit_arguments[submit_arguments.index("--segment-threshold") + 1],
            "10",
        )

    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_highlight_analysis_uses_model(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-hl"}, "", "", 0),
            CommandResult(
                {"status": "completed", "clips": [{"score": 0.9}]},
                "",
                "",
                0,
            ),
        ]
        payload, _ = await analyze_video_highlights(
            Path("/tmp/in.mp4"),
            model="Game",
            poll_interval_seconds=10,
            max_poll_attempts=20,
        )
        self.assertEqual(payload["clips"][0]["score"], 0.9)
        submit_arguments = run_cli_async.await_args_list[0].args[0]
        self.assertEqual(
            submit_arguments[submit_arguments.index("--model") + 1], "Game"
        )
        self.assertEqual(
            submit_arguments[submit_arguments.index("--mode") + 1],
            "HighlightExtract",
        )

    @patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock)
    async def test_probe_metadata_returns_payload(self, run_cli_async):
        run_cli_async.side_effect = [
            CommandResult({"task_id": "task-meta"}, "", "", 0),
            CommandResult(
                {
                    "status": "completed",
                    "video_stream_meta": {"width": 1920},
                },
                "",
                "",
                0,
            ),
        ]
        payload, task_id = await probe_video_metadata(
            Path("/tmp/in.mp4"),
            poll_interval_seconds=10,
            max_poll_attempts=20,
        )
        self.assertEqual(task_id, "task-meta")
        self.assertEqual(payload["video_stream_meta"]["width"], 1920)
        self.assertIn("probe-video-metadata", run_cli_async.await_args_list[0].args[0])

    def test_find_subtitle_url_prefers_subtitle_field(self):
        payload = {"file_url": "https://x/a.txt", "subtitle_url": "https://x/a.srt"}
        self.assertEqual(
            find_subtitle_url(payload), "https://x/a.srt"
        )

    def test_find_subtitle_url_falls_back_to_any_file_url(self):
        payload = {"file_url": "https://x/a.srt"}
        self.assertEqual(
            find_subtitle_url(payload), "https://x/a.srt"
        )
