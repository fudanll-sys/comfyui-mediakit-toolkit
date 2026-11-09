# ComfyUI MediaKit Toolkit

[简体中文](./README.md) | [English](./README.en.md)

一个面向 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 的非官方
[火山引擎 AI MediaKit](https://www.volcengine.com/docs/6448) 社区插件。它将
MediaKit 云端视频 AI 能力封装为原生 ComfyUI 节点，并在节点内部完成本地视频
上传、异步任务轮询和结果下载。

> 使用云端节点需要你自己的火山引擎账号和 AI MediaKit API Key，并可能产生
> 费用。视频将从本地 ComfyUI 直接上传至火山引擎，不会经过插件维护者的服务器。

## 当前状态

当前版本为 `0.5.0`，包含 P1 编辑节点及原生媒体接口修复：

| 节点 | 说明 |
| --- | --- |
| `MediaKit Environment Check` | 检查 MediaKit CLI、鉴权、运行环境与 schema 快照基线。 |
| `Enhance · 视频增强` | 标准版/专业版视频画质增强，原生 `VIDEO → VIDEO`。 |
| `Enhance Ultra · 视频增强（大模型版）` | 基于扩散大模型的生成式视频增强修复。 |
| `Erase Subtitle · 字幕擦除` | 智能检测并擦除视频硬字幕。 |
| `Erase Subtitle Pro · 字幕擦除（增强版）` | 精细化字幕/文字擦除，支持限定擦除区域。 |
| `ASR · 语音转字幕` | 识别视频语音，输出带时间戳的字幕文本。 |
| `OCR · 视频识别字幕` | 识别视频画面中的字幕和文字。 |
| `Matte · 人像抠图` | 识别人物主体并移除背景，输出透明背景视频。 |
| `Matte · 绿幕抠图` | 对绿幕或纯色背景视频抠图，输出透明背景视频。 |
| `Scene · 场景切分` | 依据转场自动切分场景，输出切片时间轴。 |
| `Highlight · 高光片段提取` | 捕捉情绪波峰与关键动作，输出高光元数据。 |
| `Metadata · 视频元信息` | 探测视频容器、视频流与音频流元信息。 |
| `Trim · 视频裁剪` | 按时间范围裁剪视频，原生 `VIDEO → VIDEO`。 |
| `Extract Audio · 提取音频` | 从视频分离音轨，原生 `VIDEO → AUDIO`。 |
| `Speed · 视频变速` | 调整视频播放速度（0.1～4.0 倍）。 |
| `Volume · 音量调整` | 调整视频音量倍数或静音。 |
| `Camera Motion · 镜头运动` | 为视频添加推拉、平移、旋转等镜头运动。 |
| `Filter · 视频滤镜` | 春日、晚霞、鲜亮、白皙、美食预设滤镜。 |
| `Flip · 视频翻转` | 水平/垂直翻转视频画面。 |
| `Rotate · 视频旋转` | 左转 90° / 右转 90° / 旋转 180°。 |
| `Concat · 视频拼接` | 顺序拼接多个视频（支持过渡效果）。 |
| `Concat Audio · 音频拼接` | 顺序拼接多个音频。 |
| `Mix · 混音` | 将多个音频混合为一条音轨。 |
| `Mux · 音视频合流` | 将视频与音频合流，支持替换/保留原音与音画同步。 |
| `Subtitle · 视频加字幕` | 将字幕文件或文本内容按自定义样式压制到画面。 |
| `Stitch · 视频拼合` | 将 2～3 个视频在同一画布左右/上下拼合。 |
| `Crop · 画面裁剪` | 按指定矩形区域裁剪视频画面。 |
| `Audio Speed · 音频变速` | 调整音频播放速度（0.1～4.0 倍），原生 `AUDIO → AUDIO`。 |
| `Audio Trim · 音频裁剪` | 按时间范围裁剪音频，原生 `AUDIO → AUDIO`。 |
| `Fade Audio · 音频淡入淡出` | 为音频添加淡入与淡出效果，原生 `AUDIO → AUDIO`。 |
| `Fade · 视频声音淡入淡出` | 为视频中的声音添加淡入与淡出效果。 |
| `Animated · 提取动图` | 将视频指定时间段提取为 GIF/WebP 动图，原生 `VIDEO → IMAGE`。 |

`Enhance · 视频增强` 不是极速版。独立的极速增强能力尚未接入，未来上线后将使用
单独的节点名称，避免与当前标准版/专业版混淆。

### 运行模式

所有 `MediaKit/Video Editing` 节点和 `Metadata · 视频元信息` 提供 `run_mode`
参数：

- `auto`（默认）：检测本机 `mediakit-cli` 是否支持该能力的本地模式；支持则本地
  同步执行（免费、不产生云端费用），否则回退云端异步任务。
- `cloud`：强制提交云端任务。

插件不会强制选择本地模式：较旧的 CLI 构建可能不支持 `--local`，强制指定会直接
失败，因此节点只暴露 `auto` 与 `cloud` 两个选项。

### 原生媒体与验证

- P1 多输入使用 ComfyUI V3 Autogrow；连接编号插槽，不能将一条连接当作多个输入。
- AUDIO 输入为 `waveform [1,C,T]` 和 `sample_rate` 字典，当前接受单批次、单/双声道；内部转为 PCM16 WAV，可能有量化误差，不会误用 VIDEO 返回类型。
- IMAGE 输出为完整帧批次；动图另有帧时长和原资源地址。
- 开发验证：在 ComfyUI Python 环境运行 `python scripts/verify_comfy_contracts.py --comfy-root /path/to/ComfyUI` 和 `python -m unittest discover -s tests`。
- 未在 ComfyUI 环境运行时，媒体往返测试会明确跳过；不能把跳过算作通过。已在隔离 ComfyUI 0.43.0 / 前端 1.57.6 验证三个 P1 示例导入、保存参数展开及本地诊断/视频保存/错误输入队列；尚未验证有效 P1 云端编辑的完整处理链。
- 前端/队列复现：`python scripts/verify_comfy_runtime.py --url http://127.0.0.1:8197 --browser-executable /path/to/chrome --fixture-file test.mp4 --artifacts-dir /path/to/test-results`，需单独安装 Playwright，且只在隔离的本机 ComfyUI 上运行。脚本不提交有效云端任务。
- CLI 0.2.2 编辑域仅支持云端；`auto` 回退云端也可能计费。

### Schema 快照与版本锁定

仓库的 [`schemas/`](./schemas) 目录保存 MediaKit CLI 全部能力的 JSON Schema
快照和 `manifest.json` 基线（CLI 版本 + 每个工具的指纹）。`scripts/sync_cli_schemas.py`
用于同步和验证：

```bash
python scripts/sync_cli_schemas.py --update    # 用本机 CLI 刷新快照
python scripts/sync_cli_schemas.py --check     # 对比当前 CLI 与快照，发现漂移（CI 可集成）
python scripts/sync_cli_schemas.py --offline   # 不调用 CLI，仅校验快照完整性
```

`--check` 会报告工具新增/消失、参数指纹变化与模式变化。`MediaKit Environment Check`
节点也会对比安装的 CLI 版本与快照基线，不一致时在诊断详情中提示。

## 使用前准备

- 支持 ComfyUI V3 原生 `VIDEO` API 的较新版本。
- Python 3.10 或更高版本。
- Node.js 18 或更高版本，用于安装官方 MediaKit CLI。
- 已开通 AI MediaKit 并准备好 API Key。
- 本地启动 ComfyUI 的进程能够访问 `mediakit-cli`。

## 开通 AI MediaKit

本插件不提供 MediaKit 账号、额度或代付服务。首次使用前请完成以下步骤：

1. 注册并登录火山引擎账号；如控制台提示，请先完成实名认证。
2. 前往 [AI MediaKit 控制台](https://console.volcengine.com/imp/ai-mediakit/settings)。
3. 按控制台提示完成服务开通和相关协议确认；已经开通的用户可以跳过。
4. 在控制台创建或复制 AI MediaKit API Key。
5. 妥善保存 API Key，不要将其提交到 GitHub、写入工作流 JSON 或分享给他人。

MediaKit 的云端能力可能按实际使用量计费。可用额度、服务区域及最新价格以
火山引擎控制台和[官方文档](https://www.volcengine.com/docs/6448)为准。

## 安装和配置 MediaKit CLI

安装火山引擎官方 CLI：

```bash
npx @volcengine/mediakit-cli install -y
```

使用 API Key 初始化：

```bash
mediakit-cli init \
  --mode cloud-first \
  --api-key "YOUR_MEDIAKIT_API_KEY" \
  --credential-store config \
  --yes
```

检查版本、云端连接和本地依赖：

```bash
mediakit-cli doctor
mediakit-cli version
```

也可以只为启动 ComfyUI 的进程提供环境变量：

```bash
export MEDIAKIT_API_KEY="YOUR_MEDIAKIT_API_KEY"
```

官方安装与鉴权说明请参阅
[volcengine/mediakit-cli](https://github.com/volcengine/mediakit-cli)。

## 安装插件

> ComfyUI Manager 只会安装本插件。每位用户仍需按照上文在本机安装并初始化
> `mediakit-cli`，使用自己的 AI MediaKit API Key 完成鉴权。

### 方法一：ComfyUI Manager（推荐）

1. 在 ComfyUI 中打开 `Manager` → `Custom Nodes`。
2. 搜索 `MediaKit Toolkit` 或 `mediakit-toolkit`。
3. 选择最新版本并点击 `Install`。
4. 安装完成后完全重启 ComfyUI。

也可以使用 Comfy CLI 安装 Registry 版本：

```bash
comfy node install mediakit-toolkit
```

### 方法二：Git 安装

如果 Manager 中暂时搜索不到，或者需要直接跟踪 GitHub 版本，可以进入 ComfyUI
的 `custom_nodes` 目录安装：

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/fudanll-sys/comfyui-mediakit-toolkit.git
```

安装后完全重启 ComfyUI。节点位于 `MediaKit/Video AI` 分类，也可以搜索
`MediaKit`、`Enhance` 或 `Erase Subtitle`。

### 更新插件

通过 Manager 安装的用户可在 `Update available` 中选择新版本并更新。通过 Git
安装的用户可在 ComfyUI 根目录运行：

```bash
git -C custom_nodes/comfyui-mediakit-toolkit pull --ff-only origin main
```

更新后完全重启 ComfyUI。

## 快速使用

首次使用建议先运行：

```text
MediaKit Environment Check
```

基础画质增强工作流：

```text
Load Video
    ↓ VIDEO
Enhance · 视频增强
    ↓ VIDEO
Save Video
```

大模型画质增强工作流：

```text
Load Video
    ↓ VIDEO
Enhance Ultra · 视频增强（大模型版）
    ↓ VIDEO
Save Video
```

字幕擦除工作流：

```text
Load Video
    ↓ VIDEO
Erase Subtitle Pro · 字幕擦除（增强版）
    ↓ VIDEO
Save Video
```

语音转字幕工作流：

```text
Load Video
    ↓ VIDEO
ASR · 语音转字幕
    ↓ STRING
（字幕文本可继续用于字幕合成等下游节点）
```

人像/绿幕抠图工作流：

```text
Load Video
    ↓ VIDEO
Matte · 人像抠图
    ↓ VIDEO
Save Video
```

裁剪/提取音频工作流：

```text
Load Video
    ↓ VIDEO
Trim · 视频裁剪
    ↓ VIDEO
Save Video

Load Video
    ↓ VIDEO
Extract Audio · 提取音频
    ↓ AUDIO
（音频可继续连接原生 AUDIO 下游节点）
```

场景切分 / 高光提取 / 元信息工作流：

```text
Load Video
    ↓ VIDEO
Scene · 场景切分   （或 Highlight · 高光片段提取 / Metadata · 视频元信息）
    ↓ STRING
（JSON 时间轴或元数据，可交给分析或可视化节点）
```

仓库中的 [`example_workflows`](./example_workflows) 提供可导入的示例工作流。
导入后请重新选择你有权处理的本地视频。

## 节点参数

### ASR · 语音转字幕

- `content_type`：`auto`、`speech`（对话）或 `singing`（歌唱）。
- `language`：`auto` 自动探测，或指定 `cmn-Hans-CN` / `eng-US`。
- `enable_speaker_info`：开启说话人识别。
- `enable_confidence`：返回识别置信度。
- 输出：`subtitle` 字幕文本，`raw_json` 完整结果（已脱敏）。

### OCR · 视频识别字幕

- `mode`：`Subtitle` 识别字幕文本；`Detailed` 识别更详细信息。
- 输出：`subtitle` 字幕文本，`raw_json` 完整结果（已脱敏）。

### Matte · 人像抠图 / Matte · 绿幕抠图

- `output_format`：`WEBM`（默认）或 `MOV` 透明视频格式。
- 输出：原生 `VIDEO`。

### Scene · 场景切分

- `enable_clip_fade`：将淡入淡出片段作为独立切片。
- `segment_threshold`：切分敏感度阈值 `[0, 100)`；`0` 使用算法默认值。
- `min_duration` / `max_duration`：单个切片的最小时长/最大时长（秒）；`0` 使用默认值。
- 输出：`scenes_json` 切片时间轴，`raw_json` 完整结果（已脱敏）。

### Highlight · 高光片段提取

- `model`：`Miniseries`（短剧）或 `Game`（小游戏）。
- 输出：`highlights_json` 高光元数据，`raw_json` 完整结果（已脱敏）。

### Metadata · 视频元信息

- 无业务参数（`run_mode` 默认 `auto`，CLI 支持本地模式时本地执行）。
- 输出：`metadata_json` 标准元信息，`raw_json` 完整结果（已脱敏）。

### Trim · 视频裁剪

- `start_time`：裁剪开始时间（秒）。
- `end_time`：裁剪结束时间（秒）；小于等于开始时间时视为裁剪到视频末尾。
- `run_mode`：`auto`（默认，本地优先）或 `cloud`。

### Extract Audio · 提取音频

- `output_format`：`mp3`、`m4a`（默认）、`ogg`、`flac`、`wav`。
- `run_mode`：`auto`（默认，本地优先）或 `cloud`。
- 输出：原生 `AUDIO`。

### Speed · 视频变速 / Audio Speed · 音频变速

- `speed`：变速倍速，范围 `0.1～4.0`，默认 `1.0`。
- 音频节点输出格式：`mp3`、`m4a`（默认）、`ogg`、`flac`、`wav`。

### Volume · 音量调整

- `volume`：音量倍数 `0～4`，默认 `1`；`0` 表示静音。
- 输出：原生 `VIDEO`。

### Camera Motion · 镜头运动

- `motion_style`：`zoom`（推拉）、`pan-zoom`（平移推拉）、`orbit-360`（环绕）、`bounce`（弹动）。
- `start_time` / `end_time`：效果时间段（秒）；`end_time=0` 表示到视频结尾。

### Filter · 视频滤镜

- `filter_style`：`spring`（春日）、`sunset`（晚霞）、`vivid`（鲜亮）、`fair_skin`（白皙）、`food`（美食）。

### Flip · 视频翻转

- `is_flip_horizontal` / `is_flip_vertical`：左右 / 上下镜像；至少开启一项。

### Rotate · 视频旋转

- `rotate_direction`：`rotate_left_90`、`rotate_right_90` 或 `rotate_180`。

### Concat · 视频拼接

- `videos`：按编号连接 1～100 个 `video_1`、`video_2` 等 Autogrow 插槽。
- `transitions`：选择一个转场资源 ID，应用到每个相邻连接点；空表示硬切。

### Concat Audio · 音频拼接

- `audios`：按编号连接 1～100 个 AUDIO 插槽。
- 输出：原生 `AUDIO`。

### Mix · 混音

- `audios`：按编号连接 1～100 个 AUDIO 插槽。
- 输出：原生 `AUDIO`。

### Mux · 音视频合流

- `audio`：待合流的音频。
- `is_audio_reserve`：是否保留原音（默认）或替换音轨。
- `is_video_audio_sync`：开启音画同步（可选 `sync_method` 与 `sync_mode`）。

### Subtitle · 视频加字幕

- `subtitle_url`：字幕文件路径或 URL（SRT/VTT/ASS）。
- `subtitles_json`：字幕内容列表 JSON（`subtitle_text` / `start_time` / `end_time`）。
- `subtitle_font_type`：`sy_black`（默认）、`pm_zhengdao`、`zhanku_kuaile`。
- `subtitle_pos_preset`：`bottom_center`（默认）、`top_center`、`center`、`lower_third`。
- `subtitle_font_size` / `subtitle_font_color` / `subtitle_text_effect`：字号、颜色与花字效果。

### Stitch · 视频拼合

- `videos`：待拼合的视频列表（2～3 个）。
- `stitch_direction`：`horizontal`（左右）或 `vertical`（上下）。

### Crop · 画面裁剪

- `top_left_x` / `top_left_y` / `bottom_right_x` / `bottom_right_y`：裁剪矩形坐标（像素），
  右下角必须大于左上角，且宽高差不得小于 16px。

### Audio Trim · 音频裁剪

- `start_time` / `end_time`：裁剪范围（秒）。
- 输出：原生 `AUDIO`。

### Fade Audio · 音频淡入淡出

- `fade_in_duration` / `fade_out_duration`：淡入/淡出时长（秒），默认 `1`。
- 输出格式默认 `mp3`；可选 `mp3`、`m4a`、`ogg`、`flac`、`wav`。

### Fade · 视频声音淡入淡出

- `fade_in_duration` / `fade_out_duration`：淡入/淡出时长（秒），默认 `1`。

### Animated · 提取动图

- `start_time` / `end_time`：动图时间范围（秒），结束时间必须大于起始时间。
- `output_format`：`gif`（默认）或 `webp`。
- 输出：`image` 为完整帧批次，`frame_durations_ms` 为每帧毫秒时长 JSON，`animated_url` 为保留原编码的 GIF/WebP 地址。
- IMAGE 帧批次本身不保存动画时序；需要原始动图时使用 `animated_url`，云端 URL 有效期以服务端为准。

### Enhance · 视频增强

- `tool_version`：`standard` 或 `professional`。
- `scene`：通用、UGC、短剧、AIGC 或老片场景；仅标准版使用。
- `resolution`：保持原分辨率，或选择 240p 至 4K。
- `bitrate_level`：低、中、高三档目标码率。
- `fps`：`0` 保持源帧率，也可以指定最高 120 fps。

### Enhance Ultra · 视频增强（大模型版）

- `resolution`：720p 或 1080p。
- `bitrate_level`：低、中、高三档目标码率。
- `fps`：`0` 保持源帧率；指定时支持 15–120 fps。

### Erase Subtitle Pro · 字幕擦除（增强版）

- `erase_mode`：仅擦除字幕，或同时擦除其他渲染文字。
- `output_encode_mode`：优先画质或优先控制输出大小。
- `restrict_region`：启用后只处理归一化坐标框内的文字。

轮询间隔和最大轮询次数属于高级参数，通常保持默认值即可。

## 计费、隐私与安全

- 所有视频 AI 节点都会向用户自己的 MediaKit 账号提交云端任务。
- 运行节点可能产生费用，提交前请确认所选能力和参数。
- 输入媒体会直接上传至火山引擎 AI MediaKit。
- 插件维护者不代理、不存储也不查看用户媒体。
- 插件不会把 API Key 写入工作流数据。
- 诊断日志会移除 API Key 和带签名 URL 的查询参数。
- 请只处理你有权上传和处理的媒体。

## 常见问题

### 找不到 `mediakit-cli`

请在启动 ComfyUI 的同一运行环境中确认 `mediakit-cli version` 可以执行。桌面程序
可能不会继承终端的 PATH，必要时请从配置好 CLI 的终端启动 ComfyUI。

### 鉴权失败

重新运行 `mediakit-cli init`，或确认启动 ComfyUI 的进程已经获得
`MEDIAKIT_API_KEY`。不要在公开日志中粘贴完整 API Key。

### 找不到节点

升级 ComfyUI，然后查看启动日志中是否存在插件导入错误。插件依赖
`comfy_api.latest` 和原生视频节点。

### 云端任务超时

任务可能仍在 MediaKit 云端运行。可在本地 ComfyUI 日志中查看已脱敏的任务 ID，
用于后续排查。

## 开发与测试

```bash
python -m unittest discover -s tests -v
```

单元测试会模拟 MediaKit CLI，不会提交付费云端任务。真实能力验证需要使用一个
较短且已获授权的测试视频手动执行。

### 付费云端冒烟（仅手动触发）

仓库提供 `Cloud Smoke (paid, manual)` GitHub Actions 工作流和
`scripts/cloud_smoke.py`。工作流使用固定提交版本的真实 ComfyUI CPU 环境，执行
`VideoFromFile → MediaKitTrimVideo.execute → 原生 VIDEO 保存 → PyAV 解码`，
验证节点、素材桥接、生产编排、CLI 模式适配、云端终态和约 1 秒输出。
**工作流存在不代表真实云端 E2E 已通过；须有对应运行成功的报告才能验收。**

- 只有 `workflow_dispatch`，push/PR 不自动付费；工作流须勾选
  `confirm_billing=true`，本地脚本同样须显式传 `--confirm-billing`；
- 固定并发组只保证串行，不是费用配额：后续排队运行仍可能收费；
- 每次最多提交一次 `trim-video`，不自动重试付费提交；提交前将 token 写入
  `smoke-state.json`，收到 task_id 后更新该文件，失败时也保留；
- 同一输出目录已有 state 文件时拒绝重新提交。超时不代表后端任务取消或未计费，
  已有 task_id 应只查询原任务。跨运行使用相同 token 仅是后端幂等辅助，
  不保证更换输入文件路径/上传地址后仍不会产生新任务；
- 配置仓库 Secret `MEDIAKIT_API_KEY` 后才可运行。不要把密钥写进代码、
  CLI 参数或工作流文件；
- 默认生成 2 秒合成素材，裁剪 0～1 秒；节点阶段最多等待 10 分钟，
  总轮询预算为间隔×次数，不因查询窗口重置而倍增；
- 成功和失败都会上传诊断报告与合成素材；报告不保存 API Key 或签名 URL。

本地需官方 `mediakit-cli`、`ffmpeg`、真实 ComfyUI 源码及其 Python 依赖。
请在 ComfyUI Python 环境中执行（会产生真实计费）：

```bash
python scripts/cloud_smoke.py --confirm-billing \
  --comfy-root /path/to/ComfyUI --work-dir ./cloud-smoke-artifacts
```

不要删除失败运行的 state 文件后盲目重跑；先检查其中的 task_id 和 token。

Registry 发布与安全自查见 [SECURITY.md](./SECURITY.md)。

## 许可证

[MIT](./LICENSE)。本项目是非官方社区集成，不代表火山引擎或 ComfyUI 官方产品。
