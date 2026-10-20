# 运行与操作（环境、启动、测试、降级）

> 入口索引与工作约定在仓库根目录 [`AGENTS.md`](../../AGENTS.md)；本文件是 `.dsh/agents/` 知识库的一部分。
> 相关：[架构](architecture.md) 说明启动后发生什么；[隐私](privacy.md) 说明配置里的密钥。

**本文件状态：`【事实】`**——命令与版本来自 2026-10-21 在本机的实测，以及 `README.md` 的安装说明。

## 本机实测（2026-10-21）

```text
python3 -V                          → Python 3.11.15
python3 -c "import streamlit"       → ModuleNotFoundError: No module named 'streamlit'
python3 -c "import torch"           → ModuleNotFoundError: No module named 'torch'
python3 -c "import numpy"           → No module named 'numpy.core._multiarray_umath'
python3 -c "import pytest"          → AttributeError: __spec__（numpy/pytest 安装损坏）
```

- 【事实】因此**本机目前既跑不了 `streamlit run app.py`，也跑不了 `pytest`**。这不是代码问题，是环境问题。
- 【事实】系统 Python 里混着一份损坏的 numpy；**不要**继续往系统环境 `pip install`，用干净 venv。

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
- 【待验证】本机尚未成功执行过上述命令（见「本机实测」）。

## 离线与降级

| 环境变量 | 默认 | 效果 |
| --- | --- | --- |
| `FINGERPRINT_TEXT_MODEL` | `google/flan-t5-small` | 设 `off`/`none`/`disabled` 跳过文本生成器，只走规则抽取 |

- 【设计】三层降级：无文本生成器 → 规则抽取；无 BLIP → 提示"请手动描述"，仍可提交；无 CLIP → 报告无法处理，页面报错并停止。
- 【事实】所有降级都静默或一次性 warning，不会中断进程。

## 故障表

| 症状 | 原因 | 动作 |
| --- | --- | --- |
| `Missing config_auth.yaml...` | 未复制模板 | 复制示例并填哈希/密钥 |
| `No module named 'streamlit'` | venv 未激活或依赖未装 | 激活 `.venv` 后重装 |
| `numpy.core._multiarray_umath` | 系统 numpy 与 pip numpy 混用/损坏 | 删 `.venv` 重建，不要装进系统 Python |
| `AttributeError: __spec__`（导入 pytest 时） | 同上，numpy 损坏的连带症状 | 同样重建 venv |
| 图注 warning "Automatic image caption is unavailable" | BLIP 权重/网络不可用 | 手填描述，或先联网下载权重 |
| 候选为空 | 对面还没有未匹配报告 | 用另一账号先报一件；`reset_db.py` 可造样例 |
| `database is locked` | 多会话并发写 | 演示时单用户操作，或等待/重试 |
| 数据"消失" | 从别的目录启动，用了另一个 `items.db` | 回到仓库根目录启动 |
| 数据全没了 | 运行过 `reset_db.py` | 该脚本会删库，无备份 |

---

## 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-21 | 首次建立：本机实测、安装/启动/测试命令、离线开关、故障表。 |
