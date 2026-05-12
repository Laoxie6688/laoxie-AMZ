# Integrated Rufus GEO Workflow

融合版默认按四阶段执行：Profile → Plan → Capture → Report。

## 1. Profile

先建产品档案，不直接下结论。每个 ASIN 至少抓：

- title、brand、price、rating、review count、BSR
- bullets、Product Overview、detail bullets
- A+ 摘要、图片/视频数量、Q&A、review themes
- 类目 pack 要求的字段，例如 pet_supplies 的 fit_size、included_components、travel_safety_features

抓不到的字段写 `not_captured`，不要猜。

## 2. Plan

根据产品档案和类目 pack 生成问题计划。每个问题要有：

- planned_question_id
- question_text
- question_origin：starter / profile_generated / category_coverage / user_supplied
- primary_dimension
- sub_category
- priority_score

没有专属类目时用 `_generic`。宠物用品优先用 `pet_supplies`。

## 3. Capture

优先使用用户已登录的 Chrome CDP。不要索要或输入密码。

两种采集模式：

- 轻量快速：`scripts/rufus_qa.py`，适合少量 live 问答。
- 稳健审计：`scripts/capture_rufus_audit.py`，适合多 ASIN、多问题、需要 checkpoint 和健康报告的任务。

稳健审计示例：

```bash
python3 scripts/capture_rufus_audit.py \
  --asins B0OWN,B0COMP1,B0COMP2 \
  --roles own,competitor_1,competitor_2 \
  --category pet_supplies \
  --depth 15 \
  --output-dir out/rufus_audit
```

## 4. Report

任何报告先写 Capture Health，再写结论：

1. Capture Health
2. 执行摘要
3. 产品档案
4. 类目 N 维担忧地图
5. COSMO 15 覆盖
6. Listing 覆盖矩阵
7. 优先级修复清单
8. Title / Bullet / A+ / Q&A / Backend 修改建议
9. A10 / COSMO / Rufus 对齐说明
10. 风险、限制、回测计划

失败率高或自家 Listing 缺失时，不允许把不完整数据包装成确定结论。
