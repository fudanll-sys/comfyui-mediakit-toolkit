"""Real tensor/media roundtrips; optional packages are installed by ComfyUI."""
import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

AVAILABLE = all(importlib.util.find_spec(x) for x in ("torch", "numpy", "PIL", "av"))

@unittest.skipUnless(AVAILABLE, "Run in ComfyUI or media verification environment")
class NativeMediaTests(unittest.TestCase):
    def test_stereo_audio_roundtrip_and_cleanup(self):
        import torch
        from mediakit_toolkit.media_bridge import materialize_audio, download_audio_output
        waveform = torch.stack([torch.full((800,), .25), torch.full((800,), -.5)]).unsqueeze(0)
        with materialize_audio({"waveform": waveform, "sample_rate": 8000}) as path:
            self.assertEqual(path.suffix, ".wav")
            result = asyncio.run(download_audio_output(str(path)))
            self.assertEqual(result["sample_rate"], 8000)
            self.assertEqual(tuple(result["waveform"].shape), (1, 2, 800))
            self.assertTrue(torch.allclose(waveform, result["waveform"], atol=1e-4))
        self.assertFalse(path.exists())

    def test_audio_batch_rejected_not_silently_truncated(self):
        import torch
        from mediakit_toolkit.errors import MediaKitInputError
        from mediakit_toolkit.media_bridge import materialize_audio
        with self.assertRaises(MediaKitInputError), materialize_audio({"waveform": torch.zeros(2,1,10), "sample_rate": 8000}):
            pass

    def test_animated_gif_retains_frames_and_timing(self):
        from PIL import Image
        from mediakit_toolkit.media_bridge import download_animated_image_output
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"test.gif"
            red, blue = Image.new("RGB", (8,8), "red"), Image.new("RGB", (8,8), "blue")
            red.save(path, save_all=True, append_images=[blue], duration=[100,300], loop=0)
            frames, durations = asyncio.run(download_animated_image_output(str(path)))
            self.assertEqual(tuple(frames.shape), (2,8,8,3))
            self.assertEqual(json.loads(durations), [100,300])
            self.assertEqual(frames[0,0,0,0].item(), 1)
            self.assertEqual(frames[1,0,0,2].item(), 1)

    def test_image_tensor_roundtrip(self):
        import torch
        from mediakit_toolkit.media_bridge import materialize_image, download_image_output
        with materialize_image(torch.ones(1,8,8,3)) as path:
            frames = asyncio.run(download_image_output(str(path)))
            self.assertEqual(tuple(frames.shape), (1,8,8,3))
            self.assertEqual(frames.min().item(), 1)
        self.assertFalse(path.exists())

class SubtitleValidationTests(unittest.TestCase):
    def test_invalid_subtitles_raise_input_error(self):
        from mediakit_toolkit.cli import build_add_subtitle_arguments
        from mediakit_toolkit.errors import MediaKitInputError
        samples = [[], [None], ["bad"], [{"subtitle_text": "x", "start_time": 1, "end_time": 0}],
                   [{"subtitle_text": "x", "start_time": float("nan"), "end_time": 3}],
                   [{"subtitle_text": "x", "start_time": True, "end_time": 3}]]
        for sample in samples:
            with self.subTest(sample=sample), self.assertRaises(MediaKitInputError):
                build_add_subtitle_arguments("video.mp4", subtitles=sample)
