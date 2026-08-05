import io
import tempfile
import unittest
from pathlib import Path

from mediakit_toolkit.errors import MediaKitInputError
from mediakit_toolkit.media_bridge import materialize_video


class FakeVideo:
    def __init__(self, source):
        self.source = source

    def get_stream_source(self):
        return self.source


class MediaBridgeTests(unittest.TestCase):
    def test_existing_path_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.mp4"
            path.write_bytes(b"video")
            with materialize_video(FakeVideo(str(path))) as result:
                self.assertEqual(result, path.resolve())
            self.assertTrue(path.exists())

    def test_memory_stream_is_materialized_and_cleaned(self):
        with materialize_video(FakeVideo(io.BytesIO(b"video"))) as result:
            temporary_path = result
            self.assertTrue(result.exists())
            self.assertEqual(result.read_bytes(), b"video")
        self.assertFalse(temporary_path.exists())

    def test_invalid_native_video_is_rejected(self):
        with self.assertRaises(MediaKitInputError):
            with materialize_video(object()):
                pass


if __name__ == "__main__":
    unittest.main()

