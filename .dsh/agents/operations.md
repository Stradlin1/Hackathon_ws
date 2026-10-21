# 运行与操作（环境、启动、测试、降级）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[架构](architecture.md) 说明启动后发生什么；[隐私](privacy.md) 说明配置里的密钥。

**本文件状态：`【事实】`**——命令与版本来自 2026-10-21 在本机的实测，以及 `README.md` 的安装说明。

## 本机实测（2026-10-21）

- 【事实】系统 Python 3.11.15 的 numpy 已损坏（`No module named 'numpy.core._multiarray_umath'`），**不要**用它装包。
- 【事实】实际运行环境是 conda `aquacore`（Python 3.10.21）：torch 2.8.0+cu129（CUDA True，RTX 5070）、numpy 2.2.5、Pillow 12.3.0、streamlit 1.65、transformers 4.57.6、sentence-transformers 3.4.1、pytest 8.4.2。
- 【事实】`streamlit run app.py` 已验证 HTTP 200；`pytest` 24 passed（本机 ROS Humble 的 pytest 插件缺 `lark`，需加 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`）。

## 推荐环境

- 【事实】README 推荐 **Python 3.10 或 3.11**；本机 3.11.15 满足。
- 【事实】版本约束的唯一来源是 [`requirements.txt`](../../requirements.txt) 与 [`requirements-dev.txt`](../../requirements-dev.txt)（含 streamlit、streamlit-authenticator、numpy、Pillow、torch、transformers、sentence-transformers、pytest）。**本文件不复制版本号**，升级时只需要改依赖文件。
- 【事实】`requirements-dev.txt` 第一行是 `-r requirements.txt`，所以测试依赖包含全部运行依赖。

## 从零开始

```sh
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

cp config_auth.example.yaml config_auth.yaml
# 编辑 config_auth.yaml：真实 bcrypt 哈希 + 新 cookie.key + 本地测试账号
python -c "import bcrypt; print(bcrypt.hashpw(b'choose-a-test-password', bcrypt.gensalt()).decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

- 【事实】`app.py` 要求 `config_auth.yaml` 与它同目录；缺失就停页。
- 【事实】`config_auth.yaml` 被 `.gitignore` 排除，**永远不要提交**。
- 【事实】`reset_db.py` **删除** `items.db` 后写入合成样例（4 件物品、1 条匹配），只在不需要保留数据时运行；它也会读取 `config_auth.yaml` 建用户。
- 【事实】样例图片是本地生成的纯色方块，不含照片或元数据。

## 启动与访问

```sh
streamlit run app.py
```

- 【事实】默认地址 `http://localhost:8501`；端口被占用时加 `--server.port <port>`。
- 【事实】必须从仓库根目录启动：`items.db` 与 `rooms.json` 都按**当前工作目录**解析。
- 【事实】首次使用 CLIP/BLIP 会下载预训练权重，CPU 上可能很慢；之后由 `lru_cache` 与本地 HF 缓存复用。

## 测试

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app.py matching state
```

- 【事实】测试 mock 掉 embedding 与模型权重，可以离线跑；`test_pages_smoke.py` 用假 `streamlit` 模块。
- 【事实】测试不覆盖真实模型精度、真实图片质量、SQLite 并发。
- 【事实】2026-10-21 在 aquacore 环境跑通：24 passed；注意 ROS 的 pytest 插件会因缺 `lark` 直接崩，必须带 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。

## DeepSeek 视觉（可选）

| 环境变量 | 默认 | 效果 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 未设置 | 未设置则整个功能关闭，拾获登记走本地 BLIP |
| `DEEPSEEK_VISION` | `on` | 设 `off`/`0`/`false` 可在保留 key 的情况下临时关闭 |
| `DEEPSEEK_VISION_MODEL` | `deepseek-flash` | 多模态对话模型名；`deepseek-v4-flash-vision-exp` 仍可调但已下线 |
| `DEEPSEEK_API_URL` | `https://api.deepseek.com/chat/completions` | 换代理或自建网关时用 |
| `DEEPSEEK_TIMEOUT` | `25` | 秒；超时按调用失败处理 |

- 【事实】请求是 OpenAI 兼容格式：`content` 数组里放 `{"type": "text"}` 与 `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}`；图片先缩放到 1600px 内再以 JPEG 质量 85 编码。
- 【事实】要求模型输出 json（`response_format={"type": "json_object"}`），只取 `description`、`visible_text`、`attributes` 三个键。
- 【设计】每次登记最多调用一次，结果进 `st.cache_data` 与指纹；检索、重排、追问完全不联网。
- 【事实】任何失败（无 key、超时、HTTP 错误、JSON 不合法、content 为空）都返回 `None`，页面自动回退本地 BLIP，不会中断登记。
- 【事实】只用标准库 `urllib`，不依赖 openai SDK，`requirements.txt` 未新增依赖。
- 【待验证】真实 key 下的延迟与计费未在本仓库实测；接口与模型名以 https://api-docs.deepseek.com/zh-cn/guides/vision 为准。

## 离线与降级

| 环境变量 | 默认 | 效果 |
| --- | --- | --- |
| `FINGERPRINT_TEXT_MODEL` | `google/flan-t5-small` | 设 `off`/`none`/`disabled` 跳过文本生成器，只走规则抽取 |

