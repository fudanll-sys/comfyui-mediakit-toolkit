# P1 本轮修复与验证记录

## 已实际修复

- 多输入改为真实 ComfyUI V3 Autogrow，执行参数为编号插槽字典，按编号排序。
- 原生 AUDIO 字典通过 PCM16 WAV 物化；使用 PyAV 解码为 [1,C,T] waveform，移除 VIDEO 回退。
- IMAGE Tensor 输入与完整动画帧输出；动图额外保留逐帧毫秒时长 JSON 和原 GIF/WebP 地址。
- 本地 VIDEO 结果直接构造真实 VideoFromFile，不将 file:// 传给 HTTP 下载器。
- 多输出补齐唯一 id；清理流物化失败时留下的临时文件。
- 字幕空数组、错误对象类型、非数值/NaN/布尔时间、反向时间范围会抛出输入错误。
- 中英文说明纠正 Volume / Motion / Filter / Flip 参数、音频输入类型、未发布状态；拼接示例改为真实动态插槽名和字符串 widget。
- schema 同步现在实际保存完整机器合同；失败不再跳过，离线检查核对参数合同和指纹。刷新 CLI 0.2.2 的 74 个工具快照。

## 实际运行证据

- ComfyUI 源码基准：ab08f7b2caa6d4007ecde3762116c6193613f43b。
- `scripts/verify_comfy_contracts.py`：32 个节点真实 schema 校验、4 个 Autogrow 映射、3 个 P1 示例的插件输入/widgets与连线检查通过。实际构造 VideoFromFile 并调用 get_stream_source；该视频夹具不作内容解码。
- `scripts/verify_editing_contracts.py`：20 个 editing builder、77 组默认/枚举变体通过完整 JSON Schema 检查。此项是合同验证，不调用云端。
- 全量 unittest：169 项通过，无跳过；独立验证环境具有 torch/numpy/Pillow/PyAV。
- 隐去 CLI 的 PATH 下：同一169项通过，无跳过。
- 真实媒体夹具：双声道 WAV 数据和采样率往返、批次拒绝、PNG tensor往返、双帧GIF颜色和100/300毫秒帧时长检查通过。
- `sync_cli_schemas.py --offline`通过；`--check --json`显示 CLI 0.2.2 无漂移。
- `scripts/verify_comfy_runtime.py` 另行验证真实前端导入和安全本地队列，结果保存为 `runtime-verification.json`；CLI参数/静态脚本中的“未验证前端”仅指它们各自的覆盖范围，实际前端验证以本记录和运行结果为准。
- compileall、git diff --check通过。

## 不得宣称已通过的范围

- 已实际启动隔离 ComfyUI 0.43.0 / 前端 1.57.6，插件32个节点注册成功；三个P1示例通过独立Chrome的真实文件导入入口，连线和保存参数正确，页面无未捕获JS错误。
- `scripts/verify_comfy_runtime.py`：本地只读诊断、原生视频保存、错误动画时间和非法字幕JSON四项实际队列验证通过；后两项是预期输入错误，不代表云端处理成功。
- 自建1秒、64×64、10fps视频经真实队列保存后，用PyAV独立解码核对10帧、64×64通过。
- 仍未执行有效P1云端编辑图；三个示例目前验证的是前端导入和待提交参数，不是完整视频处理链。
- 未执行真实 MediaKit 云端任务；未验证服务端合成、云端输出结构/URL、账户鉴权与实际计费。
- 源码基准是当前下载的 ComfyUI，不代表每个旧版 ComfyUI 兼容；Autogrow需要近期版本。
- 音频物化当前明确只接受单批次 mono/stereo，PCM16有量化误差；不支持多批次或多声道静默截断。
- 动画帧 Tensor 本身不含播放时序；原动画需使用原资源URL，URL有效期由服务端决定。
- Python无媒体依赖时，四个原生媒体测试会显示跳过，不能算完整验收。
- 本记录对应 P1 开发代码提交，不创建正式发布版本、tag、Release 或 Registry；已发布版本仍为 0.4.0。

## 复现命令

在具有 ComfyUI 依赖的 Python 环境里：

```bash
python scripts/verify_comfy_contracts.py --comfy-root /absolute/path/to/ComfyUI
python scripts/verify_editing_contracts.py
python -m unittest discover -s tests
python scripts/sync_cli_schemas.py --offline
python scripts/sync_cli_schemas.py --check --json
```

请在本仓库根目录运行复现命令；不要依赖开发者本机的临时工作目录。
