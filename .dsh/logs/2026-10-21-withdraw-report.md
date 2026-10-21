# 2026-10-21 可以撤销失物 / 拾获了

## 为什么

用户问「不能撤销失物和拾获吗」。之前确实没有入口：`db_manager` 里早就有 `remove_item`/`remove_lost_item`/`remove_found_item`，但没有任何页面调用；而且直接删 `items` 会留下孤儿请求和配对，`match_requests` 的 JOIN 会让请求从列表里消失、`accepted` 却仍能查到联系方式。

## 做了什么

- `state/profile.py` 每张物品卡片多一个「撤销登记」按钮，点开是确认弹窗：显示物品、地点日期 id、会连带删除的请求数量、以及"无法恢复"的提示。
- `_remove_report` 先验归属（`lost_items`/`found_items`），不是本人直接 `PermissionError`；然后依次删请求与配对（`MatchRequests.cancel_for_item`）、指纹（`FingerprintStore.delete`）、归属行、`items` 行。
- **已 `accepted` 的物品不允许撤销**，弹窗只给提示：避免单方面抹掉双方已经交换的联系方式记录。
- 撤销的如果正是当前匹配会话里的物品，同时清掉 `match_session`。

## 验证

- `pytest` 60 passed（新增：指纹删除、按物品取消请求、撤销后状态清空）。
- 真浏览器：alice 的「我的记录」有 5 个「撤销登记」按钮，点第一个 → 弹窗出现 → 确认后按钮变 4，物品卡片消失。
- 演示库用备份原样还原，没有留下测试数据。

## 留下的

- 撤销是硬删除，没有"回收站"；误删只能重新登记。
- 撤销没有通知对方的机制：对方下次打开列表时请求已经消失。
