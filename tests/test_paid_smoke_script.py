"""CLI-free safety/contract tests for the paid smoke script; no paid calls."""
import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from mediakit_toolkit.cli import CommandResult, build_trim_video_arguments
from mediakit_toolkit.errors import MediaKitConfigurationError, MediaKitTaskError

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("paid_smoke_script", ROOT / "scripts/cloud_smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class PaidSmokeSafetyTests(unittest.TestCase):
    def options(self, **overrides):
        values = dict(confirm_billing=True, duration_seconds=2, poll_interval=5,
                      max_attempts=60, client_token="safe-token")
        return values | overrides

    def test_rejects_unconfirmed_or_invalid_inputs_before_submission(self):
        for overrides in [dict(confirm_billing=False), dict(duration_seconds=float("nan")),
                          dict(duration_seconds=4), dict(poll_interval=0),
                          dict(max_attempts=5001), dict(client_token="a\nb"),
                          dict(client_token="x" * 65), dict(client_token="中文")]:
            with self.subTest(overrides=overrides), self.assertRaises(MediaKitConfigurationError):
                smoke.validate_options(**self.options(**overrides))

    def test_printable_shell_metacharacters_remain_data(self):
        token = 'token-$(do-not-execute)-";'
        smoke.validate_options(**self.options(client_token=token))
        args = build_trim_video_arguments("input.mp4", start_time=0, client_token=token)
        self.assertEqual(args[-1], token)

    def test_workflow_has_no_expression_in_run_blocks(self):
        lines = (ROOT / ".github/workflows/cloud_smoke.yml").read_text().splitlines()
        in_run = False
        indentation = 0
        for line in lines:
            if line.strip() == "run: |":
                in_run, indentation = True, len(line) - len(line.lstrip())
                continue
            if in_run and line.strip():
                if len(line) - len(line.lstrip()) <= indentation:
                    in_run = False
                else:
                    self.assertNotIn("${{", line)
        text = "\n".join(lines)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)
        self.assertIn('"$SMOKE_CLIENT_TOKEN"', text)
        self.assertIn("contents: read", text)
        self.assertIn("--confirm-billing", text)

    def runtime(self, directory, *, repeat=False, fail=False):
        async def real_cli(args, **kwargs):
            # State exists before submission and never contains secrets/URLs.
            state = json.loads((directory / "smoke-state.json").read_text())
            self.assertEqual(state["paid_submissions"], 1)
            return CommandResult({"task_id": "task-original", "status": "completed"}, "", "", 0)
        orchestrator = SimpleNamespace(run_cli_async=AsyncMock(side_effect=real_cli))

        class OutputVideo:
            def save_to(self, path):
                Path(path).write_bytes(b"synthetic-output")

        class Node:
            @classmethod
            async def execute(cls, **kwargs):
                self.assertEqual(kwargs["run_mode"], "cloud")
                self.assertEqual(kwargs["end_time"], 1)
                args = build_trim_video_arguments("input.mp4", start_time=0,
                                                  client_token=kwargs["client_token"])
                await orchestrator.run_cli_async(args)
                if repeat:
                    await orchestrator.run_cli_async(args)
                if fail:
                    raise TimeoutError("test timeout")
                return [OutputVideo()]
        return (lambda path: path, Node, orchestrator, object()), orchestrator

    def run_mock_smoke(self, directory, *, repeat=False, fail=False):
        runtime, orchestrator = self.runtime(directory, repeat=repeat, fail=fail)
        with patch.object(smoke, "require_api_key"), patch.object(smoke, "require_cli"), \
             patch.object(smoke, "_load_runtime", return_value=runtime), \
             patch.object(smoke, "_create_fixture"), \
             patch.object(smoke, "_inspect_output", return_value={"decoded_frames": 15}):
            result = smoke.run_smoke(work_dir=directory, comfy_root=directory, **self.options())
        return result, orchestrator

    def test_actual_node_invocation_retains_state_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            result, orchestrator = self.run_mock_smoke(path)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["task_id"], "task-original")
            self.assertEqual(result["paid_submissions"], 1)
            self.assertEqual(orchestrator.run_cli_async.await_count, 1)
            self.assertTrue((path / "smoke-output.mp4").is_file())
            with self.assertRaises(MediaKitConfigurationError):
                self.run_mock_smoke(path)

    def test_timeout_retains_original_task_without_resubmitting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaises(TimeoutError):
                self.run_mock_smoke(path, fail=True)
            state = json.loads((path / "smoke-state.json").read_text())
            self.assertEqual(state["task_id"], "task-original")
            self.assertEqual(state["paid_submissions"], 1)
            self.assertEqual(state["status"], "failed")

    def test_second_paid_submit_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaises(MediaKitTaskError):
                self.run_mock_smoke(path, repeat=True)
            self.assertEqual(json.loads((path / "smoke-state.json").read_text())["paid_submissions"], 1)

    def test_output_inspection_rejects_bad_duration_or_no_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.mp4"
            output.write_bytes(b"fixture")
            for duration, frames in [(1, [object()] * 15), (2, [object()]), (1, [])]:
                container = Mock()
                container.streams.video = [SimpleNamespace(duration=duration, time_base=1,
                    codec_context=SimpleNamespace(width=320, height=240))]
                container.decode.return_value = iter(frames)
                opened = Mock()
                opened.__enter__ = Mock(return_value=container)
                opened.__exit__ = Mock(return_value=False)
                av = SimpleNamespace(open=Mock(return_value=opened))
                if duration == 1 and frames:
                    self.assertEqual(smoke._inspect_output(output, av)["decoded_frames"], 15)
                else:
                    with self.assertRaises(MediaKitTaskError):
                        smoke._inspect_output(output, av)


class ProductionDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_deadline_keeps_task_id_and_prevents_second_query(self):
        from mediakit_toolkit.orchestrator import _poll_until_terminal
        with patch("mediakit_toolkit.orchestrator.monotonic", side_effect=[0, 0, 11]), \
             patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock) as cli:
            cli.return_value = CommandResult({"status": "running"}, "", "", 0)
            with self.assertRaisesRegex(MediaKitTaskError, "task_id=original"):
                await _poll_until_terminal("original", poll_interval_seconds=5,
                                          max_poll_attempts=2, capability="trim", flatten=True)
            self.assertEqual(cli.await_count, 1)
            self.assertLessEqual(cli.await_args.kwargs["timeout"], 10)

    async def test_invalid_poll_options_issue_no_queries(self):
        from mediakit_toolkit.orchestrator import _poll_until_terminal
        with patch("mediakit_toolkit.orchestrator.run_cli_async", new_callable=AsyncMock) as cli:
            with self.assertRaises(MediaKitTaskError):
                await _poll_until_terminal("original", poll_interval_seconds=0,
                                          max_poll_attempts=2, capability="trim", flatten=True)
            cli.assert_not_called()


if __name__ == "__main__":
    unittest.main()
