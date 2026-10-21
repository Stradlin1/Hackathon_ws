# 2026-10-22 · 撤销 Windows 压缩包合并，回到可运行状态

## 现象

工作区能启动，但仓库里没有 `matching/`、`state/`、`ui/`、`tests/`、`static/`、`demo/photos/`，
`app.py` 却 `from state.browse import browse` —— 一导入就 ModuleNotFoundError。

## 根因

队友在 Windows 上开发、没有 git，交付的是压缩包。为了合并，压缩包内容被直接提交成
`820b496 fix:114514上传了一些新功能`，父提交是 `3f17878`。这个提交：

- 只带来文档（`MODIFICATIONS.md`、`.dsh/agents/` 的新主题、`.dsh/logs/` 的新日志）；
- 修改了 `app.py` / `db_manager.py` / `reset_db.py` / `seed_demo.py` / `run.sh` / `README.md`；
- **删除了整个源码树**（`matching/` 9 个文件、`state/` 8 个、`ui/` 3 个、`tests/` 6 个、
  `static/` 3 个、`demo/photos/` 4 张图）。

也就是说：压缩包里没有这些目录，提交却把「文件不存在」写成了删除。

更麻烦的是，新功能的模块（`matching/{notifications,lifecycle,report_meta,content_hash}.py`、
`state/{report,browse,notifications}.py`）**从未进入过任何提交**。`git fsck --unreachable`
只剩旧版本的 blob，没有这些文件；本机 `/mnt/c`、`/mnt/d`、`/mnt/e` 与 `$HOME` 也没有副本。
所以它们不可从 git 恢复。

## 处理

1. 备份损坏状态：分支 `wip/win-zip-merge-broken`（= `d37ea9d`，含合并结果与全部新文档）。
2. `dsh` `reset --hard 3f17878`（最后一个通过 62 tests、HTTP 200 的提交）。
3. 清掉 Windows 迁移残留：`.venv/`（213 MB，只有 `Lib/` 的 Windows venv）、`.pytest_cache/`。
4. `core.autocrlf` 由 `true`（Windows 默认，会在 Linux 检出时写回 CRLF）改为 `input`，
   并新增 `.gitattributes`（`* text=auto eol=lf`，图片与 `*.db` 标 binary）。
5. 修 `README.md` 演示账号表格里 `Demo`1234`` 的反引号错位。
6. 验证：`pytest -q` → 62 passed；`streamlit run app.py` → HTTP 200。

## 仍然缺什么

`wip/win-zip-merge-broken` 里的文档描述了一整套没进仓库的功能：统一登记入口、双向近期动态、
订阅与站内通知、已归还/归档、请求生命周期（pending 上限 3、拒绝冷却、接受自动关闭）、
发布时间与内容指纹、dHash 查重、水印、时间/地点软先验、失物可选照片。

两条路：

- **要好代码**：向队友要原始压缩包（或他机器上的目录），照文档逐文件补回后正常提交；
- **不要了**：保持 `3f17878` 的状态，把 `AGENTS.md` / `README.md` / `backlog.md` 里对
  这些功能的描述一起删掉，避免文档与代码继续背离。

## 教训

- 别人的压缩包不能直接覆盖工作树：先在临时目录解压，用 `git diff --stat` 看清删除/新增，
  再按文件挑选；`git add -A` 会把「缺文件」变成「删文件」。
- 合并前先 `git log --stat --diff-filter=D` 检查有没有意外删除。
- 没有 git 的协作者，交付前先让他 `git init` 并给一个分支，比压缩包便宜得多。
