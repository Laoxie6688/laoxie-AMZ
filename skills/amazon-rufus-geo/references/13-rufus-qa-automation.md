# 13-rufus-qa-automation.md — Rufus Live QA 安全自动化说明

本文件记录当前验证过的 Rufus live 问答采集方式。不要使用旧版“输入 Amazon 邮箱和密码”的脚本。账号登录必须由用户本人在浏览器中手动完成。

## 安全规则

- 不要索要 Amazon 账号、密码、验证码、token。
- 让用户自己在 Chrome 窗口中登录 Amazon。
- 自动化只连接已经登录的浏览器会话。
- 请求频率要保守：建议每题间隔 5-8 秒，完整 15 问分批执行。

## macOS 启动 Chrome

```bash
open -na "Google Chrome" --args \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-rufus-profile \
  "https://www.amazon.com"
```

打开后，让用户在这个新窗口里手动登录 Amazon 买家账号。普通已打开的 Chrome 通常不会暴露 CDP，必须用 `--remote-debugging-port` 启动。

## 检查 CDP

```bash
curl http://127.0.0.1:9222/json/list
python3 scripts/check_rufus_env.py
```

必须看到 `type: "page"` 且 URL 包含 `amazon.com` 的页面 target。页面自动化要连接 `/json/list` 中的 page websocket，不要连接 `/json/version` 中的 browser websocket。

## 准备问题文件

`questions.txt` 一行一个问题，例如：

```text
What is B0D2B7FFFS mainly used for, and what problem does it solve?
Is B0D2B7FFFS good for one large cat?
I want a stainless steel litter box that is easy to clean and controls odor. Should I choose B0D2B7FFFS?
```

## 运行采集

```bash
python3 scripts/rufus_qa.py \
  --cdp http://127.0.0.1:9222 \
  --keyword "B0D2B7FFFS stainless steel litter box large cats odor control" \
  --questions questions.txt \
  --output rufus_results.json \
  --wait 45 \
  --pause 6
```

## 输出字段

每个结果包含：

- `question`：问题。
- `success`：是否成功。
- `answer`：按当前问题切出的回答。
- `rawPanelText`：完整 Rufus 面板文本，仅用于调试。
- `elapsed`：耗时。
- `timestamp`：时间戳。

分析时优先使用 `answer`，不要把 `rawPanelText` 当作单题答案。

## 常见问题

### Rufus 按钮找不到

原因可能是未登录、账号/地区没有 Rufus、页面未加载完成、Amazon UI 变动。先让用户确认页面顶部是否能看到 Rufus。

### 返回 Scheduled actions 或无关回答

问题触发了 Rufus 的其他模式。改写问题，加入产品名、ASIN、品类词，再重跑。

### 每题回答里出现之前的聊天历史

脚本会自动用当前问题切分 `answer`。如果仍然混入历史，检查问题是否和历史问题重复，必要时开启新 chat 或清空面板。

### 登录态丢失

让用户在 `/tmp/chrome-rufus-profile` 对应的 Chrome 窗口重新登录。不要让用户把密码发给代理。
