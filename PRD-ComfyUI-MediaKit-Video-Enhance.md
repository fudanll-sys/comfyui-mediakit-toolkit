# ComfyUI 火山引擎 MediaKit 视频画质增强节点 PRD

## 1. 文档信息

- 项目名称：ComfyUI MediaKit Video Enhance
- 交付形态：可通过 Comfy Registry / ComfyUI Manager 安装的社区自定义节点插件
- 目标平台：本地部署的 ComfyUI
- 云端服务：火山引擎 AI MediaKit
- 调用方式：官方 `mediakit-cli`
- 文档版本：v1.0
- 日期：2026-08-05
- 主要目标：实现与 ComfyUI 内置 Topaz Video Enhance 类似的使用体验

### 1.1 最终产品边界

本项目止于“社区插件可用”阶段：

- 插件代码公开托管在 GitHub；
- 插件发布至 Comfy Registry，并可被 ComfyUI Manager 发现、安装和升级；
- 用户使用自己的火山引擎 AI MediaKit 账号及 API Key；
- 用户视频由其本地 ComfyUI 直接提交至火山引擎，不经过插件作者的服务器；
- 插件作者不提供账户、额度、计费、对象存储、任务中转或 SaaS 服务；
- 插件不得依赖作者持续运行的后端服务才能工作。

明确不建设：

- 自有云服务网关；
- 用户注册与登录系统；
- 自有 API Key；
- 套餐、充值、计费和订单系统；
- 用户视频中转或持久化存储；
- MediaKit 成本代付或转售；
- 多租户任务队列和管理后台。

## 2. 项目背景

用户希望在本地 ComfyUI 工作流中调用火山引擎 AI MediaKit 的视频画质增强能力。节点必须支持来自 ComfyUI 工作流的原生视频输入，自动完成本地视频上传、云端任务提交、任务轮询和结果下载，并将处理结果继续作为 ComfyUI 原生 `VIDEO` 输出。

最终用户不应接触以下中间概念：

- 公网视频 URL 准备；
- MediaKit 上传地址申请；
- `mediakit://` 文件标识；
- `task_id`；
- 任务轮询；
- 临时结果 URL；
- 手动下载结果。

期望工作流：

```text
Load Video
    ↓ VIDEO
MediaKit Video Enhance
    ↓ VIDEO
Save Video / Preview Video / 其他视频节点
```

## 3. 产品目标

### 3.1 核心目标

1. 提供一个输入、输出均为 ComfyUI 原生 `VIDEO` 类型的画质增强节点。
2. 接受本地上传的视频以及其他节点生成的视频。
3. 使用官方 `mediakit-cli` 自动处理本地文件上传和云端任务提交。
4. 在节点内部自动等待任务完成。
5. 将增强结果转换为 ComfyUI 原生 `VIDEO` 对象。
6. 允许结果直接连接 ComfyUI 原生 `Save Video` 节点。
7. 对安装、鉴权、CLI、网络和云端任务错误提供可理解的报错。

### 3.2 非目标

首个版本不实现：

- 自建 MediaKit HTTP API 客户端；
- 自定义浏览器视频上传按钮；
- 视频逐帧解码和重新编码；
- 批量并发处理多个视频；
- MediaKit 大模型版或极速版画质增强；
- 字幕擦除、视频裁剪等其他 MediaKit 工具；
- 对 VideoHelperSuite 所有内部类型的原生兼容；
- API Key 输入框；
- 任务提交后脱离 ComfyUI 队列异步运行。
- 插件作者托管的商业云服务；
- 插件作者代管用户的 MediaKit API Key；
- 插件作者代付 MediaKit 费用。

## 4. 用户故事

### 4.1 本地视频增强

作为 ComfyUI 用户，我希望使用原生 `Load Video` 选择本地 MP4 文件，将其连接至 MediaKit 节点，选择增强版本、场景和目标分辨率，运行后直接得到增强视频。

### 4.2 上游生成视频增强

作为视频生成工作流用户，我希望将上游节点产生的原生 `VIDEO` 直接连接到 MediaKit 节点，不需要先手动保存和重新上传。

### 4.3 下游继续处理

作为工作流编排用户，我希望 MediaKit 输出能直接连接原生 `Save Video`、预览节点或其他接收 `VIDEO` 的节点。

