import importlib
import sys
import types
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mediakit_toolkit.errors import MediaKitDependencyError


class _Input:
    def __init__(self, identifier, **kwargs):
        self.id = identifier
        self.kwargs = kwargs


class _Output:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _Schema:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _NodeOutput:
    def __init__(self, *values, **kwargs):
        self.values = values
        self.kwargs = kwargs


class _ComfyNode:
    pass


class _ComfyExtension:
    pass


def _fake_comfy_modules():
    io = types.SimpleNamespace(
        ComfyNode=_ComfyNode,
        Schema=_Schema,
        NodeOutput=_NodeOutput,
    )
    for name in ("Video", "Boolean", "Combo", "Float", "Int", "String"):
        setattr(io, name, types.SimpleNamespace(Input=_Input, Output=_Output))

    comfy_api = types.ModuleType("comfy_api")
    latest = types.ModuleType("comfy_api.latest")
    latest.ComfyExtension = _ComfyExtension
    latest.io = io
    comfy_api.latest = latest
    return comfy_api, latest


class NodeSchemaTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        comfy_api, latest = _fake_comfy_modules()
        cls.module_patch = patch.dict(
            sys.modules,
            {"comfy_api": comfy_api, "comfy_api.latest": latest},
        )
        cls.module_patch.start()
        cls.extension = importlib.import_module("mediakit_toolkit.extension")

    @classmethod
    def tearDownClass(cls):
        cls.module_patch.stop()
        for name in (
            "mediakit_toolkit.extension",
            "mediakit_toolkit.nodes.environment",
            "mediakit_toolkit.nodes.video_ai",
        ):
            sys.modules.pop(name, None)

    async def test_extension_registers_diagnostic_and_video_nodes(self):
        extension = await self.extension.comfy_entrypoint()
        nodes = await extension.get_node_list()
        self.assertEqual(
            [node.define_schema().node_id for node in nodes],
            [
                "MediaKitEnvironmentCheck",
                "MediaKitVideoEnhance",
                "MediaKitVideoEnhanceGenerative",
                "MediaKitEraseVideoSubtitle",
                "MediaKitEraseVideoSubtitlePro",
            ],
        )

    def test_video_ai_nodes_use_short_bilingual_display_names(self):
        expected = {
            "MediaKitVideoEnhance": "Enhance · 视频增强（极速版）",
            "MediaKitVideoEnhanceGenerative": (
                "Enhance Ultra · 视频增强（大模型版）"
            ),
            "MediaKitEraseVideoSubtitle": "Erase Subtitle · 字幕擦除",
            "MediaKitEraseVideoSubtitlePro": (
                "Erase Subtitle Pro · 字幕擦除（增强版）"
            ),
        }
        for node in (
            self.extension.MediaKitVideoEnhance,
            self.extension.MediaKitVideoEnhanceGenerative,
            self.extension.MediaKitEraseVideoSubtitle,
            self.extension.MediaKitEraseVideoSubtitlePro,
        ):
            schema = node.define_schema()
            self.assertEqual(schema.display_name, expected[schema.node_id])

    def test_video_enhance_uses_native_video_input_and_output(self):
        schema = self.extension.MediaKitVideoEnhance.define_schema()
        self.assertIsInstance(schema.inputs[0], _Input)
        self.assertEqual(schema.inputs[0].id, "video")
        self.assertIsInstance(schema.outputs[0], _Output)
        self.assertEqual(
            [item.id for item in schema.inputs[-4:]],
            [
                "poll_interval_seconds",
                "max_poll_attempts",
                "bitrate_level",
                "fps",
            ],
        )

    def test_video_ai_nodes_use_native_video_input_and_output(self):
        for node in (
            self.extension.MediaKitVideoEnhanceGenerative,
            self.extension.MediaKitEraseVideoSubtitle,
            self.extension.MediaKitEraseVideoSubtitlePro,
        ):
            schema = node.define_schema()
            self.assertIsInstance(schema.inputs[0], _Input)
            self.assertEqual(schema.inputs[0].id, "video")
            self.assertIsInstance(schema.outputs[0], _Output)

    async def test_generative_node_maps_quality_parameters(self):
        video_ai = importlib.import_module("mediakit_toolkit.nodes.video_ai")
        with (
            patch.object(
                video_ai,
                "materialize_video",
                return_value=nullcontext(Path("/tmp/input.mp4")),
            ),
            patch.object(
                video_ai,
                "enhance_video_generative",
                new_callable=AsyncMock,
                return_value=("https://example.com/ai.mp4", "task-ai"),
            ) as enhance,
            patch.object(
                video_ai,
                "download_video_output",
                new_callable=AsyncMock,
                return_value=object(),
            ),
        ):
            await video_ai.MediaKitVideoEnhanceGenerative.execute(
                object(),
                resolution="1080p",
                bitrate_level="high",
                fps=60,
            )
        self.assertEqual(enhance.await_args.kwargs["resolution"], "1080p")
        self.assertEqual(enhance.await_args.kwargs["bitrate_level"], "high")
        self.assertEqual(enhance.await_args.kwargs["fps"], 60)

    async def test_pro_subtitle_node_maps_optional_region(self):
        video_ai = importlib.import_module("mediakit_toolkit.nodes.video_ai")
        with (
            patch.object(
                video_ai,
                "materialize_video",
                return_value=nullcontext(Path("/tmp/input.mp4")),
            ),
            patch.object(
                video_ai,
                "erase_video_subtitle",
                new_callable=AsyncMock,
                return_value=("https://example.com/clean.mp4", "task-1"),
            ) as erase,
            patch.object(
                video_ai,
                "download_video_output",
                new_callable=AsyncMock,
                return_value=object(),
            ),
        ):
            await video_ai.MediaKitEraseVideoSubtitlePro.execute(
                object(),
                erase_mode="Subtitle",
                output_encode_mode="Quality",
                restrict_region=True,
                top_left_x=0.0,
                top_left_y=0.5,
                bottom_right_x=1.0,
                bottom_right_y=1.0,
            )
        self.assertEqual(erase.await_args.kwargs["erase_region"]["top_left_y"], 0.5)

    def test_missing_cli_is_reported_without_breaking_node_loading(self):
        environment = importlib.import_module("mediakit_toolkit.nodes.environment")
        with patch.object(
            environment,
            "find_cli",
            side_effect=MediaKitDependencyError("CLI missing"),
        ):
            output = environment.MediaKitEnvironmentCheck.execute()
        self.assertEqual(output.values[0], "not_ready")
        self.assertIn("CLI missing", output.values[1])


if __name__ == "__main__":
    unittest.main()
