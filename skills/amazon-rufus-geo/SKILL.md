---
name: amazon-rufus-geo
description: Amazon Rufus/COSMO GEO skill for Amazon sellers. Use when the user provides an ASIN, Amazon URL, listing copy, reviews, competitors, or asks for Rufus AI visibility, Rufus live Q&A, Amazon AI search/GEO optimization, listing audit, title/bullet/A+ rewrite, Q&A strategy, review mining, backend attribute consistency, category-pack listing audit, capture health, or why Rufus recommends competitors.
metadata:
  keywords:
    - amazon
    - rufus
    - cosmo
    - geo
    - asin
    - listing
    - amazon-seo
    - q-and-a
    - review-mining
    - browser-automation
---

# Amazon Rufus GEO

这个 skill 是融合版：保留 `amazon-rufus-geo` 的 Rufus/COSMO/GEO 判断能力，同时吸收 `amazon-rufus-listing-audit` 的工程化审计纪律。

它用来做三件事：

1. **Rufus live 问答采集**：连接已经登录 Amazon 买家账号的 Chrome，打开 Rufus，批量提问，保存真实回答。
2. **Rufus/COSMO Listing 优化**：根据 Rufus 回答、Listing、评论、竞品和后台字段，审计并优化标题、五点、A+、Q&A、图片/alt-text 和后台属性。
3. **类目化 Listing 审计**：按 Profile → Plan → Capture → Report 四阶段，输出 Capture Health、类目 N 维担忧地图、覆盖矩阵和运营执行清单。

默认输出语言：中文分析 + 英文美国站可直接使用文案。  
安全规则：不要索要、接收或输入 Amazon/GitHub 密码、验证码、token。需要登录时，让用户自己在浏览器窗口手动登录。

## 触发场景

用户出现以下任何内容时使用本 skill：

- 给出 ASIN 或 Amazon 链接，要分析、审计、优化、改文案。
- 询问 Rufus、COSMO、Amazon AI 搜索、GEO、AI 推荐、AI 搜不到我的产品。
- 要做竞品 Rufus 对比、Rufus live 问答、市场调研、买家需求挖掘。
- 要写/改标题、五点、描述/A+、Q&A、后台属性。
- 粘贴评论、差评、竞品文案，要挖掘卖点和风险。

## 一句话原则

不要把 Rufus GEO 做成“关键词堆砌”。要把 Listing 写成 Rufus 能引用的证据：

- 这个产品解决什么问题？
- 适合谁？
- 适合什么场景？
- 适合放在哪里/什么时候用？
- 和什么搭配？
- 不适合什么情况？
- 评论和 Q&A 有没有证明？

## 融合版默认纪律

每次任务按复杂度选择流程：

- **轻量流程**：用户只要快速判断、少量 ASIN、少量 live 问答时，使用当前 `SKILL.md` + `scripts/rufus_qa.py`。
- **稳健审计流程**：多 ASIN、竞品池、要给运营/美工执行、要给 Hermes 或另一个 AI 使用时，必须按 `references/14-integrated-audit-workflow.md` 执行，并优先使用 `scripts/capture_rufus_audit.py`。

稳健审计必须先写 Capture Health。失败率 > 30%、自家 Listing 没抓到、ASIN 漂移或 Rufus 答错产品时，不能把不完整数据包装成确定结论。细节见 `references/15-capture-health-output-schema.md`。

安全规则仍以本 skill 为准：不要索要、接收或输入 Amazon/GitHub 密码、验证码、token。需要登录时，让用户自己在浏览器窗口手动登录；agent 只连接已登录 Chrome。

## 类目包选择

先判断类目，再生成问题计划：

1. 用户明确指定类目 → 直接用。
2. 从 Amazon subcategory / title / product type 推断。
3. 宠物用品、dog harness、pet travel、cat litter box、pet training → 用 `pet_supplies`。
4. 识别不到 → 用 `_generic`，并在报告里说明“未使用专属类目包”。

现有类目包：

- `categories/pet_supplies/`：宠物用品，尤其适合 dog harness / pet travel / pet training。
- `categories/_generic/`：通用兜底。

