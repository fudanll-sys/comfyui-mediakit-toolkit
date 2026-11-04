# Changelog

## Unreleased

- Cover the full MediaKit `editing` domain (20/20 tools) with 18 new native
  ComfyUI nodes, all with mode-adaptive `run_mode` (`auto`/`cloud`) and the
  existing multi-input architecture:
  - Basic video editing: `Speed · 视频变速`, `Volume · 音量调整`,
    `Camera Motion · 镜头运动`, `Filter · 视频滤镜`, `Flip · 视频翻转`,
    `Rotate · 视频旋转`.
  - Assembly: `Concat · 视频拼接` (with transitions), `Concat Audio · 音频拼接`,
    `Mix · 混音`, `Mux · 音视频合流` (keep/replace audio, A/V sync).
  - Subtitle / stitch / crop: `Subtitle · 视频加字幕` (file or inline JSON),
    `Stitch · 视频拼合`, `Crop · 画面裁剪`.
  - Audio and fades: `Audio Speed · 音频变速`, `Audio Trim · 音频裁剪`,
    `Fade Audio · 音频淡入淡出`, `Fade · 视频声音淡入淡出`.
  - Animated image: `Animated · 提取动图` (`VIDEO → IMAGE`, GIF/WebP).
- Use real ComfyUI Autogrow inputs for multi-media nodes, native AUDIO dictionaries
  and IMAGE tensors, and PyAV audio decoding (never VIDEO fallback).
- Preserve animated image frames, per-frame duration JSON and original GIF/WebP URL.
- Add real ComfyUI contract validation, media roundtrip tests and strict subtitle validation.
- Add localhost-only real frontend import and queue verification via
  `scripts/verify_comfy_runtime.py`; no valid cloud tasks are submitted.
- Assign unique output ids and fix P1 workflow wiring and parameter documentation.
- Fix result URL extraction so audio/image task results are recognized
  (`video_url` / `audio_url` / `image_url`), fixing a latent failure of the
  cloud path for audio capabilities.

## 0.4.0 - 2026-11-03

- Add `Trim · 视频裁剪` and `Extract Audio · 提取音频` editing nodes with
  native `VIDEO → VIDEO` / `VIDEO → AUDIO` interfaces.
- Add mode-adaptive execution: nodes expose `run_mode` (`auto`/`cloud`) and use
  local synchronous execution when the installed CLI supports it, otherwise
  fall back to cloud tasks. `Metadata · 视频元信息` adopts the same parameter.
- Add the MediaKit CLI schema synchronization script
  (`scripts/sync_cli_schemas.py`) with `--update`, `--check`, `--json` and
  `--offline` modes, plus a committed snapshot tree (`schemas/`) covering all
  CLI capabilities with a versioned `manifest.json` baseline.
- Add CLI version vs schema-baseline drift detection to the
  `MediaKit Environment Check` node.
- Extend the media bridge with AUDIO/IMAGE materialization, multi-input list
  materialization, and native AUDIO/IMAGE output downloads.
- Generate the initial schema snapshot baseline from CLI 0.2.2 (video 29,
  editing 20, image 21, audio 4 = 74 tools).

## 0.3.0 - 2026-08-05

- Add cloud video understanding and analysis nodes: ASR speech-to-subtitle,
  video OCR, portrait and greenscreen matting, scene segmentation, highlight
  analysis, and video metadata probing.
- Add native `VIDEO` to `STRING` output paths for subtitle, scene, highlight,
  and metadata results, and `VIDEO` to `VIDEO` paths for matting.
- Extract subtitle files from task results and expose redacted raw JSON for
  downstream processing.
- Keep the fast-edition label reserved for a future dedicated capability.
- Shorten the four video AI node titles with consistent bilingual labels while
  preserving their internal node IDs and existing workflow compatibility.
- Rename the current enhancement node to `Enhance · 视频增强`, reserving the
  fast-edition label for a future dedicated capability.
- Add Chinese and English README files with AI MediaKit activation, API key,
  installation, billing, privacy, and troubleshooting guidance.

## 0.2.1 - 2026-08-05

- Add native `VIDEO` to `VIDEO` generative large-model enhancement.
- Validate the official 720p/1080p, bitrate, and optional 15–120 fps inputs
  before submitting a paid cloud task.
- Add a generative enhancement example workflow and tests.

## 0.2.0 - 2026-08-05

- Add native `VIDEO` to `VIDEO` standard subtitle erasure.
- Add native `VIDEO` to `VIDEO` professional subtitle erasure with text mode,
  output encoding preference, and optional normalized erase regions.
- Add structured, redacted task lifecycle logs.
- Identify CLI cloud requests as a ComfyUI plugin runtime.
- Align cloud commands with the current official MediaKit CLI syntax.
- Record successful paid smoke validation of the v0.1 video enhancement path.

## 0.1.0 - 2026-08-05

- Add the ComfyUI V3 extension scaffold.
- Add the native `VIDEO` to `VIDEO` MediaKit Video Enhance node.
- Add a read-only MediaKit Environment Check node.
- Add a safe MediaKit CLI adapter, cloud task orchestration, redaction, and
  temporary video bridging.
