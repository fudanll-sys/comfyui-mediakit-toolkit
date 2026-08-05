import json
import subprocess
import unittest
from unittest.mock import patch

from mediakit_toolkit.cli import (
    build_enhance_arguments,
    build_query_arguments,
    parse_final_json,
    run_cli,
)
from mediakit_toolkit.errors import (
    MediaKitConfigurationError,
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

    def test_professional_ignores_scene_and_keep_resolution(self):
        args = build_enhance_arguments(
            "/tmp/input.mp4",
            tool_version="professional",
            scene="aigc",
            resolution="keep",
        )
        self.assertNotIn("--scene", args)
        self.assertNotIn("--resolution", args)

    def test_query_is_blocking_and_bounded(self):
        args = build_query_arguments(
            "task-1", poll_interval_seconds=5, max_poll_attempts=12
        )
        self.assertIn("--poll-complete", args)
        self.assertEqual(args[-1], "12")


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


if __name__ == "__main__":
    unittest.main()

