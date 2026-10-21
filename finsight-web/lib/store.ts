import type { ChatMsg } from "./api";
import type { Report } from "./finance";

// Browser-only cache so reopening a ticker doesn't re-run the 2-minute pipeline on the free backend.
const REPORTS = "finsight:reports";
const MAX_REPORTS = 5;

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage full or blocked: the app still works, just without the cache */
  }
}

export const listReports = () => read<Report[]>(REPORTS, []);
export const getReport = (ticker: string) => listReports().find((r) => r.ticker === ticker.toUpperCase());

export function saveReport(r: Report) {
  const rest = listReports().filter((x) => x.ticker !== r.ticker);
  const kept = [{ ...r, savedAt: Date.now() }, ...rest].slice(0, MAX_REPORTS);
  write(REPORTS, kept);
  try {
    for (const old of rest.slice(MAX_REPORTS - 1)) localStorage.removeItem(`finsight:chat:${old.ticker}`);
  } catch {}
}

export const getChat = (ticker: string) => read<ChatMsg[]>(`finsight:chat:${ticker}`, []);
export const saveChat = (ticker: string, msgs: ChatMsg[]) => write(`finsight:chat:${ticker}`, msgs.slice(-40));
