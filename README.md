# MediaKit Toolkit for ComfyUI

MediaKit Toolkit is an unofficial community connector for Volcengine AI
MediaKit. It exposes MediaKit capabilities as native ComfyUI nodes while
keeping upload, cloud task polling, and result download details inside the
node implementation.

> You need your own Volcengine AI MediaKit account and API key, and you are
> responsible for MediaKit usage charges. Input media is sent directly from
> your local ComfyUI installation to Volcengine. It does not pass through a
> server operated by this plugin's maintainers.

## Status

Version `0.2.1` is an early development release. It currently includes:

- **MediaKit Environment Check** — checks the local CLI and configuration.
- **MediaKit Video Enhance** — native ComfyUI `VIDEO` input and `VIDEO`
  output using MediaKit standard or professional enhancement.
- **MediaKit Video Enhance Generative** — diffusion-based large-model video
  restoration with 720p/1080p output, bitrate control, and optional target fps.
- **MediaKit Erase Video Subtitle** — standard hard-subtitle erasure.
- **MediaKit Erase Video Subtitle Pro** — higher-quality erasure with subtitle
  or rendered-text modes, output encoding preference, and an optional region.

Planned modules include additional video AI, video editing, audio processing,
image tools, and shared MediaKit utilities.

## Requirements

- A recent ComfyUI version with the V3 native `VIDEO` API.
- Python 3.10 or newer for this plugin.
- Node.js 18 or newer when installing MediaKit CLI through npm.
- The official `mediakit-cli` available to the process that launches ComfyUI.
- A valid AI MediaKit API key.

## Install the MediaKit CLI

Install the official CLI using its current one-step installer:

```bash
npx @volcengine/mediakit-cli install -y
mediakit-cli version
```

Initialize it with your own API key:

```bash
mediakit-cli init \
  --mode cloud-first \
  --api-key "YOUR_MEDIAKIT_API_KEY" \
  --credential-store config \
  --yes
```

Alternatively, provide `MEDIAKIT_API_KEY` to the environment that starts
ComfyUI. Never place the key in a workflow JSON file.

Run the official health check before opening ComfyUI:

```bash
mediakit-cli doctor
```

## Install the custom nodes

### ComfyUI Manager / Registry

Registry installation will be enabled after the first public release.

### Manual development install

Clone this repository into `ComfyUI/custom_nodes`:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/fudanll-sys/comfyui-mediakit-toolkit.git
```

Restart ComfyUI after installation. If the nodes do not appear, inspect the
ComfyUI startup log for an import error and verify that your ComfyUI version
provides `comfy_api.latest` and native video nodes.

## Usage

Start with the diagnostic node:

```text
MediaKit Environment Check
```

The basic video workflow is:

```text
Load Video
    ↓ VIDEO
MediaKit Video Enhance
    ↓ VIDEO
Save Video
```

Subtitle erasure can be inserted before or after enhancement:

```text
Load Video
    ↓ VIDEO
MediaKit Erase Video Subtitle Pro
    ↓ VIDEO
MediaKit Video Enhance
    ↓ VIDEO
Save Video
```

Enhancement parameters:

- `tool_version`: `standard` or `professional`.
- `scene`: `common`, `ugc`, `short_series`, `aigc`, or `old_film`; only sent
  for the standard version.
- `resolution`: keep the source resolution, or request 240p through 4K.
- `bitrate_level`: choose a low, medium, or high target bitrate.
- `fps`: `0` keeps the source frame rate; positive values request a target up
  to 120 fps.
- polling controls are advanced options and should normally remain at their
  defaults.

Professional subtitle-erasure parameters:

- `erase_mode`: `Subtitle` removes detected subtitles; `Text` also removes
  other rendered text while attempting to preserve text in the scene.
- `output_encode_mode`: `Quality` prioritizes output quality; `Size` keeps the
  output bitrate closer to the source.
- `restrict_region`: when enabled, only text fully inside the normalized
  rectangle is removed. Coordinates range from `0.0` to `1.0`; the default
  rectangle covers the lower half of the frame.

All video AI nodes submit paid cloud tasks to the user's own MediaKit account.

Generative enhancement parameters:

- `resolution`: `720p` or `1080p`.
- `bitrate_level`: `low`, `medium`, or `high`.
- `fps`: `0` keeps the source frame rate; otherwise use 15–120 fps. MediaKit
  recommends staying within four times the source frame rate.

## Privacy and billing

- Cloud nodes upload input media to Volcengine AI MediaKit.
- MediaKit processing may incur charges on your Volcengine account.
- The plugin does not proxy, store, or inspect your media on a maintainer-run
  service.
- The plugin does not include an API key in workflow data.
- Signed upload and download URL query strings are removed from diagnostics.

Only process media that you are authorized to upload to the service.

## Troubleshooting

### `mediakit-cli` is not found

Confirm `mediakit-cli version` works in the same environment used to launch
ComfyUI. Desktop applications may not inherit the PATH configured in an
interactive terminal.

### Authentication fails

Run `mediakit-cli init --api-key ... --yes` again, or configure
`MEDIAKIT_API_KEY` for the ComfyUI process.

### Native VIDEO API is unavailable

Upgrade ComfyUI. The main nodes intentionally use the native ComfyUI media
types instead of falling back to path strings or private VHS types.

### Cloud task times out

The cloud task may still be active. The task ID is retained in local ComfyUI
logs for diagnosis, but it is not exposed as a normal workflow output.

## Development

Run the dependency-free unit suite:

```bash
python -m unittest discover -s tests -v
```

Unit tests mock the MediaKit CLI and never submit a paid cloud task. A real
smoke test must be run manually with a short, authorized MP4 file.

## License

MIT. This project is an unofficial community integration and is not an
official Volcengine or ComfyUI product.
