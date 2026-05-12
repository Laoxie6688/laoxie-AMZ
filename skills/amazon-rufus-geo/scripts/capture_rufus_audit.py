#!/usr/bin/env python3
"""
单 ASIN Rufus 抓取主程序

实现 references/browser-capture.md 描述的状态机:
  ready → login_check → listing_snapshot → product_profile
       → question_plan → submit_one_question → wait_thinking
       → wait_stable → capture_answer → loop → final_save → close_browser

跟原 qa skill 的 batch_ask 区别:
1. 状态机驱动,失败行不丢
2. 一次只问一题,严格 sequential submission rule
3. 答案稳定判定不只看 length > 200,而是看 thinking 消失 + length 不变
4. 不靠"关闭面板重置限流"作为成功率保证 — 关面板是为了减少上下文污染
5. CSV 输出 30+ 字段,带完整失败原因和 verification 状态

环境变量:
  CHROME_REMOTE_PORT(默认 9222)

用法:
  python3 scripts/capture_rufus_audit.py \
      --asin B0XXXXXXX \
      --role own \
      --depth 20 \
      --marketplace com \
      --output-dir out/

  # 多 ASIN(批量,逗号分隔):
  python3 scripts/capture_rufus_audit.py \
      --asins B0AAA,B0BBB,B0CCC \
      --roles own,competitor_1,competitor_2 \
      --depth 20

  # 跳过 profile/plan(用已有的 plan):
  python3 scripts/capture_rufus_audit.py \
      --asin B0XXXX --role own \
      --plan-file out/question_plan.csv

依赖:
  pip3 install websockets --break-system-packages
"""
import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import websockets
except ImportError:
    print("✗ pip3 install websockets --break-system-packages")
    sys.exit(1)


CHROME_PORT = int(os.environ.get('CHROME_REMOTE_PORT', '9222'))


@dataclass
class CaptureRow:
    capture_id: str
    capture_date: str
    marketplace: str
    product_role: str
    asin: str
    product_url: str
    persona_label: str = "default"
    login_status: str = "unknown"
    challenge_type: str = "none"
    verification_action: str = "none"
    source_depth: int = 0
    parent_question_id: str = ""
    planned_question_id: str = ""
    question_origin: str = "rufus_starter"
    profile_signal: str = ""
    capture_status: str = "answered"
    failure_reason: str = ""
    raw_question: str = ""
    normalized_question: str = ""
    raw_answer: str = ""
    answer_summary: str = ""
    answer_length_chars: int = 0
    answer_confidence: str = "high"
    answer_type: str = ""
    follow_up_prompts: str = ""
    primary_dimension: str = ""
    sub_category: str = ""
    buyer_concern_cn: str = ""
    competitor_strength: str = ""
    competitor_mentions: str = ""
    price_evidence: str = ""
    review_evidence_summary: str = ""
    concern_scope: str = ""
    recovery_action: str = ""
    submit_attempt_count: int = 0
    submit_method: str = ""
    selector_strategy: str = ""
    notes: str = ""

    # === v2.1 (2026-05-11) Amazon Rufus 专利 AMZN-PATENT-RUFUS-STREAM 吸收增量 ===
    # 见 references/rufus-capture-strategy-patent-aligned.md
    capture_context: str = "own_pdp"             # own_pdp / competitor_pdp / search_results / home_page
    query_variant_group: str = ""                # 同义意图组 id(如 q-graduation-petite),变体共享
    question_type: str = ""                      # 5 种官方:factoid / navigation / review / item_summary / item_comparison
    retrieval_source_signals: str = ""           # 5 种 source 逗号分隔:item_search,review,qa,public,multimodal
    intermediate_tokens_detected: str = ""       # 7 种 token 逗号分隔:ITEM-LIST,aspect-list,comparison,related-questions 等


# ============================================================
# v2.1 启发式分类器 — Amazon Rufus 专利 AMZN-PATENT-RUFUS-STREAM 吸收
# 见 references/rufus-capture-strategy-patent-aligned.md
# ============================================================

def classify_question_type(query: str) -> str:
    """5 种官方 question type 的启发式分类(基于 query 文本)。"""
    q = (query or "").lower().strip()
    if not q:
        return "unknown"
    # navigation / help
    nav_signals = ("where is my", "how do i return", "shipping policy",
                   "order status", "how to cancel", "return policy",
                   "how do i contact")
    if any(s in q for s in nav_signals):
        return "navigation"
    # review question
    review_signals = ("do customers say", "what do people", "is it good for",
                      "are reviews", "does it leak", "does it last",
                      "is it durable", "how do buyers")
    if any(s in q for s in review_signals):
        return "review"
    # item_comparison
    if " vs " in q or " versus " in q or "compare" in q or "which is better" in q:
        return "item_comparison"
    # item_summary
    summary_signals = ("tell me about", "what is this product", "describe",
                       "summary of", "key features of")
    if any(s in q for s in summary_signals):
        return "item_summary"
    return "factoid"


_RETRIEVAL_SOURCE_SIGNALS = {
    "review": ("according to reviews", "customer reviews", "buyers mention",
               "customers report", "reviewers say", "based on reviews",
               "feedback from customers"),
    "qa": ("frequently asked", "common question", "asked by buyers",
           "according to the q&a", "in the questions section"),
    "public": ("according to wikipedia", "in general", "industry standard",
               "typically", "generally speaking", "as a general rule"),
    "multimodal": ("see image", "in the photo", "from the video",
                   "as shown in the picture", "image gallery"),
    "item_search": ("here are some options", "you might consider",
                    "products that match", "available items"),
}


def detect_retrieval_sources(answer_text: str) -> str:
    """识别答案 quote 来自哪些 retrieval source(可多选,逗号分隔)。"""
    text = (answer_text or "").lower()
    if not text:
        return ""
    hits = []
    for source_name, signals in _RETRIEVAL_SOURCE_SIGNALS.items():
        if any(sig in text for sig in signals):
            hits.append(source_name)
    # 启发式:含产品卡(价格 + 评分)也算 item_search
    if "$" in text and any(kw in text for kw in ("rating", "stars", "reviews")):
        if "item_search" not in hits:
            hits.append("item_search")
    return ",".join(hits)


_TOKEN_SIGNALS = {
    "ITEM-LIST": ("you might consider", "here are some products",
                  "options include", "products to consider"),
    "aspect-list": ("factors to consider", "things to consider",
                    "key considerations", "look for"),
    "category-list": ("categories include", "sub-categories", "types of"),
    "comparison": (" vs ", "compare these", "side by side",
                   "the differences are"),
    "related-questions": ("you might also ask", "related questions",
                          "people also ask", "you may also want to know"),
    "related-keywords": ("related searches", "you might search",
                         "related terms"),
}


def detect_intermediate_tokens(answer_text: str) -> str:
    """识别答案结构含哪些 intermediate token 残留信号(可多选)。"""
    text_l = (answer_text or "").lower()
    if not text_l:
        return ""
    hits = []
    for token_name, signals in _TOKEN_SIGNALS.items():
        if any(sig in text_l for sig in signals):
            hits.append(token_name)
    # ASIN 检测
    if re.search(r"\bB0[A-Z0-9]{8}\b", answer_text or ""):
        hits.append("ASIN-placeholder")
    return ",".join(hits)


def annotate_capture_row_v21(row) -> None:
    """对一条 CaptureRow 跑 v2.1 启发式标注(就地修改空字段)。"""
    if not row.question_type:
        row.question_type = classify_question_type(
            row.normalized_question or row.raw_question
        )
    if not row.retrieval_source_signals:
        row.retrieval_source_signals = detect_retrieval_sources(row.raw_answer)
    if not row.intermediate_tokens_detected:
        row.intermediate_tokens_detected = detect_intermediate_tokens(row.raw_answer)