### 4.4 错误定位

作为部署者，我希望节点能够明确区分 CLI 未安装、API Key 未配置、输入格式不支持、上传失败、任务失败、轮询超时和结果下载失败。

## 5. 功能需求

## 5.1 节点基本信息

- 节点 ID：`MediaKitVideoEnhance`
- 显示名称：`MediaKit Video Enhance`
- 中文显示名称可选：`MediaKit 视频画质增强`
- 分类：`video/MediaKit`
- 输入类型：ComfyUI 原生 `VIDEO`
- 输出类型：ComfyUI 原生 `VIDEO`
- 节点实现 API：优先使用 ComfyUI 新版 V3 Schema API

建议定义：

```python
IO.Video.Input("video")
IO.Video.Output("video")
```

## 5.2 输入参数

### video

- 类型：`VIDEO`
- 必填：是
- 描述：待增强视频
- 支持来源：
  - ComfyUI 原生 `Load Video`；
  - 其他输出原生 `VIDEO` 的节点；
  - 内存中的视频对象；
  - 文件路径型视频对象。

### tool_version

- 类型：下拉选择
- 必填：是
- 默认值：`standard`
- 可选值：
  - `standard`：标准版；
  - `professional`：专业版。

### scene

- 类型：下拉选择
- 默认值：`common`
- 可选值：
  - `common`；
  - `ugc`；
  - `short_series`；
  - `aigc`；
  - `old_film`。
- 规则：仅当 `tool_version=standard` 时传递给 CLI。
- 当选择专业版时，界面可以继续显示该参数，但执行时必须忽略。

### resolution

- 类型：下拉选择
- 默认值：`1080p`
- 可选值：
  - `保持原分辨率`；
  - `240p`；
  - `360p`；
  - `480p`；
  - `540p`；
  - `720p`；
  - `1080p`；
  - `2k`；
  - `4k`。
- 规则：选择“保持原分辨率”时，不向 CLI 传递 `--resolution`。

### bitrate_level

- 类型：下拉选择
- 默认值：`medium`
- 可选值：`low`、`medium`、`high`。

### fps

- 类型：浮点数
- 默认值：`0`，表示保持源视频帧率；
- 有效目标值范围：大于 `0` 且不超过 `120`。

### poll_interval_seconds

- 类型：整数
- 默认值：5
- 最小值：2
- 最大值：60
- 建议标记为高级参数。

### max_poll_attempts

- 类型：整数
- 默认值：720
- 最小值：1
- 最大值：5000
- `0` 是否表示无限等待，应以当前 CLI Schema 为准；首版建议不允许无限值。
- 建议标记为高级参数。

## 5.3 输出

### video

- 类型：ComfyUI 原生 `VIDEO`
- 描述：MediaKit 增强完成后下载到本地的视频对象
- 必须能够直接连接原生 `Save Video`。

首版不在主节点暴露 `task_id` 和结果 URL，保持与 Topaz 相似的简洁体验。调试信息写入日志。

可选增强：后续增加 `MediaKit Video Enhance (Debug)` 节点，额外输出任务 JSON。

## 6. 用户体验要求

1. 节点表面只显示视频增强相关参数。
2. 不显示 API Key 输入框。
3. 不显示上传按钮。
4. 不要求用户输入公网 URL。
5. 执行期间节点保持运行状态，直到任务完成或报错。
6. ComfyUI 队列在该节点完成前不得继续执行依赖其输出的下游节点。
7. 运行成功后，下游获得原生视频对象。
8. 错误必须以 ComfyUI 节点异常形式显示，不允许仅写终端日志后返回空结果。

理想状态文案：

```text
Preparing local video
Submitting MediaKit task
Waiting for MediaKit
Downloading enhanced video
Completed
```

如果无法从 CLI 获得连续进度，首版允许只显示 ComfyUI 的运行状态与阶段日志。

## 7. 技术方案

## 7.1 总体架构

```text
ComfyUI VIDEO
    │
    ├─ 文件路径 → 直接使用
    │
    └─ BytesIO/内存流 → 写入安全临时 MP4
                    │
                    ▼
mediakit-cli video enhance-video --cloud
                    │
                    ▼
              返回 task_id
                    │
                    ▼
mediakit-cli shared query-task --poll-complete
                    │
                    ▼
              返回 video_url
                    │
                    ▼
download_url_to_video_output(video_url)
                    │
                    ▼
             ComfyUI VIDEO
```

