# 2026-10-22 · 本地库换成 6 个账号的多用户演示数据

## 要求

- 直接灌进本地 `items.db`；
- 账号密码全部等于用户名；多建几个账号；
- 每个账号都要有几件失物、几件拾获；描述要像真实用户随手输入的。

## 账号

`create_demo_users.py` 从 3 个账号扩到 6 个：alice / bob / carol / david / erin / frank，
密码就是用户名本身（原来 alice 是 `demo-pass-alice`、demo 是 `Demo@1234`）。
`config_auth.yaml` 已用 `--force` 重新生成，**cookie key 也换了，旧登录态全部失效**，重新登录即可。

## 数据

`seed_demo.py` 不再是 bob 拾获 / alice 失物的 1:1：

- 12 张照片按 2 张一组分给 6 个账号（每人 2 件拾获）；
- 12 条对应失物分给**另一个**账号（A 捡到、B 报失），每人再补 1 条没有对应照片的干扰失物；
- 最终每人 2 件拾获 + 3 件失物，全库 30 件物品；
- 文案改成用户口吻（`在图书馆三楼捡到的…`、`白色充电宝丢了，塑料的…`），拾获与失物换一种说法，只保留能核对的事实。

## 破坏性操作与回滚

重灌前备份了旧库：`items.db.bak-20261022`（22 MB，含旧的 pending 请求与通知）。
旧库的 4 对演示数据、`settings.yaml` 里的 key 都不受影响。

## 验证

```text
账号：6 个，bcrypt.checkpw(用户名) 全部 True
items 30 / users 6 / lost_items 18 / found_items 12 / item_fingerprints 30
每人：2 件拾获 + 3 件失物
evaluate  prior=on   Recall@1=11/12  Recall@5=12/12  MRR=0.944
evaluate  prior=off  Recall@1=10/12  Recall@5=12/12  MRR=0.903
pytest -q  108 passed；streamlit HTTP 200
```

漏掉的 top-1 是耳机：失物写的是“黑色头戴式耳机…AKG”，但黑耳机照片的 CLIP 相似度低于黑色行李箱
（0.459），耳机排第 3。这是文字改口语之后暴露出来的排序问题，不是数据写错；
记录在此，暂不调权重。

## 后续

- 演示时建议走 alice 捡到充电宝 / bob 报失充电宝这条线，双方在不同账号里；
- 干扰失物（蓝色保温杯、钥匙串、眼镜盒等）没有照片对应，正好用来展示“候选里混进无关物品”；
- 想回到旧库：停掉应用，`mv items.db.bak-20261022 items.db`。
