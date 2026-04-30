# COSMO 15 关系类型 × Rufus 意图映射指南

> **Skill 使用者注意**:当 SKILL.md 的审计流程、10 问模拟、或撰写模板需要展开到"具体要写什么词、覆盖什么维度"时,请完整读取本文件。这是整个 Skill 的**知识底座**。

---

## 一、这份文件是什么,凭什么权威

COSMO 不是"四种意图"。它是亚马逊 2024 年 SIGMOD 论文提出的电商常识知识图谱,定义了 **15 种结构化的产品-用户关系类型**(Relation Types),用 `(head, relation, tail)` 三元组组织用户行为数据,再把这些知识喂给下游的搜索、推荐和 Rufus。

**原论文**:*COSMO: A Large-Scale E-commerce Common Sense Knowledge Generation and Serving System at Amazon*,Changlong Yu 等,SIGMOD-Companion 2024。论文里 COSMO 是系统名,**不是首字母缩写**,不要展开成 "Common Sense Model for Online Shopping"——那是网上流传的错误版本。

**为什么用"登山背包 / 露营装备"做全文案例**:这是亚马逊自己选的 Rufus 代言品类。下面这 7 条是 Rufus 发布期间亚马逊官方和权威媒体实际使用的查询样例,**不是编的**:

| # | 亚马逊 Rufus 样例原话 | 出处 |
|---|---|---|
| 1 | "What do I need for camping?" | Amazon Canada Rufus 发布稿, 2024-10 |
| 2 | "What are the best options for a durable backpack?" | Amazon Canada Rufus 发布稿, 2024-10 |
| 3 | "What's the material of the backpack?" | Amazon 官方 Rufus 使用指南 (aboutamazon.com) + TechCrunch 报道 |
| 4 | "What do I need for cold weather golf?" | Amazon 官方 Rufus 全球发布稿, 2024-02 |
| 5 | "planning a camping trip" | AWS Machine Learning Blog (Rufus on Bedrock), 2025-11 |
| 6 | "What's the best hiking backpack for a weekend trip?" | Incrementum Digital Rufus 广告优化指南 |
| 7 | "What's the best water filter for camping in freezing temperatures?" | Cosmy Rufus Guide, 2025-11 |

**落地原则**:卖家 listing 里出现的句子,越接近这 7 条官方原话的结构,就越容易被 Rufus 的 RAG 检索召回。15 种 COSMO 关系就是把这 7 条原话的"语义维度"拆解成的可执行清单。

---

## 二、15 种关系速查表(先看这张)

| # | Relation | 中文 | 核心问题 | 在 Rufus 里触发什么样的用户提问 |
|---|---|---|---|---|
| 1 | USED_FOR_FUNC | 功能用途 | 这个产品能做什么? | "What does this backpack do?" |
| 2 | USED_FOR_EVE | 适用场合/活动 | 什么场合/活动用? | "What do I need for camping?" |
| 3 | USED_FOR_AUD | 目标人群 | 为谁设计? | "Good hiking backpack for beginners?" |
| 4 | CAPABLE_OF | 能力特性 | 有什么能力/性能? | "Can this backpack hold a 15-inch laptop?" |
| 5 | USED_TO | 用来(具体任务) | 用来做什么具体动作? | "Can I use this to carry climbing gear?" |
| 6 | USED_AS | 用作(本质/替代用法) | 可以当什么用? | "Can this work as a carry-on?" |
| 7 | IS_A | 品类归属 | 属于哪一类? | (系统级,不直接对话) |
| 8 | USED_ON | 时间/季节 | 什么时候/季节用? | "Best backpack for winter hikes?" |
| 9 | USED_IN_LOC | 地点/环境 | 在哪里/什么环境用? | "Good backpack for rainforest trekking?" |
| 10 | USED_IN_BODY | 身体部位 | 作用于身体哪? | "Which backpack won't hurt my shoulders?" |
| 11 | USED_WITH | 搭配产品 | 和什么一起用? | "What accessories go with this backpack?" |
| 12 | USED_BY | 使用者群体 | 谁在用? | "What backpack do thru-hikers use?" |
| 13 | XINTERESTED_IN | 潜在兴趣 | 哪些人可能会感兴趣? | "Lightweight backpacks for minimalists?" |
| 14 | XIS_A | 用户自我定位 | 我是什么样的用户? | "I'm looking for a 60L backpack…" |
| 15 | XWANT | 明确需求 | 我想要什么? | "I want a waterproof backpack under $100" |