## 7.2 ComfyUI 视频读取

通过原生视频对象获取源：

```python
stream_source = video.get_stream_source()
```

需要处理两种情况：

1. 返回文件系统路径：直接传给 CLI；
2. 返回 `BytesIO` 或其他内存流：写入临时 `.mp4` 文件后传给 CLI。

禁止将整个大型视频额外复制到 Python 字节数组。内存流落盘必须使用分块复制：

```python
shutil.copyfileobj(stream_source, temp_file)
```

## 7.3 CLI 调用

提交命令基础格式：

```bash
mediakit-cli video enhance-video \
  --cloud \
  --video-url /absolute/path/input.mp4 \
  --tool-version standard \
  --scene aigc \
  --resolution 1080p
```

轮询命令：

```bash
mediakit-cli shared query-task \
  --task-id TASK_ID \
  --poll-complete \
  --poll-interval-seconds 5 \
  --max-poll-attempts 720
```

调用要求：

- 必须使用参数数组调用 `subprocess`；
- 禁止 `shell=True`；
- 禁止字符串拼接后交给 Shell；
- 使用 `shutil.which("mediakit-cli")` 定位程序；
- 必须设置整体超时；
- 捕获 stdout 和 stderr；
- 不得只依赖退出码判断成功；
- 需要同时检查输出 JSON 中的 `error` 和 `status=failed`。

CLI 可能在 JSON 前后输出提示信息。应实现健壮的 JSON 对象提取函数，从输出中查找最后一个合法 JSON 对象。

## 7.4 异步执行

节点 `execute` 应为异步函数。阻塞式 CLI 调用通过线程执行，避免阻塞 ComfyUI 事件循环：

```python
result = await asyncio.to_thread(run_cli, arguments)
```

不要求任务从 ComfyUI 队列中脱离。用户取消 ComfyUI 执行时，首版允许后台 CLI 子进程继续到超时；第二版应支持主动终止子进程。

## 7.5 视频输出

获取最终 `video_url` 后，优先复用 ComfyUI 当前版本提供的视频下载转换工具：

```python
from comfy_api_nodes.util import download_url_to_video_output

output_video = await download_url_to_video_output(video_url)
return IO.NodeOutput(output_video)
```

如果目标 ComfyUI 版本未暴露该工具，应实现兼容层，但最终仍必须构造原生 `VIDEO` 输出，不能退化成普通字符串路径。

## 7.6 临时文件

- 使用 `tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")`；
- 临时文件必须在 `finally` 中删除；
- 删除前验证路径确实为本节点创建的临时文件；
- 不得删除上游提供的原始视频；
- 任务失败、超时或用户中断时也要清理临时文件。

## 7.7 鉴权

支持以下方式，优先级由 `mediakit-cli` 官方行为决定：

1. `mediakit-cli init` 保存的配置；
2. 环境变量 `MEDIAKIT_API_KEY`。

禁止：

- 将 API Key 放入节点参数；
- 将 API Key 写入 workflow JSON；
- 在异常、stdout、日志中打印 API Key；
- 将 API Key 固化在插件源码。

## 8. 兼容性

## 8.1 必须支持

- macOS arm64 / x86_64；
- Linux arm64 / x86_64；
- Windows x86_64；
- Node.js 18 及以上；
- 当前稳定版 ComfyUI 原生 `VIDEO` API；
- MP4 输入。

## 8.2 尽量支持

- MOV、MKV 等由上游原生 `VIDEO` 接受的格式；
- 内存视频流；
- ComfyUI Desktop；
- Python 虚拟环境和 portable 环境。

如果 MediaKit 或 CLI 实际只接受特定容器，节点应在执行前明确报错，不应静默转码。

## 8.3 VideoHelperSuite

`VHS_FILENAMES` 与 ComfyUI 原生 `VIDEO` 不是同一类型。首版不要求主节点直接接受 `VHS_FILENAMES`。

可选后续节点：

- `VHS Filenames → Native Video`；
- `Native Video → VHS Filenames`。

