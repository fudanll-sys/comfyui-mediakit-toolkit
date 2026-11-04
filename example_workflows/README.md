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

## P1 示例（0.5.0）

- `mediakit_video_edit_basic.json`：加载视频 → 变速 → 旋转 → 保存。
- `mediakit_video_concat.json`：两路视频连接 `videos.video_1` / `videos.video_2` → 拼接 → 保存。
- `mediakit_video_audio_edit.json`：加载视频 → 提取音频 → 音频变速 → 保存 AUDIO。

以上三个 P1 图已用真实 ComfyUI V3 schema 检查，并在隔离 ComfyUI 0.43.0 / 前端 1.57.6 中通过浏览器文件入口导入；连线和保存参数展开正确。尚未执行有效 P1 云端编辑的完整处理链。导入后必须选择自己的文件；空输入不可直接运行。Autogrow 多输入要求近期 ComfyUI。CLI 0.2.2 的编辑能力仅支持云端，`auto` 也会回退收费云任务。

The workflows require a recent ComfyUI build that includes the native
`LoadVideo`, `SaveVideo`, and `SaveAudio` nodes. Select your own authorized
MP4 input after importing one. Running a video AI workflow submits a paid
MediaKit cloud task; trimming and audio extraction run locally when the
installed CLI supports it.