**粗略分组**(便于记忆):
- **1-6 商品本体意图**:产品能做什么 / 用在哪类活动上 / 给谁用 / 有什么能力 / 具体任务 / 本质归类
- **7-12 使用情境意图**:属于什么品类 / 什么时间 / 什么地点 / 身体部位 / 搭配什么 / 被谁使用
- **13-15 用户主观意图**:对什么感兴趣 / 自己是谁 / 明确想要什么

---

## 三、15 种关系完整展开

每一种关系都包含 6 个字段,写 listing 或做审计时逐字段对照。

---

### 1. USED_FOR_FUNC(用于-功能)

**定义**:描述商品最主要的功能或用途。回答"这个产品是做什么的"这个最根本的问题。

**COSMO 论文示例** → 三元组:`(登山背包, USED_FOR_FUNC, 携带登山装备)`

**Rufus 实际会问的话**:
- "What is a hiking backpack designed for?"
- "What does this backpack do?"
- (针对具体产品)"What's the main purpose of this 60L pack?"

**英文触发词库**(listing 里要出现这些结构):
`is used for` / `is designed for` / `serves as` / `enables` / `provides` / `offers` / `features` / `is intended for` / `is designed to` / `aims to` / `The purpose of` / `The main function of`

**登山背包示例句**:
> "Our 60L trekking backpack **is designed to** carry 4-7 days of gear for long-distance hikes, with a load-bearing frame that transfers weight from your shoulders to your hips."

**Listing 落点**:
- 标题后半段(功能说明)
- 五点描述第 1 条(核心功能)
- A+ 第一屏标题图文

**写作前自检话术**:
- 这个产品的主要功能是什么?
- 用户购买它主要是为了解决什么问题?
- 如果只能用一句话告诉 Rufus 这是个什么东西,你会怎么说?

---

### 2. USED_FOR_EVE(用于-事件/场合)

**定义**:描述商品适用于什么特定事件、活动或场合。这是 Rufus 最高频触发的关系之一,因为亚马逊发布稿里 "shop by occasion or purpose" 这个能力就是靠这个关系支撑的。

**COSMO 论文示例** → 三元组:`(50L 登山包, USED_FOR_EVE, 5日长途徒步)`

**Rufus 实际会问的话**(这是官方原话,直接引用):
- **"What do I need for camping?"** — Amazon Canada 发布稿原句
- **"What do I need for cold weather golf?"** — Amazon 官方全球发布稿原句
- **"What's the best hiking backpack for a weekend trip?"** — Incrementum Digital 行业指南
- **"planning a camping trip"** — AWS ML Blog

**英文触发词库**:
`is used for` / `is best for` / `is ideal for` / `is suited for` / `is perfect for` / `great for` / `made for [activity]` / `ready for`

**登山背包示例句**:
> "**Ideal for weekend camping trips and 2-3 day thru-hikes**, this pack holds everything from a 2-person tent to a week's worth of dehydrated meals without bulging at the seams."

**Listing 落点**:
- 标题末段(场景化长尾)
- 五点描述第 3 条(使用场景)
- A+ 生活场景图说明
- **后台属性 Occasion / Activity**

**写作前自检话术**:
- 这个产品最适合什么活动?(越具体越好:不要写 "outdoor",写 "weekend camping" "thru-hiking" "day hike")
- 用户在什么场合会想到要买它?
- 有没有哪个节日或季节活动是它的核心场景?

**⚠️ 这个关系最容易被漏掉,也是 Rufus 最依赖的**。如果五点描述里没有任何一条提到具体活动名,审计时直接扣分。

---

### 3. USED_FOR_AUD(用于-受众)

**定义**:描述商品主要面向的受众群体或职业。注意和 USED_BY 的区别:USED_FOR_AUD 是**产品设计时的目标人群**(卖家视角),USED_BY 是**实际使用者**(用户证据视角,来自评论/QA)。

**COSMO 论文示例** → 三元组:`(儿童登山背包, USED_FOR_AUD, 儿童)`

**Rufus 实际会问的话**:
- "What's a good hiking backpack for beginners?"
- "Is this backpack suitable for kids?"
- "Best backpack for a tall person?"

