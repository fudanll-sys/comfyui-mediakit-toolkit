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
        self.id = kwargs.get("id")
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
    for name in ("Video", "Audio", "Image", "Boolean", "Combo", "Float", "Int", "String"):
        setattr(io, name, types.SimpleNamespace(Input=_Input, Output=_Output))

    io.Autogrow = types.SimpleNamespace(
        Input=_Input,
        TemplateNames=lambda input, names, min=1: types.SimpleNamespace(input=input, names=names, min=min),
    )
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
                "MediaKitVideoASR",
                "MediaKitVideoOCR",
                "MediaKitVideoMattePortrait",
                "MediaKitVideoMatteGreenscreen",
                "MediaKitVideoSegmentScenes",
                "MediaKitVideoAnalyzeHighlights",
                "MediaKitVideoProbeMetadata",
                "MediaKitTrimVideo",
                "MediaKitExtractAudio",
                "MediaKitAdjustVideoSpeed",
                "MediaKitAdjustVideoVolume",
                "MediaKitCameraMotion",
                "MediaKitVideoFilter",
                "MediaKitFlipVideo",
                "MediaKitRotateVideo",
                "MediaKitConcatVideo",
                "MediaKitConcatAudio",
                "MediaKitMixAudio",
                "MediaKitMuxAudioVideo",
                "MediaKitAddSubtitle",
                "MediaKitStitchVideo",
                "MediaKitCropVideo",
                "MediaKitAdjustAudioSpeed",
                "MediaKitTrimAudio",
                "MediaKitFadeAudio",
                "MediaKitFadeVideoAudio",
                "MediaKitExtractAnimatedImage",
            ],
        )

    def test_editing_nodes_register_with_bilingual_names(self):
        expected = {
            "MediaKitTrimVideo": "Trim · 视频裁剪",
            "MediaKitExtractAudio": "Extract Audio · 提取音频",
            "MediaKitAdjustVideoSpeed": "Speed · 视频变速",
            "MediaKitAdjustVideoVolume": "Volume · 音量调整",
            "MediaKitCameraMotion": "Camera Motion · 镜头运动",
            "MediaKitVideoFilter": "Filter · 视频滤镜",
            "MediaKitFlipVideo": "Flip · 视频翻转",
            "MediaKitRotateVideo": "Rotate · 视频旋转",
            "MediaKitConcatVideo": "Concat · 视频拼接",
            "MediaKitConcatAudio": "Concat Audio · 音频拼接",
            "MediaKitMixAudio": "Mix · 混音",
            "MediaKitMuxAudioVideo": "Mux · 音视频合流",
            "MediaKitAddSubtitle": "Subtitle · 视频加字幕",
            "MediaKitStitchVideo": "Stitch · 视频拼合",
            "MediaKitCropVideo": "Crop · 画面裁剪",
            "MediaKitAdjustAudioSpeed": "Audio Speed · 音频变速",
            "MediaKitTrimAudio": "Audio Trim · 音频裁剪",
            "MediaKitFadeAudio": "Fade Audio · 音频淡入淡出",
            "MediaKitFadeVideoAudio": "Fade · 视频声音淡入淡出",
            "MediaKitExtractAnimatedImage": "Animated · 提取动图",
        }
        for node_id, display_name in expected.items():
            schema = getattr(self.extension, node_id).define_schema()
            self.assertEqual(schema.display_name, display_name)
            self.assertEqual(schema.category, "MediaKit/Video Editing")

    def test_editing_nodes_use_auto_run_mode_by_default(self):
        editing_nodes = [
            self.extension.MediaKitTrimVideo,
            self.extension.MediaKitExtractAudio,
            self.extension.MediaKitAdjustVideoSpeed,
            self.extension.MediaKitAdjustVideoVolume,
            self.extension.MediaKitCameraMotion,
            self.extension.MediaKitVideoFilter,
            self.extension.MediaKitFlipVideo,
            self.extension.MediaKitRotateVideo,
            self.extension.MediaKitConcatVideo,
            self.extension.MediaKitConcatAudio,
            self.extension.MediaKitMixAudio,
            self.extension.MediaKitMuxAudioVideo,
            self.extension.MediaKitAddSubtitle,
            self.extension.MediaKitStitchVideo,
            self.extension.MediaKitCropVideo,
            self.extension.MediaKitAdjustAudioSpeed,
            self.extension.MediaKitTrimAudio,
            self.extension.MediaKitFadeAudio,
            self.extension.MediaKitFadeVideoAudio,
            self.extension.MediaKitExtractAnimatedImage,
        ]
        for node in editing_nodes:
            schema = node.define_schema()
            run_mode_input = next(item for item in schema.inputs if item.id == "run_mode")
            self.assertEqual(run_mode_input.kwargs["default"], "auto")

    def test_extract_audio_outputs_native_audio(self):
        schema = self.extension.MediaKitExtractAudio.define_schema()
        self.assertIsInstance(schema.outputs[0], _Output)

    def test_probe_metadata_exposes_run_mode(self):
        schema = self.extension.MediaKitVideoProbeMetadata.define_schema()
        self.assertIn(
            "run_mode", [item.id for item in schema.inputs]
        )

    def test_video_ai_nodes_use_short_bilingual_display_names(self):
        expected = {
            "MediaKitVideoEnhance": "Enhance · 视频增强",
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


class VideoUnderstandingNodeSchemaTests(unittest.IsolatedAsyncioTestCase):
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
            "mediakit_toolkit.nodes.video_understanding",
        ):
            sys.modules.pop(name, None)

    async def test_extension_registers_understanding_nodes(self):
        extension = await self.extension.comfy_entrypoint()
        nodes = [node.define_schema().node_id for node in await extension.get_node_list()]
        for node_id in (
            "MediaKitVideoASR",
            "MediaKitVideoOCR",
            "MediaKitVideoMattePortrait",
            "MediaKitVideoMatteGreenscreen",
            "MediaKitVideoSegmentScenes",
            "MediaKitVideoAnalyzeHighlights",
            "MediaKitVideoProbeMetadata",
        ):
            self.assertIn(node_id, nodes)

    def test_understanding_nodes_use_bilingual_display_names(self):
        expected = {
            "MediaKitVideoASR": "ASR · 语音转字幕",
            "MediaKitVideoOCR": "OCR · 视频识别字幕",
            "MediaKitVideoMattePortrait": "Matte · 人像抠图",
            "MediaKitVideoMatteGreenscreen": "Matte · 绿幕抠图",
            "MediaKitVideoSegmentScenes": "Scene · 场景切分",
            "MediaKitVideoAnalyzeHighlights": "Highlight · 高光片段提取",
            "MediaKitVideoProbeMetadata": "Metadata · 视频元信息",
        }
        for node in (
            self.extension.MediaKitVideoASR,
            self.extension.MediaKitVideoOCR,
            self.extension.MediaKitVideoMattePortrait,
            self.extension.MediaKitVideoMatteGreenscreen,
            self.extension.MediaKitVideoSegmentScenes,
            self.extension.MediaKitVideoAnalyzeHighlights,
            self.extension.MediaKitVideoProbeMetadata,
        ):
            schema = node.define_schema()
            self.assertEqual(schema.display_name, expected[schema.node_id])

    def test_understanding_nodes_use_native_video_input(self):
        for node in (
            self.extension.MediaKitVideoASR,
            self.extension.MediaKitVideoOCR,
            self.extension.MediaKitVideoMattePortrait,
            self.extension.MediaKitVideoMatteGreenscreen,
            self.extension.MediaKitVideoSegmentScenes,
            self.extension.MediaKitVideoAnalyzeHighlights,
            self.extension.MediaKitVideoProbeMetadata,
        ):
            schema = node.define_schema()
            self.assertIsInstance(schema.inputs[0], _Input)
            self.assertEqual(schema.inputs[0].id, "video")

    async def test_asr_node_maps_parameters_and_downloads_subtitle(self):
        video_understanding = importlib.import_module(
            "mediakit_toolkit.nodes.video_understanding"
        )
        with (
            patch.object(
                video_understanding,
                "materialize_video",
                return_value=nullcontext(Path("/tmp/in.mp4")),
            ),
            patch.object(
                video_understanding,
                "asr_video_subtitles",
                new_callable=AsyncMock,
                return_value=(
                    {"subtitle_url": "https://example.com/out.srt"},
                    "task-asr",
                ),
            ),
            patch.object(
                video_understanding,
                "download_text_output",
                new_callable=AsyncMock,
                return_value="1\n00:00:00,000 --> 00:00:05,000\n你好\n",
            ),
        ):
            output = await video_understanding.MediaKitVideoASR.execute(
                object(),
                content_type="speech",
                language="cmn-Hans-CN",
                enable_speaker_info=True,
                enable_confidence=True,
            )
        self.assertEqual(output.values[0], "1\n00:00:00,000 --> 00:00:05,000\n你好\n")
        self.assertIn("out.srt", output.values[1])

    async def test_matte_node_downloads_video_output(self):
        video_understanding = importlib.import_module(
            "mediakit_toolkit.nodes.video_understanding"
        )
        with (
            patch.object(
                video_understanding,
                "materialize_video",
                return_value=nullcontext(Path("/tmp/in.mp4")),
            ),
            patch.object(
                video_understanding,
                "matte_video",
                new_callable=AsyncMock,
                return_value=("https://example.com/out.webm", "task-matte"),
            ),
            patch.object(
                video_understanding,
                "download_video_output",
                new_callable=AsyncMock,
                return_value=object(),
            ),
        ):
            output = await video_understanding.MediaKitVideoMattePortrait.execute(
                object(), output_format="WEBM"
            )
        self.assertEqual(len(output.values), 1)

    async def test_scene_node_maps_zero_durations_to_none(self):
        video_understanding = importlib.import_module(
            "mediakit_toolkit.nodes.video_understanding"
        )
        with (
            patch.object(
                video_understanding,
                "materialize_video",
                return_value=nullcontext(Path("/tmp/in.mp4")),
            ),
            patch.object(
                video_understanding,
                "segment_video_scenes",
                new_callable=AsyncMock,
                return_value=({"segments": []}, "task-scene"),
            ) as segment,
        ):
            await video_understanding.MediaKitVideoSegmentScenes.execute(
                object(),
                enable_clip_fade=False,
                segment_threshold=0.0,
                min_duration=0.0,
                max_duration=0.0,
            )
        self.assertIsNone(segment.await_args.kwargs["segment_threshold"])
        self.assertIsNone(segment.await_args.kwargs["min_duration"])
        self.assertIsNone(segment.await_args.kwargs["max_duration"])
