/**
 * Team proxy for the dashboard assistant. Powered by DeepSeek.
 *
 * Holds one DeepSeek key as a Worker secret so the whole team can use the
 * assistant without anyone setting up an account. The key never reaches the
 * browser, is never in this repository, and is set from your terminal with
 * `wrangler secret put` - see worker/README.md.
 *
 * The proxy is deliberately narrow. It does not forward whatever the caller
 * sends: it builds the system prompt itself from facts.json, pins the model,
 * the reasoning effort and the token ceiling, and passes through only the
 * conversation. So even someone who reads the passphrase out of the public page
 * cannot turn this into a free general-purpose model - it can only answer
 * questions about this dashboard.
 *
 * Four things stand between the public internet and the bill:
 *   1. Origin allow-list        - browsers may only call it from our own site
 *   2. Shared team passphrase   - a word you give the team
 *   3. Per-IP hourly rate limit - optional, needs the KV binding
 *   4. Global daily cap         - optional, needs the KV binding; a hard ceiling
 *
 * DeepSeek's API is OpenAI-shaped, so the request carries the system prompt as
 * the first message and the answer comes back on choices[0].message.content.
 * The reply is normalised to {text, usage} so the page never has to know which
 * provider is behind it.
 */

const API = "https://api.deepseek.com/chat/completions";
const FACTS_TTL_MS = 5 * 60 * 1000;      // re-read facts.json at most every 5 min

let factsCache = { at: 0, prompt: null };

function corsHeaders(origin, allowed) {
  const ok = allowed.length === 0 || allowed.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok && origin ? origin : (allowed[0] || "*"),
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type, x-team-pass",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(obj, status, headers) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...headers, "content-type": "application/json" },
  });
}

/** Build the system prompt from facts.json. Cached briefly so a burst of
 *  questions does not re-fetch it, and so a rebuild is picked up on its own. */
async function systemPrompt(env) {
  const now = Date.now();
  if (factsCache.prompt && now - factsCache.at < FACTS_TTL_MS) return factsCache.prompt;

  const r = await fetch(env.FACTS_URL, { cf: { cacheTtl: 300 } });
  if (!r.ok) throw new Error("facts.json returned " + r.status);
  const facts = await r.json();

  const rules = facts._prompt;
  if (!rules) throw new Error("facts.json has no _prompt");
  delete facts._prompt;                    // don't ship the rules twice

  const prompt = rules + "\n\nFACTS:\n" + JSON.stringify(facts);
  factsCache = { at: now, prompt };
  return prompt;
}

/** Counter with a TTL. Returns the new value, or null when KV isn't bound. */
async function bump(env, key, ttlSeconds) {
  if (!env.ASK_KV) return null;
  const cur = parseInt((await env.ASK_KV.get(key)) || "0", 10) + 1;
  await env.ASK_KV.put(key, String(cur), { expirationTtl: ttlSeconds });
  return cur;
}

export default {
  async fetch(request, env) {
    const allowed = (env.ALLOWED_ORIGINS || "")
      .split(",").map((s) => s.trim()).filter(Boolean);
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin, allowed);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST") return json({ error: "POST only" }, 405, cors);

    if (allowed.length && origin && !allowed.includes(origin)) {
      return json({ error: "This assistant only answers from the team dashboard." }, 403, cors);
    }

    if (env.TEAM_PASS && request.headers.get("x-team-pass") !== env.TEAM_PASS) {
      return json({ error: "bad_pass" }, 401, cors);
    }

    if (!env.DEEPSEEK_API_KEY) {
      return json({ error: "The assistant is not configured yet (no API key set)." }, 503, cors);
    }

    // --- spend guards (skipped entirely when KV is not bound) ---
    const day = new Date().toISOString().slice(0, 10);
    const hour = new Date().toISOString().slice(0, 13);
    const ip = request.headers.get("CF-Connecting-IP") || "anon";

    const perHour = parseInt(env.MAX_PER_IP_HOUR || "40", 10);
    const perDay = parseInt(env.MAX_PER_DAY || "500", 10);

    const mine = await bump(env, `ip:${ip}:${hour}`, 3700);
    if (mine !== null && mine > perHour) {
      return json({ error: `Slow down - ${perHour} questions an hour each. Try again shortly.` }, 429, cors);
    }
    const total = await bump(env, `day:${day}`, 90000);
    if (total !== null && total > perDay) {
      return json({ error: "The team has hit today's question limit. It resets at midnight UTC." }, 429, cors);
    }

    // --- forward, on our terms ---
    let body;
    try { body = await request.json(); } catch (e) { return json({ error: "bad JSON" }, 400, cors); }

    const turns = Array.isArray(body.messages) ? body.messages.slice(-8) : null;
    if (!turns || !turns.length) return json({ error: "no messages" }, 400, cors);
    // Guard against a caller pasting an essay in to run up input cost.
    for (const m of turns) {
      if (typeof m.content !== "string" || m.content.length > 4000) {
        return json({ error: "That question is too long." }, 400, cors);
      }
      if (m.role !== "user" && m.role !== "assistant") {
        return json({ error: "bad message role" }, 400, cors);
      }
    }

    let system;
    try { system = await systemPrompt(env); }
    catch (e) { return json({ error: "Could not load the dashboard data: " + e.message }, 502, cors); }

    let upstream, raw;
    try {
      upstream = await fetch(API, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: "Bearer " + env.DEEPSEEK_API_KEY,
        },
        body: JSON.stringify({
          model: env.MODEL || "deepseek-v4-flash",
          // Reasoning on, but low: the model is looking up numbers in a brief we
          // already computed, not deriving them. Thinking is drawn from the same
          // budget as the answer, so the ceiling sits above reply length.
          thinking: { type: "enabled" },
          reasoning_effort: env.REASONING_EFFORT || "low",
          max_tokens: parseInt(env.MAX_TOKENS || "1500", 10),
          stream: false,
          messages: [{ role: "system", content: system }, ...turns],
        }),
      });
      raw = await upstream.text();
    } catch (e) {
      return json({ error: "Could not reach DeepSeek: " + e.message }, 502, cors);
    }

    if (!upstream.ok) {
      let detail = raw.slice(0, 300);
      try { const j = JSON.parse(raw); detail = (j.error && (j.error.message || j.error)) || detail; } catch (e) {}
      const msg = upstream.status === 401
        ? "The team's DeepSeek key was rejected - tell the captain."
        : upstream.status === 402
          ? "The team's DeepSeek account is out of credit - tell the captain."
          : upstream.status === 429
            ? "DeepSeek is rate limiting us. Try again in a moment."
            : "DeepSeek returned " + upstream.status + ". " + detail;
      return json({ error: msg }, upstream.status, cors);
    }

    // Normalise so the page never has to know which provider answered.
    let data;
    try { data = JSON.parse(raw); } catch (e) { return json({ error: "bad reply from DeepSeek" }, 502, cors); }
    const m = (data.choices && data.choices[0] && data.choices[0].message) || {};
    const text = (m.content || "").trim();
    if (!text) return json({ error: "The model returned an empty answer. Try rephrasing." }, 502, cors);

    return json({ text, usage: data.usage || null }, 200, cors);
  },
};
