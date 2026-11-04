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

    async def test_audio_never_falls_back_to_video_downloader(self):
        from mediakit_toolkit.media_bridge import download_audio_output
        with patch("mediakit_toolkit.media_bridge._read_media_bytes", return_value=b"audio"), patch(
            "mediakit_toolkit.media_bridge._decode_audio_bytes", return_value={"waveform": "tensor", "sample_rate": 48000}
        ) as decode:
            result = await download_audio_output("https://example.com/out.m4a")
            self.assertEqual(result["sample_rate"], 48000)
            decode.assert_called_once_with(b"audio")

    async def test_download_local_video_uses_video_from_file(self):
        from mediakit_toolkit.media_bridge import download_video_output
        fake_util = type("util", (), {"download_url_to_video_output": AsyncMock()})()
        factory = type("factory", (), {"VideoFromFile": staticmethod(lambda p: ("VIDEO", p))})()
        latest = type("latest", (), {"InputImpl": factory})()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.mp4"
            path.write_bytes(b"x")
            with patch.dict("sys.modules", {"comfy_api_nodes": type("m", (), {"util": fake_util})(), "comfy_api.latest": latest}):
                self.assertEqual(await download_video_output(str(path)), ("VIDEO", str(path.resolve())))
                fake_util.download_url_to_video_output.assert_not_awaited()

    async def test_missing_result_image_raises_input_error(self):
        from mediakit_toolkit.media_bridge import download_image_output
        with self.assertRaises(MediaKitInputError):
            await download_image_output("/does/not/exist.png")



if __name__ == "__main__":
    unittest.main()

