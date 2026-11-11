# 首发推广手册

## 一、先确认闸门，再花钱花时间

推广动作分两道闸门，闸门没开就投放，只会把“装了不能用”的口碑一次性消耗掉。

| 闸门 | 通过标准 | 当前状态 | 不通过时的对外口径 |
| --- | --- | --- | --- |
| G0 可被搜到 | `GET /comfy-nodes?node_id=mediakit-toolkit` 返回 `total > 0` | 实测 `total=0`，Manager 搜不到 | “已上传，Registry 索引处理中” |
| G1 可被装上 | 最新版本为 `NodeVersionStatusActive` | 0.5.x 为 Flagged / Pending | “已上传，待审核” |

**G0/G1 未通过时只能做一件事**：把素材备齐、把种子用户单独邀请（发 Git 安装命令，不发 Registry 链接）。不投公域流量，不买量，不在社区发“已上架”。

## 二、渠道优先级与每个渠道的用法

按“每单位时间能带来多少真正跑通的用户”排序。

### 1. ComfyUI 官方 Discord（custom-nodes 频道）

- 用 `#custom-nodes` 的 `Show and tell` / 发布类频道，一条帖只讲一个场景，附一条 GIF。
- 不要在多个频道重复刷同一帖。
- 有人问“怎么装”，回 git 命令 + CLI 前置步骤，不甩一句“Manager 搜一下”。

### 2. Reddit r/comfyui

- 标题写任务，不写包名：`Erase burned-in subtitles from video in ComfyUI without After Effects`。
- 正文给前后对比图 + 一条可复制的安装命令 + 成本说明（避免被当成隐性收费推广）。
- 回复比发帖重要：搜 “remove watermark comfyui”“video subtitle removal”，在别人的求助帖里给可执行方案。

### 3. B 站 / 小红书（国内主战场）

- B 站：3–5 分钟实操，选题用“痛点 + 结果”，如“短剧素材批量去字幕，一条链路搞定”。
- 小红书：图文，首图必须是前后对比，标题带工具名与任务词。
- 两个平台都不适合放长安装步骤，安装步骤统一指到 README。

### 4. 火山引擎 / 豆包开发者社群

- 这里的人是 MediaKit 潜在付费客户，可直接讲“ComfyUI 里怎么用”。
- 适合发“接入案例 + 成本页”，不适合发“求 star”。

### 5. GitHub 自身

- Repo About 填一句话描述 + Topics：`comfyui` `video-editing` `subtitle-removal` `video-enhancement` `volcengine`。
- README 首屏放 GIF 和“三件套”模板链接，比目录树有用。

**不建议**：买量、刷下载、进互赞群、在无关仓库提 PR 打广告。这些要么无效，要么直接踩平台规则。

## 三、可直接粘贴的帖子

### 帖 1 · Discord（英文）

> **Erase burned-in subtitles in ComfyUI, natively.**
>
> Three nodes, one graph: `Load Video → Erase Subtitle Pro → Save Video`.
> Region restriction lets you wipe only the lower third instead of the whole frame.
>
> The node handles upload, async polling, and download internally — cloud runs on your own Volcengine MediaKit key, nothing routes through my server.
>
> Install (Manager listing is still under review, use git for now):
> ```
> cd ComfyUI/custom_nodes
> git clone https://github.com/fudanll-sys/comfyui-mediakit-toolkit.git
> npx @volcengine/mediakit-cli install -y
> mediakit-cli init
> ```
> Then restart ComfyUI. Ready-made graph: `example_workflows/mediakit_erase_video_subtitle_pro.json`.
>
> Cost: `Erase Subtitle` standard is ¥0.4/min, `Pro` is ¥1/min of erased duration — cut the clip first, pay for what you actually deliver.

### 帖 2 · Reddit（英文）

