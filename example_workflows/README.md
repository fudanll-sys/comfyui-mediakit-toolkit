# Example workflows

`mediakit_video_enhance.json` demonstrates the intended enhancement graph:

```text
Load Video → Enhance · 视频增强 → Save Video
```

`mediakit_erase_video_subtitle_pro.json` demonstrates professional subtitle
erasure:

```text
Load Video → Erase Subtitle Pro · 字幕擦除（增强版） → Save Video
```

`mediakit_video_enhance_generative.json` demonstrates large-model video
restoration:

```text
Load Video → Enhance Ultra · 视频增强（大模型版） → Save Video
```

`mediakit_video_trim.json` demonstrates local-first trimming:

```text
Load Video → Trim · 视频裁剪 → Save Video
```

`mediakit_video_extract_audio.json` demonstrates audio-track extraction:

```text
Load Video → Extract Audio · 提取音频 → Save Audio
```

The workflows require a recent ComfyUI build that includes the native
`LoadVideo`, `SaveVideo`, and `SaveAudio` nodes. Select your own authorized
MP4 input after importing one. Running a video AI workflow submits a paid
MediaKit cloud task; trimming and audio extraction run locally when the
installed CLI supports it.
