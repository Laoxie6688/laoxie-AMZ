# Capture Health And Output Schema

## Capture Health 闸门

报告开头必须写：

- 任务时间
- marketplace
- 产品数：own + competitors
- 计划提问数
- answered / question_only / blocked / out_of_scope
- 成功率
- 主要失败原因
- 自家 Listing 是否抓到
- 是否影响结论

规则：

- 失败行占比 > 30%：报告顶部必须警告，不能直接做确定性 gap 结论。
- 自家 Listing 没抓到：只能输出竞品担忧地图，不能说“我家缺失”。
- ASIN 漂移或回答明显答错产品：标 `out_of_scope`，不计入结论。
- Rufus live 失败但 listing 可抓：标“公开页面 + 模拟诊断”。

## 覆盖矩阵字段

```csv
担忧描述,维度,优先级,优先级标签,我家覆盖,标题证据,bullet证据,图片证据,A+证据,Q&A证据,review证据,gap类型,改哪里,具体怎么改,预期Rufus收益,信心
```

覆盖状态：

- `strong`：标题/五点/A+/Q&A 有直接证据。
- `partial`：有证据但不完整。
- `weak`：只有模糊表达，容易被竞品反驳。
- `missing`：没有受控内容证据。
- `review_only`：评论里有，但 Listing 没有。
- `contradicted`：Listing 和评论/图片/后台冲突。

## 报告骨架脚本

如果有 `capture_baseline.csv`，可先聚合骨架：

```bash
python3 scripts/build_rufus_report.py \
  --capture out/rufus_audit/capture_baseline.csv \
  --health out/rufus_audit/capture_health.json \
  --snapshots-dir out/rufus_audit \
  --own-asin B0OWN \
  --category pet_supplies \
  --output-dir out/rufus_audit
```

脚本只做确定性聚合；最终 gap 判断和文案方案仍由 agent 结合业务上下文完成。
