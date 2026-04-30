# 04-bullet-formula.md — 五点描述写作公式

> **使用时机**：标题写完后，写五点描述。
> 五点是 Rufus RAG 检索的核心文本来源，每条 bullet 都应该是一个完整的"场景-痛点-解决"三元组。

---

## 一、核心写作公式

```
场景痛点 → 独特机制 → 技术支撑
```

**为什么用这个公式而不是 FAB（Feature-Advantage-Benefit）？**

FAB 是"功能先行"，Rufus 时代要"场景先行"。Rufus 做 RAG 时召回的是整句话，一个句子里要同时出现 `场景 + 痛点 + 解决方式` 三要素才能被完整引用。

---

## 二、三种写法对比（以登山包防水为例）

### ❌ 规格堆砌（最差）
```
IP68 waterproof, 60L capacity, aluminum frame, ventilated back panel
```
Rufus 无法从这句话里提取场景，无法召回。

### ⚠️ 功能优先 FAB（一般）
```
IP68 waterproof rating (F), higher than competitors (A), works in rain (B)
```
有改善，但仍然是"品牌自述"，Rufus 信任度低于 UGC。

### ✅ 场景优先（最佳）
```
Caught in a three-day rainstorm on the AT? Your gear stays bone dry.
The fully taped seams and roll-top closure give you full submersion-level
protection — not just the 'water-resistant' nylon most packs rely on —
so you can pitch camp in a downpour without repacking wet clothes.
```

**这一句自然覆盖了 5 种 COSMO 关系：**
- USED_ON（three-day rainstorm）
- USED_IN_LOC（AT 步道）
- USED_FOR_EVE（露营）
- CAPABLE_OF（防水等级）
- USED_FOR_FUNC（保持装备干燥）

---

## 三、五条描述的维度分配

每条 bullet 至少承载 2-3 种 COSMO 关系：

| 条目 | 主要维度 | COSMO 关系 | 字符目标 |
|------|---------|-----------|---------|
| **Bullet 1** | 核心功能 + 最大卖点 | USED_FOR_FUNC + CAPABLE_OF | 200-300字符 |
| **Bullet 2** | 材质/品质 + 耐久性 | CAPABLE_OF + USED_BY（社会证明） | 200-300字符 |
| **Bullet 3** | 使用场景 + 目标人群 | USED_FOR_EVE + USED_FOR_AUD + USED_ON/USED_IN_LOC | 200-400字符 |
| **Bullet 4** | 差异化 + 互补搭配 | USED_AS + USED_WITH | 150-300字符 |
| **Bullet 5** | 包装内容 + 售后保障 | XWANT（风险消除）+ XIS_A（用户定位） | 150-250字符 |

---

## 四、逐条写作指引

### Bullet 1：核心功能 + 最大卖点
**公式：** `[痛点场景开头] + [产品解决方式] + [技术支撑]`

开头选项（从 cosmo-intent-mapping.md 触发词库选）：
- `Designed to [解决什么问题]`
- `[场景痛点]? [产品名] [解决方式]`
- `The [产品核心功能] that [用户得到什么]`

示例：
```
Designed to carry 4-7 days of backcountry gear without destroying
your lower back — the internal aluminum stay transfers 70% of pack
weight from your shoulders to your hips, so mile 15 feels like mile 5.
```

---

### Bullet 2：材质/品质 + 社会证明
**公式：** `[用户群体] + [信任/认可] + [材质能力故事]`

开头选项：
- `Trusted by [用户群体]`
- `[材质名], the same material used in [知名应用场景]`
- `Built to last [具体时长/里程/次数]`

示例：
```
Trusted by Pacific Crest Trail thru-hikers across 2,650 miles —
the 210D nylon ripstop body resists abrasion from granite scrambles
and tree branches without adding a single ounce of unnecessary weight.
```

---

### Bullet 3：使用场景 + 目标人群
**公式：** `[具体活动] + [具体人群] + [为什么适合他们]`

开头选项：
- `Ideal for [具体活动] and [另一个活动]`
- `Whether you're [人群A] or [人群B]`
- `Perfect for [季节] [活动] in [地点]`

示例：
```
Ideal for weekend camping trips, 3-5 day thru-hikes, and hut-to-hut
trekking in the Alps — the adjustable torso (15-21 inches) fits both
5'0" beginners and 6'3" seasoned hikers without a trip to the gear shop.
```

---

### Bullet 4：差异化 + 互补搭配
**公式：** `[跨界用法 or 独特差异] + [搭配产品/兼容性]`

开头选项：
- `Doubles as [跨界用法]`
- `Compatible with [知名品牌配件]`
- `Unlike [竞品通病], [我们的差异化]`

示例：
```
At 40L with a clamshell opening, doubles as a carry-on for budget airline
travel (fits United/Delta/American personal item dimensions). Pairs
seamlessly with Osprey, Platypus, and CamelBak 3L hydration bladders.
```

---

### Bullet 5：包装内容 + 风险消除
**公式：** `[包装清单] + [保修/保障] + [用户自我定位收尾]`

开头选项：
- `Includes [完整包装清单]`
- `If you need [明确需求], this is your pack`
- `For [用户类型] who [需求描述]`

示例：
```
Includes pack, integrated rain cover, stuff sack, and lifetime repair
guarantee. If you need a single pack that handles everything from your
first overnight to a multi-week expedition, this is it.
```

---

## 五、五点描述整体自检

写完五条后，对照以下清单：

- [ ] 每条 bullet 都以**场景/痛点/用户**开头，不以规格/数字开头
- [ ] 每条 bullet 承载至少 2 种 COSMO 关系
- [ ] 15 种 COSMO 关系中，至少 10 种在五点里有覆盖
- [ ] 没有纯规格罗列的 bullet（如 "IP68, 60L, 2.1lbs"）
- [ ] 每条字符在 150-400 之间
- [ ] 读出来像真实卖家在描述产品体验，不像 SEO 文案
- [ ] **USED_FOR_EVE（场合）和 USED_ON（季节）都有覆盖**（最常被漏）

---

## 六、COSMO 覆盖率目标

| COSMO 关系 | 五点中的落点 | 优先级 |
|-----------|------------|--------|
| USED_FOR_FUNC | Bullet 1 | 必须 |
| CAPABLE_OF | Bullet 1-2 | 必须 |
| USED_FOR_EVE | Bullet 3 | 必须 ⚠️ |
| USED_FOR_AUD | Bullet 3 | 必须 |
| USED_BY | Bullet 2 | 强烈建议 |
| USED_WITH | Bullet 4 | 强烈建议 |
| USED_AS | Bullet 4 | 强烈建议 |
| USED_ON | Bullet 3 | 强烈建议 ⚠️ |
| USED_IN_LOC | Bullet 3 | 建议 |
| USED_IN_BODY | Bullet 1-2 | 有身体接触必须 |
| XWANT | Bullet 5 | 建议 |
| XIS_A | Bullet 5 | 建议 |

**完成五点后，进入 Step 6：读取 05-description-aplus.md，写产品描述/A+。**
