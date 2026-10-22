# 界面层（ui/）

> 入口索引在仓库根目录 [AGENTS.md](../../AGENTS.md)；本文件只讲展示层。
> 相关：[架构与页面流程](architecture.md)、[隐私](privacy.md)、[上台展示页](showcase.md)。

**本文件状态：【事实】**——读自 `ui/*.py`、`.streamlit/config.toml`、`static/` 与 `tools/`（2026-10-22），并用登录后的真实页面 + 组件预览壳截图核对。

## 设计语言

照 pioneer-wiki 的**旧纸档案 / 铜版画 / 木活字**方案重建（2026-10-22）：

- 纸底 `#E9E1D1`、纸片 `#F3EEE4`、凹井 `#E0D7C5`；墨色三阶 `#24221E` / `#4A453C` / `#5C5548`。
- 语义色：失物 = 砖红（文字 `#94493A`，底 `rgba(185,106,89,.13)`）；拾获 = 苔绿（文字 `#4D5A43`，底 `rgba(101,116,90,.14)`）；警示 = 金 `#6E5829`；中性强调 = 靛蓝 `#34465A`。
- 方角（2–4px）、1px 细线、纸片阴影；状态与分类是**方角橡皮章**，不再是圆胶囊。
- 正文仍是系统无衬线栈（Droid Sans Fallback 兜底）；标题、数字、字标用**自托管 Noto Serif SC 子集**。
- **不用 emoji 当图标**：图标全部在 `ui/icons.py`，内联 SVG，线宽 1.4，颜色跟随 `currentColor`。

## 令牌与主题

- `.streamlit/config.toml`：`primaryColor=#34465A`、`backgroundColor=#E9E1D1`、`secondaryBackgroundColor=#F3EEE4`、`textColor=#24221E`、`borderColor=#D8CDB9`、`baseRadius=3px`、`buttonRadius=3px`、`font=sans-serif`；另有 `[server] enableStaticServing = true`。
- 【事实】配置文件在**进程启动时读取一次**：改完必须重启 `streamlit run`，浏览器刷新不够。
- 其余细节在 `ui/theme.py` 的 CSS 变量与规则里；纸纹是两层 SVG `feTurbulence`（大块浓淡 + 细颗粒）直接画在 `[data-testid="stAppViewContainer"]` 的背景上，不盖在文字上。
- 稳定选择器清单：`data-testid`（`stVerticalBlockBorderWrapper`、`stForm`、`stAlertContainer`、`stProgressBarTrack`、`stPills`、`stFileUploaderDropzone`…）与 `st.container(key=...)` 生成的 `.st-key-*`。**不要用 emotion 哈希类名**。

## 字体（自托管子集）

- 【事实】仓库只带子集：`static/fonts/noto-serif-sc-subset.woff2`（约 131 KB，按 App + 展示页实际用字裁剪）+ `OFL.txt`；展示页另有一份同源文件在 `showcase/assets/fonts/`。
- 【事实】Streamlit 通过 `/app/static/fonts/noto-serif-sc-subset.woff2` 提供；实测 HTTP 200、`content-type: font/woff2`。
- 【设计】重新生成：`python -m venv /tmp/fontenv && /tmp/fontenv/bin/pip install fonttools brotli`，再 `/tmp/fontenv/bin/python tools/build_font.py`（会重新扫描用字、重写两份 woff2 与 OFL 文本）。
- 运行期**不需要** fontTools/brotli。文件缺失或 404 时 `@font-face` 静默失败 → 系统宋体 → serif，不影响功能。

## 生成插图（`static/art/`）