# ============================================================
# CDP 通信
# ============================================================

class CDPClient:
    def __init__(self, ws):
        self.ws = ws
        self._counter = 0
    
    def _next_id(self):
        self._counter += 1
        return self._counter
    
    async def send(self, method, params=None):
        msg_id = self._next_id()
        await self.ws.send(json.dumps({
            'id': msg_id, 'method': method, 'params': params or {}
        }))
        while True:
            resp = json.loads(await self.ws.recv())
            if resp.get('id') == msg_id:
                if 'error' in resp:
                    raise RuntimeError(f"CDP error: {resp['error']}")
                return resp.get('result', {})
    
    async def eval(self, expression, await_promise=False, timeout_ms=30000):
        result = await self.send('Runtime.evaluate', {
            'expression': expression,
            'returnByValue': True,
            'awaitPromise': await_promise,
            'timeout': timeout_ms,
        })
        r = result.get('result', {})
        if r.get('subtype') == 'error':
            raise RuntimeError(f"JS error: {r.get('description', '')}")
        return r.get('value')


async def get_cdp_ws_url():
    """
    返回 page target 的 WebSocket URL,而不是 browser 级的。
    
    Page.navigate / Runtime.evaluate 等 domain 必须在 page target 上执行。
    走 /json/version 拿到的是 browser 级 WS URL,不能用于这些 domain。
    
    流程:
      1. 先尝试 /json/list 拿到现有 page target
      2. 如果没有 page target,用 /json/new 创建一个
      3. 返回 page 的 webSocketDebuggerUrl
    
    历史 bug:之前直接返回 /json/version 的 webSocketDebuggerUrl(browser 级),
    导致 'Page.navigate' wasn't found 错误(2026-05-06 修复)
    """
    list_url = f'http://127.0.0.1:{CHROME_PORT}/json/list'
    try:
        with urllib.request.urlopen(list_url, timeout=5) as r:
            targets = json.loads(r.read())
    except Exception as e:
        raise RuntimeError(
            f"无法连接 Chrome /json/list — Chrome 是否启动且加了 --remote-debugging-port={CHROME_PORT}?\n"
            f"原始错误:{e}"
        )
    
    # 找一个 type=page 的 target(过滤掉 service_worker / iframe / browser 等)
    page_targets = [t for t in targets if t.get('type') == 'page']
    
    if page_targets:
        # 优先选 amazon.com 相关页(如果已经在 amazon),否则用第一个 page
        amazon_targets = [t for t in page_targets if 'amazon.' in t.get('url', '')]
        target = amazon_targets[0] if amazon_targets else page_targets[0]
        return target['webSocketDebuggerUrl']
    
    # 没有现成的 page target → 创建一个
    new_url = f'http://127.0.0.1:{CHROME_PORT}/json/new?about:blank'
    try:
        # /json/new 走 PUT 方法(部分 Chrome 版本要求)
        req = urllib.request.Request(new_url, method='PUT')
        with urllib.request.urlopen(req, timeout=5) as r:
            new_target = json.loads(r.read())
            return new_target['webSocketDebuggerUrl']
    except Exception:
        # 回退:用 GET(老版本 Chrome)
        with urllib.request.urlopen(new_url, timeout=5) as r:
            new_target = json.loads(r.read())
            return new_target['webSocketDebuggerUrl']


# ============================================================
# 状态机各阶段
# ============================================================

async def state_login_check(cdp: CDPClient):
    name = await cdp.eval(
        "document.querySelector('#nav-link-accountList-nav-line-1')?.innerText || ''"
    )
    if name and ('Hello' in name or 'Hi,' in name):
        return {'logged_in': True, 'evidence': name}
    return {'logged_in': False, 'evidence': name or 'no_header_text'}


async def state_check_mobile_required(cdp: CDPClient):
    return await cdp.eval("""
        (function() {
            const txt = (document.body.innerText || '').toLowerCase();
            return txt.includes('add a mobile number')
                || txt.includes('add mobile number')
                || !!document.querySelector('input[name*="phone" i]:not([type="hidden"])');
        })()
    """)


async def state_navigate_asin(cdp: CDPClient, asin: str, marketplace: str = "com"):
    url = f"https://www.amazon.{marketplace}/dp/{asin}"
    await cdp.send('Page.navigate', {'url': url})
    await asyncio.sleep(3)
    
    # 等到页面有 Rufus 按钮或 product title
    for _ in range(15):
        ready = await cdp.eval("""
            !!document.querySelector('#productTitle, .nav-rufus-disco, .nav-rufus-disco-text')
        """)
        if ready:
            break
        await asyncio.sleep(1)
    
    # 验证 ASIN 一致
    actual = await cdp.eval(f"""
        (function() {{
            const inp = document.querySelector('input[name="ASIN"]');
            if (inp) return inp.value;
            const m = document.URL.match(/\\/dp\\/([A-Z0-9]+)/);
            return m ? m[1] : '';
        }})()
    """)
    
    return {
        'ok': actual == asin,
        'actual_asin': actual,
        'url': url,
    }


async def state_listing_snapshot(cdp: CDPClient):
    """快速读 Listing 关键字段。"""
    return await cdp.eval("""
        (function() {
            const t = (sel) => document.querySelector(sel)?.innerText?.trim() || '';
            const ts = (sel) => Array.from(document.querySelectorAll(sel)).map(e => e.innerText.trim());
            return {
                title: t('#productTitle'),
                brand: t('#bylineInfo'),
                price: t('.a-price .a-offscreen'),
                rating: t('[data-hook="rating-out-of-text"], #acrPopover .a-icon-alt'),
                reviewCount: t('#acrCustomerReviewText'),
                bullets: ts('#feature-bullets li:not(.aok-hidden)').slice(0, 8),
                imageCount: document.querySelectorAll('#altImages li img, #imageBlock img.a-dynamic-image').length,
                hasAplus: !!document.querySelector('#aplus_feature_div, #aplus, #aplusBrandStory_feature_div'),
            };
        })()
    """)


# ============================================================
# Rufus 探针 + 提问
# ============================================================

PROBE_RUFUS_JS = """
(function() {
    // v2.0.3 (2026-05-06): Hermes P0-1 修复 — 不只检查存在,还检查可交互
    // 历史 bug:.nav-rufus-disco-text 在某些产品页是 1×1 隐藏 div(display:none),
    //          探针返回 opener:true 但 click() 无效 → 整个采集流程在此中断
    
    // 多套 selector 兜底(Amazon 频繁 A/B 测试,单一 selector 不可靠)
    const OPENER_SELECTORS = [
        '.nav-rufus-disco-text',
        '.nav-rufus-disco',
        '#nav-rufus-button',
        '[aria-label*="Rufus" i]',
        '[aria-label*="Ask Rufus" i]',
        'button[id*="rufus" i]',
    ];
    
    let opener = null;
    let openerSelector = null;
    for (const sel of OPENER_SELECTORS) {
        const el = document.querySelector(sel);
        if (!el) continue;
        // 关键:可交互性验证(不是只看存在)
        const cs = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const interactive = cs.visibility !== 'hidden'
                          && cs.display !== 'none'
                          && rect.width > 1
                          && rect.height > 1;
        if (interactive) {
            opener = el;
            openerSelector = sel;
            break;
        }
    }
    
    const p = document.querySelector('#nav-flyout-rufus');
    const i = document.querySelector('#rufus-text-area, textarea[aria-label*="Rufus" i]');
    const s = document.querySelector('#rufus-submit-button, [data-testid="rufus-submit"]');
    return {
        opener: !!opener,
        opener_selector: openerSelector,  // 诊断信息:实际找到的是哪个 selector
        panel: !!p,
        input: !!i,
        submit: !!s,
        sameForm: !!(s && i && s.closest('form') === i.closest('form'))
    };
})()
"""


