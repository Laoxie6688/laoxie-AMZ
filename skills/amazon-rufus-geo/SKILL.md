---
name: amazon-rufus-geo
description: Analyze, audit, and optimize Amazon listings for Rufus AI and COSMO-style generative search visibility. Use when working on Amazon Rufus, COSMO relation coverage, Amazon AI search/GEO, listing audits or rewrites, ASIN or Amazon URL analysis, competitor comparison, Rufus visibility diagnosis, Q&A strategy, review mining, backend attribute consistency, or when collecting Rufus answers through browser automation for market research.
---

# Amazon Rufus GEO

Use this skill to combine two workflows:

1. **Rufus QA collection**: ask Amazon Rufus batches of buyer-style questions and save the answers.
2. **Rufus/COSMO GEO optimization**: audit or rewrite listings so Rufus can retrieve stronger evidence from title, bullets, description/A+, Q&A, reviews, images, and backend attributes.

Treat claims about Rufus ranking behavior as working hypotheses unless verified by Amazon documentation or live tests. Be concrete, evidence-backed, and honest when reviews, weak product fundamentals, or data conflicts limit what copywriting can fix.

## Decision Tree

| User request | Workflow | Load |
| --- | --- | --- |
| ASIN / Amazon URL / "审计 listing" | Full listing audit | `references/10-audit-flow.md`, then relevant references |
| "写/改 listing 文案" | Listing creation or rewrite | Progressive workflow below |
| "竞品分析" / "和竞品比" | Competitor visibility matrix | `references/11-competitor-analysis.md` |
| "Rufus 搜不到我" / "为什么推荐竞品" | Visibility diagnosis | `references/12-visibility-diagnosis.md` |
| "优化 Q&A" / "生成 Q&A" | Q&A engineering | `references/06-qa-engineering.md` |
| Reviews pasted / "评论挖掘" | Review mining | `references/08-review-mining.md` |
| Backend fields / data consistency | Backend audit | `references/07-backend-attributes.md` |
| "批量问 Rufus" / market research via Rufus | QA collection | This file + `references/13-rufus-qa-automation.md` |
| Concept explanation only | Explain Rufus/COSMO | `references/cosmo-intent-mapping.md` |

For any concrete listing work, run or simulate the **15 COSMO relation questions** before scoring or rewriting. Use `references/cosmo-intent-mapping.md` for definitions and trigger patterns.

## Progressive Listing Workflow

Load references only as needed, in this order:

1. Optional data collection: `references/00-data-collection.md`
2. Product knowledge template: `references/01-product-research.md`
3. COSMO 15-question simulation: `references/cosmo-intent-mapping.md`
4. Keyword strategy: `references/02-keyword-strategy.md`
5. Title: `references/03-title-formula.md`
6. Bullets: `references/04-bullet-formula.md`
7. Description/A+: `references/05-description-aplus.md`
8. Q&A: `references/06-qa-engineering.md`
9. Backend attributes and consistency: `references/07-backend-attributes.md`
10. Scoring: `references/scoring-rubric.md`
11. Final report: `references/09-output-template.md`

If review data is available, insert `references/08-review-mining.md` after product research. For partial rewrites, still complete the COSMO 15-question simulation before jumping to the requested section.

## Rufus QA Collection

Use live Rufus QA collection when the task needs actual Rufus answers, recommendation behavior, market research, or competitor recall evidence.

Preferred path:

1. Make sure Chrome is launched with remote debugging and an Amazon buyer account is already logged in. Never ask the user to share Amazon credentials; have them log in manually.
2. Verify CDP is listening with `curl http://127.0.0.1:9222/json/list` and confirm an Amazon `type: "page"` target exists.
3. Use `scripts/rufus_qa.py` to ask a question list through the Chrome DevTools Protocol. The script selects the Amazon page websocket from `/json/list`; do not use the browser websocket from `/json/version` for page automation.
4. Save JSON results and feed them into the audit, competitor, or visibility diagnosis workflow.

On macOS, open a separate debuggable Chrome instance with:

```bash
open -na "Google Chrome" --args \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-rufus-profile \
  "https://www.amazon.com"
```

After the window opens, the user must log in manually in that specific window. A normal already-open Chrome profile does not expose CDP unless it was launched with `--remote-debugging-port`.

Example:

```bash
python3 scripts/rufus_qa.py \
  --cdp http://127.0.0.1:9222 \
  --keyword "sous vide" \
  --questions questions.txt \
  --output rufus_results.json
```

`questions.txt` should contain one question per line. The script JSON-escapes questions before injecting them into the browser, which avoids the string-injection issue in the original prototype. Each result includes `answer` cut from the latest matching question and `rawPanelText` for debugging the full Rufus chat history.

For environment checks:

```bash
python3 scripts/check_rufus_env.py
```

Do not ask the user for Amazon credentials. If login is required, instruct them to log in manually in the Chrome profile used for testing. Keep request rates conservative and respect Amazon's terms.

## Core Audit Rules

- Prefer scene-based natural language over keyword lists.
- Mark each COSMO relation as `covered`, `weak`, or `missing`; do not invent evidence.
- Treat Q&A and reviews as high-value evidence, but distinguish observed data from assumptions.
- Flag contradictions across title, bullets, description, images, variants, package quantity, backend attributes, and reviews.
- Do not promise that copy changes alone will overcome severe review gaps, bad ratings, or product/market weakness.
- Output concrete copy when asked to optimize: title, bullets, description/A+, Q&A, backend attribute suggestions, and a prioritized fix list.

## Reference Index

- `00-data-collection.md`: LinkFox/API data collection notes.
- `01-product-research.md`: product knowledge template.
- `02-keyword-strategy.md`: traditional + Rufus semantic keyword strategy.
- `03-title-formula.md`: title formula and checks.
- `04-bullet-formula.md`: bullet formula.
- `05-description-aplus.md`: description and A+ writing.
- `06-qa-engineering.md`: 15-question Q&A engineering.
- `07-backend-attributes.md`: backend attributes and consistency.
- `08-review-mining.md`: review mining and COSMO annotation.
- `09-output-template.md`: final report template.
- `10-audit-flow.md`: full listing audit.
- `11-competitor-analysis.md`: competitor matrix.
- `12-visibility-diagnosis.md`: visibility diagnosis.
- `13-rufus-qa-automation.md`: original Rufus automation notes.
- `cosmo-intent-mapping.md`: COSMO 15 relations.
- `scoring-rubric.md`: 100-point scoring rubric.