不得为了兼容 VHS 而把主节点输入、输出退化为 `STRING`。

## 9. 错误处理

必须覆盖以下错误：

### CLI 未安装

提示：

```text
找不到 mediakit-cli。请安装 @volcengine/mediakit-cli，并确认启动 ComfyUI 的环境可以访问该命令。
```

### API Key 未配置

识别 CLI 返回的认证失败信息，并提示执行：

```bash
mediakit-cli init --api-key <API_KEY> --yes
```

或设置 `MEDIAKIT_API_KEY`。

### 输入视频不可用

包括：

- 视频对象为空；
- 流无法读取；
- 本地路径不存在；
- 容器格式不支持；
- 临时文件写入失败。

### CLI 提交失败

异常中应包含：

- 命令阶段；
- CLI 返回的错误消息；
- 不包含密钥的 stdout/stderr 尾部；
- 不打印完整预签名上传 URL。

### 任务失败

异常中应显示 MediaKit 错误类型、错误码和可读消息。

### 轮询超时

提示任务可能仍在云端运行，并在日志中保留 `task_id`，便于人工查询。

### 下载失败

区分：

- URL 过期；
- HTTP 错误；
- 磁盘空间不足；
- 视频输出构造失败。

## 10. 安全要求

1. 所有 CLI 调用必须使用 `shell=False`。
2. 不执行用户构造的任意命令字符串。
3. API Key 不进入工作流。
4. 日志输出需要对 URL 查询参数进行脱敏。
5. 临时文件使用系统临时目录和随机名称。
6. 不覆盖用户原文件。
7. 不递归删除任何目录。
8. 不信任 CLI 输出中的文件路径；如果后续使用路径，必须验证存在性和范围。
9. 下载和 CLI 调用必须设置超时。
10. 限制单节点一次只处理一个视频。

## 11. 性能要求

1. 不将文件路径型视频完整载入内存。
2. 内存流落盘采用流式复制。
3. 云端结果下载使用 ComfyUI 官方视频工具或流式下载。
4. 本地准备阶段不应重新编码视频。
5. 插件不得占用 GPU。
6. 对长视频的本地额外磁盘占用不超过输入临时副本加输出副本。

## 12. 插件结构

推荐目录：

```text
ComfyUI/custom_nodes/comfyui-mediakit/
├── __init__.py
├── nodes.py
├── cli.py
├── video_io.py
├── errors.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── LICENSE
├── tests/
│   ├── test_cli_json.py
│   ├── test_cli_command.py
│   ├── test_video_source.py
│   └── test_error_redaction.py
└── example_workflows/
    └── mediakit_video_enhance.json
```

职责划分：

- `nodes.py`：ComfyUI Schema 和执行编排；
- `cli.py`：CLI 定位、命令构建、执行与 JSON 解析；
- `video_io.py`：视频源路径解析、内存流落盘和输出转换；
- `errors.py`：错误分类、用户提示和日志脱敏；
- `tests/`：不调用真实付费接口的单元测试。

## 13. 依赖

Python 侧尽量只依赖 ComfyUI 自带模块和标准库。

外部运行依赖：

- `mediakit-cli`；
- Node.js 18+（仅 npm 安装 CLI 时需要）；
- 有效 MediaKit API Key；
- 网络访问火山引擎 MediaKit。

CLI 安装：

```bash
npx @volcengine/mediakit-cli install -y
```

初始化：

```bash
mediakit-cli init \
  --mode cloud-first \
  --api-key <YOUR_API_KEY> \
  --credential-store config \
  --yes
```

健康检查：

```bash
mediakit-cli doctor
```

## 14. 日志要求

正常执行至少记录：

```text
[MediaKit] Preparing video source
[MediaKit] Submitting enhancement task
[MediaKit] Task submitted: <task_id>
[MediaKit] Waiting for task completion
[MediaKit] Downloading enhanced video
[MediaKit] Completed
```

不得记录：

- API Key；
- 完整预签名 URL；
- 带鉴权参数的下载 URL；
- 用户无关的环境变量。

URL 日志只保留协议、主机和路径，移除 query string。

## 15. 测试要求

## 15.1 单元测试

必须覆盖：

