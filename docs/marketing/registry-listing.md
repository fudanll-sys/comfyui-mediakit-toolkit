# 商店文案（中英双语）

> 用途：ComfyUI Registry 节点页、GitHub Repo About、Manager 搜索结果、社群帖子共用一套文案。
> 发布前提：版本状态为 `NodeVersionStatusActive` 才可对外说“已上架”。Flagged / Pending 期间只能用“已上传、待审核”。

## 0. 命名与搜索词

用户的搜索对象是任务，不是包名。以下词必须出现在 Registry 描述、README 首屏和帖子标题里。

- 中文：字幕擦除、去水印、视频去字幕、视频增强、画质修复、超分、视频抠图、人像抠图、绿幕抠像、语音转字幕、视频转字幕、视频识别字幕、场景切分、高光片段、视频拼接、视频裁剪、ComfyUI 视频处理
- 英文：remove watermark、subtitle remover、erase subtitles、video upscale、video enhance、video restore、background removal、portrait matte、green screen、speech to subtitle、video OCR、scene detection、highlight extraction

包名与节点名保持稳定：`mediakit-toolkit`、`MediaKit`、`Erase Subtitle Pro`、`Enhance Ultra`。不再改命名，避免搜索结果断链。

## 1. Registry 短描述（一句话）

中文：
> 在 ComfyUI 里用原生节点擦字幕、去水印、增强画质、抠像和转字幕，云端处理，本地 VIDEO 直连。

英文：
> Erase subtitles and watermarks, upscale video, matte portraits, and transcribe speech inside ComfyUI with native VIDEO nodes.

## 2. Registry 长描述（中文）

标题：**MediaKit · 视频 AI 节点集（字幕擦除 / 画质增强 / 抠像 / 转字幕）**

正文：

32 个原生 ComfyUI 节点，把火山引擎 AI MediaKit 的云端视频 AI 能力接成 `VIDEO → VIDEO`。节点内部完成本地上传、异步轮询和结果下载，不需要你写 API 调用。

**最常用的三个场景**

- **字幕擦除与去水印**：`Erase Subtitle Pro` 支持限定擦除区域，二次剪辑、短剧出海、素材清洗都用得上。
- **画质增强**：`Enhance`（标准版 / 专业版）与 `Enhance Ultra`（大模型版）三档可选，老片修复和 AIGC 素材修正各有对应。
- **抠像与转字幕**：`Matte` 人像 / 绿幕抠像输出透明视频；`ASR` 出带时间戳字幕，`OCR` 识别画面内嵌文字。

**其余能力**：裁剪、拼接、变速、旋转、翻转、滤镜、镜头运动、裁剪拼合、音视频合流、混音、音频裁剪与淡入淡出、动图提取、场景切分、高光片段提取、视频元信息。

**需要你知道的三件事**

1. 云端能力用**你自己的**火山引擎账号和 AI MediaKit API Key，费用直接结算在你的账号上，插件不收钱也不代付。
2. 视频从本地 ComfyUI 直传火山引擎，不经过插件维护者服务器。
3. 编辑类节点在 CLI 支持本地模式时免费本地执行；CLI 0.2.2 编辑域仅云端，此时 `auto` 会回退成付费云任务。

**安装**：Manager 安装插件后，仍需在本机安装 `mediakit-cli` 并 `mediakit-cli init` 配置 Key，然后完全重启 ComfyUI。完整步骤见 README。

## 3. Registry Long Description (English)

Title: **MediaKit Video AI for ComfyUI — subtitle erasure, upscaling, matting, transcription**

32 native nodes that turn Volcengine AI MediaKit cloud video AI into `VIDEO → VIDEO` inside ComfyUI. Upload, async polling, and result download are handled inside the node — no API wiring.

**Three most-used workflows**

- **Erase subtitles / watermarks** — `Erase Subtitle Pro` with region restriction, for re-editing, short-drama localization, and stock cleanup.
- **Video enhancement** — `Enhance` (standard / professional) plus `Enhance Ultra` (generative model) for old footage and AIGC artifacts.
- **Matting and transcription** — `Matte` outputs transparent portrait / green-screen video; `ASR` returns timestamped subtitles; `OCR` reads burned-in text.

**Also included**: trim, concat, speed, rotate, flip, filters, camera motion, stitch, crop, mux, mix, audio trim / speed / fade, animated image extraction, scene segmentation, highlight extraction, metadata probe.

**What you should know**

1. Cloud calls use **your own** Volcengine account and AI MediaKit API key. Billing lands on your account; the plugin is free and never pays on your behalf.
2. Video goes from your local ComfyUI directly to Volcengine — never through the maintainer's servers.
3. Editing nodes run locally at no cloud cost when the installed CLI supports local mode; CLI 0.2.2 supports cloud only in the editing domain, so `auto` falls back to a paid cloud task.

**Install**: after the Manager install, still install `mediakit-cli` and run `mediakit-cli init` on the ComfyUI host, then fully restart ComfyUI.

## 4. 与相近插件的差异（用于帖子，不放进 Registry）

| 维度 | 纯本地 FFmpeg 节点 | 本插件 |
| --- | --- | --- |
| 字幕擦除 | 需要自己框区域 + 模糊，痕迹明显 | 模型检测，可限定区域 |
| 画质增强 | 只能调锐化、对比度 | 三档模型增强，重建细节 |
| 抠像 | 色键，绿幕外基本不可用 | 人像抠像直接出透明视频 |
| 依赖 | 本地 ffmpeg 与显卡 | 云端算力，不吃本地 GPU |
| 成本 | 电费 | 按分钟计费，需自备账号 |

## 5. 素材位清单（发布时逐项打勾）

- [ ] 节点截图 1：`Erase Subtitle Pro` 连线（Load Video → 节点 → Save Video）
- [ ] 节点截图 2：`Enhance` 参数展开（版本、场景、分辨率）
- [ ] 前后对比 GIF：字幕擦除，同一帧擦前 / 擦后，2 秒循环
- [ ] 前后对比 GIF：画质增强 720P → 1080P 局部放大
- [ ] 一条 30–60 秒录屏：导入模板 → 选文件 → 运行 → 出片
- [ ] 成本页截图：`docs/marketing/cost-comparison.html`

GIF 与录屏比文字更有用，所有帖子优先带图，其次带模板链接。
