# 2026-10-21 演示数据也进仓库：账号脚本 + 4 张照片

## 为什么

之前协作者拿到仓库要自己准备 `input/` 照片、自己配 `config_auth.yaml`，跑出来的演示数据各不一样。用户决定把"用户 + 失物 + 拾获"这套演示数据共享出去。

## 做法（不共享凭据文件本身）

- **账号**：新增 `create_demo_users.py`。它生成 `config_auth.yaml`，三个演示账号（alice / bob / demo）密码写在 README 里，**每次运行重新生成随机 `cookie.key`**。所以共享的是"怎么生成"，不是"带签名的凭据文件"：别人的 cookie 不能签到你机器上的会话。
- **物品**：把 4 张演示照片从 `input/`（私人目录、gitignore）复制到 `demo/photos/` 并提交；`seed_demo.py` 改成优先读 `demo/photos/`，找不到再退回 `input/`。
- 仍然不提交 `items.db`：它是二进制 + pickle，而且每台机器重新生成更干净。

## 风险与取舍

- 演示密码公开是有意的，只能在本地演示环境使用；README 已标注。
- `demo/photos/` 是用户提供的生活照；提交意味着公开这部分图像。已在发布说明里写明，如需撤回删除该目录并改回只读 `input/` 即可。
- `items.db` 依然不入库，避免二进制历史与 pickle 反序列化风险。

## 验证

- `tests/test_demo_data.py`：三个账号都能用公开密码通过 bcrypt 校验、每次生成的 cookie key 不同、`demo/photos/` 覆盖了 `SAMPLES` 里全部 4 个文件名。
- 全量 `pytest` 通过；`seed_demo.py` 的源码扫描确认优先目录是 `demo/photos`。