1. 从纯 JSON CLI 输出解析对象；
2. 从提示文本加 JSON 的混合输出解析最后一个对象；
3. CLI 返回多个 JSON 时选取最终结果；
4. CLI 退出码非零；
5. CLI 退出码为零但包含 `error`；
6. `status=failed`；
7. `task_id` 缺失；
8. `video_url` 缺失；
9. 标准版命令包含 `--scene`；
10. 专业版命令不包含 `--scene`；
11. 保持原分辨率时不包含 `--resolution`；
12. 文件路径源不产生临时副本；
13. 内存流源创建并清理临时文件；
14. 异常路径也清理临时文件；
15. 日志脱敏不保留 URL 查询参数。

单元测试必须 mock `subprocess`，不得调用真实 MediaKit 服务。

## 15.2 集成测试

在测试账号下完成：

1. 原生 `Load Video → MediaKit → Save Video`；
2. 内存视频输出节点 → MediaKit；
3. 标准版 + AIGC 场景 + 1080p；
4. 专业版 + 1080p；
5. 无 API Key；
6. 无 CLI；
7. 无网络；
8. 不支持格式；
9. 人工设置较小轮询次数触发超时；
10. ComfyUI 重启后节点仍可加载。

## 15.3 UI 验收

- 节点能在搜索中找到；
- 输入端口显示为 `VIDEO`；
- 输出端口显示为 `VIDEO`；
- 能与原生 Load/Save Video 连线；
- 参数默认值正确；
- 高级参数不会干扰普通用户；
- 失败时节点变红并显示可读错误。

## 16. 验收标准

以下条件全部满足才算完成：

1. 插件可以在目标 ComfyUI 启动时无错误加载。
2. 节点输入和输出均为原生 `VIDEO`。
3. 本地 MP4 可以通过原生 Load Video 进入节点。
4. 用户不需要准备公网 URL。
5. 用户不需要手动操作 task_id。
6. CLI 自动完成本地视频上传。
7. 节点自动等待任务完成。
8. 增强结果能直接连接并通过原生 Save Video 保存。
9. 标准版、专业版和分辨率参数按预期传递。
10. API Key 不出现在工作流 JSON。
11. 临时文件在成功与失败时均被清理。
12. CLI 未安装和鉴权失败时有明确提示。
13. 单元测试全部通过。
14. 提供可导入的示例工作流。
15. README 包含安装、配置、使用、排错和卸载说明。

## 17. 部署流程

### 17.1 部署前检查

Codex 应先确认：

```bash
python --version
node --version
mediakit-cli version
mediakit-cli doctor
```

并确认 ComfyUI 支持：

```python
from comfy_api.latest import IO, ComfyExtension, Input
```

### 17.2 安装插件

将插件放入：

```text
ComfyUI/custom_nodes/comfyui-mediakit
```

不得修改 ComfyUI 核心源码。

### 17.3 配置 CLI

推荐使用：

```bash
mediakit-cli init \
  --mode cloud-first \
  --api-key <YOUR_API_KEY> \
  --credential-store config \
  --yes
```

对于服务方式启动的 ComfyUI，可使用 `MEDIAKIT_API_KEY` 环境变量，但不得把 Key 写入仓库。

### 17.4 重启与验证

1. 重启 ComfyUI；
2. 检查启动日志无 import error；
3. 搜索 `MediaKit Video Enhance`；
4. 导入示例工作流；
5. 使用短 MP4 完成一次标准版 1080p 测试；
6. 确认结果可由 Save Video 保存；
7. 检查系统临时目录无残留测试视频。

## 18. README 必须包含

1. 功能说明；
2. ComfyUI 版本要求；
3. MediaKit CLI 安装；
4. API Key 初始化；
5. 示例工作流截图；
6. 参数解释；
7. 计费提醒；
8. 常见错误；
9. Windows/macOS/Linux PATH 排错；
10. 隐私说明：视频会上传至火山引擎云端处理；
11. 卸载方法。

## 19. 实现注意事项

1. `mediakit-cli` 的部分错误可能不会正确映射到进程退出码，因此必须解析 JSON 错误字段。
2. CLI 在无 API Key 时可能按其配置降级，因此提交增强时必须显式使用 `--cloud`。
3. CLI 命令参数可能随版本变化。实现前应执行：

