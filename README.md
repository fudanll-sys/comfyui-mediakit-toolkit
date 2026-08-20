# ComfyUI MediaKit Toolkit

[简体中文](./README.md) | [English](./README.en.md)

一个面向 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 的非官方
[火山引擎 AI MediaKit](https://www.volcengine.com/docs/6448) 社区插件。它将
MediaKit 云端视频 AI 能力封装为原生 ComfyUI 节点，并在节点内部完成本地视频
上传、异步任务轮询和结果下载。

> 使用云端节点需要你自己的火山引擎账号和 AI MediaKit API Key，并可能产生
> 费用。视频将从本地 ComfyUI 直接上传至火山引擎，不会经过插件维护者的服务器。

## 当前状态

当前版本为 `0.3.0`，已提供以下节点：

| 节点 | 说明 |
| --- | --- |
| `MediaKit Environment Check` | 检查 MediaKit CLI、鉴权和运行环境。 |
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

`Enhance · 视频增强` 不是极速版。独立的极速增强能力尚未接入，未来上线后将使用
单独的节点名称，避免与当前标准版/专业版混淆。

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

- 无业务参数。
- 输出：`metadata_json` 标准元信息，`raw_json` 完整结果（已脱敏）。

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

## 许可证

[MIT](./LICENSE)。本项目是非官方社区集成，不代表火山引擎或 ComfyUI 官方产品。
