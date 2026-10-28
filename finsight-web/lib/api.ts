import type { Metrics, Report } from "./finance";

const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
const HEALTH = BASE.replace(/\/api\/v1$/, "") + "/health";

export type ChatMsg = { role: "user" | "assistant"; content: string };

async function call<T>(url: string, init: RequestInit, timeoutMs: number): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...init, signal: ctrl.signal, headers: { "Content-Type": "application/json" } });
    if (!res.ok) {
      const detail = await res.json().then((j) => j?.detail, () => null);
      throw new Error(typeof detail === "string" ? detail : `Server returned ${res.status}`);
    }
    return (await res.json()) as T;
  } catch (e) {
    if ((e as Error).name === "AbortError") throw new Error("The server took too long to respond. It may still be waking up — try again in a minute.");
    if (e instanceof TypeError) throw new Error("Can't reach the analysis server. Check your connection or try again shortly.");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

/** Render's free tier sleeps after 15 min idle; one ping wakes it (~50 s). */
export const wake = () => call<{ status: string }>(HEALTH, { method: "GET" }, 90_000).then(() => true);

/** Pre-generated report shipped with the site (scripts/build_samples.py), or null. Opens presets instantly while the backend sleeps. */
export const getSample = (ticker: string): Promise<Report | null> =>
  fetch(`/samples/${encodeURIComponent(ticker.toUpperCase())}.json`)
    .then((r) => (r.ok ? (r.json() as Promise<Report>) : null))
    .catch(() => null);

const inFlight = new Map<string, Promise<Report>>();

/** Runs the 4-agent pipeline. Concurrent calls for one ticker share a request so the 512 MB backend never runs it twice. */
export function analyze(ticker: string): Promise<Report> {
  const key = ticker.toUpperCase();
  let p = inFlight.get(key);
  if (!p) {
    p = call<Report>(`${BASE}/analyze`, { method: "POST", body: JSON.stringify({ ticker: key }) }, 180_000)
      .then((r) => ({ ...r, ticker: key }))
      .finally(() => inFlight.delete(key));
    inFlight.set(key, p);
  }
  return p;
}

export function chat(report: Report, history: ChatMsg[], query: string) {
  return call<{ answer: string }>(
    `${BASE}/chat`,
    {
      method: "POST",
      body: JSON.stringify({
        ticker: report.ticker,
        tenant_id: report.tenant_id,
        user_query: query,
        chat_history: history.slice(-6), // backend only reads the last 6
        memo_text: report.final_memo.slice(0, 3000), // backend truncates at 3000
        financial_metrics: report.financial_metrics as Metrics,
      }),
    },
    90_000,
  ).then((r) => r.answer);
}
