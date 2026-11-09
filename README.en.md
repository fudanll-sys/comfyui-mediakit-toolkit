# ComfyUI MediaKit Toolkit

[简体中文](./README.md) | [English](./README.en.md)

An unofficial community integration that exposes
[Volcengine AI MediaKit](https://www.volcengine.com/docs/6448) cloud video AI
capabilities as native [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
nodes. Local upload, asynchronous task polling, and result download are handled
inside each node.

> Cloud nodes require your own Volcengine account and AI MediaKit API key and
> may incur charges. Videos are uploaded directly from your local ComfyUI
> installation to Volcengine and never pass through a server operated by this
> plugin's maintainers.

## Status

Version `0.5.0` includes the P1 editing nodes and native media integration fixes:

| Node | Description |
| --- | --- |
| `MediaKit Environment Check` | Checks MediaKit CLI, authentication, runtime, and the schema snapshot baseline. |
| `Enhance · 视频增强` | Standard or professional video enhancement with native `VIDEO → VIDEO`. |
| `Enhance Ultra · 视频增强（大模型版）` | Diffusion-based generative video restoration. |
| `Erase Subtitle · 字幕擦除` | Automatic hard-subtitle detection and removal. |
| `Erase Subtitle Pro · 字幕擦除（增强版）` | Advanced subtitle/text removal with optional region control. |
| `ASR · 语音转字幕` | Speech recognition that outputs timestamped subtitle text. |
| `OCR · 视频识别字幕` | Recognizes subtitles and text in video frames. |
| `Matte · 人像抠图` | Portrait matting that removes the background and outputs transparent video. |
| `Matte · 绿幕抠图` | Greenscreen/color-key matting with transparent output. |
| `Scene · 场景切分` | Automatic scene segmentation that outputs a clip timeline. |
| `Highlight · 高光片段提取` | Extracts highlight timestamps, scores, and metadata. |
| `Metadata · 视频元信息` | Probes container, video-stream, and audio-stream metadata. |
| `Trim · 视频裁剪` | Time-range video trimming with native `VIDEO → VIDEO`. |
| `Extract Audio · 提取音频` | Separates the audio track with native `VIDEO → AUDIO`. |
| `Speed · 视频变速` | Adjusts playback speed from 0.1× to 4.0×. |
| `Volume · 音量调整` | Adjusts video volume or mutes the audio. |
| `Camera Motion · 镜头运动` | Adds push, pull, pan, and rotate camera motion. |
| `Filter · 视频滤镜` | Spring, sunset, vivid, fair-skin, and food presets. |
| `Flip · 视频翻转` | Flips the video horizontally or vertically. |
| `Rotate · 视频旋转` | Rotates 90° left / 90° right / 180°. |
| `Concat · 视频拼接` | Concatenates multiple videos (with optional transitions). |
| `Concat Audio · 音频拼接` | Concatenates multiple audio files. |
| `Mix · 混音` | Mixes multiple audio tracks into one. |
| `Mux · 音视频合流` | Muxes video and audio with keep/replace and A/V sync options. |
| `Subtitle · 视频加字幕` | Burns subtitle files or inline text with custom styles. |
| `Stitch · 视频拼合` | Stitches 2–3 videos side by side or stacked. |
| `Crop · 画面裁剪` | Crops the video to a rectangular region. |
| `Audio Speed · 音频变速` | Adjusts audio speed (0.1×–4.0×), native `AUDIO → AUDIO`. |
| `Audio Trim · 音频裁剪` | Trims audio by time range, native `AUDIO → AUDIO`. |
| `Fade Audio · 音频淡入淡出` | Fades audio in and out, native `AUDIO → AUDIO`. |
| `Fade · 视频声音淡入淡出` | Fades the audio of a video in and out. |
| `Animated · 提取动图` | Extracts a GIF/WebP animated image, native `VIDEO → IMAGE`. |

`Enhance · 视频增强` is not the fast edition. A dedicated fast-enhancement
capability has not been integrated yet and will use a separate node name when
it becomes available.

### Run modes

All `MediaKit/Video Editing` nodes and `Metadata · 视频元信息` expose a
`run_mode` parameter:

- `auto` (default): detects whether the installed `mediakit-cli` supports local
  execution for the capability; local runs are synchronous and free, otherwise
  the node falls back to a cloud task.
- `cloud`: always submits a cloud task.

The plugin never forces local mode: older CLI builds may not implement
`--local`, and forcing it would fail at runtime, so nodes only expose `auto`
and `cloud`.

### Native media and verification

- Multi-media nodes use ComfyUI V3 Autogrow numbered slots.
- AUDIO is a waveform `[1,C,T]` tensor and sample-rate dictionary. Single-batch mono/stereo inputs are serialized as PCM16 WAV, which can introduce quantization; outputs are AUDIO, never VIDEO fallback.
- Animated IMAGE batches include all frames, with separate duration JSON and the original animation URL.
- Run `python scripts/verify_comfy_contracts.py --comfy-root /path/to/ComfyUI` in a ComfyUI Python environment, plus the full unittest suite.
- Native media tests explicitly skip when dependencies are absent. Three P1 imports and save-widget expansion passed in isolated ComfyUI 0.43.0 / frontend 1.57.6, with local diagnostic/save and expected input-error queue checks. Successful cloud editing chains remain unverified.
- Reproduce frontend/queue checks with `scripts/verify_comfy_runtime.py` (see `--help`); Playwright and Chrome are test-only dependencies. Use an isolated localhost server. The script does not submit valid cloud tasks.
- CLI 0.2.2 editing is cloud-only; `auto` fallback can incur cloud charges.

### Schema snapshots and version locking

The [`schemas/`](./schemas) directory stores JSON Schema snapshots of every
MediaKit CLI capability plus a `manifest.json` baseline (CLI version and a
fingerprint per tool). `scripts/sync_cli_schemas.py` syncs and verifies them:

```bash
python scripts/sync_cli_schemas.py --update    # refresh snapshots from local CLI
python scripts/sync_cli_schemas.py --check     # detect drift vs snapshots (CI-ready)
python scripts/sync_cli_schemas.py --offline   # validate snapshots without the CLI
```

`--check` reports added/removed tools, fingerprint changes, and mode changes.
The `MediaKit Environment Check` node also compares the installed CLI version
with the snapshot baseline and warns in the diagnostic details when they
differ.

## Requirements

- A recent ComfyUI version with the V3 native `VIDEO` API.
- Python 3.10 or newer.
- Node.js 18 or newer to install the official MediaKit CLI.
- An activated AI MediaKit service and API key.
- `mediakit-cli` available to the process that launches ComfyUI.

## Activate AI MediaKit

This plugin does not provide a MediaKit account, credits, or billing proxy.
Complete these steps before first use:

1. Register or sign in to Volcengine. Complete identity verification if the
   console requests it.
2. Open the [AI MediaKit console](https://console.volcengine.com/imp/ai-mediakit/settings).
3. Follow the console prompts to activate the service and accept the relevant
   terms. Existing users can skip this step.
4. Create or copy an AI MediaKit API key from the console.
5. Store the key securely. Never commit it to GitHub, put it in workflow JSON,
   or share it with other people.

Cloud capabilities may be billed by actual usage. Available credits, service
regions, and current pricing are governed by the Volcengine console and
[official documentation](https://www.volcengine.com/docs/6448).

## Install and configure MediaKit CLI

Install the official Volcengine CLI:

```bash
npx @volcengine/mediakit-cli install -y
```

Initialize it with your API key:

```bash
mediakit-cli init \
  --mode cloud-first \
  --api-key "YOUR_MEDIAKIT_API_KEY" \
  --credential-store config \
  --yes
```

Check the version, cloud connectivity, and local dependencies:

```bash
mediakit-cli doctor
mediakit-cli version
```

Alternatively, expose the key only to the process that launches ComfyUI:

```bash
export MEDIAKIT_API_KEY="YOUR_MEDIAKIT_API_KEY"
```

See [volcengine/mediakit-cli](https://github.com/volcengine/mediakit-cli) for
the official installation and authentication guidance.

## Install the plugin

> ComfyUI Manager installs only this plugin. Every user must still install and
> initialize `mediakit-cli` locally as described above and authenticate with
> their own AI MediaKit API key.

### Option 1: ComfyUI Manager (recommended)

1. Open `Manager` → `Custom Nodes` in ComfyUI.
2. Search for `MediaKit Toolkit` or `mediakit-toolkit`.
3. Select the latest version and click `Install`.
4. Fully restart ComfyUI after installation.

The Registry version can also be installed with Comfy CLI:

```bash
comfy node install mediakit-toolkit
```

### Option 2: Git

If the package is not yet visible in Manager, or if you want to track the
GitHub version directly, open the ComfyUI `custom_nodes` directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/fudanll-sys/comfyui-mediakit-toolkit.git
```

Fully restart ComfyUI after installation. The nodes appear under
`MediaKit/Video AI` and can be found by searching for `MediaKit`, `Enhance`, or
`Erase Subtitle`.

### Update

Manager users can select a new release under `Update available`. Git users can
run this command from the ComfyUI root directory:

```bash
git -C custom_nodes/comfyui-mediakit-toolkit pull --ff-only origin main
```

Fully restart ComfyUI after updating.

## Quick start

Run the diagnostic node first:

```text
MediaKit Environment Check
```

Basic enhancement:

```text
Load Video
    ↓ VIDEO
Enhance · 视频增强
    ↓ VIDEO
Save Video
```

Large-model enhancement:

```text
Load Video
    ↓ VIDEO
Enhance Ultra · 视频增强（大模型版）
    ↓ VIDEO
Save Video
```

Subtitle removal:

```text
Load Video
    ↓ VIDEO
Erase Subtitle Pro · 字幕擦除（增强版）
    ↓ VIDEO
Save Video
```

Speech-to-subtitle:

```text
Load Video
    ↓ VIDEO
ASR · 语音转字幕
    ↓ STRING
(subtitle text is ready for downstream captioning nodes)
```

Portrait/greenscreen matting:

```text
Load Video
    ↓ VIDEO
Matte · 人像抠图
    ↓ VIDEO
Save Video
```

Scene segmentation, highlight analysis, or metadata:

```text
Load Video
    ↓ VIDEO
Scene · 场景切分   (or Highlight · 高光片段提取 / Metadata · 视频元信息)
    ↓ STRING
(JSON timeline or metadata for downstream analysis nodes)
```

Importable workflows are available in [`example_workflows`](./example_workflows).
Select your own authorized local video after importing one.

## Node parameters

### ASR · 语音转字幕

- `content_type`: `auto`, `speech`, or `singing`.
- `language`: `auto` detection, or `cmn-Hans-CN` / `eng-US`.
- `enable_speaker_info`: enable speaker diarization.
- `enable_confidence`: return confidence scores.
- Outputs: `subtitle` text and a redacted `raw_json` payload.

### OCR · 视频识别字幕

- `mode`: `Subtitle` for subtitle text or `Detailed` for richer detail.
- Outputs: `subtitle` text and a redacted `raw_json` payload.

### Matte · 人像抠图 / Matte · 绿幕抠图

- `output_format`: `WEBM` (default) or `MOV` transparent output.
- Output: native `VIDEO`.

### Scene · 场景切分

- `enable_clip_fade`: emit detected fades as separate clips.
- `segment_threshold`: sensitivity in `[0, 100)`; `0` uses the default.
- `min_duration` / `max_duration`: per-clip duration limits in seconds; `0`
  uses the default.
- Outputs: `scenes_json` timeline and a redacted `raw_json` payload.

### Highlight · 高光片段提取

- `model`: `Miniseries` or `Game`.
- Outputs: `highlights_json` metadata and a redacted `raw_json` payload.

### Metadata · 视频元信息

- No business parameters (`run_mode` defaults to `auto`, which runs locally when
  the CLI supports it).
- Outputs: `metadata_json` and a redacted `raw_json` payload.

### Trim · 视频裁剪

- `start_time`: trim start in seconds.
- `end_time`: trim end in seconds; a value at or below `start_time` means
  "trim to the end of the video".
- `run_mode`: `auto` (default, local-first) or `cloud`.

### Extract Audio · 提取音频

- `output_format`: `mp3`, `m4a` (default), `ogg`, `flac`, or `wav`.
- `run_mode`: `auto` (default, local-first) or `cloud`.
- Output: native `AUDIO`.

### Speed · 视频变速 / Audio Speed · 音频变速

- `speed`: playback rate in `0.1–4.0`, default `1.0`.
- Audio node output format: `mp3`, `m4a` (default), `ogg`, `flac`, or `wav`.

### Volume · 音量调整

- `volume`: multiplier `0–4`, default `1`; `0` mutes the audio.
- Output: native `VIDEO`.

### Camera Motion · 镜头运动

- `motion_style`: `zoom`, `pan-zoom`, `orbit-360`, or `bounce`.
- `start_time` / `end_time`: effect range in seconds; `end_time=0` means the end of the video.

### Filter · 视频滤镜

- `filter_style`: `spring`, `sunset`, `vivid`, `fair_skin`, or `food`.

### Flip · 视频翻转

- `is_flip_horizontal` / `is_flip_vertical`: horizontal / vertical mirror; enable at least one.

### Rotate · 视频旋转

- `rotate_direction`: `rotate_left_90`, `rotate_right_90`, or `rotate_180`.

### Concat · 视频拼接

- `videos`: 1–100 numbered Autogrow slots (`video_1`, `video_2`, etc.).
- `transitions`: one transition resource ID applied to each boundary; empty means hard cuts.

### Concat Audio · 音频拼接

- `audios`: 1–100 numbered AUDIO Autogrow slots.
- Output: native `AUDIO`.

### Mix · 混音

- `audios`: 1–100 numbered AUDIO Autogrow slots.
- Output: native `AUDIO`.

### Mux · 音视频合流

- `audio`: the audio track to mux in.
- `is_audio_reserve`: keep the original audio (default) or replace it.
- `is_video_audio_sync`: enable A/V sync (`sync_method` and `sync_mode` optional).

### Subtitle · 视频加字幕

- `subtitle_url`: subtitle file path or URL (SRT/VTT/ASS).
- `subtitles_json`: inline subtitle list JSON (`subtitle_text` / `start_time` / `end_time`).
- `subtitle_font_type`: `sy_black` (default), `pm_zhengdao`, or `zhanku_kuaile`.
- `subtitle_pos_preset`: `bottom_center` (default), `top_center`, `center`, `lower_third`.
- `subtitle_font_size` / `subtitle_font_color` / `subtitle_text_effect`: size, color, and effects.

### Stitch · 视频拼合

- `videos`: list of videos to stitch (2–3).
- `stitch_direction`: `horizontal` or `vertical`.

### Crop · 画面裁剪

- `top_left_x` / `top_left_y` / `bottom_right_x` / `bottom_right_y`: crop rectangle
  in pixels; bottom-right must be greater than top-left and each side ≥ 16px.

### Audio Trim · 音频裁剪

- `start_time` / `end_time`: trim range in seconds.
- Output: native `AUDIO`.

### Fade Audio · 音频淡入淡出

- `fade_in_duration` / `fade_out_duration`: seconds, default `1`.
- Output format defaults to `mp3`; `mp3`, `m4a`, `ogg`, `flac`, or `wav`.

### Fade · 视频声音淡入淡出

- `fade_in_duration` / `fade_out_duration`: seconds, default `1`.

### Animated · 提取动图

- `start_time` / `end_time`: time range in seconds; end must exceed start.
- `output_format`: `gif` (default) or `webp`.
- Outputs: `image` (all frames), `frame_durations_ms` (per-frame milliseconds JSON), and `animated_url` (original GIF/WebP resource).
- IMAGE batches do not encode animation timing; use the original URL for the encoded animation. Cloud URL expiry is determined by the service.

### Enhance · 视频增强

- `tool_version`: `standard` or `professional`.
- `scene`: common, UGC, short series, AIGC, or old film; used by the standard
  edition only.
- `resolution`: preserve the source or request 240p through 4K.
- `bitrate_level`: low, medium, or high target bitrate.
- `fps`: `0` preserves the source frame rate; a target up to 120 fps can also
  be requested.

### Enhance Ultra · 视频增强（大模型版）

- `resolution`: 720p or 1080p.
- `bitrate_level`: low, medium, or high target bitrate.
- `fps`: `0` preserves the source; specified values must be 15–120 fps.

### Erase Subtitle Pro · 字幕擦除（增强版）

- `erase_mode`: remove subtitles only, or include other rendered text.
- `output_encode_mode`: prioritize quality or output size.
- `restrict_region`: process only text inside a normalized rectangle.

Polling interval and maximum attempts are advanced settings and should
normally remain at their defaults.

## Billing, privacy, and security

- Every video AI node submits a cloud task to the user's own MediaKit account.
- Running a node may incur charges. Review the capability and parameters first.
- Input media is uploaded directly to Volcengine AI MediaKit.
- Plugin maintainers do not proxy, store, or inspect user media.
- The plugin never writes the API key into workflow data.
- Diagnostic logs remove API keys and signed-URL query parameters.
- Process only media you are authorized to upload and transform.

## Troubleshooting

### `mediakit-cli` is not found

Confirm that `mediakit-cli version` works in the same environment used to
launch ComfyUI. Desktop applications may not inherit your terminal PATH, so
you may need to launch ComfyUI from a terminal configured for the CLI.

### Authentication fails

Run `mediakit-cli init` again, or ensure the ComfyUI process receives
`MEDIAKIT_API_KEY`. Never paste a complete API key into public logs.

### Nodes do not appear

Upgrade ComfyUI and inspect its startup log for plugin import errors. This
plugin requires `comfy_api.latest` and native video nodes.

### A cloud task times out

The task may still be active in MediaKit. Use the redacted task ID in the local
ComfyUI log for further diagnosis.

## Development and tests

```bash
python -m unittest discover -s tests -v
```

Unit tests mock MediaKit CLI and never submit a paid cloud task. Real capability
validation must be performed manually with a short, authorized test video.

### Paid cloud smoke test (manual only)

The manual workflow runs a pinned, real ComfyUI CPU runtime through
`VideoFromFile → MediaKitTrimVideo.execute → native VIDEO save → PyAV decode`.
It exercises the production node, media bridge, orchestrator and CLI, then checks
that the output is decodable and approximately one second long.
**A configured workflow is not evidence of a passing paid cloud E2E run.**

- `workflow_dispatch` only, with explicit `confirm_billing=true`. Local execution
  also requires `--confirm-billing`; push/PR never triggers paid work.
- A fixed concurrency group serializes runs; it is not a billing quota. A queued
  run may later submit another billable task.
- At most one submission per run, without automatic submit retries. A token is
  persisted to `smoke-state.json` before sending, and task_id is saved on receipt.
- Reusing an output directory with existing state refuses to submit again.
  A timeout does not cancel the remote task or prove there was no charge.
  Query an existing task_id instead of resubmitting. A fixed token helps backend
  idempotency but cannot guarantee deduplication if the uploaded input URL changes.
- Configure repository Secret `MEDIAKIT_API_KEY`; never put the key in command
  arguments, source files or workflow YAML.
- The synthetic two-second input is trimmed to 0–1 seconds. The node phase is
  capped at ten minutes and polling has a total interval×attempts deadline.
- Success/failure reports and synthetic media are uploaded. No API key or signed
  result URL is stored in the report.

For local execution, use the Python environment of a real ComfyUI checkout with
its dependencies, official `mediakit-cli` and `ffmpeg` (this incurs a real charge):

```bash
python scripts/cloud_smoke.py --confirm-billing \
  --comfy-root /path/to/ComfyUI --work-dir ./cloud-smoke-artifacts
```

Preserve state after failure; inspect its task_id/token before considering a new run.

See [SECURITY.md](./SECURITY.md) for the Registry publishing and security self-review.

## License

[MIT](./LICENSE). This is an unofficial community integration and is not an
official Volcengine or ComfyUI product.
