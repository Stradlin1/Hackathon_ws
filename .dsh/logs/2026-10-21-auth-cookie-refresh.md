# 2026-10-21 刷新页面掉登录：cookie 写了，但没送到浏览器

## 现象

登录成功、业务页正常；浏览器一刷新就回到登录页，必须重新输入账号密码。演示时尤其刺眼。

## 根因

- 登录状态靠 `streamlit-authenticator` 写在浏览器里的 cookie（HS256 JWT）。库在**密码校验成功的那一轮**调用 `cookie_controller.set_cookie()`。
- 同一轮结尾，`state/login.py` 立刻 `st.rerun()` 切到 `lost_or_found`。
- Streamlit 会丢弃「被 rerun 中断的那一轮」渲染出的元素，于是负责写 cookie 的那个组件从未到达前端。
- 刷新时新 session 没有 `authentication_status`，cookie 又不存在，只能回登录页。

## 怎么确认的

用 Playwright 缓存的 chromium + CDP 驱动真实浏览器（临时脚本在 /tmp，不入库）：

1. 登录 alice 成功，业务页正常；`document.cookie` 里**没有** `lost_found_auth`。
2. 手工把一个合法 JWT 写进 `lost_found_auth` 再刷新，登录状态**能**恢复。

结论：不是 cookie 配置、不是域名、不是 7 天有效期，读路径没问题，问题只在写。

## 改了什么

- `state/login.py`：认证成功后只置 `st.session_state.auth_cookie_pending = True`，照旧 rerun。
- `app.py`：下一轮开头 `pop` 这个标记并调用 `authenticator.cookie_controller.set_cookie()`；这一轮正常结束，组件得以送达。
- `app.py::_restore_from_cookie`：不再依赖库的 `login()` 恢复（它会先画登录框、下一轮才跳转，刷新时会闪一下）。改为直接读 `st.context.cookies`，校验签名与 `exp_date`，再调 `authenticator.authentication_controller.login(token=...)`。
- 页面分发：`state == login` 且已认证时直接改判为 `lost_or_found`，刷新后的第一帧就是业务页。

## 验证

- 真浏览器：登录 → cookie 写入 → 连续刷新两次仍是登录态（约 1 秒出业务页，轮询期间没出现过登录框）。
- 真浏览器：退出登录删掉 cookie，刷新仍是未登录；伪造的 cookie 刷新被拒。
- `pytest` 25 passed；`check_links.py` 0 断链。

## 留下的坑

- 刷新只恢复「已登录」，不恢复页面位置；`match_session` 不持久化，追问历史仍会丢（见 [privacy](../agents/privacy.md)）。
- `localhost` 与 `127.0.0.1` 是不同站点，换地址访问要重新登录。
- 这类「只有真浏览器才看得见」的问题单测覆盖不到，见 [`backlog.md`](../../backlog.md) 的端到端项。