**英文触发词库**:
`Designed for` / `Perfect for` / `Ideal for` / `Suitable for` / `Tailored to` / `Specifically made for` / `Created for` / `Best suited for` / `Engineered for` / `Targeted at` / `Exclusively for` / `Especially for` / `Crafted for` / `Optimized for`

**登山背包示例句**:
> "**Crafted for** first-time backpackers who want gear that won't fight them on the trail, with simplified strap adjustments and pre-set torso sizing."

**Listing 落点**:
- 五点描述第 3-4 条
- A+ 第二屏(人群切分)
- Q&A(主动问答"Is this good for X?")

**写作前自检话术**:
- 你是为谁设计的这个产品?(不要回答"所有人",这等于没答)
- 有没有哪类用户用起来特别顺手?
- 有没有哪类用户 **不适合**?明确说出来反而是 Rufus 加分项。

---

### 4. CAPABLE_OF(能力特性)

**定义**:描述商品具备什么具体能力或性能参数。这是把"规格参数"翻译成"能力故事"的关系。

**COSMO 论文示例** → 三元组:`(登山背包, CAPABLE_OF, 固定外挂登山杖和水壶)`

**Rufus 实际会问的话**:
- "Can this backpack hold a 15-inch laptop?"
- "Is this backpack waterproof?"
- "How much weight can this pack carry?"
- "Does it have hydration bladder compatibility?"

**英文触发词库**:
`is capable of` / `is equipped with` / `Features` / `Enables` / `Allows` / `Offers` / `Provides` / `Delivers` / `Supports` / `Ensures` / `Integrates` / `Incorporates` / `Enhances`

**登山背包示例句**:
> "**Equipped with** dual ice axe loops, trekking pole attachment points, and a hydration sleeve **that fits up to 3L reservoirs**, so you can carry every essential without dangling anything off the outside."

**Listing 落点**:
- 五点描述第 1-2 条(核心卖点 + 差异化能力)
- 产品详情后台属性
- A+ 参数对比图

**写作前自检话术**:
- 列出产品的 5 个规格参数,然后为每个参数写一句"所以用户能…"
- Rufus 经常被问"Can this X?"——你 listing 里有没有直接回答这些"能不能"问题?

---

### 5. USED_TO(用来做具体任务)

**定义**:描述商品被用来完成什么具体任务或动作。和 USED_FOR_FUNC 的区别:USED_FOR_FUNC 是宽泛的功能归属,USED_TO 是**颗粒更细的动作级任务**。

**COSMO 论文示例** → 三元组:`(登山背包, USED_TO, 存放登山用品)`

**Rufus 实际会问的话**:
- "Can I use this backpack to carry a sleeping bag outside?"
- "Is this good for organizing climbing gear?"
- "Can I pack a 2-person tent in this?"

**英文触发词库**:
`Used to` / `Designed to` / `Intended for` / `Perfect for` / `Meant to` / `Can be used for` / `Configured to` / `Adapted for`

**登山背包示例句**:
> "The front shove-it pocket **is designed to** stash a wet rain shell or a dirty pair of camp shoes without contaminating the main compartment."

**Listing 落点**:
- 五点描述的补充说明句
- 产品描述段落
- Q&A

**写作前自检话术**:
- 用户拿到这个产品之后,第一个、第二个、第三个会做的动作是什么?每个动作写一句 "used to…"

---

### 6. USED_AS(用作-本质/替代用法)

**定义**:描述商品可以被当作什么来使用,包括非主流用法或跨品类定位。这是**关联流量**的关系——它能把一个品类的商品打进另一个品类的 Rufus 召回池。

**COSMO 论文示例** → 三元组:`(登山背包, USED_AS, 户外装备)`

**Rufus 实际会问的话**:
- **"What's the material of the backpack?"** — aboutamazon.com 官方样例
- "Can this backpack work as a carry-on?"
- "Can I use a hiking backpack for everyday commuting?"

**英文触发词库**:
`Used as` / `Serves as` / `Functions as` / `Acts as` / `Doubles as` / `Works as` / `Suitable for use as` / `Transforms into`

**登山背包示例句**:
> "At 40L with a clamshell opening, this pack **doubles as** a carry-on for budget airline travel — it meets the 22×14×9 inch personal item dimensions on United, Delta, and American."