类目包的用途不是堆关键词，而是把“买家问题 → Listing 证据 → 修改动作”映射起来。新建类目见 `references/16-category-pack-guide.md`。

## 标准执行流程

### A. 用户只给 ASIN

按下面顺序执行：

1. Profile：抓取公开 Listing 信息：标题、品牌、价格、评分、评论数、五点、A+、Product Overview、BSR、变体、图片/视频、Q&A、评论主题；抓不到写 `not_captured`。
2. Category：选择类目包，宠物用品用 `pet_supplies`。
3. Plan：用类目 N 维 + COSMO 15 关系生成问题计划。
4. Capture：如果 Chrome CDP 可用且用户已登录 Amazon，跑 Rufus live 问答；否则明确标注“未做 live Rufus，仅基于公开页面模拟”。
5. Report：先写 Capture Health，再写 Rufus 真实判断、类目担忧地图、COSMO 覆盖表、评分、根因、优先修复项、可执行文案建议。

### B. 用户说“跑 Rufus / live 问答”

1. 检查环境：

```bash
python3 scripts/check_rufus_env.py
curl http://127.0.0.1:9222/json/list
```

2. 如果没有 CDP，macOS 用：

```bash
open -na "Google Chrome" --args \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-rufus-profile \
  "https://www.amazon.com"
```

3. 让用户在这个新窗口里手动登录 Amazon 买家账号。
4. 准备问题文件，一行一个问题。
5. 少量问题用轻量脚本：

```bash
python3 scripts/rufus_qa.py \
  --cdp http://127.0.0.1:9222 \
  --keyword "<ASIN + product keyword>" \
  --questions questions.txt \
  --output rufus_results.json \
  --wait 45 \
  --pause 6
```

6. 多 ASIN / 需要 checkpoint / 需要健康报告时用稳健脚本：

```bash
python3 scripts/capture_rufus_audit.py \
  --asins B0OWN,B0COMP1,B0COMP2 \
  --roles own,competitor_1,competitor_2 \
  --category pet_supplies \
  --depth 15 \
  --output-dir out/rufus_audit
```

7. 有 `capture_baseline.csv` 后，可先生成报告骨架：

```bash
python3 scripts/build_rufus_report.py \
  --capture out/rufus_audit/capture_baseline.csv \
  --health out/rufus_audit/capture_health.json \
  --snapshots-dir out/rufus_audit \
  --own-asin B0OWN \
  --category pet_supplies \
  --output-dir out/rufus_audit
```

8. 分析 JSON/CSV 中的有效 `answer`；`rawPanelText` 只用于排查。失败行必须保留在 Capture Health 中。

### C. 用户说“帮我改文案”

不要直接改。先做最小审计：

1. 读当前标题、五点、描述/A+。
2. 判断 Rufus 认可的最佳人群和最佳场景。
3. 判断 Rufus 会质疑的弱场景。
4. 再输出“修改前 / 修改后 / 修改原因”。

必须包含：

- 标题前后对比。
- 5 条 Bullet 前后对比。
- A+ / Product Description 前后对比。
- 推荐新增 Q&A。
- 后台属性建议。
- 优先修复清单。

## COSMO 15 关系速查

审计任何具体 Listing 时，都要检查这 15 个关系：

