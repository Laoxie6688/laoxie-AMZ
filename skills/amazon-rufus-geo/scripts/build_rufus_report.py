#!/usr/bin/env python3
"""
报告生成器:把抓取数据聚合成"中文报告骨架 + 结构化中间数据"

设计原则:
- 这个脚本只做**数据聚合**,不做 LLM 推理
- 产出两份文件:
    1. report_skeleton_cn.md  — 填好"已知数据"节(健康、档案对比、七维担忧聚合)
                                 留 TODO 节(修改方案、算法对齐总结、风险)给 Claude 在 chat 里填
    2. aggregated_data.json   — 结构化中间数据,供 Claude 读取后产出最终报告

为什么不直接出最终报告:
- 最终报告要做 gap 判定 + 算法对齐 + 修改方案,这些是推理任务,需要 LLM
- 数据聚合(按维度归类、健康率计算、矩阵生成)是确定性任务,脚本做更可靠

用法:
    python3 scripts/build_report.py \
        --capture out/capture_baseline.csv \
        --health out/capture_health.json \
        --snapshots-dir out/ \
        --own-asin B0XXXX \
        --output-dir out/

依赖: 仅标准库
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# v2.0.0:维度配置不再硬编码,从 categories/<cat>/pack.yaml 动态加载。
# 下面是通用兜底,只在 pack 加载失败时使用。

APPAREL_DIM_CN_FALLBACK = {
    'specs': '规格/参数',
    'usage': '使用场景/方法',
    'quality': '品质/做工/材质',
    'complaint': '差评/退货原因',
    'vs_competitor': '竞品对比',
}
APPAREL_DIM_ORDER_FALLBACK = ['specs', 'usage', 'quality', 'complaint', 'vs_competitor']
APPAREL_DIM_WEIGHT_FALLBACK = {
    'specs': 5, 'usage': 4, 'quality': 4, 'complaint': 5, 'vs_competitor': 4,
}
APPAREL_CRITICAL_FALLBACK = {'quality', 'complaint'}


def load_category_config(category, pack_dir=None):
    """v2.0.0 新增:从 categories/<cat>/pack.yaml 加载维度配置。
    
    返回 (DIM_CN, DIM_ORDER, DIM_WEIGHT, CRITICAL_DIMS) tuple。
    pack 加载失败时,fallback 到通用五维。
    """
    if pack_dir is None:
        script_dir = Path(__file__).parent
        pack_dir = script_dir.parent / 'categories'
    else:
        pack_dir = Path(pack_dir)
    
    pack_path = pack_dir / category / 'pack.yaml'
    if not pack_path.exists():
        print(f"⚠ 找不到 pack.yaml: {pack_path}")
        print(f"  fallback 到通用五维")
        return (APPAREL_DIM_CN_FALLBACK, APPAREL_DIM_ORDER_FALLBACK,
                APPAREL_DIM_WEIGHT_FALLBACK, APPAREL_CRITICAL_FALLBACK)
    
    try:
        import yaml
    except ImportError:
        # 借用 capture_rufus_audit.py 的简易 parser
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from capture_rufus_audit import _parse_pack_yaml_simple
        pack = _parse_pack_yaml_simple(pack_path)
    else:
        with open(pack_path, encoding='utf-8') as f:
            pack = yaml.safe_load(f)
    
    dim_cn = {}
    dim_order = []
    dim_weight = {}
    
    for d in pack.get('dimensions', []):
        if isinstance(d, dict):
            code = d.get('code')
            if not code:
                continue
            dim_cn[code] = d.get('name_cn', code)
            dim_order.append(code)
            try:
                dim_weight[code] = int(d.get('weight', 3))
            except (ValueError, TypeError):
                dim_weight[code] = 3
    
    critical = set(pack.get('critical_dimensions', []))
    
    if not dim_order:
        print(f"⚠ pack.yaml 没有 dimensions 字段或解析失败,fallback 到通用五维")
        return (APPAREL_DIM_CN_FALLBACK, APPAREL_DIM_ORDER_FALLBACK,
                APPAREL_DIM_WEIGHT_FALLBACK, APPAREL_CRITICAL_FALLBACK)
    
    return (dim_cn, dim_order, dim_weight, critical)


# 全局变量,在 main() 里被覆盖。先用通用兜底初始化,保证 import 时不崩。
DIM_CN = APPAREL_DIM_CN_FALLBACK
DIM_ORDER = APPAREL_DIM_ORDER_FALLBACK
DIM_WEIGHT = APPAREL_DIM_WEIGHT_FALLBACK
CRITICAL_DIMS = APPAREL_CRITICAL_FALLBACK


def dim_section_number(dim):
    """给维度返回其在第 4 节"N 维担忧地图"中的子章节号(1-based)。"""
    try:
        return DIM_ORDER.index(dim) + 1
    except ValueError:
        return len(DIM_ORDER) + 1


def load_capture(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def load_health(path):
    if not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_snapshots(snapshots_dir):
    snapshots = {}
    for p in Path(snapshots_dir).glob('listing_snapshot_*.json'):
        asin = p.stem.replace('listing_snapshot_', '')
        try:
            snapshots[asin] = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return snapshots


# ============================================================
# 健康摘要
# ============================================================

def compute_health(capture_rows):
    total = len(capture_rows)
    if total == 0:
        return {'total': 0, 'success_rate': 0, 'warning': '无抓取数据'}
    
    by_status = defaultdict(int)
    by_failure = defaultdict(int)
    by_asin = defaultdict(lambda: defaultdict(int))
    
    for r in capture_rows:
        status = r.get('capture_status', 'unknown')
        by_status[status] += 1
        by_asin[r.get('asin', '?')][status] += 1
        if status in ('blocked', 'question_only'):
            reason = r.get('failure_reason', 'unknown')
            by_failure[reason] += 1
    
    answered = by_status.get('answered', 0)
    success_rate = round(answered / total, 3)
    
    warning = None
    if success_rate < 0.7:
        warning = (
            f"⚠ 抓取失败率 {round((1-success_rate)*100, 1)}%,"
            "高于 30% 警戒线。本报告结论应谨慎对待,建议补充抓取后再下结论。"
        )
    
    return {
        'total': total,
        'answered': answered,
        'question_only': by_status.get('question_only', 0),
        'blocked': by_status.get('blocked', 0),
        'duplicate': by_status.get('duplicate', 0),
        'out_of_scope': by_status.get('out_of_scope', 0),
        'success_rate': success_rate,
        'by_failure': dict(by_failure),
        'by_asin': {a: dict(s) for a, s in by_asin.items()},
        'warning': warning,
    }


# ============================================================
# 七维聚合
# ============================================================

def aggregate_by_dimension(capture_rows, own_asin=None):
    """按七维 + 子类聚合,每子类列出哪些 ASIN 被问到 + 典型问法 + answer_type。"""
    agg = defaultdict(lambda: defaultdict(lambda: {
        'questions': [],
        'asin_set': set(),
        'answer_types': defaultdict(int),
        'own_covered': False,
        'competitor_covered': False,
        'total_answered': 0,
        'rufus_redirect_risk': False,
    }))
    
    for r in capture_rows:
        if r.get('capture_status') != 'answered':
            continue
        
        dim = r.get('primary_dimension', '').strip()
        sub = r.get('sub_category', '').strip()
        asin = r.get('asin', '')
        role = r.get('product_role', '')
        if not dim:
            continue
        
        bucket = agg[dim][sub]
        bucket['questions'].append({
            'asin': asin,
            'role': role,
            'q': r.get('raw_question', ''),
            'a_summary': (r.get('raw_answer', '') or '')[:240],
            'answer_type': r.get('answer_type', ''),
            'follow_ups': r.get('follow_up_prompts', ''),
        })
        bucket['asin_set'].add(asin)
        bucket['answer_types'][r.get('answer_type', '')] += 1
        bucket['total_answered'] += 1
        
        if own_asin and asin == own_asin:
            bucket['own_covered'] = True
        elif role and role.startswith('competitor'):
            bucket['competitor_covered'] = True
        
        if r.get('answer_type') == 'alternative_recommendation':
            bucket['rufus_redirect_risk'] = True
    
    # 转回普通 dict + set 转 list
    out = {}
    for dim, subs in agg.items():
        out[dim] = {}
        for sub, b in subs.items():
            out[dim][sub] = {
                **b,
                'asin_set': sorted(b['asin_set']),
                'answer_types': dict(b['answer_types']),
                'concern_scope': (
                    'category_concern' if len(b['asin_set']) >= 2
                    else 'competitor_specific' if not b['own_covered']
                    else 'own_opportunity'
                ),
            }
    return out


# ============================================================
# 优先级计算(对应类目 question-taxonomy 的加分制)
# v2.0.0:三大死穴从 pack.yaml.critical_dimensions 动态读
# ============================================================

def score_concern(dim, sub, bucket):
    """1-5 分,起步 1。
    
    v2.0.0:命中类目死穴的判定改用全局 CRITICAL_DIMS(从 pack.yaml 加载)。
    """
    score = 1
    
    # +1: 命中类目死穴(从 pack.yaml.critical_dimensions 读,各类目不同)
    if dim in CRITICAL_DIMS or 'complaint' in (sub or ''):
        score += 1
    
    # +1: ≥ 2 个 ASIN 都被问到(category_concern)
    if len(bucket['asin_set']) >= 2:
        score += 1
    
    # +1: 自家未覆盖
    if not bucket['own_covered']:
        score += 1
    
    # +1: Rufus 推了别人 / 出现 alternative_recommendation
    if bucket.get('rufus_redirect_risk'):
        score += 1
    
    # +1 假设可一次更新内修复 — 保守不加,留给 Claude 判断
    
    return min(score, 5)


def label_score(score):
    return {5: 'critical', 4: 'high', 3: 'medium', 2: 'low', 1: 'watch'}[score]


# ============================================================
# 产出 markdown 骨架
# ============================================================

def render_markdown(health, dim_agg, snapshots, own_asin, output_path,
                    category='_generic', category_display=None):
    """v2.0.0:加 category 参数,标题和章节动态化。"""
    md = []
    cat_label = category_display or category
    md.append(f"# Amazon Rufus Listing 审计报告({cat_label})\n")
    md.append(f"_生成时间:{datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")
    md.append(f"_自家 ASIN:{own_asin or '未指定'}_\n\n")
    
    # 1. 抓取健康
    md.append("## 1. 抓取健康\n")
    if health['warning']:
        md.append(f"**{health['warning']}**\n\n")
    md.append(f"- 总计抓取:{health['total']} 行")
    md.append(f"- ✓ answered:{health['answered']}({round(health['success_rate']*100, 1)}%)")
    md.append(f"- ⚠ question_only:{health['question_only']}")
    md.append(f"- ✗ blocked:{health['blocked']}")
    md.append(f"- duplicate:{health['duplicate']} / out_of_scope:{health['out_of_scope']}\n")
    
    if health['by_failure']:
        md.append("\n**主要失败原因**:\n")
        for reason, n in sorted(health['by_failure'].items(), key=lambda x: -x[1]):
            md.append(f"- `{reason}` × {n}")
        md.append("")
    
    md.append("\n**各 ASIN 抓取情况**:\n")
    md.append("| ASIN | answered | question_only | blocked |")
    md.append("|---|---|---|---|")
    for asin, statuses in health['by_asin'].items():
        md.append(f"| {asin} | {statuses.get('answered', 0)} | {statuses.get('question_only', 0)} | {statuses.get('blocked', 0)} |")
    md.append("")
    
    # 2. 执行摘要(留给 Claude 填)
    md.append("\n## 2. 执行摘要\n")
    md.append("> **TODO(Claude 填写)**:基于下面的七维担忧地图和覆盖矩阵,产出 Top 5 必改点。")
    md.append("> 每条必须给:位置 + 现状 + 改成什么 + 算法对齐打分。")
    md.append("> 参考 references/output-schema-cn.md §2 模板。\n")
    
    # 3. 产品档案
    md.append("\n## 3. 产品档案\n")
    if not snapshots:
        md.append("_(未提供 listing snapshot,无法对比产品档案。请先用 capture_rufus_audit.py 跑过抓取以生成 snapshot。)_\n")
    else:
        md.append("| ASIN | role | title | bullets 数 | 图数 | 有 A+ |")
        md.append("|---|---|---|---|---|---|")
        for asin, snap in snapshots.items():
            role = "own" if asin == own_asin else "competitor"
            title = (snap.get('title', '') or '')[:60]
            bullets = len(snap.get('bullets', []))
            imgs = snap.get('imageCount', 0)
            aplus = '是' if snap.get('hasAplus') else '否'
            md.append(f"| {asin} | {role} | {title} | {bullets} | {imgs} | {aplus} |")
        md.append("")
        md.append(f"> **TODO(Claude 填写)**:按 `categories/{category}/product-profile.md` 的字段,")
        md.append(f"> 给每个 ASIN 输出完整档案(类目专属字段,服装如 silhouette / fabric / size_chart_present / model_height_disclosed 等)。")
        md.append(f"> 如果该文件不存在,降级使用 `references/product-profiling-base.md` 通用字段。")
        md.append("> 上面的快照只是基础信息,完整档案需要 Claude 在 chat 中读 Listing 完成。\n")
    
    # 4. 七维担忧地图
    md.append("\n## 4. N 维买家担忧地图\n")
    md.append(f"_本类目 (`{category}`) 共 {len(DIM_ORDER)} 维:{', '.join(DIM_ORDER)}_\n")
    
    # 按权重 × 担忧条数排维度
    dim_score_order = sorted(
        DIM_CN.keys(),
        key=lambda d: -(DIM_WEIGHT.get(d, 0) * len(dim_agg.get(d, {}))),
    )
    
    for dim in dim_score_order:
        if dim not in dim_agg or not dim_agg[dim]:
            md.append(f"\n### 4.{dim_section_number(dim)} {DIM_CN[dim]} (`{dim}`)\n")
            md.append("_本次抓取没拿到这个维度的有效问答。这本身可能是信号:可能维度没被覆盖。_\n")
            continue
        
        md.append(f"\n### 4.{dim_section_number(dim)} {DIM_CN[dim]} (`{dim}`)\n")
        
        # 每子类一段
        for sub, bucket in sorted(dim_agg[dim].items(), key=lambda x: -bucket_score(x[1])):
            score = score_concern(dim, sub, bucket)
            label = label_score(score)
            md.append(f"\n#### {sub} — 优先级 {score}/5 ({label})")
            md.append(f"- 涉及 ASIN:{', '.join(bucket['asin_set'])}")
            md.append(f"- 答案类型分布:{dict(bucket['answer_types'])}")
            md.append(f"- 担忧范围:{bucket['concern_scope']}")
            if bucket['rufus_redirect_risk']:
                md.append("- ⚠ **Rufus 出现 alternative_recommendation,主动把流量推给了别家**")
            md.append(f"- 自家是否被问到:{'是' if bucket['own_covered'] else '否'}")
            md.append(f"- 典型问法和答案:")
            for q in bucket['questions'][:3]:  # 前 3 个示例
                md.append(f"  - **[{q['role']}]** Q: _{q['q']}_")
                md.append(f"    A: {q['a_summary']}...")
                if q['follow_ups']:
                    md.append(f"    follow-ups: {q['follow_ups']}")
        md.append("")
    
    # 5. 覆盖矩阵(自家 vs 七维 — 只在有 own_asin 时填)
    md.append("\n## 5. Listing 覆盖矩阵\n")
    if not own_asin:
        md.append("_(没指定 --own-asin,无法做覆盖矩阵。)_\n")
    else:
        md.append("> **TODO(Claude 填写)**:对每个 ≥ 3 分的担忧,判断自家 Listing 受控内容(标题/bullet/图/A+)是否覆盖。")
        md.append("> 标 strong / partial / weak / missing / contradicted / review_only。")
        md.append("> 完整字段参考 references/output-schema-cn.md §5。\n")
    
    # 6. 优先级修复清单
    md.append("\n## 6. 优先级修复清单\n")
    md.append(f"> **TODO(Claude 填写)**:根据 §4 N 维担忧地图和 §5 覆盖矩阵,按优先级桶生成修复清单。")
    md.append(f"> 每条必须按 `categories/{category}/fix-playbook.md` 末尾的标准格式:")
    md.append("> 优先级 / 位置 / 现状 / 改成什么 / 为什么 / 算法对齐 / 执行人 / 工时。\n")
    
    # 7. 修改方案分位置
    md.append("\n## 7. 修改方案(按位置)\n")
    md.append("### 7.1 主图 7 张\n")
    md.append(f"> **TODO**:按 `categories/{category}/fix-playbook.md` 的 7 张图标准结构,逐图给修改建议。\n")
    md.append("### 7.2 A+ 模块\n")
    md.append("> **TODO**:按 7 模块结构,逐模块给修改/新增建议。\n")
    md.append("### 7.3 Bullet 5 条\n")
    md.append(f"> **TODO**:按 `categories/{category}/fix-playbook.md` 的类目专用模板逐条给前后对比。\n")
    md.append("### 7.4 Title\n")
    md.append("> **TODO**:给保守版 / 平衡版(推荐)/ 激进版三选项。\n")
    md.append("### 7.5 Search Terms 后台\n")
    md.append("> **TODO**:按品类 30% / 场景 30% / 人群 20% / 特征 20% 分配,给 250 字符候选。\n")
    md.append("### 7.6 Q&A / Review 引导\n")
    md.append("> **TODO**:给老客户问的问题模板 + 售后引导文案(合规框架内)。\n")
    
    # 8. 算法对齐总结
    md.append("\n## 8. 算法对齐总结\n")
    md.append("> **TODO**:把所有修改建议汇总成 A10/COSMO/Rufus 三栏打分表,按总分降序排。")
    md.append("> 模板见 references/output-schema-cn.md §8。\n")
    
    # 9. 风险与限制
    md.append("\n## 9. 风险与限制\n")
    md.append("- 抓取时间:" + datetime.now().strftime('%Y-%m-%d'))
    md.append(f"- 抓取成功率:{round(health['success_rate']*100, 1)}%")
    if health['warning']:
        md.append(f"- {health['warning']}")
    md.append("- 本报告**不保证**:BSR / 排名提升、Rufus 一定推荐你、转化率具体提升幅度")
    md.append("- 算法吃多个信号(销量、价格、review 量),本报告只覆盖**内容侧**")
    md.append("- Title 大改有 search rank 重置风险,建议保守版优先")
    md.append("- Rufus 答案有时效性,3-6 月后建议复抓\n")
    
    # 10. 回测计划
    md.append("\n## 10. 回测计划\n")
    md.append("**第 1 周**:Listing 改完后,亲自跑 [algo-alignment.md] 末尾的 8 题反向验证 Rufus 引用情况。\n")
    md.append("**第 1 个月**:观察 BSR、conversion rate、退货率(尤其尺码相关)、review 增长速度、1-3 星 review 主题分布。\n")
    md.append("**第 3 个月**:复抓 Rufus(同样问题集),对比七维覆盖标签变化(missing → strong)、是否还出现 alternative_recommendation。\n")
    md.append("**第 6 个月**:重新跑完整 audit,因为竞品也在改。\n")
    
    Path(output_path).write_text('\n'.join(md), encoding='utf-8')


def bucket_score(bucket):
    """子类内部排序辅助。"""
    base = len(bucket['asin_set']) * 2
    if bucket.get('rufus_redirect_risk'):
        base += 5
    if not bucket['own_covered']:
        base += 2
    return base


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='把抓取数据聚合成中文报告骨架')
    parser.add_argument('--capture', required=True, help='capture_baseline.csv 路径')
    parser.add_argument('--health', help='capture_health.json 路径(可选)')
    parser.add_argument('--snapshots-dir', default='out', help='listing snapshot JSON 所在目录')
    parser.add_argument('--own-asin', help='自家 ASIN(必须给才能做覆盖矩阵 TODO)')
    parser.add_argument('--output-dir', default='out', help='输出目录')
    parser.add_argument('--category', default='_generic',
                        help='产品类目代号:pet_supplies / apparel / electronics / home_kitchen / beauty / _generic。'
                             '决定 N 维 taxonomy 和报告章节,从 categories/<cat>/pack.yaml 加载。'
                             '默认 _generic；宠物用品建议 pet_supplies')
    args = parser.parse_args()
    
    # v2.0.0:加载类目配置,覆盖全局 DIM_CN/DIM_ORDER/DIM_WEIGHT/CRITICAL_DIMS
    global DIM_CN, DIM_ORDER, DIM_WEIGHT, CRITICAL_DIMS
    DIM_CN, DIM_ORDER, DIM_WEIGHT, CRITICAL_DIMS = load_category_config(args.category)
    print(f"类目: {args.category} ({len(DIM_ORDER)} 维: {', '.join(DIM_ORDER)})")
    print(f"  死穴维度: {sorted(CRITICAL_DIMS)}")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"读取 capture: {args.capture}")
    rows = load_capture(args.capture)
    print(f"  → {len(rows)} 行")
    
    print(f"计算健康指标...")
    # v1.1.0: 删除被加载但未使用的 health_raw 变量
    health = compute_health(rows)
    if args.health and Path(args.health).exists():
        try:
            health_from_file = load_health(args.health)
            if health_from_file:
                file_total = sum(
                    sum(s.values()) for s in 
                    (a.get('statuses', {}) for a in health_from_file.get('asins', {}).values())
                )
                if file_total != health['total']:
                    print(f"  ⚠ {args.health} 中行数 ({file_total}) 与 CSV 行数 ({health['total']}) 不一致,以 CSV 为准")
        except Exception as e:
            print(f"  ⚠ 读取 {args.health} 失败: {e},以 CSV 重算为准")
    
    print(f"  → success_rate={round(health['success_rate']*100, 1)}%")
    if health['warning']:
        print(f"  {health['warning']}")
    
    print(f"按 {len(DIM_ORDER)} 维聚合...")
    dim_agg = aggregate_by_dimension(rows, own_asin=args.own_asin)
    for dim in DIM_ORDER:
        n = len(dim_agg.get(dim, {}))
        cn_name = DIM_CN.get(dim, dim)
        print(f"  → {cn_name:18s}: {n} 个子类被问到")
    
    print(f"读 listing snapshots...")
    snapshots = load_snapshots(args.snapshots_dir)
    print(f"  → {len(snapshots)} 个 snapshot")
    
    # 写 aggregated_data.json
    agg_path = output_dir / 'aggregated_data.json'
    
    dim_agg_serializable = {}
    for dim, subs in dim_agg.items():
        dim_agg_serializable[dim] = {}
        for sub, b in subs.items():
            dim_agg_serializable[dim][sub] = {
                **{k: v for k, v in b.items() if k != 'asin_set'},
                'asin_set': list(b['asin_set']) if isinstance(b.get('asin_set'), (list, set)) else [],
            }
    
    agg_data = {
        'generated_at': datetime.now().isoformat(),
        'category': args.category,
        'category_dimensions': DIM_ORDER,
        'critical_dimensions': sorted(CRITICAL_DIMS),
        'own_asin': args.own_asin,
        'health': health,
        'dimensions': dim_agg_serializable,
        'snapshots': snapshots,
    }
    agg_path.write_text(
        json.dumps(agg_data, ensure_ascii=False, indent=2, default=str),
        encoding='utf-8',
    )
    print(f"  ✓ 写 {agg_path}")
    
    # 写 markdown 骨架
    md_path = output_dir / 'report_skeleton_cn.md'
    render_markdown(health, dim_agg, snapshots, args.own_asin, md_path,
                    category=args.category)
    print(f"  ✓ 写 {md_path}")
    
    print(f"\n完成。下一步:")
    print(f"  把 {md_path} 和 {agg_path} 喂给 Claude,让 Claude 把 TODO 节填完。")
    print(f"  (TODO 节包括:执行摘要、产品档案完整字段、覆盖矩阵、修复清单、修改方案、算法对齐总结)")


if __name__ == '__main__':
    main()