> **Title:** Removing hard-coded subtitles and watermarks from video, inside ComfyUI
>
> I kept bouncing between ffmpeg delogo (leaves a smear) and shipping clips to a web tool, so I wrapped Volcengine's AI MediaKit into ComfyUI nodes.
>
> What it actually does:
> - subtitle / text erasure with optional region box (standard and pro)
> - video enhancement in three tiers (standard / professional / generative)
> - portrait and green-screen matting to transparent video
> - ASR to timestamped subtitles, OCR for burned-in text
> - plus the usual editing set: trim, concat, speed, rotate, filters, stitch, mux, mix
>
> Native `VIDEO` in and `VIDEO` out, 32 nodes, upload/poll/download handled inside the node.
>
> Two honest caveats: it needs your own MediaKit API key (paid per minute, not free), and the editing domain of the current CLI is cloud-only, so `auto` can still bill you.
>
> Repo: https://github.com/fudanll-sys/comfyui-mediakit-toolkit — subtitle-erasure graph is in `example_workflows/`.

### 帖 3 · B 站 / 小红书（中文）

> **标题**：短剧素材批量去字幕，ComfyUI 一条链路搞定
>
> 以前去硬字幕：PR 里跟踪遮罩，或者 ffmpeg delogo 抹一片模糊。
> 现在：`Load Video → Erase Subtitle Pro → Save Video`，可限定只擦下方字幕区，画面其他地方不动。
>
> 三个不得不说的点：
> 1. 用自己的火山引擎账号，按分钟计费，标准版 0.4 元/分钟、精细化版 1 元/分钟——先裁掉不要的片段，只处理要交付的部分。
> 2. 视频从你本机直传火山引擎，不经过任何第三方服务器。
> 3. 插件免费，但**不送额度、不代付**。
>
> 安装：`custom_nodes` 里 git clone，再装官方 `mediakit-cli` 并 `init` 配 Key，重启 ComfyUI。
> 现成工作流在仓库 `example_workflows/`，导入后选自己的视频即可。

## 四、首周节奏

| 时间 | 动作 | 目的 |
| --- | --- | --- |
| D0 | 备齐三个模板、README 首屏 GIF、成本页链接；建一个“安装问题”FAQ | 让来的人能自己跑通 |
| D0 | 私邀 5–10 位已有 MediaKit Key 的同事 / 客户试用，逐个跟进 | 拿到第一手“哪里卡住” |
| D1 | Discord + Reddit 各发一帖（帖 1 / 帖 2） | 抢第一波海外流量 |
| D2 | 根据私邀反馈修 README / FAQ，再发 B 站视频 | 避免把已知坑带给更多人 |
| D3 | 在小红书发图文版；去 r/comfyui 搜关键词回帖 | 长尾入口 |
| D7 | 复盘：看“成功跑通云端任务”的人数，不看下载数 | 决定是否加大投放 |

## 五、指标与止损

**北极星指标**：一周内完成至少一次成功云端任务的独立用户数。下载量受 Registry 索引影响，失真严重，不作考核。

辅助指标：
- Manager / Registry 页面访问 → 仓库访问转化率
- README 中“安装 CLI”段落的跳出点（说明卡在哪一步）
- 社群提问里出现频率最高的错误字段（直接改 FAQ）

**止损线**：任一渠道发帖后 24 小时内，若出现两条以上“装不上 / 节点不出现 / 跑不起来”的反馈，暂停后续投放，先修安装路径。继续投放只会扩大差评面。

## 六、内容素材清单

| 素材 | 对应文件 | 用途 |
| --- | --- | --- |
| 字幕擦除模板 | `example_workflows/mediakit_erase_video_subtitle_pro.json` | 帖 1、帖 3 |
| 画质增强模板 | `example_workflows/mediakit_video_enhance.json` | Reddit 正文、对比图 |
| 大模型增强模板 | `example_workflows/mediakit_video_enhance_generative.json` | 老片修复选题 |
| 裁剪模板 | `example_workflows/mediakit_video_trim.json` | 成本对比“先裁后处理”演示 |
| 成本页 | `docs/marketing/cost-comparison.html` | 所有渠道的成本质疑回复 |
| 商店文案 | `docs/marketing/registry-listing.md` | Registry / About / 帖子标题 |

以上模板均为仓库内已存在并通过结构校验的图，不新造未验证的工作流，避免“导入即报错”。
