# Example workflows

`mediakit_video_enhance.json` demonstrates the intended enhancement graph:

```text
Load Video → Enhance · 视频增强（极速版） → Save Video
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

The workflows require a recent ComfyUI build that includes the native
`LoadVideo` and `SaveVideo` nodes. Select your own authorized MP4 input after
importing one. Running either workflow submits a paid MediaKit cloud task.