**Listing 落点**:
- 五点描述第 2 条或第 4 条(差异化 / 多场景)
- A+ "One Pack, Many Uses" 类型的对比图

**写作前自检话术**:
- 有没有哪个其他品类的用户也会买你的产品?
- 你的产品能不能"跨界"?跨界场景写出来,能拿到额外的召回流量。

---

### 7. IS_A(品类归属)

**定义**:描述商品属于哪个类别。**这是系统级关系,主要由亚马逊后台类目匹配决定,不需要硬写进文案。**

**⚠️ COSMO 论文原话**:如果没有强关联,不要硬凑。这个关系类型的权重主要落在**后台 Browse Node / Category / Item Type** 这些结构化字段上,而不是 listing 文案里。

**登山背包对应**:Browse Node = "Backpacking Packs" (而不是 "Backpacks" 或 "Travel Bags")

**Listing 落点**:
- ❌ 不要在文案里写 "This is a type of backpack"
- ✅ 在后台 **Item Type Keyword / Category / Browse Node** 填准确
- ✅ 如果要在文案里出现,用 `A type of` / `Belongs to` / `Part of` 作为自然过渡

**审计重点**:检查后台类目是否和文案声称的品类一致。"标题写 hiking backpack 但类目挂在 Luggage" = 数据冲突,Rufus 会直接压制展示。

---

### 8. USED_ON(时间 / 季节 / 特定时段)

**定义**:描述商品在什么时间、季节或时段下使用。这是 Rufus 的**季节性流量**入口。

**COSMO 论文示例** → 三元组:`(登山包, USED_ON, 冬季高山探险)`

**Rufus 实际会问的话**(这一条有官方出处):
- **"What's the best water filter for camping in freezing temperatures?"** — Cosmy Rufus Guide 引用的亚马逊演示
- "Best backpack for winter hikes?"
- "Good summer trekking pack?"

**英文触发词库**:
`be used during` / `best for [season]` / `ideal for` / `Designed for [winter/summer/spring]` / `Best enjoyed in` / `Recommended for` / `Perfectly timed for` / `Great choice for [season]`

**登山背包示例句**:
> "**Designed for winter alpine conditions**, the reinforced hipbelt stays flexible down to -20°F and the external loops are glove-friendly so you can rig your ice axe without taking off mittens."

**Listing 落点**:
- 五点描述(至少 1 条提到季节或时段)
- A+ 季节场景图
- 后台 Season 属性(如果品类有)

**写作前自检话术**:
- 这个产品有季节性偏好吗?(全季通用也是一个答案,但要明说 "all-season")
- 一年里哪几个月它最被需要?节日呢?

**⚠️ 多数 listing 完全忽略这个维度**。补上之后,Rufus 能在季节性长尾查询里召回你的 listing。

---

### 9. USED_IN_LOC(地点 / 环境)

**定义**:描述商品在什么地理位置或环境下使用。

**COSMO 论文示例** → 三元组:`(登山包, USED_IN_LOC, 高山徒步)`

**Rufus 实际会问的话**:
- "Good backpack for rainforest trekking?"
- "Is this pack good for desert hiking?"
- "Backpack for urban commuting and weekend hiking?"

**英文触发词库**:
`be used in` / `be used at` / `be placed in` / `works in [environment]` / `built for [terrain]` / `ready for`

**登山背包示例句**:
> "**Built for humid, rainforest environments**, the quick-dry mesh back panel and rust-proof hardware hold up against constant moisture that eats through ordinary backpacks in a single season."

**Listing 落点**:
- 五点描述的场景句
- A+ 环境实拍图

**写作前自检话术**:
- 在什么地形/环境下使用这个产品?(山地?沙漠?雨林?城市?海边?)
- 环境里有没有什么特殊挑战(湿度/沙尘/盐雾)是你的产品专门解决的?

---

### 10. USED_IN_BODY(身体部位)

**定义**:描述商品作用于身体的哪个部位,或针对什么身体问题。

**COSMO 论文示例** → 三元组:`(登山包肩带, USED_IN_BODY, 肩部)`

**Rufus 实际会问的话**:
- "Which backpack won't hurt my shoulders on long hikes?"
- "Best backpack for people with back pain?"
- "Is this backpack good for narrow shoulders?"

