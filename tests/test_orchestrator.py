import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mediakit_toolkit.cli import CommandResult
from mediakit_toolkit.orchestrator import enhance_video, erase_video_subtitle


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


if __name__ == "__main__":
    unittest.main()
