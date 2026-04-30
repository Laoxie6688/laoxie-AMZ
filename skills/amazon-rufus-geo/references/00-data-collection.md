# 00-data-collection.md — LinkFox API 数据获取指南

> **使用时机**：执行任何审计/创建流程之前，先用此文件获取 ASIN 数据和评论。
> 所有 API 使用 `LINKFOXAGENT_API_KEY` 认证。

---

## 一、商品详情获取

调用 `linkfox-amazon-product-detail` skill（POST `https://tool-gateway.linkfox.com/amazon/product/detail`）：

**请求参数：**
- `asins`：ASIN 列表（逗号分隔，最多 40 个）
- `amazonDomain`：站点域名（默认 amazon.com）
  - 支持 22 个站点：amazon.com / amazon.co.uk / amazon.de / amazon.fr / amazon.it / amazon.es / amazon.co.jp / amazon.ca / amazon.com.au / amazon.com.br / amazon.in / amazon.nl / amazon.se / amazon.pl / amazon.sg / amazon.sa / amazon.ae / amazon.com.tr / amazon.com.mx / amazon.eg / amazon.cn / amazon.com.be
- `returnAuthorsReviews: true`（可获取精选评论，通常 8-10 条）
- `returnBoughtTogether: true`（获取关联商品，可选）
- `returnRelatedProducts: true`（获取竞品列表，可选）

**返回数据包含：** 标题、五点描述、产品描述、图片、价格、评分、品牌、规格、变体、星级分布、A+ 页面等。

---

## 二、评论获取：决策树

⚠️ **美国站和非美国站使用完全不同的工具！**

```
需要评论数据？
├── 站点 = 美国站（amazon.com）？
│   └── YES → 使用 @亚马逊-商品评论(美国站) — LinkFox Agent MCP 工具
│             ✅ 支持按星级筛选：all_stars / one_star~five_star / positive / critical
│             ✅ 支持排序：recent（最新）/ helpful（最有帮助）
│             ✅ 每页 10 条，最多 10 页 = 100 条评论
│             ⚠️ 仅支持单个 ASIN，多个需分次调用
│
└── 非美国站 → linkfox-amazon-reviews（POST tool-gateway.linkfox.com/amazon/reviews/list）
              支持 14 个站点：ca / co.uk / in / de / fr / it / es / co.jp /
              com.au / com.br / nl / se / com.mx / ae（默认 domainCode=ca）
              ✅ 支持按星级筛选：star1Num~star5Num（每级最多 100 条）
              ✅ 支持关键词过滤：filterByKeyword
              ✅ 支持排序：sortBy=recent 或 helpful
              ✅ 支持筛选：reviewerType=avp_only_reviews（仅验证购买）
```

---

## 三、美国站评论获取示例

**Prompt 模板（通过 LinkFox Agent MCP）：**
```
@亚马逊-商品评论(美国站) 查询美国站，asin为[ASIN]，star=positive，排序=recent，抓取10页
@亚马逊-商品评论(美国站) 查询美国站，asin为[ASIN]，star=critical，排序=recent，抓取10页
```

**参数说明：**
- 星级过滤：all_stars / one_star / two_star / three_star / four_star / five_star / positive / critical
- 页数：1~10（每页 10 条）
- 排序：recent / helpful

---

## 四、非美国站评论获取示例

```bash
curl -X POST https://tool-gateway.linkfox.com/amazon/reviews/list \
  -H "Authorization: $LINKFOXAGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "asin": "B08N5WRWNW",
    "domainCode": "ca",
    "star4Num": 20,
    "star5Num": 20,
    "star1Num": 20,
    "star2Num": 20,
    "sortBy": "recent"
  }'
```

---

## 五、各流程的数据获取策略

| 流程 | 需要获取的数据 |
|------|-------------|
| 流程一（全面审计） | 商品详情 + positive 评论 100条 + critical 评论 100条 + 竞品数据 |
| 流程二（创建/改写） | 竞品商品详情 + 竞品评论（无自有数据时） |
| 流程三（竞品分析） | 竞品商品详情 × 3-5个 ASIN |
| 流程六（评论挖掘） | positive 评论 100条 + critical 评论 100条（自有 + 竞品） |
| 流程七（可见性诊断） | 商品详情 + positive/critical 评论 + 竞品数据 |

---

**完成数据获取后，进入 Step 1：读取 `01-product-research.md`。**