**英文触发词库**:
`protect` / `relieve pressure on` / `supports your [body part]` / `reduces strain on` / `contoured for` / `ergonomic` / `fits your [body part]`

**登山背包示例句**:
> "The S-curved shoulder straps **relieve pressure on your trapezius muscles**, and the load-lifter straps transfer 70% of the weight from your shoulders down to the padded hipbelt — the difference you feel after hour 6 on the trail."

**Listing 落点**:
- 五点描述第 2 条(人体工学卖点)
- A+ 人体图解

**写作前自检话术**:
- 用户身体的哪个部位会和产品直接接触?
- 有没有身体上的痛点是这个产品在解决的?
- 差评里有没有提到身体部位不适?把这些反过来写成"正面承诺"。

---

### 11. USED_WITH(搭配 / 互补产品)

**定义**:描述商品通常和什么一起使用。这是**关联商品流量**的关系,能把你的商品推进 Rufus 的"you might also need"召回池。

**COSMO 论文示例** → 三元组:`(登山包, USED_WITH, 防雨罩)`

**Rufus 实际会问的话**:
- "What accessories do I need with a hiking backpack?"
- "What should I buy along with this backpack?"
- **"planning a camping trip"** → Rufus 会同时推荐背包 + 帐篷 + 睡袋 + 炉具 + 净水器

**英文触发词库**:
`Pair with` / `Pairs well with` / `Complements` / `Combine with` / `Use with` / `Goes with` / `Designed to be used with` / `Compatible with`

**登山背包示例句**:
> "**Pairs seamlessly with** standard 3L hydration bladders (Osprey, Platypus, CamelBak), and the front daisy chain is sized to clip on most carabiners and ice tools."

**Listing 落点**:
- 五点描述第 4 条(兼容性 / 搭配)
- A+ "Complete Your Setup" 类型的搭配图
- Q&A("What bladder fits in this?")

**写作前自检话术**:
- 买了这个产品的人接下来还会买什么?
- 有哪些知名品牌/型号的配件能兼容?把它们写进去,Rufus 会把品牌名当作强信号。

---

### 12. USED_BY(使用者群体 / 实际用户画像)

**定义**:描述**实际**在使用这个产品的人群。和 USED_FOR_AUD 的区别:USED_FOR_AUD 是"为谁设计的"(品牌承诺),USED_BY 是"谁真的在用"(用户证据)。

**COSMO 论文示例** → 三元组:`(登山包, USED_BY, 登山爱好者)`

**Rufus 实际会问的话**:
- "What backpack do thru-hikers use?"
- "What do professional guides carry?"
- "Who uses this backpack?"

**英文触发词库**:
`Used by` / `Trusted by` / `Favored by` / `Loved by` / `The go-to choice for` / `Popular among`

**登山背包示例句**:
> "**Trusted by** Pacific Crest Trail thru-hikers for durability across 2,650 miles, and **favored by** weekend backpackers who want PCT-tested reliability without the ultralight price tag."

**Listing 落点**:
- 五点描述第 4 条(社会证明)
- A+ 用户故事区
- **Q&A + 评论**(这是 Rufus 权重最高的证据源)

**⚠️ 关键**:USED_BY 的最强信号不来自你写的文案,而来自**评论里用户自己的描述**。如果你能让真实买家在评论里自发提到 "I'm a thru-hiker and this pack…",这比五点描述里自吹自擂强 10 倍。这也是 Skill 里"评论挖掘"模块要做的事。

**写作前自检话术**:
- 你的产品最核心的 3 类真实用户是谁?(不是目标,是现状)
- 评论里反复出现的"I am a ___"是什么?把这些自称词写进文案。

---

### 13. XINTERESTED_IN(潜在兴趣 / 未明说的需求)

**定义**:描述对这个产品**可能**感兴趣的人群及其兴趣点。这是通过 co-buy 和 search-buy 行为挖掘出来的**潜在需求关系**,针对的是"还在浏览、没下决心"的用户。

**COSMO 论文示例** → 三元组:`(长途徒步者, XINTERESTED_IN, 轻量化登山包)`

**Rufus 实际会问的话**:
- "Lightweight backpacks for minimalist travelers?"
- "Backpacks for people who care about sustainability?"
- "I like long-distance hiking, what pack should I consider?"

**英文触发词库**:
`For those interested in` / `For those who value` / `For [demographic] looking for` / `Appeals to` / `A favorite among [interest group]`

