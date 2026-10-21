# 2026-10-21 发布前检查与交接清单

## 发布范围

`main` 从 `51da41f` 到 `dsh` 最新，共 6 个提交：

1. `239c4ac` 拾获登记接入 DeepSeek 视觉模型（VLM 优先、BLIP 兜底）。
2. `8f41971` 手工配置收进 `settings.yaml`。
3. `a3df2fc` 追问答案以属性形式落库；候选卡显示对方属性；「补全信息」。
4. `b4a9d43` 我的记录支持撤销失物/拾获（级联删除请求/配对/指纹）。
5. `2313b89` 撤销按钮改成小号红色。
6. `1ed8d8d` 删掉失物登记追问；同族取值（杯子/水瓶、圆形/圆柱形）改按一致计分。

## 交接清单

新机器从零到能跑，按顺序：

```bash
# 1. 环境（本仓库验证于 conda aquacore；venv 亦可）
conda activate aquacore
python -m pip install -r requirements.txt

# 2. 账号
cp config_auth.example.yaml config_auth.yaml     # 填 bcrypt 哈希 + 新 cookie.key

# 3. 可选配置（DeepSeek key 等；不建也能跑）
cp settings.example.yaml settings.yaml

# 4. 模型权重（约 2.3 GB，走 hf-mirror，可重复运行）
python download_models.py

# 5. 演示数据（二选一；reset_db 会删库）
python seed_demo.py        # 从 input/ 的 4 张照片灌数据，需要 alice/bob 账号
# python reset_db.py       # 合成样例，会删除 items.db

# 6. 启动
./run.sh                   # 需要先激活环境；脚本只负责 HF_HUB_OFFLINE=1
```

- 【事实】`run.sh` 不会激活 conda/venv，找不到 `streamlit` 时先检查这一步。
- 【事实】必须从仓库根目录启动：`items.db` 与 `rooms.json` 都按当前目录解析。
- 【事实】`settings.yaml` 只在进程启动时读一次，改完要重启。

## 不入库的东西

| 文件 | 为什么 | 协作者怎么办 |
| --- | --- | --- |
| `config_auth.yaml` | 账号与 cookie key | 从 `.example` 复制自己填 |
| `settings.yaml` | 含 DeepSeek API key | 从 `.example` 复制自己填 |
| `items.db` | 本地演示数据 | 跑 `seed_demo.py` 或 `reset_db.py` |
| `input/`、`models/` | 私人照片与权重 | 自备照片；权重跑 `download_models.py` |

## 验证结果（2026-10-21）

- `pytest`：**59 passed**（模型权重全部 mock）。
- `check_links.py`：31 篇 Markdown、136 条相对链接、**0 断链**。
- 干净 shell 冒烟：`./run.sh` 起在 8598，HTTP **200**。
- 真浏览器跑过：登录 → 首页 → 报失 → 匹配 → 我的记录；刷新保持登录；退出登录清 cookie；390×844 无横向溢出；撤销与补全弹窗可用。
- 真实 DeepSeek 视觉接口：`input/水杯.jpg` 1.79 秒返回中文描述与 `visible_text=FUGUANG`。
- 演示库 `items.db` 未提交；发布前用备份核对过，没有测试残留。

## 已知限制（详见 backlog）

- 手机窄屏导航横向滚动；Streamlit 内置控件文案仍英文。
- 撤销是硬删除，没有回收站；已 `accepted` 的物品不允许撤销。
- 同族表是手工维护的；颜色/材质/标记仍是严格比较。
- 评分里 0.72 是原始 CLIP 相似度（常见 0.2–0.35），所以总分绝对值不高。
- 没有真实照片下的端到端留证；DeepSeek 计费未核算。

## 发布步骤

```bash
git checkout main
git merge --ff-only dsh
pytest -q                  # 在 main 上复跑一次
git push origin main
```
