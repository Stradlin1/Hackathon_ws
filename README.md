# 404NotFound — 多模态失物招领匹配

404NotFound 是一个本地运行的 Streamlit 应用：失主用文字描述丢失的物品，拾获者上传物品照片，系统用 CLIP 做跨模态召回，用带证据校验的「物品指纹」重排候选，再通过信息增益驱动的追问逐步收敛，最后由双方确认后才交换联系方式。

> **项目定位**：黑客松 / 课程演示用的单机原型。账号、数据与模型都跑在本机，界面文案为中文，**不包含**云端部署、多租户、真实校方系统对接或移动端适配。首次使用 CLIP/BLIP 时需要下载预训练权重。

## 目录
- [404NotFound — 多模态失物招领匹配](#404notfound--多模态失物招领匹配)
  - [目录](#目录)
  - [能做什么](#能做什么)
  - [匹配流程](#匹配流程)
  - [页面与操作](#页面与操作)
  - [快速开始](#快速开始)
    - [1. 环境](#1-环境)
    - [2. 安装依赖](#2-安装依赖)
    - [3. 配置账号](#3-配置账号)
    - [4. 生成样例数据（可选，会删库）](#4-生成样例数据可选会删库)
    - [5. 下载模型（新机器/协作者只需一次）](#5-下载模型新机器协作者只需一次)
    - [6. 启动](#6-启动)
    - [7. 走一遍完整流程](#7-走一遍完整流程)
  - [配置项](#配置项)
  - [数据、隐私与边界](#数据隐私与边界)
  - [测试与校验](#测试与校验)
  - [目录与模块地图](#目录与模块地图)
  - [已知限制](#已知限制)
  - [常见问题](#常见问题)
  - [项目知识库与开发约定](#项目知识库与开发约定)


## 能做什么

- **跨模态检索**：把失物的中文/英文描述与拾获物品的照片映射到同一向量空间，用余弦相似度召回候选。
- **证据化指纹**：从描述和图注中抽取六类属性（类型、颜色、材质、形状、品牌、特殊标记）。图注同时用**原始英文与中文译文**，因为机翻会丢细节。轻量文本模型可以补充提案，但**只有字面出现在描述或图注里的值才会被接受**；模型不可用时自动退回规则抽取。
- **主动追问，两边都问**：拾获者手里有实物，所以在**检索之前**就问他 2–3 个高信息量问题（选项来自失物池的实际取值，"无特殊标记"也算答案）；失主则在候选排好后按信息增益被追问，一次一个、最多四轮、可以跳过。
- **动态重排**：每回答一次就重新排序。语义相似度与「一致/矛盾」证据线性组合；**任一边缺失的属性保持中性**，不会被当成矛盾。
- **双方确认**：一方发送配对请求，另一方在「我的物品与请求」里接受或拒绝；**接受之前任何人都看不到对方联系方式**。
- **本地留存**：报告、图片、指纹、请求与配对结果都写在本地 SQLite（`items.db`）。

## 匹配流程

1. **报失**：填写描述、最后出现地点和日期。系统生成文本向量与指纹，并把报告存入数据库。
2. **报拾获**：上传照片。配置了 `DEEPSEEK_API_KEY` 时先由 DeepSeek 视觉模型（`deepseek-flash`）识别，返回中文描述与图上文字；没配 key 或调用失败则回退本地 BLIP。系统先把从照片读到的属性列出来，**误读的点一下就剔除**；再根据未配对失物池的分歧，问 2–3 个封闭问题（外形、颜色、是否有贴纸/划痕/文字）。用户确认后提交，生成图像向量，并从「描述 + 双语图注 + 问题答案」生成指纹。
3. **召回**：只从**尚未配对**的对面类型报告里取候选，用 CLIP 语义相似度取前 8 个。
4. **重排**：逐字段比较指纹。双方都有该字段时才计入证据：一致加分、矛盾按较轻的权重扣分、缺失不计。特殊标记（划痕、贴纸、挂绳等）权重最高。
5. **追问**：若靠前候选在某个未知属性上明显分裂，就针对该属性问一个问题。问题来自固定模板，**不会把候选的具体取值当提示泄露出去**。用户回答或跳过后立即重排。
6. **确认**：对满意的候选发送请求；对方接受后写入配对表，双方才能看到彼此的联系方式，且这一对不再出现在后续候选池里。

> 页面上显示的分数是**排序指标，不是所有权概率**。算法细节（权重、矛盾惩罚、翻转阈值、追问门槛）见 [`.dsh/agents/matching-engine.md`](.dsh/agents/matching-engine.md)。

## 页面与操作

| 页面 | 能做什么 |
| --- | --- |
| 登录 / 注册 | 账号来自 `config_auth.yaml`；注册使用自建表单，支持中文姓名、无需验证码，成功后回到登录页 |
| 首页 | 顶部导航栏切换页面；两张卡片分别进入报失 / 报拾获；下方三个计数：我的失物、我的拾获、待我确认 |
| 报失 | 描述（1000 字以内）、地点下拉、近 30 天内的日期；提交后直接进入匹配页 |
| 报拾获 | 上传 png/jpg/jpeg（≤8 MB）；DeepSeek 视觉模型（或本地 BLIP）生成描述，可改；确认 AI 读到的属性，回答 2–3 个封闭问题；提交后进入匹配页 |
| AI 匹配 | 查看指纹、前 5 个候选及一致/矛盾字段；回答追问；选择候选发送请求 |
| 我的物品与请求 | 查看自己的失物/拾物、待确认请求、已发请求、已确认配对与联系方式 |

- 注册页规则：姓名不限语言；用户名 3–20 位字母/数字/下划线/连字符；密码至少 8 位且同时包含字母和数字；邮箱需唯一。
- 导航由 `st.session_state.state` 驱动，没有 URL 路由。
- 已登录页面共用一条顶部导航栏（品牌 + 首页 / 登记失物 / 登记拾获 / 我的记录 + 退出登录），没有侧边栏；样式见 `.dsh/agents/ui.md`。
- **刷新匹配页会丢失当前会话**（包括已回答的追问），需要重新提交报告；这是有意的：追问答案不落库。

## 快速开始

### 1. 环境

- **Python 3.10 或 3.11**（推荐 3.11）。
- 不强制 GPU；CPU 可以跑，但首次加载模型与推理会明显更慢。
- 首次使用需要联网下载 CLIP/BLIP（以及可选的 flan-t5）权重，模型缓存在用户目录，不入库；图注中译模型 `Helsinki-NLP/opus-mt-en-zh` 约 300 MB，缓存在 `models/opus-mt-en-zh/` 或 HF 缓存。
- 国内网络访问 `huggingface.co` 可能超时；启动前设置 `export HF_ENDPOINT=https://hf-mirror.com` 可走镜像。

### 2. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

版本约束以 [`requirements.txt`](requirements.txt) 为准，本文不复制版本号。

### 3. 配置账号

复制模板并填写本地测试账号：

```bash
cp config_auth.example.yaml config_auth.yaml
```

`config_auth.yaml` 里必须改三处：

1. `credentials.usernames.<用户名>.password` 填 **bcrypt 哈希**，不是明文；
2. `cookie.key` 换成一个新的随机串；
3. 按需修改 `cookie.expiry_days`（默认 7 天）。

登录状态就是这个 cookie（HS256 JWT，`username` + 过期时间），所以刷新页面不会退出登录；改掉 `cookie.key` 会让已发的 cookie 立刻失效，所有人都要重新登录。

生成哈希与随机串：

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'choose-a-test-password', bcrypt.gensalt()).decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`config_auth.yaml` 已被 `.gitignore` 排除，**不要提交真实账号、哈希或 cookie key**。

### 4. 生成样例数据（可选，会删库）

```bash
python reset_db.py
```

它**先删除 `items.db`**，再写入 4 件合成物品和 1 条配对，方便直接演示。脚本会读取 `config_auth.yaml` 创建用户，所以必须先完成第 3 步。**需要保留旧报告时不要运行。**

如果已经有真实照片，改用种子脚本（不会删库，已有物品时会拒绝运行）：

```bash
# 照片放在 input/：充电宝.jpg 水杯.jpg 键盘.jpg 鼠标.jpg
HF_HUB_OFFLINE=1 python seed_demo.py
```

它会把 4 张照片写成 bob 的拾获物品，并写入 alice 的对应失物描述，同时预计算 CLIP 向量与指纹。

### 5. 下载模型（新机器/协作者只需一次）

模型权重不放进 git（体积大、更新频繁）。新环境先跑一次：

```bash
python download_models.py
```

脚本默认使用 `hf-mirror.com`，会拉取 BLIP、CLIP、flan-t5 与中译模型；已缓存的会跳过，可重复运行。

### 6. 启动

模型就绪后，用 `run.sh` 启动（自动设置 `HF_HUB_OFFLINE=1`）：

```bash
./run.sh
```

也可以手动启动。首次启动（需要下载模型时）走镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
streamlit run app.py
```

模型缓存到 `~/.cache/huggingface` 后，改用离线模式启动，避免每次加载都向不可达的 `huggingface.co` 发请求：

```bash
export HF_HUB_OFFLINE=1
streamlit run app.py
```

打开 `http://localhost:8501`。端口被占用时用 `streamlit run app.py --server.port 8502`。

**必须从仓库根目录启动**：`items.db` 与 `rooms.json` 都按当前工作目录解析，换目录会用到另一个空库或直接找不到地点文件。

### 7. 走一遍完整流程

1. 用账号 A 报一件失物（例如「黑色耳机，充电盒有红色贴纸」）。
2. 用账号 B 报一件拾获物品并上传照片。
3. 在 A 的匹配页回答一两个追问，观察候选顺序变化。
4. A 对 B 的物品发送请求；登录 B，在「我的物品与请求」里接受。
5. 双方在「已确认的匹配」中看到对方联系方式。

## 可选：接入 DeepSeek 视觉模型

不配置也能跑，走本地 BLIP；配置后拾获登记会用视觉模型识图，能读出型号、序列号这类图注写不出的细节。

```bash
export DEEPSEEK_API_KEY='sk-...'        # 必填，未设置则整个功能关闭
export DEEPSEEK_VISION=on               # 设为 off/0/false 可临时关闭
export DEEPSEEK_VISION_MODEL=deepseek-flash   # 默认值，一般不用改
export DEEPSEEK_TIMEOUT=25              # 秒，超时即回退本地
```

- 只在**登记时**调用一次，结果随指纹入库；检索、重排、追问全部仍在本机。
- 失败、超时、没有 key 都只是回退 BLIP，不会让登记失败。
- **隐私**：开启后照片会发送到 DeepSeek API；不想让照片离开本机就别设 key。页面上的隐私说明会随开关变化。
- 实现只用标准库 `urllib`，不引入 openai SDK。

## 配置项

| 配置 | 作用 | 默认 / 说明 |
| --- | --- | --- |
| `FINGERPRINT_TEXT_MODEL` | 指纹抽取用的文本生成模型 | `google/flan-t5-small`；设为 `off` 可跳过，只用规则抽取 |
| `config_auth.yaml` | 账号、cookie、有效期 | 不入库；缺失时应用直接停止并提示 |
| `items.db` | SQLite 数据库 | 相对**启动目录**；被 `.gitignore` 排除 |
| `rooms.json` | 地点下拉选项 | 想增删地点直接改这个文件 |

离线或模型下载失败时的降级行为：没有 flan-t5 → 规则抽取照常；没有 BLIP → 提示手填描述；没有 CLIP → 无法生成/比较向量，报告会报错停止。详见 [`.dsh/agents/operations.md`](.dsh/agents/operations.md)。

## 数据、隐私与边界

- **联系方式门禁**：只有状态为 `accepted` 的配对才会 JOIN `users` 表返回用户名与邮箱；未确认请求只显示物品描述。
- **请求权限**：只能对自己发布的报告发起请求；只有对方能接受或拒绝。
- **图片清洗**：入库前统一做 EXIF 方向纠正、缩放到最长边 1600、转 RGB，**不保留 EXIF**（包括定位信息）；上传上限 8 MB，像素上限 2000 万。
- **追问答案不落库**：只存在当前 Streamlit 会话里，刷新即失。
- **本地信任边界**：`items.db` 用 Python pickle 存图片数组与向量，只应作为可信本地数据使用，不要当交换格式。
- **不入库的内容**：`items.db`、`config_auth.yaml`、`.env*`、上传目录与模型权重；原因写在 [`.gitignore`](.gitignore) 里。

## 测试与校验

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app.py matching state
```

- 测试覆盖中英属性抽取、生成式提案的拒绝与接受、信息增益追问、回答后重排、指纹表 upsert、双方确认与拒绝、页面烟测。
- 测试**全部 mock 掉模型权重**，可以离线运行；通过单元测试不等于真实模型下端到端可用。
- 文档校验：`python .dsh/tools/check_links.py`，检查 `.dsh/` 与根目录 Markdown 的相对链接和锚点。

## 目录与模块地图

| 路径 | 职责 |
| --- | --- |
| `app.py` | 入口：读配置、构造认证器、按 `state` 分发页面 |
| `db_manager.py` | `items` / `users` / `lost_items` / `found_items` / `matches` 的访问层 |
| `matching/models.py` | 懒加载 CLIP/BLIP；图像清洗、编码、图注与中译 |
| `matching/fingerprint.py` | 文本 → 六维属性；生成式提案的证据校验 |
| `matching/workflow.py` | 取未配对候选、语义召回 top 8、组装匹配会话 |
| `matching/engine.py` | 证据重排与信息增益追问 |
| `matching/storage.py` | `item_fingerprints` 表读写 |
| `matching/requests.py` | 配对请求状态机；接受时写 `matches` |
| `state/` | 各页面的 Streamlit 流程（登录、报失、报拾获、匹配、我的记录） |
| `ui/` | 展示层：设计令牌与全局样式（`theme.py`）、顶栏 / 页头 / 卡片 / 统计等组件（`components.py`）、内联 SVG 图标（`icons.py`） |
| `tests/` | 算法测试与页面烟测（mock 模型） |
| `reset_db.py` | 删除并重建本地样例库 |
| `seed_demo.py` | 从 `input/` 的 4 张照片灌入演示数据（bob 拾获 / alice 失物） |
| `download_models.py` | 一次性拉取所有模型权重（默认 hf-mirror，已缓存则跳过） |
| `run.sh` | 以 `HF_HUB_OFFLINE=1` 启动 Streamlit |
| `rooms.json` | 地点选项 |
| `config_auth.example.yaml` | 账号配置模板 |
| `static/` | 品牌图 `logo_rounded.png`（页面图标与顶栏）；另有未被引用的 Lost / Found 两张图 |
| `.streamlit/config.toml` | Streamlit 主题与工具栏默认值；只在进程启动时读取，改完要重启 |
| `.dsh/` | 项目知识库：分主题事实、开发日志、校验脚本 |
| `AGENTS.md` | 智能体索引：分支纪律、红线、路由表 |

模块的精确行为、表结构与不变量见 [`.dsh/agents/`](.dsh/agents/)，以代码为最终权威。

## 已知限制

- **时间与地点当前不参与排序或过滤**，只作为报告信息保存与展示。
- **被拒绝的配对无法重新发起**：请求主键是「拾获物品 + 失物」，拒绝后没有回到待处理的路径。
- **待处理请求不会把物品移出候选池**，只有接受后写入的 `matches` 才会。
- **图注是机器翻译**：BLIP 先出英文，再由 `opus-mt-en-zh` 翻成中文，可能出现「close up → 关闭」这类误译；提交前可以手动修改，模型本身不保证准确。
- 没有速率限制、邮箱验证、封禁或审计日志；适合演示，不适合直接对外服务。
- 单进程 SQLite，没有迁移脚本；多会话并发写入的锁行为尚未实测。
- 仓库只有单元测试与 mock 烟测，**没有真实模型下的端到端验证记录**。
- 排名分不是所有权概率；生成属性也需要人工复核。
- **Streamlit 自带控件的文案改不了**：文件上传的 `Upload`、日期选择器的月份与星期仍是英文，只能靠自定义组件解决。
- **主题只在启动时生效**：改 `.streamlit/config.toml` 后必须重启 `streamlit run`，浏览器刷新不够。

当前卡点与下一步要找谁，见 [`backlog.md`](backlog.md)。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| `缺少 config_auth.yaml` | 复制 [`config_auth.example.yaml`](config_auth.example.yaml) 并填写哈希与 cookie key |
| `No module named 'streamlit'` | venv 未激活或依赖未装：重新 `pip install -r requirements.txt` |
| `numpy.core._multiarray_umath` 导入失败 | 系统 Python 与 venv 的 numpy 混装或损坏：删掉 `.venv` 重建，不要装进系统环境 |
| 图片图注提示不可用 | BLIP 权重未下载或网络不可用：设置 `HF_ENDPOINT=https://hf-mirror.com` 后重启，或手填描述继续 |
| 图注仍是英文 | 中译模型 `models/opus-mt-en-zh` 缺失且无法下载；补模型或手动改描述 |
| 图片描述一直转圈 / 很慢 | 首次在下载 BLIP（约 1 GB）；若缓存已完整仍慢，是加载时在向 `huggingface.co` 发 HEAD。设 `HF_ENDPOINT` 下载，之后用 `HF_HUB_OFFLINE=1` 启动 |
| 候选列表为空 | 对面还没有未配对的报告：换账号先报一件，或运行 `reset_db.py` |
| 数据「消失」 | 从别的目录启动了应用，或运行过 `reset_db.py`（会删库） |
| 配色 / 圆角没生效 | `.streamlit/config.toml` 只在进程启动时读取：重启 `streamlit run` |
| 刷新页面后要求重新登录 | cookie 过期（`cookie.expiry_days`）、换过 `cookie.key`，或浏览器禁用了 cookie；重新登录即可，登录状态默认保持 7 天 |

更多排查见 [`.dsh/agents/operations.md`](.dsh/agents/operations.md)。

## 项目知识库与开发约定

这个仓库同时维护一份给智能体用的渐进披露知识库：

- [`AGENTS.md`](AGENTS.md) 是每轮自动加载的索引，只放分支纪律、红线、路由表和目录表；**不要往里堆细节**。
- [`.dsh/agents/`](.dsh/agents/) 按主题存放项目事实：架构、匹配算法、指纹、数据模型、隐私、运行、不变量。
- [`backlog.md`](backlog.md) 记录「缺什么、找谁、卡住什么」，做完即删。
- [`.dsh/logs/`](.dsh/logs/README.md) 是只追加的过程记录，索引手工维护。

开发在 `dsh` 分支进行，`main` 只在用户明确确认后合并。提交前先确认分支：

```bash
[ "$(git branch --show-current)" = dsh ] || { echo "wrong branch, aborting"; exit 1; }
```

**为什么 README 不是智能体的入口**：DSH 只自动加载命名为 `AGENTS.md` / `CLAUDE.md` 的指令文件，`README.md` 不会被注入上下文。所以给人看的内容留在这里，给智能体的索引放在根目录的 `AGENTS.md`。
