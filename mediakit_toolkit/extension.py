"""ComfyUI V3 extension registration."""

from comfy_api.latest import ComfyExtension, io

from .nodes.environment import MediaKitEnvironmentCheck
from .nodes.video_ai import (
    MediaKitEraseVideoSubtitle,
    MediaKitEraseVideoSubtitlePro,
    MediaKitVideoEnhance,
    MediaKitVideoEnhanceGenerative,
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
        ]


async def comfy_entrypoint() -> MediaKitToolkitExtension:
    return MediaKitToolkitExtension()
