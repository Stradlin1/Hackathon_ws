# 2026-10-22 · 项目改名：Picture is All You Need

## 需求

`todo.md`：项目要改成 **Picture is All You Need**，showcase 和真正项目的名字都要改，不要漏。

## 做法

- **应用**：`app.py` 的 `page_title`；顶栏字标（`ui/components.py`）与登录页大标题（`state/login.py`）；
  圆形印章从「404」改成「P」，字号与字距按更长的名字重调，顶栏第一列加宽，1440 / 390 都不折行。
- **展示页**：`<title>`、封面眉标、收尾 tagline；封面 CSS 印章里的 `content` 改成 `P`。
- **水印**：`matching/content_hash.py` 的公开图水印改成 `Picture is All You Need · #尾号 · 日期`。
  品牌名变长，所以加了实测宽度：窄图放不下时退化成 `#尾号 · 日期`，不会被裁掉。
- **素材**：`static/logo_rounded.png` 原来是带「404」的位图，换成新的 `mark-icon.png`；
  `tools/prepare_art.py` 与 `static/art/ATTRIBUTION.md` 的说明同步。
- **文档**：README 标题/首段/目录锚点、AGENTS 标题、`.dsh/agents/{ui,showcase,anti-copy}.md`、
  MODIFICATIONS 的水印与印章描述、`tools/preview_ui.py` 的预览文案。
- **没有改**：`.dsh/logs/` 里的历史日志（约定是「当时快照，不改写正文」）、git 提交历史、
  `showcase/data/demo.json` 里恰好含 404 的数字 id、以及 HTTP 404 这类真正的状态码措辞。
  旧名字在历史日志里仍会出现，这是记录而不是现行品牌。

## 验证

- 全量 `pytest`（aquacore 环境、禁用插件自动加载）→ 通过；展示页测试覆盖 `#openApp` 与页面不再引用 qr.png。
- 真实应用 1440×960：顶栏 `PICTURE IS ALL YOU NEED` 宽 234px，未溢出；首页、登录页截图正常。
- 390×844 登录页：标题与正文不折行溢出，表单卡片正常。
- 展示页 1920×1080 与 1440×900：封面眉标宽约 625px（容器 1180px），一行放下；收尾 tagline 同步。
- 水印实测 800 / 260 / 180 px 三种宽度：前两者完整显示品牌，180px 仍完整显示品牌+尾号（<240 不显示日期）。
- `check_links.py` 与 `git diff --check` 通过。
