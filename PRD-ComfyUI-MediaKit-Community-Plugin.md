# ComfyUI × 火山引擎 AI MediaKit 社区插件总 PRD

## 1. 文档信息

- 项目名称：MediaKit for ComfyUI
- 产品定位：火山引擎 AI MediaKit 非官方社区连接器
- 交付形态：可通过 Comfy Registry / ComfyUI Manager 安装的节点套件
- 目标用户：本地 ComfyUI 视频、音频和图像工作流用户
- 调用方式：首版优先使用官方 `mediakit-cli`
- 鉴权归属：用户使用自己的 MediaKit API Key
- 云端费用：由用户直接向火山引擎承担
- 文档版本：v1.0
- 日期：2026-08-05

本 PRD 是插件总规范。画质增强的详细实现继续参考：

```text
PRD-ComfyUI-MediaKit-Video-Enhance.md
```

## 2. 产品背景

当前目标不再是发布单一 `enhance-video` 节点，而是构建一个可持续扩展的 MediaKit 能力连接器。插件应统一解决 MediaKit 接入中的公共问题：

- MediaKit API Key 配置；
- 本地媒体文件读取；
- 本地媒体自动上传；
- ComfyUI 原生媒体类型适配；
- 云端异步任务提交；
- 任务轮询；
- 结果下载；
- 本地同步处理；
- 日志脱敏；
- 错误处理；
- 跨平台 CLI 检测；
- Registry 安装和升级。

在公共层之上，分别提供视频 AI、剪辑、音频、图像和通用工具节点。

## 3. 产品目标

### 3.1 核心目标

1. 建立一套统一的 MediaKit ComfyUI 节点基础设施。
2. 覆盖 `mediakit-cli` 当前适合工作流编排的主要能力。
3. 节点优先使用 ComfyUI 原生 `VIDEO`、`AUDIO`、`IMAGE` 类型。
4. 用户无需准备公网 URL、手动上传或手动查询 task_id。
5. 所有节点共享同一套鉴权、上传、轮询、下载和诊断逻辑。
6. 新增 MediaKit 能力时，只需要增加参数 Schema 和薄适配节点。
7. 插件可通过 ComfyUI Manager 搜索、安装和升级。
8. 插件不依赖作者运营的服务器。

### 3.2 最终产品体验

视频 AI：

```text
Load Video
→ MediaKit Video Enhance
→ MediaKit Erase Video Subtitle
→ Save Video
```

本地剪辑：

```text
Load Video
→ MediaKit Trim Video
→ MediaKit Adjust Video Speed
→ Save Video
```

音视频处理：

```text
Load Video ─┐
            ├→ MediaKit Mux Audio Video → Save Video
Load Audio ─┘
```

### 3.3 非目标

社区版不建设：

- 作者托管的云服务；
- 用户注册、登录和套餐系统；
- 自有 API Key；
- 视频中转服务；
- 自有对象存储；
- 代付或转售 MediaKit 调用额度；
- MediaKit 控制台管理功能；
- 所有 MediaKit API 的无差别自动暴露；
- 任意 JSON 参数直接执行的默认用户节点；
- 工作流执行期间安装 CLI 或系统依赖。

## 4. 产品命名与节点分类

插件包建议名称：

```text
mediakit-toolkit
```

Registry Display Name：

```text
MediaKit Toolkit
```

节点分类：

```text
MediaKit
├── Video AI
├── Video Editing
├── Audio
├── Image
├── Shared
└── Diagnostics
```

节点 ID 必须带稳定前缀，避免冲突：

```text
MediaKitVideoEnhance
MediaKitTrimVideo
MediaKitExtractAudio
MediaKitEnvironmentCheck
```

节点 ID 发布后不得随意修改。

## 5. 能力范围

## 5.1 首版必须交付的公共节点

### MediaKit Environment Check

只读检查：

- 操作系统和架构；
- ComfyUI 版本；
- 原生 `VIDEO` API 是否可用；
- `mediakit-cli` 是否存在；
- CLI 版本；
- CLI 健康检查；
- API Key/本地凭证是否有效；
- MediaKit 网络连通性；
- FFmpeg/FFprobe 状态；
- 默认输出目录。

不得返回 API Key 原文。

### MediaKit Fetch File

- 输入：远程 URL 或本地媒体引用；
- 输出：适合后续节点使用的本地文件或原生媒体对象；
- 用途：远程媒体预处理和兼容适配。

首版可标记为高级节点。

## 5.2 首版视频 AI 节点

### Enhance · 视频增强（极速版）

- 能力：标准版/专业版视频画质增强；
- 输入：原生 `VIDEO`；
- 输出：原生 `VIDEO`；
- 详细参数和验收：参考画质增强子 PRD。

### Enhance Ultra · 视频增强（大模型版）