ASK_RUFUS_JS_TEMPLATE = r"""
(async function(question) {
    function setReactText(el, text) {
        const proto = el instanceof HTMLTextAreaElement
            ? HTMLTextAreaElement.prototype
            : HTMLInputElement.prototype;
        // v1.1.0: 加 ?. 防御。极端浏览器环境下 getOwnPropertyDescriptor 可能返回 undefined
        const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
        if (!setter) {
            // 兜底:直接赋值。React state 可能不会更新,但至少不抛异常
            el.value = text;
        } else {
            setter.call(el, text);
        }
        el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }
    function dispatchClick(el) {
        for (const t of ['pointerdown','mousedown','mouseup','click']) {
            el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window }));
        }
    }
    
    // v2.0.3 (2026-05-06): Hermes P0-1+P0-2 修复
    //   P0-1: 多 selector 兜底 + 可交互性验证(避开 1×1 隐藏 div)
    //   P0-2: click 后做面板可见性二次确认,最多重试 3 次
    
    const OPENER_SELECTORS = [
        '.nav-rufus-disco-text',
        '.nav-rufus-disco',
        '#nav-rufus-button',
        '[aria-label*="Rufus" i]',
        '[aria-label*="Ask Rufus" i]',
        'button[id*="rufus" i]',
    ];
    
    let opener = null;
    for (const sel of OPENER_SELECTORS) {
        const el = document.querySelector(sel);
        if (!el) continue;
        const cs = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        if (cs.visibility !== 'hidden' && cs.display !== 'none' && rect.width > 1 && rect.height > 1) {
            opener = el;
            break;
        }
    }
    if (!opener) return { ok: false, reason: 'rufus_not_visible' };
    
    // v2.0.4 (2026-05-06): Hermes P1-4 修复 — 滚动 + 多事件类型
    //   旧 bug: 页面有滚动偏移时,opener.click() 落在错误坐标无法触发 flyout
    //          (B0COMP1A01 实战中无法打开 Rufus 面板)
    //   修复: ① 先 scrollIntoView 让 opener 归位到 viewport
    //         ② 不只 click(),还派发完整 mouse 事件序列(pointerdown/mousedown/mouseup/click)
    //         ③ Python 侧 ask_rufus 失败时再降级用 CDP Input.dispatchMouseEvent(见 ask_rufus 函数)
    
    // 滚动到 opener 位置
    opener.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise(r => setTimeout(r, 300));
    
    // 重试 3 次:派发完整鼠标事件 → 等 → 检查 panel 是否真的可见
    let panel = null;
    for (let attempt = 0; attempt < 3; attempt++) {
        // 派发完整鼠标事件序列(比单纯 click() 更鲁棒)
        for (const t of ['pointerdown', 'mousedown', 'mouseup', 'click']) {
            opener.dispatchEvent(new MouseEvent(t, {
                bubbles: true, cancelable: true, view: window,
                button: 0, buttons: 1
            }));
        }
        await new Promise(r => setTimeout(r, 1000 + attempt * 500));  // 1.0/1.5/2.0s
        const p = document.getElementById('nav-flyout-rufus');
        if (p) {
            const cs = window.getComputedStyle(p);
            const rect = p.getBoundingClientRect();
            if (cs.visibility !== 'hidden' && cs.display !== 'none' && rect.height > 50) {
                panel = p;
                break;
            }
        }
    }
    if (!panel) return { ok: false, reason: 'panel_not_visible_after_click' };
    
    const input = document.getElementById('rufus-text-area');
    const submit = document.querySelector('#rufus-submit-button, [data-testid="rufus-submit"]');
    if (!input || !submit) return { ok: false, reason: 'selector_verification_failed' };
    if (input.closest('form') !== submit.closest('form')) {
        return { ok: false, reason: 'selector_verification_failed' };
    }
    
    input.focus();
    setReactText(input, question);
    await new Promise(r => setTimeout(r, 300));
    dispatchClick(submit);
    
    // 等 user turn 出现
    let acked = false;
    const ackStart = Date.now();
    while (Date.now() - ackStart < 6000) {
        await new Promise(r => setTimeout(r, 250));
        if (panel.innerText.includes(question.slice(0, Math.min(40, question.length)))) {
            acked = true;
            break;
        }
    }
    if (!acked) return { ok: false, reason: 'submit_not_acknowledged' };
    
    // 等答案稳定
    // v2.0.4 (2026-05-06): Hermes P0-3 修复 — 显式文本判定,不再模糊匹配
    //   旧 bug: txt.includes('generating') 会匹配 class 名 'rufus-generating-animation'
    //          导致永远判定为"仍在生成",90s 后超时 100% 失败
    //   修复: 只检测显式短语
    let lastLen = -1;
    let stableHits = 0;
    const start = Date.now();
    const maxMs = 90000;  // 90s,长答案兜底
    
    while (Date.now() - start < maxMs) {
        await new Promise(r => setTimeout(r, 1500));
        
        const txt = panel.innerText || '';
        // ✅ 只检测显式短语,不模糊匹配(避免误判 class 名)
        const isThinking = txt.includes('currently generating')
            || txt.includes('generating a response')
            || txt.includes('Rufus is thinking');
        const hasResume = !!panel.querySelector('[aria-label*="Resume" i]')
            || Array.from(panel.querySelectorAll('button')).some(b =>
                (b.innerText || '').includes('Resume response'));
        
        if (isThinking || hasResume) {
            stableHits = 0;
            continue;
        }
        
        if (txt.length === lastLen && txt.length > 100) {
            stableHits++;
            if (stableHits >= 2) {
                // 提取 follow-up
                const followups = Array.from(panel.querySelectorAll(
                    'button[data-testid*="suggestion" i], button[data-testid*="follow" i]'
                )).map(b => b.innerText.trim()).filter(Boolean);
                
                // v2.0.4 (2026-05-06): Hermes P0-1+P0-2 修复 — turn 选择器 + 按问题匹配
                //   旧 bug 1: 选择器 [role="article"] 在 Rufus 实际 DOM 中不存在
                //            → turns.length 永远为 0 → 永远 fallback 到 panel.innerText
                //   旧 bug 2: 取 turns[turns.length-1] 在新 turn 出现延迟时拿到旧 turn
                //            → Hermes 实战中 48/50 题答案错位一题
                //   修复: 多 selector 优先级 + 按问题文本匹配
                const TURN_SELECTORS = [
                    '.rufus-papyrus-turn',           // ✅ Hermes 实战验证的真实 selector
                    '[role="article"]',               // 兜底(以防未来 Amazon 改 DOM)
                    '[data-testid*="rufus-message" i]',
                    '[class*="message-turn"]',
                    '[class*="rufus-turn"]',
                ];
                
                let turns = [];
                let usedSelector = '';
                for (const sel of TURN_SELECTORS) {
                    const found = panel.querySelectorAll(sel);
                    if (found.length > 0) {
                        turns = found;
                        usedSelector = sel;
                        break;
                    }
                }
                
                let scopedAnswer = txt;
                let strategy = 'panel_text_fallback';
                
                if (turns.length) {
                    // ① 优先:从后往前找包含问题前 30 字的 turn(避免新 turn 延迟问题)
                    const shortQ = question.slice(0, Math.min(30, question.length));
                    let matchedTurn = null;
                    for (let i = turns.length - 1; i >= 0; i--) {
                        const turnText = turns[i].innerText || '';
                        if (turnText.includes(shortQ) && turnText.length > 50) {
                            matchedTurn = turns[i];
                            break;
                        }
                    }
                    
                    if (matchedTurn) {
                        scopedAnswer = matchedTurn.innerText;
                        strategy = 'question_matched_turn:' + usedSelector;
                    } else {
                        // ② 降级:取最后一个非空 turn
                        for (let i = turns.length - 1; i >= 0; i--) {
                            const t = turns[i].innerText || '';
                            if (t.length > 50) {
                                scopedAnswer = t;
                                strategy = 'last_nonempty_turn:' + usedSelector;
                                break;
                            }
                        }
                    }
                }
                
                return {
                    ok: true,
                    answer: scopedAnswer,
                    panelText: txt,
                    answerLength: scopedAnswer.length,
                    followups: followups,
                    selectorStrategy: strategy,
                    answerContainsQuestion: scopedAnswer.includes(question.slice(0, Math.min(30, question.length))),
                };
            }
        } else {
            stableHits = 0;
            lastLen = txt.length;
        }
    }
    
    return { ok: false, reason: 'answer_stabilization_timeout' };
})(__QUESTION__)
"""


