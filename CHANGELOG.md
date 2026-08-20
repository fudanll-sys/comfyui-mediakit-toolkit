# Changelog

## Unreleased

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