**登山背包示例句**:
> "**For those interested in** ultralight backpacking without sacrificing durability, this pack uses Dyneema composite fabric to hit 1.8 lbs while still carrying 35 lbs of base weight."
>
> "**For those who value** sustainable gear, the main body is made from 100% recycled ocean plastic."

**Listing 落点**:
- 五点描述第 5 条或 A+ 开头
- 品牌故事区

**写作前自检话术**:
- 你的产品有没有能打动一个"理念型用户群"的点?(环保/极简/硬核/复古/平价)
- 这些用户未必是你的主流客户,但他们的搜索词 Rufus 会召回——值得覆盖。

---

### 14. XIS_A(用户自我定位)

**定义**:描述用户在提问时对自己是什么样的人的声明。这是用户视角的关系,但 listing 要主动"迎接"这些自称。

**COSMO 论文示例** → 三元组:`(我, XIS_A, 需要大容量登山包的人)`

**Rufus 实际会问的话**(注意句式,Rufus 用户真的会这么说):
- "I'm looking for a 60L backpack for multi-day trips"
- "I'm a beginner hiker, what pack do I need?"
- "I'm short (5'2"), what backpack fits?"

**英文触发词库**(用"You are" 句式直接回应用户的 "I am"):
`If you're a ___, this is for you` / `Whether you're a [type A] or [type B]` / `For the [user type] who ___`

**登山背包示例句**:
> "**Whether you're a first-time backpacker** heading out on your first overnight or **a seasoned thru-hiker** planning your third PCT attempt, the adjustable torso (15-21 inches) and interchangeable hipbelt sizes let this pack grow with your experience."

**Listing 落点**:
- A+ 第二屏(人群分类图)
- Q&A("I am X, is this right for me?")

**写作前自检话术**:
- 你的用户会如何自我介绍?("I am a ___")列出至少 3 种。
- 每一种自我介绍,你 listing 里有没有一句话专门在回应?

---

### 15. XWANT(明确需求)

**定义**:描述用户明确说出的需求或目标。这是 Rufus 最"直球"的意图关系。

**COSMO 论文示例** → 三元组:`(我, XWANT, 防水的登山背包)`

**Rufus 实际会问的话**(这是最贴官方发布稿的一类):
- **"What do I need for camping?"** — Amazon Canada 官方原句
- **"I want to start an indoor garden"** — Amazon 官方发布稿原句模板
- "I want a waterproof backpack under $100"
- "I need a carry-on sized backpack for a 5-day trip"

**英文触发词库**(直接回答 "I want X" 式需求):
`If you need` / `If you want` / `When you need` / `For [specific need]` / `Solves [specific problem]`

**登山背包示例句**:
> "**If you want** one pack that handles both weekend car camping and a 5-day hut-to-hut trek, this 50L with removable lid converts from full expedition pack to summit daypack in under 30 seconds."

**Listing 落点**:
- 标题(核心需求词)
- 五点描述第 1 条的开头("If you need…")
- 后台搜索词(XWANT 类查询就是长尾词金矿)

**写作前自检话术**:
- 用户在搜索框里输入 "I want a ___ that ___",空格里会填什么?列出 10 个,然后让 listing 里出现 6-8 个。
- 看你的差评——用户"想要但没得到"的东西,都是 XWANT 信号。

---

## 四、Rufus 真实查询 → COSMO 关系反查表

审计或竞品分析时,拿到一个 Rufus 查询,用这张表反向定位要补的关系。

| Rufus 查询类型 | 主关系 | 副关系 | 优化动作 |
|---|---|---|---|
| "What do I need for X?" | XWANT | USED_FOR_EVE + USED_WITH | 五点加场景句 + 搭配商品 |
| "Best [品类] for [活动]" | USED_FOR_EVE | USED_FOR_AUD | 标题加场景长尾 |
| "Is this good for [人群]?" | USED_FOR_AUD | USED_BY | Q&A 主动回答 |
| "Can this [动作]?" | CAPABLE_OF | USED_TO | 五点加"能力故事" |
| "What's the material of X?" | USED_AS | IS_A | A+ 材质专区 + 后台属性 |
| "Best X for [季节]" | USED_ON | USED_IN_LOC | 五点加季节句 |
| "X for [身体痛点]" | USED_IN_BODY | CAPABLE_OF | 人体工学卖点 |
| "What accessories with X?" | USED_WITH | CAPABLE_OF | 兼容性声明 |
| "Who uses X?" | USED_BY | XINTERESTED_IN | 评论挖掘+社会证明 |
| "Compare X vs Y" | CAPABLE_OF | USED_AS | 对比图表 + 差异化句 |
| "I'm [自称], need X" | XIS_A | XWANT | 人群切分 A+ |
| "I want X that Y" | XWANT | CAPABLE_OF | 标题主卖点 |

