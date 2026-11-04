"""Tests for the CLI schema synchronization script."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sync_cli_schemas import (  # noqa: E402
    cli_version,
    collect_snapshots,
    diff_report,
    fingerprint,
    parse_domains,
    parse_modes,
    parse_tools,
    validate_snapshot_tree,
    write_snapshots,
)


class ParseTests(unittest.TestCase):
    def test_parse_domains_tsv(self):
        output = "audio\t4\t音频处理。\nediting\t20\t音视频剪辑。\n"
        self.assertEqual(parse_domains(output), [("audio", "音频处理。"), ("editing", "音视频剪辑。")])

    def test_parse_tools_from_help(self):
        output = """
mediakit-cli editing [command]
- trim-audio    用于音频裁剪
- trim-video    用于视频裁剪
  查看详情: mediakit-cli editing trim-video --help
Usage:
"""
        self.assertEqual(parse_tools(output), ["trim-audio", "trim-video"])

    def test_parse_modes(self):
        output = "支持模式: Cloud, Local\n当前模式: Cloud\n"
        self.assertEqual(parse_modes(output), ("Cloud", "Local"))

    def test_parse_modes_deduplicates(self):
        output = "支持模式: Cloud, Cloud\n"
        self.assertEqual(parse_modes(output), ("Cloud",))

    def test_fingerprint_is_stable_and_order_sensitive(self):
        left = {"b": 2, "a": {"x": 1}}
        right = {"a": {"x": 1}, "b": 2}
        changed = {"a": {"x": 9}, "b": 2}
        self.assertEqual(fingerprint(left), fingerprint(right))
        self.assertNotEqual(fingerprint(left), fingerprint(changed))


class DiffReportTests(unittest.TestCase):
    def _snapshot(self, tool, domain="video"):
        return type(
            "Tool",
            (),
            {"domain": domain, "tool": tool, "fingerprint": "abc", "modes": ("Cloud",)},
        )()

    def test_detects_added_and_removed_tools(self):
        current = {"video": [self._snapshot("new-tool")]}
        previous = {
            "cli_version": "0.2.2",
            "domains": {"video": [{"tool": "old-tool", "fingerprint": "abc", "modes": ["Cloud"]}]},
        }
        drifted, report = diff_report("0.2.2", current, previous)
        self.assertTrue(drifted)
        text = "\n".join(report)
        self.assertIn("工具新增", text)
        self.assertIn("工具消失", text)

    def test_detects_fingerprint_change(self):
        changed = self._snapshot("trim-video")
        current = {"editing": [changed]}
        previous = {
            "cli_version": "0.2.2",
            "domains": {"editing": [{"tool": "trim-video", "fingerprint": "xyz", "modes": ["Cloud"]}]},
        }
        drifted, report = diff_report("0.2.2", current, previous)
        self.assertTrue(drifted)
        self.assertIn("参数变化", "\n".join(report))

    def test_detects_mode_change(self):
        changed = self._snapshot("trim-video")
        current = {"editing": [changed]}
        previous = {
            "cli_version": "0.2.2",
            "domains": {"editing": [{"tool": "trim-video", "fingerprint": "abc", "modes": ["Cloud", "Local"]}]},
        }
        drifted, report = diff_report("0.2.2", current, previous)
        self.assertTrue(drifted)
        self.assertIn("模式变化", "\n".join(report))

    def test_no_drift_when_identical(self):
        current = {"video": [self._snapshot("enhance-video")]}
        previous = {
            "cli_version": "0.2.2",
            "domains": {"video": [{"tool": "enhance-video", "fingerprint": "abc", "modes": ["Cloud"]}]},
        }
        drifted, report = diff_report("0.2.2", current, previous)
        self.assertFalse(drifted)
        self.assertEqual(report, [])

    def test_version_change_is_drift(self):
        current = {"video": [self._snapshot("enhance-video")]}
        previous = {
            "cli_version": "0.1.0",
            "domains": {"video": [{"tool": "enhance-video", "fingerprint": "abc", "modes": ["Cloud"]}]},
        }
        drifted, report = diff_report("0.2.2", current, previous)
        self.assertTrue(drifted)
        self.assertIn("CLI 版本变化", "\n".join(report))


class SnapshotTreeTests(unittest.TestCase):
    def test_write_and_validate_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            schemas_dir = Path(directory) / "schemas"
            snapshot = type(
                "Tool",
                (),
                {"domain": "video", "tool": "enhance-video", "fingerprint": fingerprint({"input_schema": {"type": "object"}}), "schema": {"input_schema": {"type": "object"}}, "modes": ("Cloud",)},
            )()
            write_snapshots(schemas_dir, "0.2.2", {"video": [snapshot]})
            self.assertTrue((schemas_dir / "manifest.json").is_file())
            self.assertTrue((schemas_dir / "video" / "enhance-video.json").is_file())
            manifest = json.loads((schemas_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["cli_version"], "0.2.2")
            self.assertEqual(validate_snapshot_tree(schemas_dir), [])

    def test_validate_reports_missing_snapshot_file(self):
        with tempfile.TemporaryDirectory() as directory:
            schemas_dir = Path(directory) / "schemas"
            schemas_dir.mkdir()
            (schemas_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "cli_version": "0.2.2",
                        "domains": {"video": [{"tool": "enhance-video", "fingerprint": "abc"}]},
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_snapshot_tree(schemas_dir)
            self.assertEqual(len(errors), 1)
            self.assertIn("enhance-video.json", errors[0])


class CliInteractionTests(unittest.TestCase):
    def test_cli_version_regex(self):
        with patch("sync_cli_schemas.run_cli") as run:
            run.return_value.stdout = "mediakit-cli 0.2.2\nbuild date: unknown\n"
            run.return_value.stderr = ""
            self.assertEqual(cli_version("mediakit-cli"), "0.2.2")

    def test_collect_snapshots_rejects_failed_schema(self):
        with patch("sync_cli_schemas.run_cli") as run:
            run.side_effect = [
                type("P", (), {"stdout": "video\t1\t视频处理。\n"})(),  # --domains
                type("P", (), {"stdout": "- enhance-video    画质增强\n"})(),  # video --help
                type("P", (), {"stdout": "", "returncode": 1, "stderr": "boom"})(),  # schema fails
                type("P", (), {"stdout": "mediakit-cli 0.2.2\n", "stderr": ""})(),  # version
            ]
            with self.assertRaisesRegex(RuntimeError, "schema failed"):
                collect_snapshots("mediakit-cli")


if __name__ == "__main__":
    unittest.main()