- 【事实】8 张图由 pioneer-wiki 的生图网关生成（模型 `gpt-image-2.5-sunburst`），`static/art/manifest.json` 记录 prompt、模型、时间与 `CC BY 4.0`；`ATTRIBUTION.md` 是给人和评委看的署名页。
- 【事实】原始 PNG 在 `static/art/src/`（已 gitignore，1–3 MB/张）；`tools/prepare_art.py` 用 Pillow 把纸底估成透明、四周 3% 羽化，输出 `static/art/<slug>.webp`（最长边 640–1200，q80）与 `mark-icon.png`（128px，页面图标）。
- 用途：`frontispiece`（登录/注册左栏）、`mark`（印章源图 / page icon）、`card-lost` / `card-found`（首页两张方向卡）、`empty-search` / `empty-box` / `empty-bell`（空状态）、`fleuron`（登录页花饰、展示页收尾）、`vector-plane`（展示页 04 页向量平面网格）。
- 【设计】重新生图：`python tools/generate_art.py --env-file <含 PW_IMAGE_API_KEY 的文件> [--only slug]`，再 `python tools/prepare_art.py`。key 只从环境变量或 `--env-file` 读，**不进仓库、不进 manifest、不进日志**。
- `ui/art.py`：`path()` / `data_uri()` / `figure()` / `entry_art()`，找不到文件时返回空串，页面只是少一张装饰图。

## 布局

- `layout="wide"` + CSS 把 `[data-testid="stMainBlockContainer"]` 限宽 1080px 居中（默认只有 736px）。
- 已登录页面统一由 `ui.components.topbar()` 渲染：圆形「P」印章 + 衬线字标「Picture is All You Need」+ 小字「失物招领 · 本地档案」+ 首页 / 登记物品 / 近期动态 / 通知 / 我的记录 + 退出登录；当前页是**墨色下划线**，不是填充按钮。
- 「登记物品」用 `st.pills` 在失物/拾获之间切换，只渲染当前方向的表单；首页两张卡只是带方向的快捷入口。
- 失物表单有「上传物品照片（可选）」；上传后显示预览，没上传也能提交。
- 「近期动态」卡片用砖红「失物」/苔绿「拾获」印章区分方向；失物与拾获都可能带照片；每张卡显示发布时间（`发布于：YYYY-MM-DD HH:MM`）。
- 匹配候选卡显示候选的地点/日期；有软先验加分时再显示「时间/地点软先验 +x.xxx」。分数说明固定写明「+ 时间/地点软先验（最多 +0.05，缺失不扣分）」。
- 近期动态、我的记录、通知、候选卡都在卡片底部显示「首次发布于：… · 内容指纹 …」；这是先后信号，不是所有权证明。
- 公开/列表图片通过 `watermark()` 加底部水印（帖子尾号 + 日期）；上传预览保持原图。
- 上传近似重复图片时显示 warning；提交时文本近似会在匹配页顶部提示一次。两者都不阻断提交。
- 顶栏的「通知」标签读取 `session_state.unread_notifications`，有未读时显示 `通知 · N`；`topbar()` 自己不查库，未读数由 `app.py` 每轮写入。
- 「我的记录」把失物/拾获分成进行中与已处理：进行中卡片有「处理」对话框（已归还/归档 + 可选备注），已处理区显示状态徽标与「恢复为进行中」。
- **没有侧边栏**：`st.sidebar` 已全站移除，CSS 同时隐藏 `stSidebar` 与折叠控件。
- 【事实】退出登录仍由 `authenticator.logout(location="main")` 渲染。不要改成先清 session 再 `st.rerun()`：删 cookie 的组件会被丢弃（见 [auth-cookie-refresh](../logs/2026-10-21-auth-cookie-refresh.md)）。

## 组件（`ui/components.py`）

| 函数 | 用途 |
| --- | --- |
| `topbar(current, authenticator)` | 顶部导航，唯一的退出登录入口 |
| `page_header(icon_name, title, subtitle, step)` | 页头：细线方框图标、衬线标题、金色步骤印章 |
| `card(key)` | `st.container(border=True, key=...)` 的纸片封装 |
| `stat_row(items)` | 统计格（顶部重线 + 细线分栏 + 衬线数字） |
| `empty(icon_name, title, hint, art_name)` | 空状态；自动按图标映射到生成插图，缺图退回内联 SVG |
| `pill` / `pills` / `pills_html` | 方形印章；`pills_html(..., art_name=)` 带方向卡插图 |
| `status_badge(status)` | 请求状态印章 |
| `auth_point(icon_name, title, detail)` | 登录 / 注册页的要点行 |
| `esc(value)` | HTML 转义 |