- 能力：基于扩散大模型的生成式视频增强修复；
- 输入：原生 `VIDEO`；
- 输出：原生 `VIDEO`；
- 分辨率：`720p`、`1080p`；
- 码率档位：`low`、`medium`、`high`；
- 可选目标帧率：保持源值或 `15–120` fps；
- 云端异步任务，节点内部自动上传、轮询和下载。

### Erase Subtitle Pro · 字幕擦除（增强版）

- 能力：视频字幕/文字智能擦除；
- 输入：原生 `VIDEO`；
- 输出：原生 `VIDEO`；
- 主要参数：擦除模式及 CLI Schema 中公开的可配置项；
- 云端异步任务；
- 节点内部自动上传、轮询和下载。

### Erase Subtitle · 字幕擦除

- 能力：标准版视频硬字幕智能擦除；
- 输入：原生 `VIDEO`；
- 输出：原生 `VIDEO`；
- 云端异步任务；
- 节点内部自动上传、轮询和下载。

## 5.3 首版剪辑节点

以下节点应按当前 `mediakit-cli editing` Schema 实现：

### MediaKit Trim Video

- 输入：`VIDEO`；
- 参数：开始时间、结束时间；
- 输出：`VIDEO`。

### MediaKit Concat Video

- 输入：视频列表；
- 参数：转场配置；
- 输出：`VIDEO`。

如果原生 `VIDEO` 输入列表在目标 ComfyUI 版本中不稳定，允许首版使用明确的“视频列表构建节点”，但不得使用逗号拼接的普通字符串作为最终产品接口。

### MediaKit Flip Video

- 输入：`VIDEO`；
- 参数：水平翻转、垂直翻转；
- 输出：`VIDEO`。

### MediaKit Adjust Video Speed

- 输入：`VIDEO`；
- 参数：速度倍率；
- 输出：`VIDEO`。

### MediaKit Add Image To Video

- 输入：`VIDEO`、`IMAGE`；
- 参数：位置、宽高、时间范围等当前 CLI Schema 参数；
- 输出：`VIDEO`。

### MediaKit Add Subtitle To Video

- 输入：`VIDEO`；
- 字幕来源：SRT 文件或结构化字幕列表；
- 参数：字幕位置等当前 CLI Schema 参数；
- 输出：`VIDEO`。

### MediaKit Image To Video

- 输入：图像列表；
- 参数：单图时长、动画类型、转场；
- 输出：`VIDEO`；
- 运行模式：以当前 CLI Schema 为准；若仅支持云端则显式使用云端模式。

## 5.4 首版音频和音视频节点

### MediaKit Trim Audio

- 输入：原生 `AUDIO` 或受支持的音频文件对象；
- 参数：开始时间、结束时间；
- 输出：原生 `AUDIO`。

### MediaKit Concat Audio

- 输入：音频列表；
- 输出：原生 `AUDIO`。

### MediaKit Extract Audio

- 输入：`VIDEO`；
- 参数：输出格式；
- 输出：原生 `AUDIO`。

### MediaKit Mux Audio Video

- 输入：`VIDEO`、`AUDIO`；
- 参数：是否保留原视频音轨；
- 输出：`VIDEO`。

## 5.5 第二阶段候选能力

以下能力不作为首个公开版阻塞项，但架构必须允许增加：

- 画质增强极速版；
- 视频转码；
- 视频转封装；
- 极智超清；
- 视频抽帧；
- 视频画质检测；
- 视频人像/绿幕抠图；
- 视频人脸打码；
- 场景切分；
- ASR；
- 视频 OCR；
- 高光片段提取；
- 人声背景音分离；
- 图像画质增强；
- 图像背景移除；
- 图像基础编辑；
- OCR；
- 其他 MediaKit 新增工具。

新能力只有在官方 CLI 提供稳定 Schema，或插件增加稳定 HTTP 后端后，才能进入正式节点集合。

## 6. 架构设计

## 6.1 分层结构

```text
ComfyUI Nodes
    ↓
Capability Adapters
    ↓
Media Type Bridge
    ↓
Task Orchestrator
    ↓
Backend Interface
    ├── MediaKit CLI Backend
    └── MediaKit HTTP Backend（未来）
```

### ComfyUI Nodes

只负责：

- 定义端口和参数；
- 参数校验；
- 调用对应 capability adapter；
- 返回原生媒体类型。

不得在每个节点中重复实现 subprocess、上传和轮询。

### Capability Adapters

每个 MediaKit 能力对应一个声明：

```python
CapabilitySpec(
    domain="video",
    tool="enhance-video",
    mode="cloud",
    input_media=["video"],
    output_media="video",
    asynchronous=True,
)
```

适配器负责把 ComfyUI 参数映射为 CLI 参数。

### Media Type Bridge

统一实现：

