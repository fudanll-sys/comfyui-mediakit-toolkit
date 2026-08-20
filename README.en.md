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

Version `0.3.0` currently provides:

| Node | Description |
| --- | --- |
| `MediaKit Environment Check` | Checks MediaKit CLI, authentication, and the runtime environment. |
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

`Enhance · 视频增强` is not the fast edition. A dedicated fast-enhancement
capability has not been integrated yet and will use a separate node name when
it becomes available.

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

- No business parameters.
- Outputs: `metadata_json` and a redacted `raw_json` payload.

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

## License

[MIT](./LICENSE). This is an unofficial community integration and is not an
official Volcengine or ComfyUI product.