- 图标新增 `bell`（通知页页头）；所有图标仍是内联 SVG，不引外部字体或 emoji。
- `ui/art.py` 只做「取图 / 内联 / 画 figure」，不含业务。

## 硬规则

1. **动态文本必须过 `esc()`。** 组件用 `unsafe_allow_html=True` 渲染，物品描述、地点、邮箱、用户名都来自数据库或表单，不转义就是注入点。
2. **只用稳定选择器**：`data-testid` 与 `st.container(key=...)` 生成的 `.st-key-*`。不要用 emotion 哈希类名（`st-emotion-cache-xxx`），它们在版本之间会变。
3. **CSS 失效不能影响功能**：样式只负责外观；Streamlit 升级后最坏情况是变回默认样式，不是功能坏掉。
4. **证据照片不调色。** 照片只加纸片边框与阴影；**不要**给用户上传的照片加 sepia/duotone/亮度滤镜——颜色、材质是匹配属性，改色会让演示失真。只有生成插图做纸版裁切与羽化。
5. **文案红线不变**：排序分叫「排序指标」，不叫概率；联系方式只在对方接受后出现（见 [matching-engine](matching-engine.md)、[privacy](privacy.md)）。

## 已知限制

- Streamlit 自带控件的文案（`Upload`、日期选择器的月份与星期、右上角菜单）无法本地化。
- 手机窄屏的顶部导航是一条横向滚动栏；导航回到 5 项后仍可能需要滑动才能看到「退出登录」（已在 [backlog](../../backlog.md) 记录）。
- 顶部工具栏被隐藏（`toolbarMode = "minimal"` + CSS）；需要 Rerun / Clear cache 时临时注释 CSS 或把 toolbarMode 改回 `auto`。
- 子集字体只覆盖当前用字：新增文案若含生僻字，该字回退到系统字体（不会缺字，只是字形不统一）。
- `static/art/` 的 webp 合计约 1.4 MB；`frontispiece.webp` 约 558 KB，登录页首屏会读它一次。

## 怎么改

1. 改颜色 / 圆角：先改 `.streamlit/config.toml`，再改 `ui/theme.py` 的变量与规则。
2. 加页面块：用 `ui/components.py` 的组件，不要在页面里堆裸 HTML。
3. 加插图：把 slug 写进 `tools/art-prompts.json`，生图 → 裁切 → 在页面里用 `ui.art` 引用。
4. 改完：重启进程 → 用下面两条命令截图 → 跑 `pytest` 与 `check_links.py`。

## 预览与截图（不依赖模型）

【事实】本机 `/usr/bin/python` 没有 streamlit/torch，但 `/home/furina061006/AAA_Software_libraries/runtime/miniconda3/envs/aquacore/bin/python` 有完整运行环境（streamlit 1.65、torch 2.8）。两条路都验证过：

```bash
# 组件画廊（只读 ui/*，不读模型）：1440×960 与 390×844
python -m venv /tmp/ui-venv && /tmp/ui-venv/bin/pip install "streamlit>=1.35,<2" playwright==1.63.0
ln -sfn ../static tools/static
/tmp/ui-venv/bin/streamlit run tools/preview_ui.py --server.port 8599
# 真页面（登录页 / 最近动态 / 我的记录…）用 aquacore 环境另起一个端口：
HF_HUB_OFFLINE=1 <aquacore>/bin/streamlit run app.py --server.port 8502
```

- 截图用 Playwright（本机 `../NEUP_protests/pioneer-wiki/node_modules/.bin/playwright screenshot` 或 `/tmp/ui-venv` 里的 Python 包）等选择器 `[data-testid="stMainBlockContainer"]`，**不要**用 `chrome --headless --screenshot`：它在 websocket 渲染前就拍了骨架屏。
- 字体自检：`curl -o /dev/null -w '%{http_code} %{content_type}' http://127.0.0.1:8599/app/static/fonts/noto-serif-sc-subset.woff2` 应为 `200 font/woff2`。
- 完整测试：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 HF_HUB_OFFLINE=1 <aquacore>/bin/python -m pytest -q`（2026-10-22：119 passed）。
