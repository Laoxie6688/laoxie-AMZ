# Category Pack Guide

类目包放在 `categories/<category>/`，至少包含：

- `pack.yaml`
- `question-taxonomy.md`
- `product-profile.md`
- `fix-playbook.md`

## pack.yaml 必备字段

- `name`
- `display_name`
- `trigger_subcategories`
- `dimensions`
- `critical_dimensions`
- `min_question_set`
- `profile_required_fields`
- `files`

## 选择类目

优先级：

1. 用户明确指定。
2. 从 Amazon subcategory / title / product type 推断。
3. 有宠物用品、dog harness、pet travel、cat litter box 等信号时用 `pet_supplies`。
4. 识别不到时用 `_generic`，并在报告里说明“未使用专属类目包”。

## 新建类目包时

每个维度都要能回答：

- Rufus 会怎么问？
- 买家真实担忧是什么？
- Listing 哪个位置能提供证据？
- 改图、Bullet、A+、Q&A 分别该怎么承接？

不要把类目包写成关键词列表；它应该是“买家问题 → 证据 → 修改动作”的映射。
