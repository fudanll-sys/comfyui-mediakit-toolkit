import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import mediakit_toolkit.cloud_smoke as cloud_smoke
from mediakit_toolkit.cloud_smoke import (
    assert_terminal_completed,
    build_poll_arguments,
    build_trim_arguments,
    download_result,
    extract_result_url,
    extract_task_id,
    parse_final_json,
    run_json_command,
)
from mediakit_toolkit.errors import MediaKitConfigurationError, MediaKitTaskError


class CloudSmokeArgumentTests(unittest.TestCase):
    def test_trim_arguments_use_cloud_and_one_second_window(self):
        input_path = Path("in.mp4")
        args = build_trim_arguments(
            input_path, start_time=0.0, end_time=1.0, client_token="smoke-token-1"
        )
        self.assertEqual(
            args,
            [
                "editing",
                "trim-video",
                "--video-url",
                str(input_path),
                "--start-time",
                "0.0",
                "--end-time",
                "1.0",
                "--client-token",
                "smoke-token-1",
            ],
        )

    def test_rejects_invalid_client_token(self):
        for token in ("", "中文-token" * 10, "x" * 65):
            with self.subTest(token=token), self.assertRaises(MediaKitTaskError):
                build_trim_arguments(
                    Path("in.mp4"),
                    start_time=0.0,
                    end_time=1.0,
                    client_token=token,
                )

    def test_rejects_inverted_trim_window(self):
        with self.assertRaises(MediaKitTaskError):
            build_trim_arguments(
                Path("in.mp4"),
                start_time=1.0,
                end_time=1.0,
                client_token="smoke-token-1",
            )

    def test_poll_arguments_are_bounded(self):
        args = build_poll_arguments("task-1", poll_interval_seconds=5, max_poll_attempts=60)
        self.assertIn("--poll-complete", args)
        self.assertEqual(args[-1], "60")

    def test_rejects_empty_task_id_or_invalid_polling(self):
        with self.assertRaises(MediaKitTaskError):
            build_poll_arguments("", poll_interval_seconds=5, max_poll_attempts=60)
        with self.assertRaises(MediaKitTaskError):
            build_poll_arguments("task-1", poll_interval_seconds=0, max_poll_attempts=60)


class CloudSmokeParsingTests(unittest.TestCase):
    def test_parses_final_json_from_mixed_output(self):
        payload = parse_final_json('progress\n{"task_id":"task-1","status":"queued"}\n')
        self.assertEqual(payload["task_id"], "task-1")

    def test_extracts_task_id(self):
        self.assertEqual(extract_task_id({"task_id": "task-1"}), "task-1")
        with self.assertRaises(MediaKitTaskError):
            extract_task_id({})

    def test_terminal_completed_requires_completed_status(self):
        assert_terminal_completed({"status": "completed", "video_url": "https://x/y"})
        for payload in (
            {"status": "running"},
            {"status": "failed", "success": False},
            {"status": "cancelled"},
        ):
            with self.subTest(payload=payload), self.assertRaises(MediaKitTaskError):
                assert_terminal_completed(payload)

    def test_extract_result_url_supports_flat_and_nested_payload(self):
        self.assertEqual(
            extract_result_url({"video_url": "https://x/out.mp4"}),
            "https://x/out.mp4",
        )
        self.assertEqual(
            extract_result_url({"result": {"video_url": "https://x/out.mp4"}}),
            "https://x/out.mp4",
        )
        with self.assertRaises(MediaKitTaskError):
            extract_result_url({"status": "completed"})


class CloudSmokeCommandTests(unittest.TestCase):
    @patch.object(cloud_smoke, "require_cli", return_value="mediakit-cli")
    def test_run_json_command_uses_argument_array_without_shell(self, _require_cli):
        completed = MagicMock(return_value=MagicMock(
            returncode=0,
            stdout='{"task_id":"task-1"}',
            stderr="",
        ))
        payload = run_json_command(["shared", "version"], timeout=30, runner=completed)
        self.assertEqual(payload["task_id"], "task-1")
        command = completed.call_args.args[0]
        # Must use an argument array with the shell explicitly disabled;
        # never allow shell=True or a single shell string.
        self.assertFalse(completed.call_args.kwargs["shell"])
        self.assertIsInstance(command, list)
        self.assertIn("mediakit-cli", command[0])

    @patch.object(cloud_smoke, "require_cli", return_value="mediakit-cli")
    def test_run_json_command_raises_on_nonzero_exit(self, _require_cli):
        completed = MagicMock(return_value=MagicMock(returncode=2, stdout="", stderr="boom"))
        with self.assertRaises(MediaKitTaskError):
            run_json_command(["bad"], timeout=30, runner=completed)

    def test_download_result_uses_temp_output_and_rejects_empty_file(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"media-bytes"

        fake_opener = MagicMock(return_value=FakeResponse())
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.mp4"
            size = download_result(
                "https://example.com/out.mp4",
                output,
                opener=fake_opener,
            )
            self.assertEqual(size, len(b"media-bytes"))
            self.assertTrue(output.is_file())
        fake_opener.assert_called_once_with("https://example.com/out.mp4")


if __name__ == "__main__":
    unittest.main()
