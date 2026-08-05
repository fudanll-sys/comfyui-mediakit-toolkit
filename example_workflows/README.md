# Example workflows

`mediakit_video_enhance.json` demonstrates the intended enhancement graph:

```text
Load Video → MediaKit Video Enhance → Save Video
```

`mediakit_erase_video_subtitle_pro.json` demonstrates professional subtitle
erasure:

```text
Load Video → MediaKit Erase Video Subtitle Pro → Save Video
```

The workflows require a recent ComfyUI build that includes the native
`LoadVideo` and `SaveVideo` nodes. Select your own authorized MP4 input after
importing one. Running either workflow submits a paid MediaKit cloud task.
