import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mediakit_toolkit.errors import MediaKitCompatibilityError, MediaKitInputError
from mediakit_toolkit.media_bridge import (
    materialize_audio,
    materialize_image,
    materialize_media_list,
    materialize_video,
)


class FakeMedia:
    def __init__(self, source):
        self.source = source

    def get_stream_source(self):
        return self.source


class MediaBridgeTests(unittest.TestCase):
    def test_existing_path_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.mp4"
            path.write_bytes(b"video")
            with materialize_video(FakeMedia(str(path))) as result:
                self.assertEqual(result, path.resolve())
            self.assertTrue(path.exists())

    def test_memory_stream_is_materialized_and_cleaned(self):
        with materialize_video(FakeMedia(io.BytesIO(b"video"))) as result:
            temporary_path = result
            self.assertTrue(result.exists())
            self.assertEqual(result.read_bytes(), b"video")
        self.assertFalse(temporary_path.exists())

    def test_invalid_native_video_is_rejected(self):
        with self.assertRaises(MediaKitInputError):
            with materialize_video(object()):
                pass

    def test_audio_stream_is_materialized_and_cleaned(self):
        with materialize_audio(FakeMedia(io.BytesIO(b"audio"))) as result:
            temporary_path = result
            self.assertTrue(result.exists())
            self.assertEqual(result.read_bytes(), b"audio")
        self.assertFalse(temporary_path.exists())

    def test_image_stream_is_materialized_and_cleaned(self):
        with materialize_image(FakeMedia(io.BytesIO(b"image"))) as result:
            temporary_path = result
            self.assertTrue(result.exists())
        self.assertFalse(temporary_path.exists())

    def test_media_list_keeps_path_inputs_and_cleans_streams(self):
        with tempfile.TemporaryDirectory() as directory:
            path_input = Path(directory) / "a.mp4"
            path_input.write_bytes(b"a")
            stream_input = io.BytesIO(b"b")
            with materialize_media_list([FakeMedia(str(path_input)), FakeMedia(stream_input)]) as paths:
                self.assertEqual(len(paths), 2)
                self.assertEqual(paths[0], path_input.resolve())
                temporary_path = paths[1]
                self.assertTrue(temporary_path.exists())
            self.assertTrue(path_input.exists())
            self.assertFalse(temporary_path.exists())

    def test_media_list_rejects_empty(self):
        with self.assertRaises(MediaKitInputError):
            with materialize_media_list([]):
                pass


class MediaBridgeDownloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_download_video_output_uses_comfy_util(self):
        fake_util = type("util", (), {"download_url_to_video_output": AsyncMock(return_value="VIDEO")})()
        with patch.dict("sys.modules", {"comfy_api_nodes": type("m", (), {"util": fake_util})()}):
            from mediakit_toolkit.media_bridge import download_video_output

            self.assertEqual(await download_video_output("https://example.com/out.mp4"), "VIDEO")
            fake_util.download_url_to_video_output.assert_awaited_once_with(
                "https://example.com/out.mp4"
            )

    async def test_download_audio_output_falls_back_to_video_downloader(self):
        fake_util = type(
            "util",
            (),
            {
                "download_url_to_audio_output": None,
                "download_url_to_video_output": AsyncMock(return_value="AUDIO"),
            },
        )()
        with patch.dict("sys.modules", {"comfy_api_nodes": type("m", (), {"util": fake_util})()}):
            from mediakit_toolkit.media_bridge import download_audio_output

            self.assertEqual(await download_audio_output("https://example.com/out.m4a"), "AUDIO")

    async def test_download_local_path_uses_file_uri(self):
        fake_util = type("util", (), {"download_url_to_video_output": AsyncMock(return_value="VIDEO")})()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.mp4"
            path.write_bytes(b"x")
            with patch.dict("sys.modules", {"comfy_api_nodes": type("m", (), {"util": fake_util})()}):
                from mediakit_toolkit.media_bridge import download_video_output

                self.assertEqual(await download_video_output(str(path)), "VIDEO")
                self.assertEqual(
                    fake_util.download_url_to_video_output.await_args.args[0],
                    path.resolve().as_uri(),
                )

    async def test_missing_comfy_util_raises_compatibility_error(self):
        with patch.dict("sys.modules", {}), self.assertRaises(MediaKitCompatibilityError):
            from mediakit_toolkit.media_bridge import download_image_output

            await download_image_output("https://example.com/out.png")


if __name__ == "__main__":
    unittest.main()

