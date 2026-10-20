# 2026-10-21 — 建立 agent 知识体系

## 目标

让后续智能体不必把整个仓库塞进上下文：根目录留一份精简索引，细节按路由表跳到 `.dsh/agents/`；同时给「还没做完的事」和「踩过的坑」各一个固定归处。

## 做了什么

1. 通读 `README.md`、`app.py`、`db_manager.py`、`matching/*`、`state/*`、`tests/*`、`.gitignore`、依赖与配置文件（`wc -l` 合计约 1796 行）。
2. 从 `main`（37e1c6e）新建 `dsh` 分支；本次所有改动只在该分支。
3. 新建 `AGENTS.md`（索引 / 分支纪律 / 8 条红线 / 路由表 / 目录表）、`backlog.md`、`.dsh/agents/` 七个主题文档、`.dsh/logs/` 索引与本日志、`.dsh/tools/check_links.py`。
4. `.gitignore` 增加「本机指令覆盖层 / 模型权重与缓存 / 运行产物」三组条目并逐条写原因。
5. `README.md` 增加 "Agent knowledge base" 一节，说明 `.dsh/`、`AGENTS.md`、`backlog.md` 与 `dsh` 分支。
6. 运行链接校验与不变量 grep（结果见「验证」）。

## 关键决策与依据

### 分支 `dsh`

`git status --short --branch` 输出 `## main...origin/main`（干净），`git log --oneline` 显示 HEAD = `37e1c6e fourth commit`，remote 为 `github.com/Stradlin1/Hackathon_ws`。据此从 `main` 新建 `dsh`，`main` 未改动；合并需要用户另行确认。

### 为什么是七个主题文档

按「一个人可以独立搞错的事」切分，而不是按目录：

| 文档 | 独立失效面 | 证据 |
| --- | --- | --- |
| `matching-engine.md` | 打分/追问数学 | `matching/engine.py` 的 `WEIGHTS`、`rank_candidates`、`choose_question` |
| `fingerprint.md` | 文本→属性、生成式幻觉 | `matching/fingerprint.py` 的 `VOCAB`、`fingerprint_from_text` |
| `data-model.md` | 表、方向、迁移 | `db_manager.py`、`matching/storage.py`、`matching/requests.py` |
| `privacy.md` | 谁能看到联系方式 | `MatchRequests.accepted`、`clean_image` |
| `architecture.md` | 页面状态机与会话 | `app.py`、`state/*.py` |
| `operations.md` | 环境、启动、降级 | `requirements*.txt`、README、本机实测 |
| `invariants.md` | 跨切面规则与机械检查 | 以上代码 + `tests/` |

### 索引留在根目录

`.dsh/agents/` 里的细节只有在根指令每轮自动加载时才有意义。DSH 的指令文件名候选是 `AGENTS.md` / `CLAUDE.md`（技能参考文件引用 `packages/context/agent-instructions/src/config.ts` 的 `DEFAULT_INSTRUCTION_FILE_CANDIDATES`）；`README.md` 不会被自动加载。所以索引放根目录，README 只写给人看。

### 结构表只记目录

`matching/`、`state/` 里的模块名会随重构变动，列进表就是文件系统的第二份副本；目录职责与根文件则稳定。把「有哪些模块」留给代码本身。

## 从原始资料里读出的结论

1. **0.389 阈值**：证据项从 +1 到 −1 只值 0.28 分，语义系数 0.72，故 CLIP 相似度差 `0.28 / 0.72 = 0.389` 可以翻转完全相反的证据。这个数写进了 `AGENTS.md` 红线 3。
2. **`static/` 未被引用**：全仓 grep 无命中，只有三张 png。已作为 backlog 条目。
3. **被拒绝的请求是终局**：主键 `(found_item_id, lost_item_id)` + `INSERT OR IGNORE`，没有回到 `pending` 的路径。
4. **pending 请求不影响候选池**：未匹配查询只看 `matches`，不看 `match_requests`。
5. **`no special mark` 是真实值**：它会与有标记的候选产生矛盾（mark 权重 2.0），不是中性；想中性只能不作答。
6. **本机环境不可用**：缺 `streamlit`/`torch`，`numpy` 导入报 `No module named 'numpy.core._multiarray_umath'`，`pytest` 导入连带失败。
7. **`get_item` 对缺失 id 抛 `TypeError`**：内部对 `None` 取下标。
8. **`users.password` 恒为空串**：登录/注册只写 `User(username, '', email)`，真实口令在 `config_auth.yaml`。

## 中途改正过的地方

- **沙箱**：第一次 `run_code` 因 `workspace-write` 找不到可用沙箱后端被拒（缺少 bubblewrap/Landlock）。随后会话文件策略改为 `danger-full-access`，之后不再请求升级。
- **分支与外部规格的确认**：`ask_user_question` 在 120 秒超时、未获答复（审批被禁用，无人应答）。没有因此停工：默认选 `dsh` 分支，并把「是否存在比赛评分标准」写成 `【待验证】` + backlog 条目，而不是臆造成事实。
- **链接层级**：`backlog.md` 初稿把日志链接写成 `../.dsh/logs/...`（多退一级），被 `check_links.py` 抓到后改成 `.dsh/logs/...`。
- **结构表**：原本想按模板登记 `.dsh/skills/`，但该目录并不存在，删掉该行——空目录不该出现在目录表里。
- **不变量 6 的检查命令**：最初写成全仓 grep，实测会把 `tests/` 里 5 处裸 `CREATE TABLE` 夹具算进来；改为只查应用代码。

## 验证

- `python3 .dsh/tools/check_links.py`：所有相对链接与锚点通过（0 broken）；它也会检查本日志里的链接。
- `grep -rn "CREATE TABLE" --include='*.py' db_manager.py matching/ state/`：7 处，全部 `IF NOT EXISTS`。
- `grep -n "observed\[field\] = " matching/fingerprint.py`：仅 1 处，位于字面证据校验分支内。
- `grep -n "if not query.get(key) or not other.get(key)" matching/engine.py`：1 处。
- `grep -rn "answers" --include='*.py' matching/storage.py matching/requests.py`：无输出。
- `grep -n "contact_email\\|u.email" matching/requests.py`：仅 `accepted()` 的 SELECT。
- `grep -n "PermissionError" matching/requests.py`：1 处。

## 未做（明确留给后续）

- **没有运行 `pytest` / `streamlit`**：本机依赖缺失且 numpy 损坏，见 [operations](../agents/operations.md)。因此本文档只陈述代码事实，不声称行为已在本机验证。
- **没有合并 `main`**、没有删 `static/`、没有改任何应用代码。
- **没有蒸馏可复用技能**：本次只建立项目知识库；若要复用，应按技能流程另写 `SKILL.md` + references。
- **没有实测并发写入**：SQLite 锁行为仍是 `【待验证】`。