---

## 五、关系覆盖率自检清单

拿一个现有 listing,逐条打勾。**及格线是 15 条里至少覆盖 10 条**,每缺一条扣 2 分。

- [ ] **USED_FOR_FUNC**:核心功能有没有用自然语言说清楚?
- [ ] **USED_FOR_EVE**:至少提到 2 个具体使用场景/活动?(⚠️ 最重要)
- [ ] **USED_FOR_AUD**:明确目标人群,不写 "for everyone"?
- [ ] **CAPABLE_OF**:关键规格都翻译成了"能力故事"?
- [ ] **USED_TO**:产品能完成的 3 个具体任务都写了?
- [ ] **USED_AS**:有没有写"还可以当 X 用"的跨界用法?
- [ ] **IS_A**:后台 Browse Node 和文案品类一致?
- [ ] **USED_ON**:有没有提季节/时段?(⚠️ 最容易漏)
- [ ] **USED_IN_LOC**:有没有提地点/环境?
- [ ] **USED_IN_BODY**:人体工学或身体痛点有没有?(有身体接触的品类必答)
- [ ] **USED_WITH**:有没有写兼容/搭配?
- [ ] **USED_BY**:评论里的"I am ___"有没有被引用?
- [ ] **XINTERESTED_IN**:有没有打动一个"理念型用户群"的句子?
- [ ] **XIS_A**:有没有正面回应 "I'm a ___ user" 式的自称?
- [ ] **XWANT**:有没有直接回答 "I want ___" 式的需求?

---

## 六、特别警告:不要为了覆盖关系而堆砌

COSMO 关系覆盖率是质量信号,不是关键词堆砌的新马甲。如果一条 listing 为了凑 15 种关系把五点写得又臭又长,Rufus 的 LLM 会判定为垃圾内容——**降分比缺失还狠**。

**正确姿势**:
- 一条 bullet 可以自然地承载 2-3 种关系(比如 USED_FOR_EVE + USED_FOR_AUD + USED_IN_LOC 同时出现在一个场景句里完全合理)
- 宁可 10 条关系写得自然,也不要 15 条全覆盖但读起来像机器写的
- **给人看的句子,AI 足够聪明能理解;给 AI 看的句子,人看不下去**

参考前面第 3 节每个关系下的"登山背包示例句",都是一句话自然覆盖 2-3 种关系的写法。照着这种密度和自然度来,不要更高。

---

## 附录:官方出处追溯

本文件的权威性依据:

1. **COSMO 论文**:Yu et al., "COSMO: A Large-Scale E-commerce Common Sense Knowledge Generation and Serving System at Amazon", SIGMOD-Companion '24, June 9-15 2024, Santiago Chile. 15 种关系类型及三元组表示法出自此文。

2. **Rufus 发布稿**(Amazon 官方):
   - aboutamazon.com/news/retail/amazon-rufus (全球发布, 2024-02)
   - aboutamazon.com/news/retail/how-to-use-amazon-rufus (使用指南, 2024-09)
   - Amazon Canada 发布稿(2024-10):提供了 "camping" 和 "durable backpack" 两条官方样例

3. **Rufus 技术实现**(AWS ML Blog, 2025-11):*How Rufus scales conversational shopping experiences to millions of Amazon customers with Amazon Bedrock*。确认了 Rufus 用 Claude Sonnet + Amazon Nova + 自研模型组合,以及 "planning a camping trip" 作为复杂查询样例。

4. **行业第三方**(辅助参考):TechCrunch 发布报道(2024-02, 2024-07)、Incrementum Digital Rufus 广告优化指南、Cosmy Rufus Guide(2025-11)。

如果这份文件里的内容和官方发布的新版本冲突,以亚马逊官方最新版本为准。本文件最后更新:2026-04。