- `VIDEO → 本地文件路径`；
- `AUDIO → 本地文件路径`；
- `IMAGE → 临时图像文件`；
- 本地文件/URL → 原生 `VIDEO`；
- 本地文件/URL → 原生 `AUDIO`；
- 本地文件/URL → `IMAGE`；
- 临时文件生命周期管理。

### Task Orchestrator

统一实现：

- 同步本地任务；
- 异步云端任务；
- task_id 提取；
- 自动轮询；
- 超时；
- 取消；
- 结果字段提取；
- 阶段日志。

### Backend Interface

建议接口：

```python
class MediaKitBackend:
    async def execute(self, capability, inputs, parameters): ...
    async def query_task(self, task_id, policy): ...
    async def health_check(self): ...
```

首版实现 `CliBackend`，未来可以加入 `HttpBackend` 而不改变节点 ID 和工作流接口。

## 6.2 CLI Schema 策略

`mediakit-cli` 可以输出能力 JSON Schema。插件应提供开发期 Schema 同步脚本：

```text
scripts/sync_cli_schemas.py
```

职责：

1. 查询支持的 domains；
2. 对目标能力执行 `--schema`；
3. 保存规范化快照到 `schemas/`；
4. 生成参数差异报告；
5. 不在用户运行工作流时动态修改节点定义。

Registry 发布包必须包含经过测试的 Schema 快照和所支持的 CLI 版本范围。

禁止在插件启动时根据任意 CLI 输出无限制地动态生成节点，以避免工作流端口在升级后漂移。

## 6.3 原生媒体类型

主节点必须优先使用：

- `IO.Video.Input/Output`；
- `IO.Audio.Input/Output`；
- `IO.Image.Input/Output`。

禁止把所有媒体统一退化为 `STRING`。

允许提供高级兼容节点：

- 路径 → 原生媒体；
- 原生媒体 → 路径；
- VHS → 原生 VIDEO；
- 原生 VIDEO → VHS。

兼容节点不得改变主节点的原生接口。

## 7. 配置与鉴权

用户使用自己的 MediaKit API Key。

首版支持：

1. `mediakit-cli init` 保存的配置；
2. 环境变量 `MEDIAKIT_API_KEY`。

后续可增加 ComfyUI 设置页面，但必须确保：

- API Key 不进入 workflow JSON；
- API Key 不返回前端；
- 日志脱敏；
- 可删除和重新配置；
- 不由插件作者服务器保存。

## 8. 节点一致性规范

所有 MediaKit 节点必须遵守：

1. 输入媒体端口放在参数前；
2. 输出主媒体放在第一个端口；
3. 云端细节默认隐藏；
4. 高级轮询参数标记为 advanced；
5. 同类参数使用一致命名；
6. 时间单位统一为秒；
7. 分辨率值与官方 API/CLI 保持一致；
8. 布尔参数使用清晰的正向名称；
9. 节点异常必须可读；
10. 不在正常节点输出 task_id 和 URL。

调试信息通过日志和可选 Debug 节点提供。

## 9. 错误体系

统一异常类型：

```text
MediaKitConfigurationError
MediaKitDependencyError
MediaKitInputError
MediaKitAuthenticationError
MediaKitUploadError
MediaKitSubmissionError
MediaKitTaskFailedError
MediaKitTimeoutError
MediaKitDownloadError
MediaKitCompatibilityError
```

错误必须包含：

- 失败阶段；
- 能力名称；
- 可执行的修复建议；
- 脱敏后的官方错误信息。

不得包含：

- API Key；
- 完整预签名 URL；
- 下载 URL 查询参数；
- 无关环境变量。

## 10. 插件目录

```text
comfyui-mediakit-toolkit/
├── __init__.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .comfyignore
├── mediakit_nodes/
│   ├── extension.py
│   ├── nodes/
│   │   ├── diagnostics.py
│   │   ├── video_ai.py
│   │   ├── video_editing.py
│   │   ├── audio.py
│   │   ├── image.py
│   │   └── shared.py
│   ├── backends/
│   │   ├── base.py
│   │   └── cli.py
│   ├── capabilities/
│   │   ├── registry.py
│   │   ├── video.py
│   │   ├── editing.py
│   │   └── audio.py
│   ├── media_bridge/
│   │   ├── video.py
│   │   ├── audio.py
│   │   ├── image.py
│   │   └── temporary.py
│   ├── tasks/
│   │   ├── orchestrator.py
│   │   └── polling.py
│   ├── errors.py
│   ├── redaction.py
│   └── logging.py
├── schemas/
├── scripts/
│   └── sync_cli_schemas.py
├── tests/
├── example_workflows/
└── .github/workflows/
```

## 11. 测试策略

### 公共层测试

- CLI 定位；
- CLI 版本检测；
- JSON 混合输出解析；
- 错误码与 JSON 错误识别；
- 参数转义和 `shell=False`；
- 日志脱敏；
- 临时文件清理；
- 轮询完成、失败和超时；
- 本地和远程结果转换。

