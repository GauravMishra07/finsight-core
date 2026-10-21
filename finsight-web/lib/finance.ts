export type Point = { fy: string; end: string; val: number };
export type Metric = { value: string; source: string; history?: Point[] };
export type Metrics = Record<string, Metric>;
export type Verdict = "Approve" | "Review" | "Decline";

export type Report = {
  ticker: string;
  tenant_id: string;
  financial_metrics: Metrics;
  risk_analysis?: string | null;
  macro_analysis?: string | null;
  competitor_analysis?: string | null;
  upcoming_projects?: string | null;
  competitors?: Competitor[]; // absent on reports cached before this field existed
  final_memo: string;
  errors?: string[];
  savedAt?: number;
};

/** "$1,234" or "$-1,234" (Python's format for negatives) -> number; "N/A" -> null. */
export function parseMoney(s: string | undefined): number | null {
  if (!s) return null;
  const n = Number(s.replace(/[$,\s]/g, ""));
  return s.trim() === "" || Number.isNaN(n) ? null : n;
}

export function latest(m: Metric | undefined): number | null {
  const h = m?.history;
  return h && h.length ? h[h.length - 1].val : parseMoney(m?.value);
}

/** Year-over-year change of the last two points; null when it can't be computed. */
export function yoy(h: Point[] | undefined): number | null {
  if (!h || h.length < 2) return null;
  const prev = h[h.length - 2].val;
  const last = h[h.length - 1].val;
  return prev === 0 ? null : (last - prev) / Math.abs(prev);
}

/** Merge several metrics' histories into one row per fiscal year (for charts and tables). */
export function byYear(metrics: Metrics, labels: string[]): Record<string, number | string>[] {
  const rows = new Map<string, Record<string, number | string>>();
  for (const label of labels)
    for (const p of metrics[label]?.history ?? []) {
      const row = rows.get(p.fy) ?? { fy: p.fy };
      row[label] = p.val;
      rows.set(p.fy, row);
    }
  return [...rows.values()].sort((a, b) => String(a.fy).localeCompare(String(b.fy)));
}

const div = (a: number | null, b: number | null) => (a === null || b === null || b === 0 ? null : a / b);

export type Ratio = { label: string; value: number | null; unit: "x" | "%"; band: string | null; level: "good" | "warn" | "crit" | null };

// shortcut: one generic band per ratio, not sector-specific; upgrade if users need sector benchmarks.
function band(v: number | null, [lo, hi]: [number, number], higherIsBetter: boolean, names: [string, string, string]) {
  if (v === null) return { band: null, level: null };
  const i = v < lo ? 0 : v <= hi ? 1 : 2;
  const levels = higherIsBetter ? (["crit", "warn", "good"] as const) : (["good", "warn", "crit"] as const);
  return { band: names[i], level: levels[i] };
}

type Vals = { rev: number | null; ni: number | null; assets: number | null; liab: number | null; eq: number | null };
export type Derived = { de: number | null; margin: number | null; roa: number | null; roe: number | null; eqr: number | null };

export function derive({ rev, ni, assets, liab, eq }: Vals): Derived {
  // Some filers (e.g. DIS) don't tag Liabilities; assets − parent equity also counts minority interest as liabilities.
  if (liab === null && assets !== null && eq !== null) liab = assets - eq;
  const negEq = eq !== null && eq <= 0;
  return {
    de: negEq ? null : div(liab, eq),
    margin: div(ni, rev),
    roa: div(ni, assets),
    roe: negEq ? null : div(ni, eq),
    eqr: div(eq, assets),
  };
}

const latestVals = (m: Metrics): Vals => ({
  rev: latest(m["Revenue"]), ni: latest(m["Net Income"]), assets: latest(m["Total Assets"]),
  liab: latest(m["Total Liabilities"]), eq: latest(m["Stockholders Equity"]),
});

const num = (v: unknown) => (typeof v === "number" ? v : null);

