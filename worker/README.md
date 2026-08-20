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

> **`DEEPSEEK_API_KEY` is a literal name, not a placeholder.** Type those 16
> characters exactly; the key goes at the `Enter a secret value:` prompt that
> follows, never on the command line. Adding it through the Cloudflare dashboard
> works too (Workers & Pages -> rcb-ask -> Settings -> Variables and Secrets),
> but a secret added there only binds on the **next deploy** - run
> `npx wrangler deploy` afterwards or the Worker will still report
> "not configured".

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

## Speed, and why reasoning is off

Reasoning is **off** (`THINKING = "off"`). That was measured, not assumed - same
questions, same model, same fact pack:

| | lookup | "weakest phase, who fixes it" | toss call | "bowling lineup, max 3 overs each" |
|---|---|---|---|---|
| reasoning high | — | 30-65s | ~65s | **277s** |
| reasoning low | 8.8s | — | 11.7s | 89s |
| **off** | **5.9s** | **5.2s** | **3.9s** | **8.3s** |

Answers stayed correct with it off. A 14-question eval pulls every number out of
every answer and checks it exists in `facts.json`; it passes. That is the fact
pack doing its job - the arithmetic already happened in Python and was reconciled
against the scorecards, so the model retrieves and phrases rather than derives.
Reasoning was paying for work that was already done.

Speed is also reliability. Phones suspend a page when you switch apps and kill the
request with it, so a 90-second answer often never arrives - that was the real
cause of "Could not reach the API".

To turn it back on: `THINKING = "on"` in `wrangler.toml` (then `REASONING_EFFORT`
applies), and redeploy. Worth trying only if answers feel shallow on a genuinely
multi-step question.

## Running costs

`deepseek-v4-pro`, reasoning off. The fact pack (~8.5k tokens) sits unchanged at
the front of every request, so DeepSeek's context cache bills repeat questions at
the cache-hit rate.

Roughly **$0.001-0.002 a question** - several hundred per dollar. With reasoning
on `high` a single hard question could reach 8,000+ output tokens, which is where
the cost and the 277 seconds both came from.

Published rates per million tokens, off-peak / peak:

| | input, cache hit | input, cache miss | output |
|---|---|---|---|
| `deepseek-v4-flash` | $0.007 / $0.014 | $0.22 / $0.44 | $0.66 / $1.32 |
| `deepseek-v4-pro` | $0.022 / $0.044 | $0.66 / $1.32 | $1.98 / $3.96 |

Peak is 01:00-04:00 and 06:00-10:00 UTC.

## Keeping answers accurate

Two rules do the heavy lifting, both in `tools/factpack.py`:

- **Never calculate.** Every figure ships precomputed. If a number is not in the
  pack the assistant says so rather than working it out.
- **Never re-derive a decision the pages already made.** `tossPolicy` holds the
  standing toss call and `opponents2025[team].target` each side's target. Without
  this the assistant answered "bowl first" to a question the match-plan page
  answers "bat" - a dashboard contradicting itself.

`python3 /tmp/eval.py`-style grounding checks are worth re-running after any
change to the pack: ask a spread of questions, extract every number from each
answer, and confirm it appears in `facts.json`.

## Everyday operation

- **Adding a match**: rebuild and push as usual. The proxy re-reads `facts.json`
  every five minutes, so the assistant updates itself — no redeploy.
- **Changing the passphrase**: `npx wrangler secret put TEAM_PASS`, then tell the
  team. Their browsers will prompt again.
- **Rotating the API key**: `npx wrangler secret put DEEPSEEK_API_KEY`.
- **Turning it off**: `npx wrangler delete`, or set `ASK_PROXY = ""` in
  `tools/build.py` and rebuild to go back to per-reader keys.
- **Watching spend**: the Cloudflare dashboard shows request counts; the DeepSeek
  platform console shows cost.