| # | 关系 | 核心问题 | 常见 Rufus 问法 |
|---|---|---|---|
| 1 | USED_FOR_FUNC | 主要功能是什么？ | What does this product do? |
| 2 | USED_FOR_EVE | 适合什么活动/场合？ | What do I need for camping/apartment use? |
| 3 | USED_FOR_AUD | 为谁设计？ | Is this good for beginners/large cats/seniors? |
| 4 | CAPABLE_OF | 有什么能力？ | Can this reduce odor / fit a big cat? |
| 5 | USED_TO | 能完成什么具体任务？ | Can I use this to clean faster / reduce tracking? |
| 6 | USED_AS | 可以当什么用？ | Can this work as a top-entry/front-entry box? |
| 7 | IS_A | 属于什么品类？ | Is this a covered box, open pan, or top-entry box? |
| 8 | USED_ON | 什么时候用？ | Can it handle daily use / long workdays? |
| 9 | USED_IN_LOC | 在哪里用？ | Is this good for apartments/bathrooms/laundry rooms? |
| 10 | USED_IN_BODY | 作用于身体/适配身体条件？ | Is this comfortable for older or short-legged cats? |
| 11 | USED_WITH | 和什么搭配？ | What litter, mat, scoop, deodorizer works with it? |
| 12 | USED_BY | 实际谁在用？ | What kind of owners/cats is this for? |
| 13 | XINTERESTED_IN | 哪些兴趣人群会感兴趣？ | Is this good for low-maintenance/stainless steel shoppers? |
| 14 | XIS_A | 用户自我定位 | I have one large cat; is this right for me? |
| 15 | XWANT | 明确需求 | I want X that does Y; should I choose this? |

标记规则：

- `covered`：Listing 或 Rufus 回答能直接回答。
- `weak`：有一点证据，但模糊、间接、容易被竞品反驳。
- `missing`：完全没证据。

## Rufus Live 问题模板

给 ASIN 跑 live Rufus 时，至少问 5 个，完整审计问 15 个。把 `[ASIN]`、`[product]`、`[core scene]` 换成实际内容。

### 5 问快速版

1. What is [ASIN] mainly used for, and what problem does it solve?
2. Is [ASIN] good for [main target user]?
3. Is [ASIN] suitable for [core scene/location]?
4. What are the limitations of [ASIN] compared with alternatives?
5. I want [product] that [top 3 needs]. Should I choose [ASIN]?

### 15 问完整版

1. What is [ASIN] mainly used for, and what problem does it solve?
2. Is [ASIN] good for [main audience]?
3. Is [ASIN] suitable for [important scenario]?
4. Can [ASIN] [core capability]?
5. What specific tasks does [ASIN] make easier?
6. Can [ASIN] be used as [alternate use/category]?
7. What category is [ASIN], and how does it compare with alternatives?
8. Can [ASIN] handle daily use / seasonal use / long workdays?
9. Where is [ASIN] best used?
10. Is [ASIN] comfortable/suitable for [body condition/user condition]?
11. What accessories or compatible products work best with [ASIN]?
12. What kinds of users are a good fit for [ASIN]?
13. Is [ASIN] a good choice for people interested in [interest/value]?
14. I am [user identity]. Is [ASIN] right for me?
15. I want [specific needs]. Should I choose [ASIN]?

如果某题返回无关内容（例如触发 Scheduled actions），必须改写问题并重跑，不能把噪声算入审计。

## 评分标准

总分 100：

| 维度 | 分值 | 高分标准 |
|---|---:|---|
| 标题 | 15 | 品牌 + 核心词 + 主要场景 + 目标用户；前 80 字符有核心购买理由 |
| 五点 | 20 | 每条回答真实买家问题，覆盖 10 个以上 COSMO 关系 |
| 描述/A+ | 20 | 扩展场景、人群、对比信息、边界说明，图片 alt-text 完整 |
| Q&A | 25 | 至少 15 条，覆盖 10 个以上关系，含差评/疑虑预防式 Q&A |
| 数据一致性 | 10 | 标题、五点、A+、图片、后台尺寸/材质/数量一致 |
| 图片/Alt-text | 10 | 主图合规，场景图清晰，alt-text 描述“图里发生什么” |

评分时要给证据，不要只给分。

## 输出模板：ASIN 审计