```bash
mediakit-cli video enhance-video --schema
mediakit-cli shared query-task --help
```

并以本机安装版本输出为准。
4. 原生 `VIDEO` API 属于较新的 ComfyUI 能力；实现时必须基于目标安装版本验证具体导入路径和视频输出构造方式。
5. 不要复用第三方节点私有类型作为主接口。
6. 不要把输入视频转成帧批次，这会显著增加内存占用并破坏音频处理。
7. MediaKit 是付费云端服务，真实集成测试必须使用短视频并避免重复提交。

## 20. Codex 实施任务清单

Codex 应按以下顺序实施：

1. 定位目标 ComfyUI 安装目录和 Python 环境。
2. 检查仓库状态及本地开发规范文件。
3. 检查 ComfyUI 原生 `VIDEO` API 的实际版本。
4. 检查 `mediakit-cli` 是否安装并读取本机 Schema。
5. 创建插件目录和最小可加载节点。
6. 实现原生 `VIDEO → VIDEO` 透传测试节点，确认类型兼容。
7. 实现视频源路径/内存流适配。
8. 实现安全 CLI 调用与 JSON 解析。
9. 实现提交任务和自动轮询。
10. 实现结果转换为原生 `VIDEO`。
11. 实现错误分类和日志脱敏。
12. 编写单元测试并运行。
13. 编写示例工作流。
14. 重启 ComfyUI 验证节点加载。
15. 在获得测试 API Key 和计费授权后执行一次真实短视频测试。
16. 完成 README 和部署说明。
17. 汇总修改文件、测试结果、已知限制和后续建议。

## 21. 交给 Codex 的执行提示词

```text
请根据仓库中的《PRD-ComfyUI-MediaKit-Video-Enhance.md》完整实现并部署 ComfyUI MediaKit Video Enhance 插件。

要求：
1. 先检查目标 ComfyUI 版本、原生 VIDEO API、项目规范和 mediakit-cli 本机 Schema，再开始编码。
2. 实现原生 VIDEO 输入和 VIDEO 输出，使用体验应与 ComfyUI 内置 Topaz Video Enhance 类似。
3. 使用官方 mediakit-cli 处理本地文件上传、任务提交和轮询，不要重新实现 MediaKit 上传 API。
4. 禁止 shell=True，禁止把 API Key 写进代码或 workflow。
5. 对文件路径视频和内存视频流都要支持，并保证临时文件清理。
6. 先完成 mock 单元测试；真实云端测试会产生费用，执行前说明测试视频和预计调用次数，并等待我确认。
7. 不修改 ComfyUI 核心源码。
8. 实现后重启并验证节点能被加载，提供示例工作流、README、测试结果和部署位置。
9. 如果目标 ComfyUI 的 VIDEO API 与 PRD 示例不同，以本机版本的官方实现为准，但必须保持原生 VIDEO → VIDEO 的产品接口。
10. 遇到阻塞时先进行安全的本地检查，不要擅自降低为 STRING 或 VHS_FILENAMES 接口。
```

## 22. 参考资料

- ComfyUI 自定义节点概览：https://docs.comfy.org/custom-nodes/overview
- ComfyUI Topaz Video Enhance：https://docs.comfy.org/built-in-nodes/TopazVideoEnhance
- MediaKit CLI 用户指南：https://www.volcengine.com/docs/6448/2523671
- MediaKit 标准版/专业版增强 API：https://www.volcengine.com/docs/6448/2279230
- MediaKit 本地媒体上传：https://www.volcengine.com/docs/6448/2536891

## 23. 社区插件发布要求

### 23.1 发布渠道

必须同时具备：

1. 独立、公开的 GitHub 仓库；
2. Comfy Registry Publisher 身份；
3. Registry 中全局唯一的节点包名称；
4. 可通过 ComfyUI Manager 搜索和安装的正式版本；
5. 可通过 `comfy node install <node-id>` 安装；
6. 使用语义化版本号发布，例如 `0.1.0`、`0.2.0`、`1.0.0`。

### 23.2 社区版安装体验

目标安装流程：

```text
ComfyUI Manager 搜索 MediaKit Video Enhance
→ Install
→ 重启 ComfyUI
→ 运行 MediaKit Environment Check
→ 按提示配置自己的 MediaKit API Key
→ 导入示例工作流并使用
```

