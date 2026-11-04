"""ComfyUI V3 extension registration."""

from comfy_api.latest import ComfyExtension, io

from .nodes.environment import MediaKitEnvironmentCheck
from .nodes.video_ai import (
    MediaKitEraseVideoSubtitle,
    MediaKitEraseVideoSubtitlePro,
    MediaKitVideoEnhance,
    MediaKitVideoEnhanceGenerative,
)
from .nodes.video_editing import (
    MediaKitAddSubtitle,
    MediaKitAdjustAudioSpeed,
    MediaKitAdjustVideoSpeed,
    MediaKitAdjustVideoVolume,
    MediaKitCameraMotion,
    MediaKitConcatAudio,
    MediaKitConcatVideo,
    MediaKitCropVideo,
    MediaKitExtractAnimatedImage,
    MediaKitExtractAudio,
    MediaKitFadeAudio,
    MediaKitFadeVideoAudio,
    MediaKitFlipVideo,
    MediaKitMixAudio,
    MediaKitMuxAudioVideo,
    MediaKitRotateVideo,
    MediaKitStitchVideo,
    MediaKitTrimAudio,
    MediaKitTrimVideo,
    MediaKitVideoFilter,
)
from .nodes.video_understanding import (
    MediaKitVideoAnalyzeHighlights,
    MediaKitVideoASR,
    MediaKitVideoMatteGreenscreen,
    MediaKitVideoMattePortrait,
    MediaKitVideoOCR,
    MediaKitVideoProbeMetadata,
    MediaKitVideoSegmentScenes,
)


class MediaKitToolkitExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            MediaKitEnvironmentCheck,
            MediaKitVideoEnhance,
            MediaKitVideoEnhanceGenerative,
            MediaKitEraseVideoSubtitle,
            MediaKitEraseVideoSubtitlePro,
            MediaKitVideoASR,
            MediaKitVideoOCR,
            MediaKitVideoMattePortrait,
            MediaKitVideoMatteGreenscreen,
            MediaKitVideoSegmentScenes,
            MediaKitVideoAnalyzeHighlights,
            MediaKitVideoProbeMetadata,
            MediaKitTrimVideo,
            MediaKitExtractAudio,
            MediaKitAdjustVideoSpeed,
            MediaKitAdjustVideoVolume,
            MediaKitCameraMotion,
            MediaKitVideoFilter,
            MediaKitFlipVideo,
            MediaKitRotateVideo,
            MediaKitConcatVideo,
            MediaKitConcatAudio,
            MediaKitMixAudio,
            MediaKitMuxAudioVideo,
            MediaKitAddSubtitle,
            MediaKitStitchVideo,
            MediaKitCropVideo,
            MediaKitAdjustAudioSpeed,
            MediaKitTrimAudio,
            MediaKitFadeAudio,
            MediaKitFadeVideoAudio,
            MediaKitExtractAnimatedImage,
        ]


async def comfy_entrypoint() -> MediaKitToolkitExtension:
    return MediaKitToolkitExtension()
