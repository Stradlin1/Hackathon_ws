# 2026-10-21 — 前端文案全部中文化

## 目标

应用已经能启动，但标题、按钮、表单、提示与错误仍是英文。把**应用自己控制**的界面文案全部改成中文，同时不破坏现有行为与测试。

## 做了什么

1. 扫描 `app.py` 与 `state/*.py` 的 `st.*` 调用，替换标题、按钮、表单标签、提示、错误、展开器与下拉选项。
2. 认证表单改为传 `fields`：`authenticator.login(fields=...)`、`register_user(fields=...)`、`logout(button_name='退出登录')`。
3. 显示层增加枚举映射：`method`（`rules` / `vision_caption_rules` / `generative_verified`）与 `status`（`pending` / `accepted` / `rejected`）翻成中文，数据库仍存原值。
4. 「我的物品与请求」里的日期从 epoch 秒改为 `YYYY-MM-DD`；追问答案按中文属性名展示。
5. 会计入 `st.error` 的异常消息（`matching/requests.py`、`workflow.py`、`models.py`、`fingerprint.py`）一并改中文。
6. 更新 `tests/test_pages_smoke.py` 中按标签匹配表单按钮的断言。
7. 同步 README、`AGENTS.md`、`invariants.md`、`matching-engine.md`、`operations.md`、`privacy.md` 里的英文界面引用。

## 关键决策与依据

### 用认证库的参数，而不是 fork

读 `streamlit_authenticator/views/authentication_view.py` 确认：

- `login(..., fields: Optional[Dict[str, str]] = None, ...)`；
- `register_user(..., fields=..., ...)`；
- `logout(button_name: str = 'Logout', ...)`。

所以中文文案可以通过参数传入，不需要改第三方源码，也不会影响升级。

### 只翻译显示层，不翻译存储值

`match_requests.status` 的 CHECK 约束是 `pending/accepted/rejected`，`item_fingerprints.method` 也已有历史数据。翻译放在 `STATUS_DISPLAY` / `METHOD_DISPLAY` 里，**不迁移数据库**。

### 品牌名保留

`404NotFound` 是项目名，保留；浏览器标题改为 `404NotFound · 失物招领`。

### 测试必须跟着改

`tests/test_pages_smoke.py` 用 `label in {...}` 和 `label.startswith('Describe')` 模拟表单提交；界面文案一变，烟测就会假失败。改为中文标签后 20 个测试仍全部通过。

## 从原始资料里读出的结论

- 登录与注册表单完全由 streamlit-authenticator 渲染；不传 `fields` 时会出现 Username / Password / Login / Email / Repeat password 等英文。
- 注册表单实际有 **6 个输入**：姓名、邮箱、用户名、密码、确认密码、验证码；`captcha` 默认开启。旧 README 没有提到验证码。
- Streamlit 自带控件（文件上传的 Browse files、日期选择器的月份名、侧边栏菜单、表单回车提示）**没有本地化 API**，仍是英文。这是框架限制，不是漏改；除非换自定义组件或注入 CSS，否则改不了。
- `state/profile.py` 原来把 `item.time` 直接打印成整数（epoch 秒），本次顺带格式化为日期。

## 中途改正过的地方

- 第一轮替换漏了 `state/lost.py` 与 `state/found.py` 的侧边栏 `Back to menu`，用 grep 复查所有 `st.*` 字面量后补上。
- 候选下拉选项初版仍是 `#1: desc (score 0.123)`，第二轮改成中文标点与「物品 / 分数」。
- `method` 的兜底值最初仍是 `'unknown'`，改为「未知」，避免界面上出现英文。
- `interactive_match` 的 `answers` 原本直接打印字典（键是英文 category/color），改为用 `DISPLAY` 映射成中文属性名。

### 补充：属性值本身也要中文

第一轮只翻了标签，用 AppTest 渲染指纹时发现值仍是 `类型：umbrella / 颜色：black`。规范值同时参与比较与存储，不能直接改，于是在 `matching/fingerprint.py` 增加 `VALUE_ZH` 与 `display_value()`：**存储/比较保持英文，展示层翻译**；组合标记（`red sticker`）按「颜色 + 标记」拼成「红色贴纸」，词表外自由文本原样显示。新增规范值必须同步补 `VALUE_ZH`，否则界面回退英文。

## 验证

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` → **20 passed**（含新增的 `display_value` 测试）。
- Streamlit `AppTest`（真实 `app.py` + 真实 `config_auth.yaml`，0 异常）：
  - 登录页：subheader「登录」，按钮「登录 / 注册账号」，输入「用户名 / 密码」；
  - 主菜单：「我丢了东西 / 我捡到东西 / 我的物品与请求 / 退出登录」；
  - 报失页：「登记失物」，描述、地点、日期、提交按钮均中文；
  - 报拾获页：「登记拾获物品」「上传物品照片」；
  - 注册页：「注册账号」，姓名/邮箱/用户名/密码/确认密码/验证码，按钮「注册 / 返回登录」；
  - 匹配页指纹：`类型：雨伞 / 颜色：黑色 / 特殊标记：红色贴纸`，抽取方式「生成式已验证」。
- `python3 .dsh/tools/check_links.py` → 0 broken。

## 未做（明确留给后续）

- Streamlit 自带英文 chrome 无法通过 API 本地化，未处理。
- 未用真实 CLIP/BLIP 权重跑端到端；本次只验证渲染与单元测试。
- 未改数据库枚举、未改认证库源码、未合并 `main`。
