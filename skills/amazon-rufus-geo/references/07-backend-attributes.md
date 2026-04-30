# 07-backend-attributes.md — 后台属性填写清单

> **使用时机**：Q&A 生成后，输出后台属性建议。
> 后台结构化字段是 COSMO 最直接的信号来源，大多数卖家只关心文案，忽略了后台属性。

---

## 一、为什么后台属性比文案更直接

COSMO 的三元组 `(head, relation, tail)` 中，很多关系的 tail 直接来自后台结构化字段：
- `USED_FOR_EVE` → 后台 **Occasion** 字段
- `USED_FOR_AUD` → 后台 **Target Audience** 字段
- `USED_ON` → 后台 **Season** 字段
- `IS_A` → 后台 **Browse Node / Item Type Keyword**

如果文案里写了 "perfect for winter camping" 但后台 Season 字段是空的，COSMO 会认为文案和结构化数据不对齐，信任度下降。

**文案 + 后台属性双重对齐 = 最强信号。**

---

## 二、必须填写的核心属性（所有品类通用）

### 1. Browse Node / Category（品类路径）
- 确认 Browse Node 和文案声称的品类完全一致
- ❌ 致命错误：标题写 "Hiking Backpack" 但 Browse Node 挂在 "Luggage & Travel Gear"
- 选择**最精确**的子品类，不要选宽泛的父品类

```
推荐格式：[大品类] > [中品类] > [精确品类]
示例：Sports & Outdoors > Outdoor Recreation > Hiking > Backpacks > Backpacking Packs
```

### 2. Item Type Keyword
- 填精确的商品类型关键词（英文，参考同类竞品）
- 示例：`backpacking-packs` / `hiking-backpacks` / `trekking-packs`

### 3. Material Type（材质）
- 必须和标题/五点/描述里提到的材质**完全一致**
- ❌ 致命错误：标题说 "Nylon" 但后台填 "Polyester"
- 示例：`Nylon` / `Ripstop Nylon` / `Dyneema` / `Canvas`

### 4. Color（颜色）
- 必须和主图颜色完全一致
- ❌ 致命错误：主图是黑色，后台填 "Midnight Navy"
- 变体产品每个颜色单独填

### 5. Size / Dimensions（尺寸）
- 外包装尺寸（长×宽×高，英寸）
- 产品实际尺寸（如适用）
- Item Package Quantity（必须和标题中的数量一致）

### 6. Weight（重量）
- 产品净重（不含包装）
- 单位统一（磅 or 公斤，选一个）

---

## 三、COSMO 高价值属性（影响 Rufus 召回的关键字段）

以下字段大多数卖家不填，填了就是竞争优势：

### 7. Occasion（场合）⚠️ 最重要
**对应 COSMO 关系：USED_FOR_EVE**

常见选项（按品类不同）：
```
Camping / Hiking / Backpacking / Travel / Everyday Use /
School / Work / Sport / Outdoor / Adventure
```
> 可以选多个，选所有真实适用的场合，不要贪多选不相关的

### 8. Target Audience / Intended For（目标受众）
**对应 COSMO 关系：USED_FOR_AUD**

```
Adults / Men / Women / Unisex / Boys / Girls / Kids / Teens /
Seniors / Beginners / Professionals / Outdoor Enthusiasts
```

### 9. Season（季节）⚠️ 最常被忽略
**对应 COSMO 关系：USED_ON**

```
All Season / Spring / Summer / Fall / Winter / Spring-Summer /
Fall-Winter
```
> 全年适用请填 "All Season"，不要留空

### 10. Special Features（特殊功能）
**对应 COSMO 关系：CAPABLE_OF**

```
Waterproof / Water Resistant / Lightweight / Ergonomic /
Padded Shoulder Straps / Multiple Compartments / Laptop Sleeve /
Hydration Compatible / Rain Cover Included / Compression Straps
```
> 列出所有真实特性，不要填没有的

### 11. Pattern（图案/款式）
影响视觉搜索和 Rufus 图片识别：
```
Solid / Striped / Camo / Geometric / Logo / Plain
```

### 12. Closure Type（关闭方式）
```
Zipper / Roll-Top / Drawstring / Buckle / Magnetic
```

---

## 四、一致性交叉验证表

填完后台属性后，用这张表逐一交叉验证：

| 后台属性 | 后台填写值 | 标题中的表述 | 五点中的表述 | 主图呈现 | 一致？ |
|---------|----------|------------|------------|---------|--------|
| Material Type | | | | | ✅/❌ |
| Color | | | | | ✅/❌ |
| Item Package Quantity | | | | | ✅/❌ |
| Size/Dimensions | | | | | ✅/❌ |
| Season | | | | | ✅/❌ |
| Occasion | | | | | ✅/❌ |
| Special Features | | | | | ✅/❌ |

**任何一行标注 ❌ = 数据冲突，Rufus 可能直接压制展示，必须修复。**

---

## 五、后台搜索词（Search Terms）最终版

在关键词策略步骤（02-keyword-strategy.md）中已有草稿，这里做最终确认：

**填写规则回顾：**
- 总字节数：不超过 250 字节（注意是字节，不是字符）
- 用空格分隔，不用逗号
- 不重复标题中已有的词
- 包含：同义词 + 拼写变体 + 长尾短语 + 常见错别字

**字节数计算方法：**
```bash
echo -n "your search terms here" | wc -c
```
或直接数：英文字母每个 = 1字节，空格 = 1字节，中文 = 3字节

**最终版草稿（填入后确认字节数）：**
```
[最终后台搜索词，空格分隔，不超过250字节]
```

---

## 六、后台属性自检清单

- [ ] Browse Node 与文案品类完全一致
- [ ] Material Type 与文案材质完全一致
- [ ] Color 与主图颜色完全一致
- [ ] Item Package Quantity 与标题数量完全一致
- [ ] **Occasion 已填写**（不为空）
- [ ] **Season 已填写**（不为空，全季填 All Season）
- [ ] **Target Audience 已填写**
- [ ] Special Features 已列出所有真实特性
- [ ] 后台搜索词 ≤ 250 字节
- [ ] 一致性交叉验证表无 ❌

**完成后，进入 Step 9：读取 scoring-rubric.md，对完整 Listing 进行六维评分。**
