"""Check every editing builder against saved CLI schema; never submit a task."""
import argparse
import inspect
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mediakit_toolkit import cli

BUILDERS = {
    "trim-video": "build_trim_video_arguments", "extract-audio": "build_extract_audio_arguments",
    "adjust-video-speed": "build_adjust_video_speed_arguments", "adjust-video-volume": "build_adjust_video_volume_arguments",
    "apply-camera-motion": "build_apply_camera_motion_arguments", "apply-video-filter": "build_apply_video_filter_arguments",
    "flip-video": "build_flip_video_arguments", "rotate-video": "build_rotate_video_arguments",
    "concat-video": "build_concat_video_arguments", "concat-audio": "build_concat_audio_arguments",
    "mix-audio": "build_mix_audio_arguments", "mux-audio-video": "build_mux_audio_video_arguments",
    "add-subtitle-to-video": "build_add_subtitle_arguments", "stitch-video": "build_stitch_video_arguments",
    "crop-video": "build_crop_video_arguments", "adjust-audio-speed": "build_adjust_audio_speed_arguments",
    "trim-audio": "build_trim_audio_arguments", "fade-audio": "build_fade_audio_arguments",
    "fade-video-audio": "build_fade_video_audio_arguments", "extract-animated-image": "build_extract_animated_image_arguments",
}

VALUES = {"video_path": "https://example.org/video.mp4", "audio_path": "https://example.org/audio.wav",
          "video_paths": ["https://example.org/a.mp4", "https://example.org/b.mp4"],
          "audio_paths": ["https://example.org/a.wav", "https://example.org/b.wav"], "start_time": 0., "end_time": 3.,
          "rotate_direction": "rotate_left_90", "stitch_direction": "horizontal",
          "top_left_x": 0, "top_left_y": 0, "bottom_right_x": 320, "bottom_right_y": 240,
          "subtitle_url": "https://example.org/sub.srt", "is_flip_horizontal": True}
ALIASES = {"video_path": "video_url", "audio_path": "audio_url", "video_paths": "video_urls",
           "audio_paths": "audio_urls", "output_format": "format"}


def parse_flags(arguments, schema):
    props = schema["properties"]
    payload, index = {}, 3
    while index < len(arguments):
        token = arguments[index]
        name, sep, raw = token[2:].partition("=")
        key = name.replace("-", "_")
        assert key in props, (key, "unknown flag")
        field = props[key]
        if not sep:
            if field["type"] == "boolean":
                raw = "true"
            else:
                index += 1
                raw = arguments[index]
        kind = field["type"]
        if kind in ("number", "integer", "boolean", "object"):
            value = json.loads(raw)
        elif kind == "array":
            if field["items"]["type"] == "object":
                value = json.loads(raw)
            else:
                payload.setdefault(key, []).append(raw)
                index += 1
                continue
        else:
            value = raw
        payload[key] = value
        index += 1
    return payload


def verify():
    count = 0
    for tool, builder_name in BUILDERS.items():
        schema = json.loads((ROOT / "schemas/editing" / f"{tool}.json").read_text())["schema"]["input_schema"]
        builder = getattr(cli, builder_name)
        params = inspect.signature(builder).parameters
        values = {k: VALUES[k] for k in params if k in VALUES}
        variants = [values]
        for parameter in params.values():
            key = ALIASES.get(parameter.name, parameter.name)
            if tool == "extract-animated-image" and parameter.name == "output_format":
                key = "output_format"
            prop = schema["properties"].get(key, {})
            if parameter.default is not inspect.Parameter.empty and parameter.default is not None and "default" in prop:
                assert parameter.default == prop["default"], (tool, parameter.name, "default mismatch")
            for value in prop.get("enum", []):
                variants.append(values | {parameter.name: value})
        for variant in variants:
            args = builder(**variant)
            assert args[:3] == ["--cloud", "editing", tool], (tool, args[:3])
            payload = parse_flags(args, schema)
            Draft202012Validator(schema).validate(payload)
            count += 1
    return {"passed": True, "editing_builders": len(BUILDERS), "valid_variants": count, "cloud_tasks": 0}

if __name__ == "__main__":
    print(json.dumps(verify()))