/** Ratios for every fiscal year in the history, oldest first, plus revenue growth. */
export function trend(m: Metrics) {
  const rows = byYear(m, ["Revenue", "Net Income", "Total Assets", "Total Liabilities", "Stockholders Equity"]);
  return rows.map((r, i) => {
    const rev = num(r["Revenue"]), prev = i ? num(rows[i - 1]["Revenue"]) : null;
    return {
      fy: String(r.fy),
      growth: rev !== null && prev ? (rev - prev) / Math.abs(prev) : null,
      ...derive({ rev, ni: num(r["Net Income"]), assets: num(r["Total Assets"]), liab: num(r["Total Liabilities"]), eq: num(r["Stockholders Equity"]) }),
    };
  });
}

/** Compound annual growth between the first and last points; null if not meaningful (sign change, < 2 points). */
export function cagr(h: Point[] | undefined): number | null {
  if (!h || h.length < 2) return null;
  const a = h[0].val, b = h[h.length - 1].val, years = Number(h[h.length - 1].fy) - Number(h[0].fy);
  return a > 0 && b > 0 && years > 0 ? (b / a) ** (1 / years) - 1 : null;
}

export type Threat = "High" | "Medium" | "Low";
export type Competitor = {
  name: string; ticker: string | null; threat: Threat | null; overlap: string; note: string;
  sec_name?: string; metrics?: Metrics;
};

export type PeerRow = Derived & { name: string; ticker: string | null; fy: string | null; rev: number | null; growth: number | null; subject?: boolean };

export function peerRow(name: string, ticker: string | null, m: Metrics, subject = false): PeerRow {
  const h = m["Revenue"]?.history;
  return { name, ticker, subject, fy: h?.length ? h[h.length - 1].fy : null, rev: latest(m["Revenue"]), growth: yoy(h), ...derive(latestVals(m)) };
}

export function ratios(m: Metrics): Ratio[] {
  const { de, margin, roa, roe, eqr } = derive(latestVals(m));
  return [
    { label: "Debt / Equity", value: de, unit: "x", ...band(de, [1, 2], false, ["Low leverage", "Moderate leverage", "High leverage"]) },
    { label: "Net margin", value: margin, unit: "%", ...band(margin, [0.05, 0.15], true, ["Thin", "Healthy", "Strong"]) },
    { label: "Return on assets", value: roa, unit: "%", ...band(roa, [0.02, 0.08], true, ["Weak", "Adequate", "Strong"]) },
    { label: "Return on equity", value: roe, unit: "%", ...band(roe, [0.08, 0.18], true, ["Weak", "Adequate", "Strong"]) },
    { label: "Equity ratio", value: eqr, unit: "%", ...band(eqr, [0.3, 0.5], true, ["Thin cushion", "Adequate", "Well capitalised"]) },
  ];
}

/** Reads the verdict from the memo's "Final Underwriting Recommendation" section. */
export function verdictFromMemo(memo: string | undefined): Verdict | null {
  if (!memo) return null;
  const i = memo.search(/#+\s*Final Underwriting Recommendation/i);
  if (i < 0) return null;
  const body = memo.slice(i).split("\n").slice(1).join("\n"); // skip the heading, which lists all three options
  const hit = body.match(/\b(approve|approved|approval|decline|declined|review)\b/i)?.[1].toLowerCase();
  if (!hit) return null;
  return hit.startsWith("appro") ? "Approve" : hit.startsWith("decl") ? "Decline" : "Review";
}

const compact = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 });
export const usd = (n: number | null) => (n === null ? "N/A" : compact.format(n));
export const pct = (n: number | null, digits = 1) => (n === null ? "N/A" : `${(n * 100).toFixed(digits)}%`);
export const fmtRatio = (r: Ratio) => (r.value === null ? "N/A" : r.unit === "x" ? `${r.value.toFixed(2)}x` : pct(r.value));
