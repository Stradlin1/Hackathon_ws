# 2026-10-22 · 界面换成旧纸 / 铜版画，并用 pioneer-wiki 的 key 生图

## 缘起

用户要求：读 `../NEUP_protests/pioneer-wiki` 的文档，把「我们的前端画风」改成那套，
再用那个项目里的生图 key 生一批本项目专属插图。范围确认后是 **Streamlit 应用 + 13 屏展示页**，
字体允许自带一份中文衬线子集。

## 先验证可行性（不写代码）

1. `pioneer-wiki/.env.local` 里的 `PW_IMAGE_BASE_URL` / `PW_IMAGE_API_KEY` 可用；
   `GET /v1/models` 返回 `gpt-image-2.5-sunburst`。实测一次 `POST /v1/images/generations`
   约 21 秒，`data[0].b64_json` 是 1536×1024 PNG——**请求 `size:1024x1024` 被忽略**，
   所以构图比例只能写进 prompt。
2. fontsource 的 `noto-serif-sc-chinese-simplified-400-normal.woff2`（1.51 MB、7946 字形）
   含 ASCII 与常用中文，可以按用字裁成子集；本机 `fontTools` 已装，`brotli` 需要临时装。
3. 本机 `/usr/bin/python` **没有** streamlit/torch，而且系统 numpy 是坏的：
   `import numpy` 直接报 `_multiarray_umath`。但 `AAA_Software_libraries/runtime/miniconda3/envs/aquacore`
   里有 streamlit 1.65.0 + torch 2.8.0，**用户的应用就跑在那个环境里（8501）**。
4. 所以截图验证分两路：组件画廊用临时 `/tmp/ui-venv`（只装 streamlit + playwright），
   真页面用 aquacore 环境在 **8502** 另起一个实例，不打扰用户正在跑的 8501。

## 做了什么

### 1. 生图 → 裁纸版

- `tools/art-prompts.json`：8 个 job（frontispiece / mark / card-lost / card-found /
  empty-search / empty-box / empty-bell / fleuron），共用 pioner-wiki 式的
  「19th-century copperplate engraving + 平纸底 `#E9E1D1` + 无文字/无边框/无渐变」尾巴。
- `tools/generate_art.py`：`--env-file` 自己解析 `KEY = value` 的空格写法（pioneer 的
  `.env.local` 就是这种），key 只在内存里；支持 `--only`、并发、b64/url 两种返回。
- `tools/prepare_art.py`：Pillow 复刻 `prepare-plates.mjs` 的
  「边框中位色 → 除 `ground*0.94` → 白转 alpha」，再对四周 3% 羽化；最长的 frontispiece
  限 1200、mark 限 640，其余 900，q80。花饰额外裁掉空白纸边。
- 产出约 1.4 MB webp；原始 PNG 在 `static/art/src/`（gitignore）。
- prompt 第一版就可用：账簿 + 蛋白照片 + 放大镜的卷首图、印章、方向卡、空状态都一次过；
  只有 fleuron 的空白边太大，靠裁切解决。

### 2. 中文字体子集

- `tools/build_font.py` 扫 `app.py` / `ui/` / `state/` / `matching/` / `showcase/` 的字符，
  加上 ASCII 与全角标点，用 `pyftsubset` 输出两份 131 KB woff2 + OFL 文本。
- Streamlit 用 `[server] enableStaticServing = true` 把 `static/` 挂到 `/app/static/`；
  `@font-face` 写成相对 URL，实测 `200 font/woff2`。展示页用 `assets/fonts/` 相对 URL。

### 3. 主题与组件

- `ui/theme.py` 整份重写：纸色/砖红/苔绿/金/靛蓝令牌、两层 `feTurbulence`、方形印章、
  衬线标题、墨色主按钮、纸井输入、扁平提示条、相纸边框、墨色进度条、窄屏规则。
- 顶栏不再用位图 logo（128px 印章在 28px 下糊成一团），改成 CSS 画的「404」圆章；
  生成印章留给 page_icon 与展示页封面。
- `ui/art.py`：`path / data_uri / figure / entry_art`，缺文件返回空串。
- `ui/components.py`：页头、统计、印章、空状态接生成插图；`state/login.py`、
  `register.py`、`lost_or_found.py` 接入卷首图与两张方向卡图。
- 证据照片**只加纸片边框，不加滤镜**——颜色是匹配属性，调色会让「白色充电宝」变米色。

### 4. 展示页

- `showcase/assets/stage.css` 只换视觉：纸色令牌、纸纹、衬线标题、方角纸片、印章标签、
  墨色按钮、苔绿/砖红数据色；结构、文案、`stage.js`、`demo.json` 一律没动。
- 封面印章同样是 CSS 的「404」圆章；收尾页花饰来自 `assets/img/art/fleuron.webp`。

## 踩过的坑

1. **Streamlit 进程会缓存已导入的本地模块。** 改完 `ui/theme.py` 后重新截图，字节数一模一样；
   必须 kill 再起进程（文件监听在 `tools/preview_ui.py` 这种主脚本不在仓库根时并不可靠）。
2. **静态目录是「主脚本旁边的 static/」**。预览壳在 `tools/` 下，字体 404；用
   `ln -sfn ../static tools/static` 解决（该软链已 gitignore）。真实入口 `app.py` 在根目录，天然正确。
3. **系统 pytest 是坏的**（`py/_vendored_packages/apipkg` 的 `__spec__`），
   `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 也救不了；改用 aquacore 环境 + 同一条禁用插件的变量，
   119 tests 全过。
4. **Streamlit 的提示条颜色画在 `stAlertContainer` 上**，只改 `stAlert` 会留下粉绿底；
   进度条的轨道是 `stProgressBarTrack`，填色是它的子 `div`。
5. `chrome --headless --screenshot` 会在 websocket 渲染前拍骨架屏；必须用 Playwright
   等 `[data-testid="stMainBlockContainer"]` 再等 2–4 秒。
6. 用户原本就在 8501 跑着应用，且工作区里有另一轮未提交的 13 屏改动；所有编辑都叠在现状上，
   没有 `git checkout` 或覆盖。

## 结果

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 HF_HUB_OFFLINE=1 <aquacore>/bin/python -m pytest -q` → **119 passed**。
- 真实应用登录后逐页截图（1440×960、390×844）；展示页 1920×1080 与 1440×900 无纵向滚动。
- `python .dsh/tools/check_links.py` → 0 broken。
- 生图 key 没进仓库、manifest 或日志；字体与插图缺失都能优雅退化。