- 【设计】三层降级：无文本生成器 → 规则抽取；无 BLIP → 提示"请手动描述"，仍可提交；无 CLIP → 报告无法处理，页面报错并停止。
- 【设计】无中译模型时保留英文图注（不是报错），用户仍可手改。
- 【事实】所有降级都静默或一次性 warning，不会中断进程。

## 模型下载与设备

- 【事实】2026-10-21 实测：本机 `huggingface.co:443` 连接超时，`hf-mirror.com` 可用；未设镜像时 BLIP/CLIP 会一直卡在下载，表现为「图片描述生成很慢」。
- 【设计】启动前 `export HF_ENDPOINT=https://hf-mirror.com`，再 `streamlit run app.py`；**已经运行的进程要重启**才会读到新环境变量。
- 【事实】首次上传会下载 BLIP（约 1 GB）与 CLIP（约 1 GB），缓存在 `~/.cache/huggingface`；下载完成后可离线使用。
- 【事实】即使权重已在缓存里，`from_pretrained` 默认仍会向 huggingface.co 发 HEAD 请求；在本机实测会连续重试 5 次、卡住 30 秒以上，然后报「Can't load image processor」。
- 【设计】`matching/models.py` 统一 **先 `local_files_only=True` 读缓存**，只有抛出 `OSError/ValueError/AttributeError` 时才联网下载。这样缓存完整时优先本地，缓存缺失时仍能首次下载。
- 【事实】仅靠 `local_files_only` 不够：sentence-transformers 的子模块仍会向 huggingface.co 发 HEAD。缓存完整后应在启动命令里加 `HF_HUB_OFFLINE=1`；实测同一个模型从「卡 45 s+」变成 **0.7 s** 加载完成。
- 【事实】BLIP 加载后会在 CUDA 可用时 `.to("cuda")`；CLIP 由 sentence-transformers 自动选择 GPU。2026-10-21 实测（RTX 5070）：BLIP 加载约 9 s，首次图注约 2.7 s，之后约 0.2–0.4 s/张（含中译，800×800）。
- 【事实】图注中译使用 `Helsinki-NLP/opus-mt-en-zh`（约 300 MB），本地优先从仓库 `models/opus-mt-en-zh/` 读取（`/models/` 已 gitignore）；缺失时尝试从 HF 下载，仍失败则返回英文原文。
- 【事实】2026-10-21 实测译文：「a close up of a white computer mouse…」→「一张黑色表面白电脑鼠标的照片」；短句可读，但会出现「close up → 关闭」「table → 表格」这类误译，提交前应人工校对。
- 【事实】同一张图重复上传会命中 `st.cache_data` 的图注缓存，不再重新生成。

## 协作者首次使用

- 【事实】模型权重不入库；新环境运行 `python download_models.py`，脚本默认走 `hf-mirror.com`，已缓存则跳过。
- 【事实】`run.sh` 会设置 `HF_HUB_OFFLINE=1` 后启动 Streamlit；适合模型已缓存的日常演示。
- 【设计】首次下载与离线启动拆成两个命令，避免「离线模式导致第一次下载失败」的混淆。

## 演示数据

- 【事实】`seed_demo.py` 读取 `input/` 的 `充电宝.jpg`、`水杯.jpg`、`键盘.jpg`、`鼠标.jpg`：4 件拾获物品归 bob，4 件对应失物归 alice；写入时预计算 CLIP 向量与规则指纹。
- 【事实】脚本在 `items` 已有记录时直接退出，避免重复灌入；它不会删除数据库。
- 【设计】演示前备份一次：`cp items.db items.demo-backup.db`（`.db` 已被 `.gitignore` 排除）。
- 【事实】`reset_db.py` 会删库，只用于重置，不要与 `seed_demo.py` 混用。

## 故障表

| 症状 | 原因 | 动作 |
| --- | --- | --- |
| `缺少 config_auth.yaml...` | 未复制模板 | 复制示例并填哈希/密钥 |
| `No module named 'streamlit'` | venv 未激活或依赖未装 | 激活 `.venv` 后重装 |
| `numpy.core._multiarray_umath` | 系统 numpy 与 pip numpy 混用/损坏 | 删 `.venv` 重建，不要装进系统 Python |
| `AttributeError: __spec__`（导入 pytest 时） | 同上，numpy 损坏的连带症状 | 同样重建 venv |
| 图注提示「自动图片描述不可用」 | BLIP 权重/网络不可用 | 设置 `HF_ENDPOINT=https://hf-mirror.com` 后重启，或手填描述 |
| 图注是英文而不是中文 | 中译模型缺失/加载失败（离线且无本地模型） | 确认 `models/opus-mt-en-zh/` 存在，或联网下载 |
| 图片描述一直转圈 | 正在下载 BLIP，或缓存的权重不完整、触发了 HEAD 重试 | 设镜像后重启；确认缓存里有 `preprocessor_config.json` 与权重 |
| 候选为空 | 对面还没有未匹配报告 | 用另一账号先报一件；`reset_db.py` 可造样例 |
| `database is locked` | 多会话并发写 | 演示时单用户操作，或等待/重试 |
| 数据"消失" | 从别的目录启动，用了另一个 `items.db` | 回到仓库根目录启动 |
| 数据全没了 | 运行过 `reset_db.py` | 该脚本会删库，无备份 |

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：本机实测、安装/启动/测试命令、离线开关、故障表。 |
