# 界面层（ui/）

> 入口索引在仓库根目录 [AGENTS.md](../../AGENTS.md)；本文件只讲展示层。
> 相关：[架构与页面流程](architecture.md)、[隐私](privacy.md)。

**本文件状态：【事实】**——读自 `ui/*.py` 与 `.streamlit/config.toml`（2026-10-21），并用无头 Chromium 截图核对。

## 设计语言

- 品牌色取自 `static/logo_rounded.png` 的深藏青 `#16324F`；浅色主题，蓝灰底 `#F5F6FA`、白卡片、16px 圆角、轻阴影。
- 语义色：失物 amber（`#B45309` / `#FEF3C7`），拾获 teal（`#0F766E` / `#CCFBF1`）；状态 ok `#047857`、warn `#B45309`、danger `#B91C1C`。
- 字体是系统栈（`-apple-system` / `PingFang SC` / `Microsoft YaHei` / `Noto Sans CJK SC`），不引外部字体：离线演示必须能跑。
- **不用 emoji 当图标**：没有彩色 emoji 字体的 Linux 会渲染成豆腐块。图标全部在 `ui/icons.py`，是内联 SVG，颜色跟随 `currentColor`。

## 令牌与主题

- `.streamlit/config.toml` 只写 Streamlit 认识的键：`primaryColor` / `backgroundColor` / `secondaryBackgroundColor` / `textColor` / `borderColor` / `baseRadius` / `buttonRadius` / `font` / `showWidgetBorder`，以及 `[client] toolbarMode = "minimal"`。
- 其余细节在 `ui/theme.py` 的 CSS 变量与规则里。
- 【事实】配置文件在**进程启动时读取一次**：改完必须重启 `streamlit run`，浏览器刷新不够。

## 布局

- `layout="wide"` + CSS 把 `[data-testid="stMainBlockContainer"]` 限宽 1120px 居中（默认只有 736px）。
- 已登录页面统一由 `ui.components.topbar()` 渲染：品牌图 + 首页 / 登记失物 / 登记拾获 / 我的记录 + 退出登录；当前页按钮用 `type="primary"` 高亮。
- **没有侧边栏**：`st.sidebar` 已全站移除，CSS 同时隐藏 `stSidebar` 与折叠控件。
- 【事实】退出登录仍由 `authenticator.logout(location="main")` 渲染。不要改成先清 session 再 `st.rerun()`：删 cookie 的组件会被丢弃（见 [auth-cookie-refresh](../logs/2026-10-21-auth-cookie-refresh.md)）。

## 组件（`ui/components.py`）

| 函数 | 用途 |
| --- | --- |
| `topbar(current, authenticator)` | 顶部导航，唯一的退出登录入口 |
| `page_header(icon_name, title, subtitle, step)` | 页头：图标、标题、步骤胶囊 |
| `card(key)` | `st.container(border=True, key=...)` 的卡片封装 |
| `stat_row(items)` | 统计胶囊行 |
| `empty(icon_name, title, hint)` | 空状态 |
| `pill` / `pills` / `pills_html` | 行内徽标、卡片标题块 |
| `status_badge(status)` | 请求状态徽标 |
| `auth_point(icon_name, title, detail)` | 登录 / 注册页的要点行 |
| `esc(value)` | HTML 转义 |

## 硬规则

1. **动态文本必须过 `esc()`。** 组件用 `unsafe_allow_html=True` 渲染，物品描述、地点、邮箱、用户名都来自数据库或表单，不转义就是注入点。
2. **只用稳定选择器**：`data-testid` 与 `st.container(key=...)` 生成的 `.st-key-*`。不要用 emotion 哈希类名（`st-emotion-cache-xxx`），它们在版本之间会变。
3. **CSS 失效不能影响功能**：样式只负责外观；Streamlit 升级后最坏情况是变回默认样式，不是功能坏掉。
4. **文案红线不变**：排序分叫"排序指标"，不叫概率；联系方式只在对方接受后出现（见 [matching-engine](matching-engine.md)、[privacy](privacy.md)）。

## 已知限制

- Streamlit 自带控件的文案（`Upload`、日期选择器的月份与星期、右上角菜单）无法本地化。
- 手机窄屏的顶部导航是一条横向滚动栏，最右侧的"退出登录"要滑动才看得到（已在 [backlog](../../backlog.md) 记录）。
- 顶部工具栏被隐藏（`toolbarMode = "minimal"` + CSS）；需要 Rerun / Clear cache 时临时注释 CSS 或把 toolbarMode 改回 `auto`。

## 怎么改

1. 改颜色 / 圆角：先改 `.streamlit/config.toml`，再改 `ui/theme.py` 的变量与规则。
2. 加页面块：用 `ui/components.py` 的组件，不要在页面里堆裸 HTML。
3. 改完：重启进程 → 1440×960 与 390×844 各截一次 → 跑 `pytest` 与 `check_links.py`。
