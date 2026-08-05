"""ComfyUI V3 extension registration."""

from comfy_api.latest import ComfyExtension, io

from .nodes.environment import MediaKitEnvironmentCheck
from .nodes.video_ai import (
    MediaKitEraseVideoSubtitle,
    MediaKitEraseVideoSubtitlePro,
    MediaKitVideoEnhance,
)


class MediaKitToolkitExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            MediaKitEnvironmentCheck,
            MediaKitVideoEnhance,
            MediaKitEraseVideoSubtitle,
            MediaKitEraseVideoSubtitlePro,
        ]


async def comfy_entrypoint() -> MediaKitToolkitExtension:
    return MediaKitToolkitExtension()
