# 06-qa-engineering.md — Q&A 工程模板

> **使用时机**：产品描述/A+ 写完后，生成 Q&A。
> Q&A 是 Rufus 时代权重最高的单项（25分），也是唯一能"主动控制"的高权重 UGC 信号。

---

## 一、为什么 Q&A 权重最高

Rufus 的 RAG 检索源明确包含 customer Q&As，且 Rufus 对 UGC 的信任度**高于**品牌自述。
- 品牌在五点里说 "waterproof" = 品牌声明
- 买家在 Q&A 里问 "Is this waterproof?" 品牌回答 "Yes, IP68 tested in 3-day rainstorm" = 有问有答的 UGC 证据

Rufus 会优先引用后者。**Q&A 是你能主动控制的最高权重信号。**

---

## 二、Q&A 来源优先级

| 来源 | 说明 | 优先级 |
|------|------|--------|
| 评论里的高频问题 | 真实买家问过的 | 🔴 最高 |
| 15 问模拟中 ⚠️/❌ 的关系 | 文案覆盖不足的维度 | 🔴 高 |
| 竞品 Q&A 里出现但自家没有的 | 品类通用问题 | 🟡 中 |
| Rufus 偏好的问题类型（见下） | 主动补充 | 🟡 中 |
| 预防式 Q&A（差评顾虑） | 把差评转化为正面信号 | 🟢 建议 |

---

## 三、Rufus 最偏好的 5 类 Q&A（按召回频率）

| 类型 | 句式模板 | 对应 COSMO 关系 |
|------|---------|---------------|
| 能力确认 | "Can this [action]?" | CAPABLE_OF |
| 人群适配 | "Is this good for [people/situation]?" | USED_FOR_AUD / XIS_A |
| 耐久度 | "How long does it last? How durable is it?" | CAPABLE_OF + USED_BY |
| 搭配询问 | "What comes with it? What do I need with it?" | USED_WITH |
| 特性确认 | "Is this waterproof / machine-washable?" | CAPABLE_OF |

---

## 四、15 条 Q&A 生成模板

目标：**至少 15 条**，覆盖 10 种以上 COSMO 关系。

### 必须包含的 Q&A（10条，覆盖核心关系）

**Q1 — CAPABLE_OF（核心能力）**
```
Q: Can this [产品] [核心能力动作]?
A: Yes. [具体数据/测试场景]. [使用场景补充，2-3句话].
```

**Q2 — USED_FOR_EVE（使用场合）**
```
Q: Is this [产品] good for [具体活动]?
A: [直接回答 Yes/It depends]. [说明适合哪种规模/强度的该活动].
   [如果有限制，诚实说明].
```

**Q3 — USED_FOR_AUD（目标人群）**
```
Q: Is this [产品] suitable for [人群，如 beginners / kids / seniors]?
A: [直接回答]. [说明为什么适合/不适合]. [给出替代建议（如不适合）].
```

**Q4 — USED_ON（季节/时段）**
```
Q: Can I use this [产品] in [季节/极端天气条件]?
A: [直接回答]. [说明具体性能参数与该条件的关系].
   [如果全季通用，明确说明 all-season].
```

**Q5 — USED_IN_LOC（地点/环境）**
```
Q: Is this [产品] good for [特定地点/环境，如 rainforest / desert / urban]?
A: [直接回答]. [说明产品哪个特性使其适合该环境].
```

**Q6 — USED_WITH（搭配）**
```
Q: What [配件类型] works with this [产品]?
A: [列出兼容的具体品牌/型号]. [说明兼容原因或规格参数].
```

**Q7 — USED_IN_BODY（身体部位，有接触产品必填）**
```
Q: Will this [产品] hurt my [身体部位] on long [活动]?
A: [诚实回答]. [说明产品如何减轻该部位压力]. [如有限制，说明调整建议].
```

**Q8 — XIS_A（用户自我定位）**
```
Q: I'm a [用户自称，如 5'2" woman / beginner hiker / ultralight enthusiast],
   is this [产品] right for me?
A: [直接回答]. [说明具体适配原因]. [如有边界条件，说清楚].
```

**Q9 — XWANT（明确需求）**
```
Q: I need a [产品] that [具体需求，如 fits airline carry-on / holds a tent outside].
   Does this work?
A: [直接回答]. [给出具体尺寸/参数]. [如不完全满足，说明替代方案].
```

**Q10 — 预防式 Q&A（差评高频顾虑）**
```
Q: [把差评里最高频的负面问题转成问句]
A: [诚实、中性的回答]. [说明产品的实际限制]. [给出解决建议].
```

---

### 建议额外添加的 Q&A（5条，提升覆盖率）

**Q11 — USED_TO（具体任务）**
```
Q: Can I use this [产品] to [具体任务，如 carry climbing gear / store a laptop]?
A: [直接回答]. [说明如何实现该任务].
```

**Q12 — USED_AS（替代用法）**
```
Q: Can this [产品] double as [替代用法，如 a carry-on / a gym bag]?
A: [直接回答]. [说明具体尺寸/条件]. [如有限制，诚实说明].
```

**Q13 — USED_BY（实际用户）**
```
Q: What kind of [活动类型] people use this [产品]?
A: [描述主要用户群]. [引用真实评论里的用户自称（如有）].
```

**Q14 — XINTERESTED_IN（理念型用户）**
```
Q: Is this [产品] suitable for [理念型用户，如 minimalists / eco-conscious shoppers]?
A: [回答]. [说明产品有哪些特性吸引这类用户].
```

**Q15 — 包装/附件确认**
```
Q: What's included in the box?
A: [完整包装清单，每项一句]. [说明哪些配件需要单独购买].
```

---

## 五、Q&A 写作规范

**语气要求：**
- 像真实买家问答，不像品牌公关稿
- 回答要具体（有数据、有场景），不要模糊（"it depends" 要接着说 depends on what）
- 诚实承认限制，Rufus 宁可看到诚实的局限声明，也不要看到夸大的营销承诺

**禁止写法：**
- ❌ "This is the best backpack on the market"
- ❌ "Our product is perfect for everyone"
- ❌ 一句话回答（太短，Rufus 无法从中提取有用信息）
- ❌ 回答里出现 "amazing" / "incredible" / "world-class" 等营销词

**推荐长度：**
- 问题（Q）：1-2 句自然语言
- 回答（A）：3-5 句，包含具体数据或场景

---

## 六、Q&A 自检清单

- [ ] 总数量 ≥ 15 条
- [ ] 覆盖 COSMO 关系 ≥ 10 种
- [ ] 包含至少 1 条预防式 Q&A（来自差评）
- [ ] 品牌方已回答所有关键问题（不只是买家问，也要有品牌回答）
- [ ] 每条回答 ≥ 3 句，包含具体场景/数据
- [ ] 没有营销腔（无 "amazing" / "best" / "perfect for everyone"）
- [ ] 评论里高频出现的问题已在 Q&A 中预先回答

**完成后，进入 Step 8：读取 07-backend-attributes.md，填写后台属性建议。**