async def ask_rufus(cdp: CDPClient, question: str):
    """提交一个问题给 Rufus 并等答案稳定。
    
    v1.1.0 注:
    - question 通过 json.dumps 转义后注入 JS 字面量,在 JS 字符串上下文里安全
      (json.dumps 转义所有 quotes、newline、unicode 控制字符)
    - 但 input source 应来自可信渠道(plan CSV 或 SKILL.md 内置题库)
    - 长 question(> 1000 字)被拒绝以防 DOM 注入意外
    - 未来如有并发需求,应改用 Runtime.callFunctionOn + 参数列表
    
    v2.0.4 (2026-05-06) Hermes P1-4 修复:
    - 主路径仍用 JS 派发 mouse 事件(已加 scrollIntoView + 多事件类型)
    - 失败时降级到 CDP Input.dispatchMouseEvent(原生鼠标事件,绕过 JS 限制)
    """
    if not isinstance(question, str):
        return {'ok': False, 'reason': 'invalid_question_type'}
    if len(question) > 1000:
        return {'ok': False, 'reason': 'question_too_long'}
    if not question.strip():
        return {'ok': False, 'reason': 'empty_question'}
    
    js = ASK_RUFUS_JS_TEMPLATE.replace('__QUESTION__', json.dumps(question))
    result = await cdp.eval(js, await_promise=True, timeout_ms=120000)
    
    # P1-4 降级路径:JS 主路径打不开面板时,改用 CDP 原生鼠标事件
    if not result.get('ok') and result.get('reason') == 'panel_not_visible_after_click':
        print("    ⚠ JS 派发事件未打开 Rufus 面板,降级到 CDP 原生鼠标事件...")
        cdp_open_ok = await _cdp_open_rufus_panel(cdp)
        if cdp_open_ok:
            # 面板已通过 CDP 打开,重跑 ASK_RUFUS_JS_TEMPLATE(它会检测到面板已可见,跳过 click 重试)
            result = await cdp.eval(js, await_promise=True, timeout_ms=120000)
    
    return result


async def _cdp_open_rufus_panel(cdp: CDPClient):
    """通过 CDP Input.dispatchMouseEvent 原生鼠标事件打开 Rufus 面板。
    
    用作 JS click 失败的降级路径。CDP 原生事件比 JS dispatchEvent 更接近真实用户行为,
    能绕过部分 Amazon 前端的 trust 检测。
    """
    # 1. 在页面里找 opener 并 scrollIntoView,返回精确坐标
    info = await cdp.eval("""
        (function() {
            const SELECTORS = [
                '.nav-rufus-disco-text', '.nav-rufus-disco', '#nav-rufus-button',
                '[aria-label*="Rufus" i]', '[aria-label*="Ask Rufus" i]',
                'button[id*="rufus" i]'
            ];
            let opener = null;
            for (const sel of SELECTORS) {
                const el = document.querySelector(sel);
                if (!el) continue;
                const cs = window.getComputedStyle(el);
                const r = el.getBoundingClientRect();
                if (cs.visibility !== 'hidden' && cs.display !== 'none' && r.width > 1 && r.height > 1) {
                    opener = el;
                    break;
                }
            }
            if (!opener) return { found: false };
            opener.scrollIntoView({ block: 'center', behavior: 'instant' });
            const rect = opener.getBoundingClientRect();
            return {
                found: true,
                x: Math.round(rect.left + rect.width / 2),
                y: Math.round(rect.top + rect.height / 2)
            };
        })()
    """)
    
    if not info or not info.get('found'):
        return False
    
    x, y = info['x'], info['y']
    
    # 2. 派发完整 CDP 鼠标事件序列
    await cdp.send('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': x, 'y': y})
    await asyncio.sleep(0.15)
    for evt in ['mousePressed', 'mouseReleased']:
        await cdp.send('Input.dispatchMouseEvent', {
            'type': evt, 'x': x, 'y': y, 'button': 'left', 'clickCount': 1
        })
        await asyncio.sleep(0.05)
    
    # 3. 等面板出现并可见
    for _ in range(6):  # 最多等 3 秒
        await asyncio.sleep(0.5)
        visible = await cdp.eval("""
            (function() {
                const p = document.getElementById('nav-flyout-rufus');
                if (!p) return false;
                const cs = window.getComputedStyle(p);
                const r = p.getBoundingClientRect();
                return cs.visibility !== 'hidden' && cs.display !== 'none' && r.height > 50;
            })()
        """)
        if visible:
            return True
    return False


async def close_rufus_panel(cdp: CDPClient):
    """关闭 Rufus 面板,减少下一题的上下文污染。
    
    注意:这不是限流绕过,只是为了避免 Rufus 把上一题答案当成本题上下文。
    """
    await cdp.eval("""
        const close = document.querySelector('[aria-label*="Close" i][aria-label*="rufus" i]')
            || document.querySelector('#nav-flyout-rufus button[aria-label*="Close" i]');
        if (close) close.click();
    """)
    await asyncio.sleep(1)


# ============================================================
# Question plan 处理
# ============================================================

def normalize_question(q):
    return re.sub(r'\s+', ' ', q.lower().strip(' ?.,!"\''))


def load_plan_csv(path):
    plan = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            plan.append(row)
    return plan


# ============================================================
# v2.0.0 新增:类目包加载
# ============================================================

