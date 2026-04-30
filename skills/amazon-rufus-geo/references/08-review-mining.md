# 08-review-mining.md — 评论挖掘反向工程

> **使用时机**：这是一个独立流程，可在任何阶段触发。
> 当有评论数据时（自有或竞品），先做评论挖掘，再开始写作，质量提升最大。
> ROI 最高的单项优化动作。

---

## 一、评论挖掘的底层逻辑

Rufus 把 UGC（评论+Q&A）当作 Ground Truth，对用户说的话的信任度 > 品牌自述。

**最聪明的 listing 策略**：让 listing 的语言和评论里的语言对齐，让 RAG 检索时证据权重叠加。

```
评论里用户说 "I use this every weekend for day hikes"
↓
五点描述里写 "for weekend day hikes"
↓
Rufus 做 RAG 时：文案证据 + UGC 证据双重叠加 → 置信度最高
```

---

## 二、评论获取方法

### 美国站（amazon.com）
使用 LinkFox Agent MCP 工具 `@亚马逊-商品评论(美国站)`：

```
分别抓取：
1. star=positive / five_star，排序=recent，10页（100条好评）
2. star=critical / one_star，排序=recent，10页（100条差评）
3. 竞品同上，每个竞品分次调用（每次仅支持1个ASIN）
```

### 非美国站
使用 `linkfox-amazon-reviews` API：

```json
{
  "asin": "ASIN_HERE",
  "domainCode": "ca",
  "star4Num": 20,
  "star5Num": 20,
  "star1Num": 20,
  "star2Num": 20,
  "sortBy": "recent"
}
```

---

## 三、评论标注方法（COSMO 15 关系反向标注）

对每条评论，识别它在讲哪种 COSMO 关系，摘出关键词/句式：

### 标注示例

**原评论：**
> "I use this backpack every weekend for day hikes in the White Mountains"

**标注结果：**
```
USED_FOR_EVE = weekend day hikes
USED_IN_LOC = White Mountains
USED_ON = weekend
```

---

**原评论：**
> "As a 5'2" woman I finally found a pack that doesn't swallow me"

**标注结果：**
```
XIS_A = short woman (5'2")
USED_FOR_AUD = women with smaller frames
USED_IN_BODY = torso fit
```

---

**原评论：**
> "The hipbelt pocket fits my iPhone 15 Pro Max perfectly"

**标注结果：**
```
CAPABLE_OF = iPhone 15 Pro Max compatible
USED_TO = carry phone while hiking
```

---

## 四、生成"买家真实语言词库"

按 COSMO 15 种关系分类，汇总所有出现过的用户原词/原句：

| COSMO 关系 | 用户原话（直接引用） | 出现频率 |
|-----------|-------------------|---------|
| USED_FOR_EVE | | |
| USED_FOR_AUD | | |
| USED_ON | | |
| USED_IN_LOC | | |
| USED_IN_BODY | | |
| CAPABLE_OF | | |
| USED_BY | | |
| XIS_A | | |
| XWANT | | |

**高频词 = 优先回灌到 listing 的词。**

---

## 五、差评分析（负面信号处理）

### 差评高频主题提取

| 差评主题 | 出现次数 | 严重程度 | 处理方式 |
|---------|---------|---------|---------|
| | | | 预防式Q&A / 产品改进 / 诚实说明 |

### 处理决策树

```
差评主题是什么？
├── 产品本身的设计缺陷？
│   ├── 已改进 → 在Q&A里说明改进情况
│   └── 未改进 → 诚实说明限制，给出替代建议
│
├── 使用方法问题（用户误用）？
│   └── 写预防式Q&A，主动说明正确用法
│
└── 与竞品对比的劣势？
    └── 承认并说明适用场景（你的产品适合谁，竞品适合谁）
```

### 预防式 Q&A 示例

**差评高频：** "The hipbelt rubs my hips raw after 10 miles"

**预防式 Q&A：**
```
Q: Does the hipbelt work for users with wider hips?
A: Our standard hipbelt fits waist sizes 28-42 inches. For users with
   wider hips or extended long-distance hikes (20+ miles/day), we
   recommend sizing up to our XL hipbelt (sold separately) which uses
   softer foam padding. The standard belt is designed for weekend trips
   up to 15 miles/day.
```

**关键原则：** 诚实承认限制 > 强行掩盖。Rufus 宁可读到品牌坦诚回答产品局限，也不愿看到差评里用户愤怒的指控。

---

## 六、评论挖掘结果回灌

### 回灌优先级

| 回灌目标 | 优先级 | 具体操作 |
|---------|--------|---------|
| 五点描述 | 🔴 最高 | 把词库里的高频词自然融入五点场景句 |
| Q&A | 🔴 最高 | 把高频问题写成Q&A预先发布 |
| 产品描述/A+ | 🟡 高 | 把高频 "I am ___" 自称写进人群分区 |
| 后台搜索词 | 🟡 高 | 把高频长尾短语加入搜索词 |
| A+ alt-text | 🟢 建议 | 把高频场景词融入图片描述 |

### 回灌写作原则

**回灌不是照抄。** 要保持评论里那种"真实买家在描述自己使用体验"的语感，不要翻译成营销腔。

```
❌ 照抄：直接把评论内容粘进五点
❌ 营销腔：把 "great for weekend hikes" 改成 "The ultimate weekend hiking companion"
✅ 正确：自然融入场景句，语气和评论一致，但句子是自己写的
```

---

## 七、效果追踪

执行完整评论挖掘回灌后，约 **2-4 周**内可通过以下指标观察提升：

- **Brand Analytics 搜索词报告**：观察新进入的长尾词
- **Rufus 对话测试**：重新跑 15 问模拟，比较 ✅/⚠️/❌ 变化
- **转化率**：对比回灌前后同时段数据

---

## 八、评论挖掘自检清单

- [ ] 好评 ≥ 20 条（自有 or 竞品）
- [ ] 差评 ≥ 10 条（自有 or 竞品）
- [ ] 按 COSMO 关系标注完成
- [ ] 词库已按关系分类整理
- [ ] 差评高频主题已识别（≥ 3 个）
- [ ] 预防式 Q&A 已为每个差评主题生成
- [ ] 回灌到五点/Q&A 完成