如果首版继续依赖 `mediakit-cli`，插件不得在运行时静默安装 Node.js、npm 包或外部二进制。必须提供明确的环境检查和跨平台安装说明。CLI 缺失时插件仍应成功加载，只有执行相关节点时才显示可操作的错误提示。

### 23.3 社区版节点清单

正式发布至少包含：

1. `MediaKit Video Enhance`：原生 `VIDEO → VIDEO` 画质增强节点；
2. `MediaKit Environment Check`：只读检查 CLI、版本、鉴权、网络及 ComfyUI 视频 API；
3. 示例工作流：`Load Video → MediaKit Video Enhance → Save Video`。

环境检查节点不得输出或记录 API Key 原文。

### 23.4 Registry 元数据

仓库必须提供有效的 `pyproject.toml`，至少包含：

```toml
[project]
name = "mediakit-video"
version = "0.1.0"
description = "Volcengine AI MediaKit video enhancement nodes for ComfyUI"
requires-python = ">=3.10"
license = { file = "LICENSE" }
dependencies = []

[project.urls]
Repository = "https://github.com/<owner>/<repository>"
Documentation = "https://github.com/<owner>/<repository>#readme"
Issues = "https://github.com/<owner>/<repository>/issues"

[tool.comfy]
PublisherId = "<publisher-id>"
DisplayName = "MediaKit Video Enhance"
Icon = "https://raw.githubusercontent.com/<owner>/<repository>/main/assets/icon.png"
Banner = "https://raw.githubusercontent.com/<owner>/<repository>/main/assets/banner.png"
requires-comfyui = ">=<verified-version>"
```

实现时必须将占位符替换为真实值，并通过 `comfy node init` 或 Registry 校验确认格式。

### 23.5 社区文档

README 除原有要求外，还必须在顶部明确写明：

```text
本插件是非官方社区连接器。使用者需要自行开通火山引擎
AI MediaKit、配置自己的 API Key，并自行承担云端调用费用。
视频将从本地 ComfyUI 直接上传至火山引擎处理，不会经过
插件作者的服务器。
```

README 必须提供：

- ComfyUI Manager 安装方式；
- 手动 Git 安装方式；
- `comfy node install` 安装方式；
- macOS、Windows、Linux 的 CLI 配置方法；
- API Key 安全说明；
- 计费和隐私提示；
- 示例工作流下载入口；
- Issue 模板和排错信息收集方法；
- 升级、版本锁定和卸载说明。

### 23.6 CI/CD

GitHub Actions 至少包含：

1. Python 单元测试；
2. Linux、Windows、macOS 基础兼容测试；
3. 插件导入及节点注册测试；
4. `pyproject.toml` 和版本号检查；
5. 手动触发的 Registry 发布工作流。

真实 MediaKit 测试不得在普通 Pull Request 中自动执行，避免泄露密钥和产生不可控费用。真实测试只能由受保护的手动工作流触发，并限制输入视频与调用次数。

### 23.7 版本策略

- `0.1.0`：内部技术预览，可完成单次短视频增强；
- `0.2.0`：补齐三平台测试、环境诊断和文档；
- `0.9.0`：Registry 公开测试版；
- `1.0.0`：社区稳定版。

破坏工作流兼容性的节点 ID、端口类型或参数名称修改必须提升主版本号。已经发布的 Registry 版本不得覆盖修改。

### 23.8 社区发布验收标准

除第 16 节验收条件外，公开发布前还必须满足：

1. 新用户能从 ComfyUI Manager 搜索并安装插件；
2. 安装后即使缺少 CLI 或 API Key，ComfyUI 仍可正常启动；
3. Environment Check 能给出准确、可操作的诊断；
4. 用户使用自己的 MediaKit API Key 完成一次短 MP4 增强；
5. 用户视频不经过插件作者控制的服务器；
6. 工作流中不包含 API Key；
7. GitHub Release、Registry 版本和 `pyproject.toml` 版本一致；
8. README、许可证、隐私和计费说明齐全；
9. 三平台 CI 通过；
10. Registry 安全扫描不存在阻断问题；
11. 示例工作流可以直接导入且不存在缺失节点；
12. GitHub Issues 可用于公开提交问题和版本反馈。
