# Team proxy for the assistant

One key, held server-side, so **the whole team just uses the assistant** — nobody
sets up an account, and the key never reaches anyone's browser.

Without it the dashboard just shows setup notes. With it, teammates open the
site, type a shared word once, and ask away.

Runs on Cloudflare Workers' free tier (100,000 requests a day; we will use a
handful).

---

## Setup — four commands

Run these from this `worker/` folder. Only the second one needs anything from
you: it prompts, you paste the DeepSeek key, and it goes straight from your
terminal to Cloudflare. The key is never written into this repository.

```bash
cd worker
npx wrangler login
npx wrangler secret put DEEPSEEK_API_KEY     # paste the key at the prompt
echo -n "rcbchatbot" | npx wrangler secret put TEAM_PASS
npx wrangler deploy
```

Wrangler prints a URL like `https://rcb-ask.<your-subdomain>.workers.dev`.

Put it in `ASK_PROXY` at the top of `tools/build.py`, then from the repo root:

```bash
python3 tools/build.py && git add -A && git commit -m "Enable team assistant" && git push
```

Done. Tell the team: open the dashboard, hit **Ask the data**, type `rcbchatbot`
once. No accounts, no keys, nothing to install.

### Optional: the hard spending cap

The steps above give you an origin check, the passphrase, and a pinned model and
token ceiling. To also get rate limits and a **hard daily cap**:

```bash
npx wrangler kv namespace create ASK_KV
```

Uncomment the `[[kv_namespaces]]` block in `wrangler.toml`, paste the id it
printed, and `npx wrangler deploy` again. Now `MAX_PER_IP_HOUR` (40) and
`MAX_PER_DAY` (500) are enforced. Without it both are simply skipped.

## What stops this being a free chatbot for the internet

The site is public, so the passphrase is discoverable by anyone who opens dev
tools. That is expected, and it is why the proxy does not simply forward what it
is given:

- **It writes the system prompt itself**, from `facts.json`. Callers send only the
  conversation, so the assistant can only ever answer questions about this
  dashboard — the prompt also refuses off-topic requests outright.
- **Model and token ceiling are pinned server-side.** Nobody can ask it for a
  different model or a huge `max_tokens`.
- **Origin allow-list** — browsers may only call it from our own site.
- **Passphrase**, **per-IP hourly limit**, **global daily cap**.

Worst case, someone determined burns a capped number of dashboard answers a day.

---

## Running costs

`deepseek-v4-flash` with reasoning on `low`. The fact pack (~8.1k tokens) sits at
the front of every request unchanged, so DeepSeek's context cache picks it up and
repeat questions bill input at the cache-hit rate rather than the miss rate.

Roughly **$0.0003 a question — about 3,000 questions per dollar.** The first
question after a quiet spell costs a little more (cache miss, ~$0.002).

Published rates per million tokens, off-peak / peak:

| | input, cache hit | input, cache miss | output |
|---|---|---|---|
| `deepseek-v4-flash` | $0.007 / $0.014 | $0.22 / $0.44 | $0.66 / $1.32 |
| `deepseek-v4-pro` | $0.022 / $0.044 | $0.66 / $1.32 | $1.98 / $3.96 |

Peak is 01:00-04:00 and 06:00-10:00 UTC.

If answers ever feel thin, `MODEL = "deepseek-v4-pro"` or
`REASONING_EFFORT = "medium"` in `wrangler.toml`, then redeploy — still around
700 questions per dollar.

## Everyday operation

- **Adding a match**: rebuild and push as usual. The proxy re-reads `facts.json`
  every five minutes, so the assistant updates itself — no redeploy.
- **Changing the passphrase**: `npx wrangler secret put TEAM_PASS`, then tell the
  team. Their browsers will prompt again.
- **Rotating the API key**: `npx wrangler secret put DEEPSEEK_API_KEY`.
- **Turning it off**: `npx wrangler delete`, or set `ASK_PROXY = ""` in
  `tools/build.py` and rebuild to go back to per-reader keys.
- **Watching spend**: the Cloudflare dashboard shows request counts; the Anthropic
  console shows cost.
