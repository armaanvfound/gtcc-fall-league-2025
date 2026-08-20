# Team proxy for the assistant

One key, held server-side, so **the whole team just uses the assistant** — nobody
sets up an API key, and the key never reaches anyone's browser.

Without this, the dashboard falls back to asking each reader for their own key.
With it, teammates open the site, type a shared word once, and ask away.

Runs on Cloudflare Workers' free tier (100,000 requests a day; we will use a
handful).

---

## Setup — about five minutes

Everything runs from this `worker/` folder.

```bash
cd worker
```

**1. Log in to Cloudflare** (creates a free account if you don't have one):

```bash
npx wrangler login
```

**2. Add your Anthropic API key.** This prompts you to paste it. It is stored
encrypted by Cloudflare and is never written into this repository:

```bash
npx wrangler secret put ANTHROPIC_API_KEY
```

**3. Pick a team passphrase.** Any word. This is what your teammates type once:

```bash
npx wrangler secret put TEAM_PASS
```

**4. Deploy:**

```bash
npx wrangler deploy
```

Wrangler prints a URL like `https://rcb-ask.<your-subdomain>.workers.dev`.

**5. Point the dashboard at it.** Put that URL in `ASK_PROXY` at the top of
`tools/build.py`, then rebuild and push:

```bash
cd .. && python3 tools/build.py && git add -A && git commit -m "Point assistant at team proxy" && git push
```

**6. Tell the team**: open the dashboard, click **Ask the data**, enter the
passphrase once. That's it — no keys, no accounts.

---

## Recommended: the hard spending cap

Steps 1–5 give you an origin check, the passphrase, and a fixed model and token
ceiling. To also get **rate limits and a hard daily cap**, add a KV namespace:

```bash
npx wrangler kv namespace create ASK_KV
```

Uncomment the `[[kv_namespaces]]` block in `wrangler.toml`, paste in the id it
printed, and `npx wrangler deploy` again.

With KV bound, the proxy enforces `MAX_PER_IP_HOUR` (40) and `MAX_PER_DAY` (500).
Without it, both are skipped — everything else still applies.

---

## What stops this being a free Claude for the internet

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

Claude Sonnet 5 with adaptive thinking on, `medium` effort. The fact pack (~7.6k
tokens) is sent with `cache_control`, so after the first question in a five-minute
window the prefix bills at about a tenth of the input rate.

Roughly **half a cent to a cent per question**. A thousand questions is a few
dollars. The daily cap is the backstop.

Sonnet 5 is on introductory pricing ($2/$10 per 1M) until **31 Aug 2026**, then
$3/$15.

To spend less: set `EFFORT = "low"` in `wrangler.toml`, or `MODEL =
"claude-haiku-4-5"` ($1/$5). To spend more for depth: `EFFORT = "high"`.

---

## Everyday operation

- **Adding a match**: rebuild and push as usual. The proxy re-reads `facts.json`
  every five minutes, so the assistant updates itself — no redeploy.
- **Changing the passphrase**: `npx wrangler secret put TEAM_PASS`, then tell the
  team. Their browsers will prompt again.
- **Rotating the API key**: `npx wrangler secret put ANTHROPIC_API_KEY`.
- **Turning it off**: `npx wrangler delete`, or set `ASK_PROXY = ""` in
  `tools/build.py` and rebuild to go back to per-reader keys.
- **Watching spend**: the Cloudflare dashboard shows request counts; the Anthropic
  console shows cost.