def load_category_pack(category, pack_dir=None):
    """读取 categories/<category>/pack.yaml,返回 dict。
    
    v2.0.0:把 v1 的硬编码 apparel 七维改成从 pack.yaml 动态读取。
    
    pack_dir 可选指定 categories/ 路径(默认相对脚本位置查找)。
    """
    if pack_dir is None:
        # 脚本在 scripts/ 下,categories 在同级
        script_dir = Path(__file__).parent
        pack_dir = script_dir.parent / 'categories'
    else:
        pack_dir = Path(pack_dir)
    
    pack_path = pack_dir / category / 'pack.yaml'
    if not pack_path.exists():
        raise FileNotFoundError(
            f"找不到类目包: {pack_path}\n"
            f"可用类目: {sorted([p.name for p in pack_dir.iterdir() if p.is_dir()])}"
        )
    
    try:
        import yaml
    except ImportError:
        # yaml 没装,简易 fallback 解析(只支持本 skill 的 pack.yaml 结构)
        return _parse_pack_yaml_simple(pack_path)
    
    with open(pack_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def _parse_pack_yaml_simple(pack_path):
    """yaml 模块没装时的兜底解析器,只支持本 skill pack.yaml 的 schema。
    
    支持:string、list of string、list of mapping(dimensions / required_secrets)。
    不支持嵌套 block scalar。
    """
    pack = {}
    current_key = None
    current_list = None
    current_dict = None  # 当前正在构建的列表 item dict
    list_item_indent = None
    
    with open(pack_path, encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')
            stripped = line.lstrip()
            
            # 跳过注释和空行
            if not stripped or stripped.startswith('#'):
                continue
            
            indent = len(line) - len(stripped)
            
            # 顶层 key: value 或 顶层 key:
            if indent == 0 and ':' in stripped:
                if current_dict and current_list is not None:
                    current_list.append(current_dict)
                    current_dict = None
                
                key, _, val = stripped.partition(':')
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                
                if val:
                    pack[key] = val
                else:
                    pack[key] = []
                    current_key = key
                    current_list = pack[key]
                    current_dict = None
                continue
            
            # 列表 item
            if stripped.startswith('- '):
                if current_dict:
                    current_list.append(current_dict)
                    current_dict = None
                
                item = stripped[2:].strip()
                if ':' in item:
                    # 列表 item 是 dict(- code: foo)
                    k, _, v = item.partition(':')
                    current_dict = {k.strip(): v.strip().strip("'").strip('"')}
                    list_item_indent = indent + 2
                else:
                    # 列表 item 是 string
                    current_list.append(item.strip("'").strip('"'))
                continue
            
            # 列表 item dict 的后续字段
            if current_dict is not None and indent >= (list_item_indent or indent):
                if ':' in stripped:
                    k, _, v = stripped.partition(':')
                    current_dict[k.strip()] = v.strip().strip("'").strip('"')
    
    # flush 最后一个 dict
    if current_dict and current_list is not None:
        current_list.append(current_dict)
    
    return pack


# 类目内置题库:每个类目一份针对 N 维 Minimum Question Set 的兜底问题
# 当用户没给 plan 文件时,根据 --category 选用对应的题库
CATEGORY_QUESTION_BANKS = {
    'apparel': [
        # 七维 Minimum Question Set
        ("size_advice_by_body", "I'm 5'6 and 140 lbs, what size should I order?", "size"),
        ("size_run", "Does this run small, large, or true to size?", "size"),
        ("fit_silhouette", "Is this oversized or fitted?", "fit"),
        ("fit_length", "How does the length fit on a 5'6 person?", "fit"),
        ("fabric_composition", "What's it made of?", "fabric"),
        ("fabric_weight_thickness", "Is the fabric thick or see-through?", "fabric"),
        ("fabric_breathability", "Is it breathable for warm weather?", "fabric"),
        ("occasion_casual_daily", "Is this good for daily wear?", "occasion"),
        ("occasion_work_office", "Is this office appropriate?", "occasion"),
        ("care_wash_method", "Can I machine wash this?", "care"),
        ("care_shrinkage", "Will it shrink after washing?", "care"),
        ("complaint_color_mismatch", "Is the color accurate to the photos?", "complaint"),
        ("complaint_quality_concern", "Is the stitching and quality good?", "complaint"),
        ("vs_competitor_feature_diff", "How does this compare to similar items?", "vs_competitor"),
        ("customer_sentiment_overall", "What do customers say about this product?", "complaint"),
    ],
    'electronics': [
        # 八维 Minimum Question Set
        ("specs_dimensions_weight", "What are the dimensions and weight?", "specs"),
        ("specs_connectivity", "What Bluetooth / Wi-Fi version does it use?", "specs"),
        ("compat_device_compatibility", "Does this work with iPhone 15 and Samsung Galaxy S24?", "compatibility"),
        ("compat_os_version", "What's the minimum iOS / Android version required?", "compatibility"),
        ("compat_port_connector", "What port does it use? USB-C or Lightning?", "compatibility"),
        ("perf_battery_life", "What's the real battery life with normal use?", "performance"),
        ("perf_signal_range", "What's the wireless range in feet?", "performance"),
        ("setup_unboxing_setup_time", "How long does setup take? Need an app?", "setup_difficulty"),
        ("dur_warranty_terms", "What's the warranty period and policy?", "durability"),
        ("dur_water_dust_resistance", "Is it waterproof? What's the IP rating?", "durability"),
        ("acc_whats_in_box", "What comes in the box? Includes charger?", "accessories_included"),
        ("complaint_dead_on_arrival", "Common to arrive defective?", "complaint"),
        ("complaint_early_failure", "Does it stop working after a few weeks?", "complaint"),
        ("vs_competitor_named_brand", "How does this compare to similar brands?", "vs_competitor"),
        ("customer_sentiment_overall", "What do customers say about this product?", "complaint"),
    ],
    'home_kitchen': [
        # 七维 Minimum Question Set
        ("size_external_dimensions", "What are the exact dimensions in inches?", "size_dimensions"),
        ("size_fits_specific_space", "Will this fit on a standard countertop?", "size_dimensions"),
        ("material_food_grade_safe", "Is the material food-safe and FDA approved?", "material"),
        ("material_heat_resistance", "Is it microwave / oven safe? What temperature?", "material"),
        ("material_bpa_free", "Is it BPA-free?", "material"),
        ("capacity_liter_oz_volume", "How many ounces / liters does it hold?", "capacity"),
        ("clean_dishwasher_safe", "Is this dishwasher safe?", "cleaning_care"),
        ("clean_stain_resistance", "Does it stain or hold odors easily?", "cleaning_care"),
        ("safety_heat_safety", "Does the handle get hot during use?", "safety"),
        ("safety_child_safe", "Is this safe to use around kids?", "safety"),
        ("complaint_arrived_damaged", "Common to arrive damaged?", "complaint"),
        ("complaint_smell_chemical", "Does it have a chemical smell out of the box?", "complaint"),
        ("vs_competitor_named_brand", "How does this compare to other similar products?", "vs_competitor"),
        ("customer_sentiment_overall", "What do customers say about this product?", "complaint"),
    ],
    'beauty': [
        # 八维 Minimum Question Set(注意合规高压)
        ("ingredients_active", "What are the active ingredients and their percentages?", "ingredients"),
        ("ingredients_free_from", "Is this paraben-free, sulfate-free, fragrance-free?", "ingredients"),
        ("ingredients_vegan_cruelty_free", "Is this vegan and cruelty-free?", "ingredients"),
        ("skin_type_dry_skin_friendly", "Is this good for dry skin?", "skin_type_match"),
        ("skin_type_sensitive_skin", "Is this safe for sensitive skin?", "skin_type_match"),
        ("effect_time_to_see_results", "How long until I see results with regular use?", "effect_timeline"),
        ("safety_dermatologist_tested", "Is this dermatologist tested?", "allergy_safety"),
        ("safety_common_allergens", "Does this contain any common allergens?", "allergy_safety"),
        ("scent_strength", "Does this have a strong scent?", "scent_texture"),
        ("scent_texture_consistency", "What's the texture like? Thick or runny?", "scent_texture"),
        ("volume_lasts_how_long", "How long does one bottle last with daily use?", "volume_value"),
        ("complaint_caused_breakout", "Has this caused breakouts for some users?", "complaint"),
        ("complaint_irritation_redness", "Does it cause irritation or redness?", "complaint"),
        ("vs_competitor_named_brand", "How does this compare to similar products?", "vs_competitor"),
        ("customer_sentiment_overall", "What do customers say about this product?", "complaint"),
    ],
    'pet_supplies': [
        ("fit_size_measurement", "What size should I choose and how should I measure my dog?", "fit_size"),
        ("fit_size_breed_weight", "Is this suitable for small, medium, large, or extra-large dogs?", "fit_size"),
        ("control_no_pull", "How does this help with pulling during daily walks?", "no_pull_control"),
        ("control_strong_puller", "Is this good for a large strong dog that pulls hard?", "no_pull_control"),
        ("comfort_pressure", "Does it reduce pressure on the neck and chest?", "comfort_pressure"),
        ("comfort_daily_wear", "Is it comfortable for daily walks and longer outings?", "comfort_pressure"),
        ("travel_car_safety", "Does it include a car seat belt or travel safety attachment?", "travel_safety"),
        ("travel_outdoor_use", "Is this good for hiking, road trips, park visits, and car rides?", "travel_safety"),
        ("accessories_included", "What comes in the set and what accessories are included?", "accessories_included"),
        ("accessories_essential_vs_extra", "Is this a practical complete walking kit or just extra accessories?", "accessories_included"),
        ("durability_hardware", "Are the buckles, rings, stitching, and nylon durable?", "durability"),
        ("cleaning_care", "Is it washable or easy to clean after outdoor use?", "cleaning_care"),
        ("complaint_common_issues", "What are common customer complaints about this harness set?", "complaint"),
        ("vs_competitor_use_case", "How does this compare with other no-pull dog harness sets?", "vs_competitor"),
        ("customer_sentiment_overall", "What do customers say about this product?", "complaint"),
    ],
    '_generic': [
        # 五维 Minimum Question Set
        ("specs_dimensions_size", "What are the dimensions of this product?", "specs"),
        ("specs_material_composition", "What's it made of?", "specs"),
        ("specs_included_components", "What comes in the package?", "specs"),
        ("usage_primary_use_case", "What is this used for?", "usage"),
        ("usage_setup_difficulty", "Is it easy to set up?", "usage"),
        ("quality_build_quality", "Does it feel cheap or sturdy?", "quality"),
        ("quality_durability", "How long does it typically last?", "quality"),
        ("complaint_defect_rate", "What are common problems with this?", "complaint"),
        ("complaint_quality_vs_photo", "Does it look like the photos?", "complaint"),
        ("vs_competitor_feature_diff", "What makes this different from alternatives?", "vs_competitor"),
        ("customer_sentiment_overall", "What do customers say about this product?", "complaint"),
    ],
}


def default_starter_plan(asin, role, category='_generic', marketplace='com'):
    """没给 plan 文件时,生成最小 starter 计划。
    
    v2.0.0:从 CATEGORY_QUESTION_BANKS 按类目读题库,不再硬编码服装。
    
    实际使用应该先读 Listing 跑 product profile 再生成,这里只是兜底。
    """
    if category not in CATEGORY_QUESTION_BANKS:
        # 未知类目,fallback 到 _generic
        print(f"  ⚠ 未知类目 '{category}',使用 _generic 题库")
        category = '_generic'
    
    base = CATEGORY_QUESTION_BANKS[category]
    plan = []
    for i, (sub, q, dim) in enumerate(base, 1):
        plan.append({
            'planned_question_id': f"{role.upper()[:3]}-{asin[:6]}-Q{i:03d}",
            'asin': asin,
            'product_role': role,
            'question_text': q,
            'question_origin': 'category_coverage_generated',
            'profile_signal': f'{category}_minimum_set',
            'primary_dimension': dim,
            'sub_category': sub,
            'priority_score': '3',
        })
    return plan


def validate_plan_coverage(plan, category='_generic', pack_dir=None):
    """验证 plan 是否覆盖类目 N 维 Minimum Question Set。
    
    v2.0.0:从 pack.yaml.min_question_set 动态读必须维度,不再硬编码单一类目。
    
    返回 (is_complete, missing_dims_list)。
    """
    try:
        pack = load_category_pack(category, pack_dir=pack_dir)
        required_dims_raw = pack.get('min_question_set', [])
        # min_question_set 里的 customer_sentiment 不是真维度,是单独那道总结题
        required_dims = {d for d in required_dims_raw if d != 'customer_sentiment'}
    except (FileNotFoundError, KeyError) as e:
        # pack 读不到,fallback 到 dimensions 字段
        print(f"  ⚠ 读取 pack 失败: {e}, 使用默认通用五维")
        required_dims = {'specs', 'usage', 'quality', 'complaint', 'vs_competitor'}
    
    covered = {q.get('primary_dimension', '') for q in plan if q.get('primary_dimension')}
    missing = required_dims - covered
    return (len(missing) == 0, sorted(missing))


# ============================================================
# 主流程
# ============================================================

async def run_one_asin(cdp, asin, role, marketplace, plan, output_dir, persona="default"):
    rows = []
    blocker = None
    
    # ===== Checkpoint resume(2026-05-06 加)=====
    # 读已有 csv,跳过 capture_status='answered' 的题(避免重复抓)
    csv_path = Path(output_dir) / f'capture_{asin}.csv'
    progress_path = Path(output_dir) / 'progress.json'
    answered_qids = set()
    if csv_path.exists():
        try:
            with open(csv_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get('capture_status') == 'answered':
                        answered_qids.add(r.get('planned_question_id'))
                        # 把已抓的也算入 rows(健康统计需要)
                        rows.append(_dict_to_capture_row(r))
            if answered_qids:
                print(f"  ↻ checkpoint: 跳过 {len(answered_qids)} 已抓题(从 capture_{asin}.csv 恢复)")
        except Exception as e:
            print(f"  ⚠ checkpoint 读失败,从头开始: {e}")
            answered_qids = set()
    
    # ===== ASIN 切换重置(2026-05-06 Hermes P0-3+P1-6 修复)=====
    # 历史 bug:切换 ASIN 时 Rufus 面板保留旧对话历史,新问题被当 follow-up,
    #          答案漂移到旧 ASIN(2026-05-06 Hermes 实测竞品 7/25,5 个维度全失败)
    # 修复:每个 ASIN 开始前强制 close_rufus_panel,让面板进入干净状态
    try:
        await close_rufus_panel(cdp)
        await asyncio.sleep(0.5)
        print(f"  ↻ ASIN 切换:已重置 Rufus 面板状态(避免上一个 ASIN 的对话污染)")
    except Exception as e:
        # close_rufus_panel 失败不致命,继续
        print(f"  ⚠ Rufus 面板重置失败(非致命): {e}")
    
    # 1. 登录检查 — 重要:已登录时直接复用,不要反复触发登录流程
    # (Amazon 买家账号一旦登录会保持很久,重复登录反而触发风控)
    login = await state_login_check(cdp)
    if not login['logged_in']:
        blocker = {
            'reason': 'amazon_buyer_login_required',
            'evidence': login['evidence'],
            'message': '浏览器没登录 Amazon 买家账号,请让用户在当前 Chrome 窗口手动登录后重试'
        }
        print(f"  ✗ 未登录(evidence: {login['evidence']}),请用户在浏览器手动登录后重试")
        return rows, blocker
    else:
        print(f"  ✓ 已登录({login['evidence']}),复用现有登录态(避免重复登录触发风控)")
    
    # 2. 检查手机号验证
    if await state_check_mobile_required(cdp):
        blocker = {
            'reason': 'mobile_number_verification_required',
            'message': 'Amazon 要求添加手机号,请通过 chat 通道提供手机号 → 提交后回复"已添加手机号" → 提供短信验证码'
        }
        return rows, blocker
    
    # 3. 导航
    nav = await state_navigate_asin(cdp, asin, marketplace)
    if not nav['ok']:
        blocker = {
            'reason': 'page_mismatch',
            'message': f"导航到 {asin} 失败,实际 ASIN: {nav.get('actual_asin')}",
        }
        return rows, blocker
    
    # 4. Listing 快照(简化版 — 完整 profile 应在外部跑)
    snapshot = await state_listing_snapshot(cdp)
    snapshot_path = Path(output_dir) / f"listing_snapshot_{asin}.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    
    # 5. Rufus 探针
    # v1.1.0:只检查 opener 必须存在(panel/input 在 ask 时打开后才会出现,不在此预检)
    # 之前用 `or True` 让检查永远通过的写法已删除
    probe = await cdp.eval(PROBE_RUFUS_JS)
    if not probe.get('opener'):
        blocker = {
            'reason': 'rufus_not_visible',
            'message': f'ASIN {asin} 上没找到 Rufus 入口按钮(可能被站点 A/B 屏蔽)',
            'probe_state': probe,  # 保留诊断信息
        }
        return rows, blocker
    
    # 6. 逐题抓取
    todo_count = len([q for q in plan if q['planned_question_id'] not in answered_qids])
    print(f"  开始抓 {todo_count}/{len(plan)} 题(已跳过 {len(answered_qids)} 题)")
    # ===== 连续失败恢复(2026-05-06 Hermes P0-3 修复)=====
    # 历史 bug:某题失败后,后续题目继续尝试,不做"重新导航 + 重新打开面板"的自愈
    # 修复:连续 3 题失败 → 执行完整重置(关面板 + 重载页面 + 重新探针)
    consecutive_failures = 0
    
    for idx, q in enumerate(plan, 1):
        # ===== checkpoint skip(2026-05-06 加)=====
        if q['planned_question_id'] in answered_qids:
            continue
        capture_id = f"{q['planned_question_id']}-CAP"
        row = CaptureRow(
            capture_id=capture_id,
            capture_date=datetime.now().isoformat(),
            marketplace=marketplace,
            product_role=role,
            asin=asin,
            product_url=nav['url'],
            persona_label=persona,
            login_status='logged_in',
            planned_question_id=q['planned_question_id'],
            question_origin=q.get('question_origin', ''),
            profile_signal=q.get('profile_signal', ''),
            primary_dimension=q.get('primary_dimension', ''),
            sub_category=q.get('sub_category', ''),
            raw_question=q['question_text'],
            normalized_question=normalize_question(q['question_text']),
        )
        
        try:
            result = await ask_rufus(cdp, q['question_text'])
        except Exception as e:
            result = {'ok': False, 'reason': f'js_exception: {str(e)[:80]}'}
        
        row.submit_attempt_count = 1
        row.submit_method = 'click_dispatch'
        
        if result.get('ok'):
            row.capture_status = 'answered'
            row.raw_answer = result['answer']
            row.answer_length_chars = result['answerLength']
            row.follow_up_prompts = ' | '.join(result.get('followups', []))
            row.selector_strategy = result.get('selectorStrategy', '')
            
            # v2.0.4 (2026-05-06): Hermes P0-2 修复 — 答案匹配验证
            # 检查答案是否真的包含当前问题文本(避免错位拿到上一题答案)
            answer_contains_q = result.get('answerContainsQuestion', False)
            if not answer_contains_q and row.selector_strategy.startswith('panel_text_fallback'):
                # fallback 模式下 panel.innerText 含整个对话历史,正常包含问题文本是巧合
                row.answer_confidence = 'low_fallback'
            elif not answer_contains_q:
                # 用了具体 turn 但答案不含问题前 30 字 → 高度可疑(可能错位)
                row.answer_confidence = 'mismatch_warning'
                print(f"    ⚠ 答案不含问题前 30 字,可能是错位({row.selector_strategy})")
            else:
                row.answer_confidence = 'high'
            
            # 简单分类 answer_type
            ans_low = row.raw_answer.lower()
            if 'instead' in ans_low and 'consider' in ans_low:
                row.answer_type = 'alternative_recommendation'
            elif re.search(r'\$\d+', row.raw_answer) and 'compar' in ans_low:
                row.answer_type = 'comparison_table'
            elif 'customers' in ans_low or 'reviewers' in ans_low or 'buyers' in ans_low:
                row.answer_type = 'review_summary'
            elif '$' in row.raw_answer:
                row.answer_type = 'price_history'
            else:
                row.answer_type = 'direct_answer'
            
            print(f"  [{idx}/{len(plan)}] ✓ {row.answer_length_chars} 字 | {row.answer_type} | conf={row.answer_confidence}")
            consecutive_failures = 0  # 成功 → 重置失败计数
        else:
            reason = result.get('reason', 'unknown')
            if reason in {'submit_not_acknowledged', 'answer_stabilization_timeout', 'first_answer_timeout'}:
                row.capture_status = 'question_only'
            else:
                row.capture_status = 'blocked'
            row.failure_reason = reason
            row.answer_confidence = 'none'
            print(f"  [{idx}/{len(plan)}] ✗ {reason}")
            consecutive_failures += 1
        
        rows.append(row)
        
        # ===== Checkpoint write(2026-05-06 加)=====
        # 逐题落盘 — 中断 = 最多丢 1 题(当前正在抓的),不会丢已成功的
        _append_row_to_csv(row, csv_path)
        _update_progress(progress_path, asin, role, q['planned_question_id'],
                         row.capture_status, len(rows), len(plan))
        
        # ===== 连续失败恢复(2026-05-06 Hermes P0-3 修复)=====
        if consecutive_failures >= 3:
            print(f"  ⚠ 连续 {consecutive_failures} 题失败,执行完整重置(关面板+重载页面+重新探针)")
            try:
                await close_rufus_panel(cdp)
                await asyncio.sleep(1)
                # 重载页面 — 让 Rufus 进入完全干净状态
                await cdp.send('Page.reload')
                await asyncio.sleep(5)
                # 重新探针
                probe = await cdp.eval(PROBE_RUFUS_JS)
                if not probe.get('opener'):
                    print(f"  ✗ 完整重置后仍无 Rufus,放弃当前 ASIN")
                    blocker = {
                        'reason': 'rufus_lost_after_reset',
                        'message': f'连续 {consecutive_failures} 题失败,完整重置后仍无 Rufus 入口',
                    }
                    break
                consecutive_failures = 0  # 重置成功 → 清零计数
                print(f"  ✓ 重置成功,继续采集")
            except Exception as e:
                print(f"  ✗ 完整重置失败: {e}")
                # 不中断主循环,让后续 try 一下
        
        # 每 5 题关一次面板,减上下文污染
        if idx % 5 == 0:
            await close_rufus_panel(cdp)
        
        await asyncio.sleep(2)  # UI 节流,不是反封
    
    return rows, blocker


# ============================================================
# Checkpoint helpers(2026-05-06 加)
# ============================================================

def _append_row_to_csv(row, csv_path):
    """逐题 append 到 csv。第一题写 header,后续只 append 数据行。"""
    file_exists = csv_path.exists()
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = list(asdict(row).keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(asdict(row))


def _update_progress(progress_path, asin, role, qid, status, done, total):
    """更新 progress.json — 中断后另一个 Agent 接力时能精确知道进度。"""
    try:
        if progress_path.exists():
            data = json.loads(progress_path.read_text(encoding='utf-8'))
        else:
            data = {'started_at': datetime.now().isoformat(), 'asins': {}}
    except Exception:
        data = {'started_at': datetime.now().isoformat(), 'asins': {}}
    
    if asin not in data['asins']:
        data['asins'][asin] = {'role': role, 'questions': []}
    
    data['asins'][asin]['questions'].append({
        'qid': qid,
        'status': status,
        'timestamp': datetime.now().isoformat(),
    })
    data['asins'][asin]['done'] = done
    data['asins'][asin]['total'] = total
    data['last_update'] = datetime.now().isoformat()
    
    progress_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _dict_to_capture_row(d):
    """从 csv dict 还原成 CaptureRow,用于 checkpoint 恢复。
    
    所有字段先以默认值创建 CaptureRow,然后覆盖 csv 里有的字段(防止字段集变化)。
    """
    row = CaptureRow()
    for k, v in d.items():
        if hasattr(row, k):
            # 数值字段类型转换
            if k in ('answer_length_chars', 'submit_attempt_count'):
                try:
                    setattr(row, k, int(v) if v else 0)
                except (ValueError, TypeError):
                    setattr(row, k, 0)
            else:
                setattr(row, k, v or '')
    return row


def write_csv(rows, path):
    if not rows:
        return
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))


def write_health(asin_results, path):
    health = {
        'capture_date': datetime.now().isoformat(),
        'asins': {},
    }
    for asin, (rows, blocker) in asin_results.items():
        statuses = {}
        for r in rows:
            statuses[r.capture_status] = statuses.get(r.capture_status, 0) + 1
        health['asins'][asin] = {
            'total': len(rows),
            'statuses': statuses,
            'blocker': blocker,
            'success_rate': round(statuses.get('answered', 0) / len(rows), 2) if rows else 0,
        }
    Path(path).write_text(json.dumps(health, ensure_ascii=False, indent=2))


async def main_async(args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    asins = args.asins.split(',') if args.asins else [args.asin]
    roles = args.roles.split(',') if args.roles else [args.role]
    if len(asins) != len(roles):
        print("✗ asin 和 role 数量不匹配")
        sys.exit(2)
    
    ws_url = await get_cdp_ws_url()
    print(f"CDP: {ws_url}")
    
    # ===== Resume 检测(2026-05-06 加)=====
    progress_path = output_dir / 'progress.json'
    if progress_path.exists():
        try:
            data = json.loads(progress_path.read_text(encoding='utf-8'))
            print(f"\n↻ 检测到既有 progress.json (上次更新: {data.get('last_update', '?')})")
            for asin, info in data.get('asins', {}).items():
                done, total = info.get('done', 0), info.get('total', 0)
                print(f"  {asin} ({info.get('role', '?')}): {done}/{total} 已抓")
            print(f"   会自动跳过 csv 里已 status=answered 的题,从断点续\n")
        except Exception as e:
            print(f"  ⚠ progress.json 读失败: {e}")
    
    asin_results = {}
    
    async with websockets.connect(ws_url, max_size=20_000_000) as ws:
        cdp = CDPClient(ws)
        
        # 拿到第一个 page tab 并激活
        targets = await cdp.send('Target.getTargets')
        page_targets = [t for t in targets['targetInfos'] if t['type'] == 'page']
        if page_targets:
            await cdp.send('Target.activateTarget', {'targetId': page_targets[0]['targetId']})
        
        for asin, role in zip(asins, roles):
            print(f"\n=== ASIN {asin} ({role}) ===")
            
            if args.plan_file:
                plan = [p for p in load_plan_csv(args.plan_file) if p['asin'] == asin]
            else:
                plan = default_starter_plan(asin, role,
                                              category=args.category,
                                              marketplace=args.marketplace)
                # 截到指定深度
                plan = plan[:args.depth]
            
            # v2.0.0:验证 plan 是否覆盖类目 N 维 Minimum Question Set(从 pack.yaml 读)
            is_complete, missing_dims = validate_plan_coverage(plan, category=args.category)
            if not is_complete:
                print(f"  ⚠ plan 未覆盖七维 Minimum Question Set,缺:{missing_dims}")
                print(f"     报告中将标注这些维度为 not_collected")
            
            print(f"  题数: {len(plan)}" + (f"(完整覆盖七维 ✓)" if is_complete else ""))
            
            try:
                rows, blocker = await run_one_asin(
                    cdp, asin, role, args.marketplace, plan, output_dir, args.persona
                )
                asin_results[asin] = (rows, blocker)
                
                # checkpoint 已经逐题落盘,这里不需要再写整体 csv
                # (但保留一次"完整重写"作为兜底,避免 append 中可能的格式不一致)
                write_csv(rows, output_dir / f'capture_{asin}.csv')
                
                if blocker:
                    print(f"  ⚠ blocker: {blocker['reason']} - {blocker['message']}")
                    # 遇到全局 blocker(login/mobile)就停,不继续后面 ASIN
                    if blocker['reason'] in {'amazon_buyer_login_required',
                                             'mobile_number_verification_required'}:
                        print("  全局 blocker,停止后续 ASIN")
                        break
            except KeyboardInterrupt:
                print(f"\n  ⚠ 中断 — 已抓数据已落盘到 {output_dir}/capture_{asin}.csv")
                print(f"     重启脚本会从 checkpoint 自动恢复")
                raise
            except Exception as e:
                print(f"  ✗ 异常: {e}")
                print(f"     已抓数据保留在 {output_dir}/capture_{asin}.csv,重启会续抓")
                asin_results[asin] = (rows if 'rows' in dir() else [],
                                      {'reason': 'exception', 'message': str(e)})
    
    # 合并所有 ASIN 的 row 到一个 baseline.csv
    all_rows = []
    for asin, (rows, _) in asin_results.items():
        all_rows.extend(rows)
    write_csv(all_rows, output_dir / 'capture_baseline.csv')
    write_health(asin_results, output_dir / 'capture_health.json')
    
    print(f"\n✓ 完成。输出在 {output_dir}/")
    print(f"  - capture_baseline.csv ({len(all_rows)} 行)")
    print(f"  - capture_health.json")


def main():
    parser = argparse.ArgumentParser(description='Rufus 单/多 ASIN 抓取(状态机版)')
    parser.add_argument('--asin', help='单个 ASIN')
    parser.add_argument('--asins', help='多个 ASIN,逗号分隔')
    parser.add_argument('--role', default='own', help='own / competitor_1 / ...')
    parser.add_argument('--roles', help='多个 role,逗号分隔(跟 --asins 对应)')
    parser.add_argument('--marketplace', default='com', help='com / co.uk / de / ...')
    parser.add_argument('--category', default='_generic',
                        help='产品类目代号:pet_supplies / apparel / electronics / home_kitchen / beauty / _generic。'
                             '决定 N 维 taxonomy 和 starter 题库,从 categories/<cat>/pack.yaml 加载。'
                             '默认 _generic；宠物用品建议 pet_supplies')
    parser.add_argument('--depth', type=int, default=20,
                        help='每个 ASIN 抓多少题(无 plan 时)。默认 20,SKILL.md 推荐 15-25。'
                             '如想抓七维 Minimum Question Set 全部,至少 15')
    parser.add_argument('--plan-file', help='question plan CSV 路径')
    parser.add_argument('--persona', default='default', help='persona 标签')
    parser.add_argument('--output-dir', default='out', help='输出目录')
    args = parser.parse_args()
    
    if not args.asin and not args.asins:
        print("✗ 必须给 --asin 或 --asins")
        sys.exit(2)
    
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