### 媒体桥接测试

- 路径型 VIDEO；
- 内存型 VIDEO；
- AUDIO 输入输出；
- IMAGE 临时编码；
- 多媒体输入；
- 成功与异常时的临时文件清理。

### 节点契约测试

每个节点至少验证：

- 节点 ID；
- 分类；
- 输入类型；
- 输出类型；
- 默认值；
- CLI 参数映射；
- 标准成功响应；
- 标准失败响应。

真实付费测试只能由受保护的手动 CI 触发。

## 12. 发布计划

### v0.1.0 基础框架

- Environment Check；
- CLI Backend；
- 媒体桥接；
- 任务编排；
- Video Enhance；
- 单元测试。

### v0.2.0 视频 AI

- Erase Video Subtitle（标准版）；
- Erase Video Subtitle Pro；
- 错误体系；
- 统一日志；
- 示例工作流。

### v0.2.1 生成式画质增强

- Video Enhance Generative；
- 大模型版参数校验；
- 原生 `VIDEO → VIDEO` 示例工作流。

### v0.3.0 视频剪辑

- Trim Video；
- Concat Video；
- Flip Video；
- Adjust Video Speed；
- Add Image To Video；
- Add Subtitle To Video；
- Image To Video。

### v0.4.0 音频与合成

- Trim Audio；
- Concat Audio；
- Extract Audio；
- Mux Audio Video。

### v0.9.0 社区测试版

- Comfy Registry 发布；
- 三平台 CI；
- 完整文档；
- Schema 版本锁定；
- 多个示例工作流。

### v1.0.0 社区稳定版

- 所有首版节点通过验收；
- Manager 可安装和升级；
- 无作者托管后端依赖；
- 用户使用自己的 MediaKit Key；
- 安全、隐私和计费说明齐全。

## 13. 验收标准

### 插件级验收

1. 可从 ComfyUI Manager 安装；
2. 无 CLI 或无 API Key 时 ComfyUI 仍能启动；
3. Environment Check 能给出准确诊断；
4. 节点共享公共后端，不存在复制粘贴式上传/轮询实现；
5. API Key 不进入工作流；
6. 视频不经过插件作者服务器；
7. 三平台测试通过；
8. Registry 安全检查无阻断；
9. README 和示例工作流完整；
10. 插件版本与 Registry/GitHub Release 一致。

### 能力级验收

1. 每个视频节点可以直接接收并输出原生 `VIDEO`；
2. 每个音频节点优先接收并输出原生 `AUDIO`；
3. 图像参数优先使用 `IMAGE`；
4. 本地文件由 CLI 自动处理，不要求公网 URL；
5. 云端任务自动轮询；
6. 下游不需要读取 task_id；
7. 本地轻量任务不产生不必要的云端调用；
8. 临时文件在成功和失败时均清理；
9. 所有错误包含可操作建议；
10. 示例工作流可直接导入。

## 14. Codex 实施提示词

```text
请根据《PRD-ComfyUI-MediaKit-Community-Plugin.md》实现并部署 MediaKit for ComfyUI 社区插件。

这是一个 MediaKit 节点套件，不是单一 enhance 节点。请先实现公共架构，再增加能力节点：
1. 检查目标 ComfyUI 原生 VIDEO/AUDIO/IMAGE API。
2. 检查本机 mediakit-cli 版本、domains 和每个目标工具的 JSON Schema。
3. 实现统一 CliBackend、Media Type Bridge、Task Orchestrator、错误体系和日志脱敏。
4. 首先交付 Environment Check 和 Video Enhance，验证端到端架构。
5. 再按 PRD 版本计划增加视频 AI、剪辑、音频和音视频合成节点。
6. 主节点必须使用原生媒体类型，不得全部退化为 STRING。
7. 禁止 shell=True，禁止运行时安装依赖，禁止把 API Key 写进 workflow。
8. 不建设或依赖作者托管的后端服务。
9. 单元测试不得调用真实付费 API；真实冒烟测试执行前必须说明次数并获得确认。
10. 最终发布到 Comfy Registry，并验证 ComfyUI Manager 可安装、升级和加载。
```

## 15. 参考资料

- MediaKit CLI 用户指南：https://www.volcengine.com/docs/6448/2523671
- MediaKit 功能入口：https://www.volcengine.com/docs/6448
- MediaKit 本地上传：https://www.volcengine.com/docs/6448/2536891
- ComfyUI 自定义节点：https://docs.comfy.org/custom-nodes/overview
- Comfy Registry 发布：https://docs.comfy.org/registry/publishing
- Comfy Registry 规范：https://docs.comfy.org/registry/specifications
- Comfy Registry 安全标准：https://docs.comfy.org/registry/standards
