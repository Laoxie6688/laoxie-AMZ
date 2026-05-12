#!/usr/bin/env python3
"""Batch ask Amazon Rufus questions through Chrome DevTools Protocol.

Prerequisites:
- Chrome is already running with --remote-debugging-port.
- The selected Chrome profile is already logged in to Amazon.
- Install dependency: python3 -m pip install websockets
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import websockets


@dataclass
class CdpClient:
    websocket: Any
    message_id: int = 0

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.message_id += 1
        await self.websocket.send(json.dumps({"id": self.message_id, "method": method, "params": params or {}}))
        while True:
            response = json.loads(await self.websocket.recv())
            if response.get("id") == self.message_id:
                if "error" in response:
                    raise RuntimeError(response["error"])
                return response.get("result", {})


def get_websocket_url(cdp: str, page_url_contains: str = "amazon.com") -> str:
    if cdp.startswith("ws://") or cdp.startswith("wss://"):
        return cdp
    base_url = cdp.rstrip("/")
    with urllib.request.urlopen(base_url + "/json/list", timeout=5) as response:
        targets = json.load(response)

    pages = [target for target in targets if target.get("type") == "page" and target.get("webSocketDebuggerUrl")]
    for target in pages:
        if page_url_contains in target.get("url", ""):
            return target["webSocketDebuggerUrl"]
    if pages:
        return pages[0]["webSocketDebuggerUrl"]

    raise RuntimeError(f"No debuggable Chrome page target found at {base_url}")


def read_questions(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#")]


async def evaluate(client: CdpClient, expression: str, timeout_ms: int = 120_000) -> Any:
    result = await client.call(
        "Runtime.evaluate",
        {
            "expression": expression,
            "awaitPromise": True,
            "returnByValue": True,
            "timeout": timeout_ms,
        },
    )
    return result.get("result", {}).get("value")


async def ask_rufus(client: CdpClient, question: str, wait_seconds: int) -> dict[str, Any]:
    question_json = json.dumps(question)
    expression = f"""
    (async function() {{
        const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
        const question = {question_json};

        const openBtn = document.querySelector('.nav-rufus-disco-text, .nav-rufus-disco');
        if (!openBtn) return {{ success: false, error: 'Rufus button not found' }};
        openBtn.click();
        await sleep(2000);

        const panel = document.getElementById('nav-flyout-rufus');
        if (!panel) return {{ success: false, error: 'Rufus panel not found' }};

        const textarea = document.getElementById('rufus-text-area');
        if (!textarea) return {{ success: false, error: 'Rufus textarea not found' }};
        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        setter.call(textarea, question);
        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
        await sleep(500);

        const submitBtn = document.querySelector('#rufus-submit-button, [data-testid="rufus-submit"]');
        if (!submitBtn) return {{ success: false, error: 'Submit button not found' }};
        submitBtn.click();

        let panelText = null;
        let answer = null;
        const attempts = Math.max(1, Math.ceil({wait_seconds} / 3));
        for (let i = 0; i < attempts; i++) {{
            await sleep(3000);
            const text = panel.innerText || '';
            if (text.includes('Rufus is currently generating') || text.includes('Thinking...')) continue;
            if (text.length > 200) {{
                panelText = text;
                const questionIndex = text.lastIndexOf(question);
                answer = questionIndex >= 0 ? text.slice(questionIndex + question.length).trim() : text;
                break;
            }}
        }}

        const closeBtn = document.querySelector('[aria-label*="Close"]');
        if (closeBtn) closeBtn.click();

        return {{
            success: answer !== null,
            answer: answer,
            answerLength: answer ? answer.length : 0,
            rawPanelText: panelText,
            rawPanelTextLength: panelText ? panelText.length : 0
        }};
    }})()
    """
    value = await evaluate(client, expression, timeout_ms=(wait_seconds + 20) * 1000)
    if not isinstance(value, dict):
        return {"success": False, "error": "Unexpected CDP result", "raw": value}
    return value


async def run(args: argparse.Namespace) -> int:
    questions = read_questions(args.questions)
    websocket_url = get_websocket_url(args.cdp, args.page_url_contains)
    search_url = "https://www.amazon.com/s?k=" + urllib.parse.quote_plus(args.keyword)
    results: list[dict[str, Any]] = []

    async with websockets.connect(websocket_url, max_size=None) as websocket:
        client = CdpClient(websocket)
        await client.call("Page.enable")
        await client.call("Runtime.enable")
        await client.call("Page.navigate", {"url": search_url})
        await asyncio.sleep(args.initial_wait)

        for index, question in enumerate(questions, start=1):
            print(f"[{index}/{len(questions)}] {question}", flush=True)
            started = time.time()
            result = await ask_rufus(client, question, args.wait)
            elapsed = round(time.time() - started, 2)
            row = {
                "question": question,
                "success": bool(result.get("success")),
                "answer": result.get("answer"),
                "answerLength": result.get("answerLength", 0),
                "rawPanelText": result.get("rawPanelText"),
                "rawPanelTextLength": result.get("rawPanelTextLength", 0),
                "error": result.get("error"),
                "elapsed": elapsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results.append(row)
            status = "OK" if row["success"] else f"FAILED: {row['error']}"
            print(f"  {status} ({elapsed}s)", flush=True)
            await asyncio.sleep(args.pause)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)
    print(f"Saved {len(results)} results to {args.output}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch ask Amazon Rufus questions through Chrome CDP.")
    parser.add_argument("--cdp", default="http://127.0.0.1:9222", help="CDP HTTP base URL or browser websocket URL.")
    parser.add_argument("--keyword", required=True, help="Amazon search keyword used as Rufus page context.")
    parser.add_argument("--questions", required=True, help="Text file with one question per line.")
    parser.add_argument("--output", default="rufus_results.json", help="Output JSON file.")
    parser.add_argument(
        "--page-url-contains",
        default="amazon.com",
        help="Substring used to pick an existing debuggable page target from /json/list.",
    )
    parser.add_argument("--wait", type=int, default=30, help="Seconds to wait for each Rufus answer.")
    parser.add_argument("--pause", type=float, default=3.0, help="Pause between questions.")
    parser.add_argument("--initial-wait", type=float, default=4.0, help="Wait after navigating to search results.")
    return parser.parse_args()


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
