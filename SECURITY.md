# Registry 发布与安全自查

本文对照 Comfy Registry 的
[质量与安全标准](https://docs.comfy.org/registry/standards) 和
[pyproject.toml 规范](https://docs.comfy.org/registry/specifications)，
记录本插件发布前的合规检查。Registry 的具体审核/标记原因不通过公开 API 返回；
如版本仍为 `NodeVersionStatusFlagged`，需要在 Comfy Registry 网站的
Publisher 后台或官方支持渠道查询具体原因。

## 安全红线

| 检查项 | 结论 | 证据 |
| --- | --- | --- |
| `eval` / `exec` 任意代码执行 | 不使用 | 运行时代码仅在 `redaction.py`、`sync_cli_schemas.py` 中使用 `re.compile`，不存在 `eval`、`exec`、`compile` 动态执行。 |
| 运行时通过 subprocess 安装依赖 | 不使用 | 代码只通过 `subprocess.run(..., shell=False)` 以参数数组调用用户自行安装的官方 `mediakit-cli`；不会在节点执行中运行 `pip install` 或其他安装命令。 |
| 代码混淆 | 不使用 | 全部源码随包发布，无打包压缩、加密或混淆产物。 |
| 作者托管服务/中转 | 不使用 | 媒体由本地 ComfyUI 直接提交到用户自己的火山引擎 MediaKit 账号；插件不提供服务器、对象存储、账号或代付能力。 |
| API Key 泄露 | 已规避 | Key 只来自 `mediakit-cli init` 配置或 `MEDIAKIT_API_KEY` 环境变量，不写入工作流 JSON；日志通过 `mediakit_toolkit/redaction.py` 脱敏。 |
| 签名 URL 泄露 | 已规避 | 诊断日志会移除 HTTP/HTTPS URL 的查询参数。 |
| 运行时第三方依赖 | 明确 | 包自身 `dependencies=[]`；ComfyUI 基础能力由宿主提供，PyAV 等可选媒体依赖沿用 ComfyUI 环境，缺失时原生媒体测试明确跳过或返回可读错误。 |

## 元数据与打包

- `[project].name`、`version`、`license`、`repository`、`requires-python` 满足规范；
  版本号使用三段式语义版本。
- `[tool.comfy].PublisherId` 为 `fudanll`，并提供 `DisplayName`、`Icon` 与
  `requires-comfyui`。
- `.comfyignore` 排除 `.git`、CI、测试、PRD、缓存和 Python 编译产物；发布包只保留
  运行所需源码、Schema、示例和文档。
- LICENSE 为 MIT，README 中英文均声明非官方社区集成、计费方式、隐私边界和
  安全注意事项。

## 发布后回查

发布新版本后检查：

```bash
curl -s https://api.comfy.org/nodes/mediakit-toolkit \
  | python -m json.tool
curl -s https://api.comfy.org/nodes/mediakit-toolkit/versions/<version> \
  | python -m json.tool
```

- 节点应保持 `NodeStatusActive`。
- 新版本应进入正常可安装状态；若仍为 `NodeVersionStatusFlagged`，公开 API
  不提供原因，需要通过 Registry Publisher 后台或官方支持渠道处理，不能在
  对外材料中宣称“已审核通过”。

## 0.5.x 版本 Flagged 排查记录

- 现象：节点本身为 `NodeStatusActive`，但 0.5.0/0.5.1/0.5.2 版本均为
  `NodeVersionStatusFlagged`，0.5.3 发布后进入 `NodeVersionStatusPending`；
  公开 API 的 `status_reason` 始终为空。
- 关键线索：`GET /comfy-nodes?node_id=mediakit-toolkit` 的 `total=0`，即 Registry
  静态分析没有从发布包提取到任何节点。对比正常上架的 V1 包（如
  comfyui-videohelpersuite，`total=40`），其根 `__init__.py` 直接导出
  `NODE_CLASS_MAPPINGS`；本包只使用 V3 的 `comfy_entrypoint`，Registry 的静态
  索引器目前无法据此提取节点，这是最可能的 Flagged 根因。运行时 ComfyUI 加载器
  （nodes.py）已支持 V3，因此本地/Manager 安装后可正常加载，差异仅在 Registry
  的离线提取链路。
- 已在仓库侧修复的审核项：补充方形图标 `[tool.comfy].Icon`、`SECURITY.md`
  安全自查（无 eval/exec、无运行时 pip、无混淆、无维护者中转、Key/URL 脱敏）。
- 仍需人工处理：登录
  [Registry Publisher 后台](https://registry.comfy.org/publishers/fudanll/nodes/mediakit-toolkit)
  查看具体 `status_reason`，或通过官方 Discord/支持渠道确认是否因 V3 静态提取
  缺失而 Flagged；若确认，再决定是否补充静态 `node_list.json` / V1 兼容映射
  （需评估与现有 V3 入口并存的加载顺序，避免双重注册）。
- 在状态转为 `NodeVersionStatusActive` 前，对外只能描述为“已上传、待审核”，
  不得宣称“Registry 审核通过/正式上架”。