```markdown
# [ASIN] Rufus GEO 审计报告

## 0. Capture Health
- 是否 live Rufus：
- 计划问题数 / 成功数：
- 失败原因：
- 数据是否足够支撑 gap 结论：

## 1. 产品概况
- ASIN：
- 品牌：
- 当前标题：
- 价格/评分/评论数/排名：
- 数据来源：

## 2. 类目与问题计划
- 类目包：
- 类目 N 维覆盖：
- COSMO 15 覆盖：

## 3. Rufus Live 结论
- 是否做了 live Rufus：
- Rufus 认可的场景：
- Rufus 质疑的场景：
- Rufus 推荐的竞品方向：
- 关键原话/摘要：

## 4. 类目担忧地图
| 维度 | 典型问题 | 我家证据 | 竞品证据 | 结论 |

## 5. COSMO 15 关系覆盖
| 关系 | 状态 | 证据 | 问题 |

## 6. 评分
| 维度 | 分数 | 证据 |

## 7. 根本问题
1.
2.
3.

## 8. 优先修复
| 优先级 | 动作 | 原因 |

## 9. 可执行优化建议
- 标题：
- 五点：
- A+：
- Q&A：
- 后台属性：

## 10. A10 / COSMO / Rufus 对齐说明

## 11. 风险与回测计划
```

## 输出模板：文案改写

```markdown
# [ASIN] Listing 文案优化前后对比

## 1. 标题前后对比
| 修改前 | 修改后 |
|---|---|

### 修改点说明
| 修改点 | 修改前问题 | 修改后收益 |

## 2. 五点描述前后对比
### Bullet 1
| 修改前 | 修改后 |
|---|---|
说明：

### Bullet 2...

## 3. A+ / Product Description 前后对比
### 修改前
### 修改后
### 修改点说明

## 4. Q&A 前后对比
### 修改前 Q&A 缺口
### 修改后建议新增 Q&A

## 5. 后台属性前后对比建议
| 字段 | 当前风险 | 建议修改后 |

## 6. 优先修复清单
```

## 文案写作规则

- 英文 Listing 文案要自然，不要关键词列表。
- 标题不要超过 200 字符，品牌尽量放前面。
- 每条 Bullet 最好覆盖 2-3 个 COSMO 关系。
- 不要写 Best / #1 / Amazing / Gift for Dad Men Him 这类堆砌词。
- 对 Rufus 已经质疑的场景，要诚实写边界，不要硬吹。
- 新品没有评论时，用竞品评论作为假设来源，但必须标注“来自竞品/推断”。

## Backend / 数据一致性检查

必须检查：

- 标题数量 vs 后台 Item Package Quantity。
- 标题材质 vs 后台 Material Type。
- 页面尺寸 vs A+ 尺寸 vs 后台尺寸。
- 主图颜色/款式 vs 文案颜色/款式。
- Unit Count / Unit Count Type 是否导致 `$xx per pound` 这类错误单位。
- Occasion、Target Audience、Special Features 是否和文案呼应。

发现冲突时，优先修数据，不要只改文案。

## 重要边界

- Rufus 推荐结果会变化；live 问答是诊断证据，不是永久排名承诺。
- 如果差评多、评分低、评论数远弱于竞品，要明确告诉用户：这不是文案能完全解决的问题。
- 如果没有 live Rufus 环境，要清楚标注“模拟审计”。
- 如果没有后台字段，只能给建议，不能假装已经验证。

## References

需要细节时再加载：

- `references/14-integrated-audit-workflow.md`：融合后的 Profile → Plan → Capture → Report 流程。
- `references/15-capture-health-output-schema.md`：Capture Health、覆盖矩阵和报告骨架。
- `references/16-category-pack-guide.md`：类目包机制和新类目创建方法。
- `categories/pet_supplies/`：宠物用品类目包。
- `categories/_generic/`：通用兜底类目包。
- `references/cosmo-intent-mapping.md`：COSMO 15 关系完整定义。
- `references/10-audit-flow.md`：完整审计流程。
- `references/scoring-rubric.md`：评分细则。
- `references/03-title-formula.md`：标题公式。
- `references/04-bullet-formula.md`：五点公式。
- `references/05-description-aplus.md`：描述/A+。
- `references/06-qa-engineering.md`：Q&A 模板。
- `references/07-backend-attributes.md`：后台属性。
- `references/08-review-mining.md`：评论挖掘。
- `references/11-competitor-analysis.md`：竞品矩阵。
- `references/12-visibility-diagnosis.md`：可见性诊断。
- `references/13-rufus-qa-automation.md`：当前安全 CDP 自动化说明。
