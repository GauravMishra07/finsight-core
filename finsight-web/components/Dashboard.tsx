"use client";
import { ArrowDownRight, ArrowUpRight, CircleAlert, CircleCheck, CircleMinus } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
  type TooltipProps,
} from "recharts";
import { byYear, cagr, fmtRatio, latest, pct, ratios, trend, usd, yoy, type Metrics, type Ratio } from "@/lib/finance";

const LABELS = ["Revenue", "Net Income", "Total Assets", "Total Liabilities", "Stockholders Equity"];
const pctFmt = (n: number) => pct(n);
const xFmt = (n: number) => `${n.toFixed(2)}x`;
export const axis = { tick: { fill: "var(--muted)", fontSize: 12 }, tickLine: false, axisLine: { stroke: "var(--axis)" } } as const;
const legend = (v: string) => <span style={{ color: "var(--ink-2)", fontSize: 12 }}>{v}</span>;

type Row = Record<string, number | string>;

export function Tip({ active, payload, label, fmt, head = (l) => `FY${l}` }: TooltipProps<number, string> & {
  fmt: (n: number) => string; head?: (label: string) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-semibold">{head(String(label))}</div>
      {payload.map((p) => (
        <div key={p.dataKey as string} className="num flex items-center gap-2 text-ink-2">
          <span className="size-2 rounded-sm" style={{ background: p.color }} aria-hidden />
          {p.name}: <span className="text-ink">{fmt(p.value as number)}</span>
        </div>
      ))}
    </div>
  );
}

function Card({ title, sub, rows, cols, fmt, children }: {
  title: string; sub: string; rows: Row[]; cols: string[]; fmt: (n: number) => string; children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-line bg-surface p-4">
      <h3 className="font-semibold">{title}</h3>
      <p className="text-xs text-muted">{sub}</p>
      {rows.length ? (
        <>
          <div className="mt-3 h-60">{children}</div>
          <details className="mt-2 text-sm">
            <summary className="cursor-pointer text-xs text-muted">View data</summary>
            <div className="overflow-x-auto">
              <table className="num mt-2 w-full text-left text-xs">
                <thead className="text-muted">
                  <tr><th className="py-1 pr-3 font-medium">FY</th>{cols.map((c) => <th key={c} className="py-1 pr-3 font-medium">{c}</th>)}</tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.fy} className="border-t border-line">
                      <td className="py-1 pr-3">{r.fy}</td>
                      {cols.map((c) => <td key={c} className="py-1 pr-3">{typeof r[c] === "number" ? fmt(r[c] as number) : "—"}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      ) : (
        <p className="mt-3 grid h-40 place-items-center rounded-md bg-surface-2 text-sm text-muted">N/A — not reported in XBRL for this filer</p>
      )}
    </section>
  );
}

function KpiTiles({ m }: { m: Metrics }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {LABELS.map((label) => {
        const h = m[label]?.history ?? [];
        const d = yoy(h);
        return (
          <div key={label} className="rounded-lg border border-line bg-surface p-4" title={m[label]?.source}>
            <div className="text-xs text-muted">{label}</div>
            <div className="mt-1 text-2xl font-semibold tracking-tight">{usd(latest(m[label]))}</div>
            <div className="mt-1 flex items-center gap-1 text-xs text-ink-2">
              {d === null ? (
                <span className="text-muted">{h.length ? `FY${h[h.length - 1].fy}` : "Latest 10-K"}</span>
              ) : (
                <>
                  {d >= 0 ? <ArrowUpRight size={14} aria-hidden /> : <ArrowDownRight size={14} aria-hidden />}
                  <span className="num">{pct(d)}</span> <span className="text-muted">YoY · FY{h[h.length - 1].fy}</span>
                </>
              )}
            </div>
            {cagr(h) !== null && (
              <div className="num mt-0.5 text-xs text-muted">
                {pct(cagr(h))} CAGR · FY{h[0].fy}–{h[h.length - 1].fy}
              </div>
            )}
            {h.length >= 2 && (
              <div className="mt-2 h-8" aria-hidden>
                <ResponsiveContainer>
                  <LineChart data={h}>
                    <YAxis hide domain={["dataMin", "dataMax"]} />
                    <Line dataKey="val" stroke="var(--s1)" strokeWidth={2} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const LEVEL = {
  good: { icon: CircleCheck, cls: "text-good-ink" },
  warn: { icon: CircleMinus, cls: "text-ink-2" },
  crit: { icon: CircleAlert, cls: "text-crit" },
};

function RatioPanel({ items }: { items: Ratio[] }) {
  return (
    <section className="rounded-lg border border-line bg-surface p-4">
      <h3 className="font-semibold">Credit ratios</h3>
      <p className="text-xs text-muted">Latest fiscal year · generic bands, not sector-adjusted</p>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {items.map((r) => {
          const L = r.level ? LEVEL[r.level] : null;
          return (
            <div key={r.label} className="rounded-md bg-surface-2 p-3">
              <div className="text-xs text-muted">{r.label}</div>
              <div className="num mt-1 text-xl font-semibold">{fmtRatio(r)}</div>
              {L && r.band ? (
                <div className={`mt-1 flex items-center gap-1 text-xs ${L.cls}`}>
                  <L.icon size={13} aria-hidden /> {r.band}
                </div>
              ) : (
                <div className="mt-1 text-xs text-muted">Insufficient data</div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

type Trend = ReturnType<typeof trend>[number];
const DERIVED: [string, keyof Trend, (n: number) => string][] = [
  ["Revenue growth", "growth", pctFmt],
  ["Net margin", "margin", pctFmt],
  ["Return on equity", "roe", pctFmt],
  ["Return on assets", "roa", pctFmt],
  ["Debt / Equity", "de", xFmt],
  ["Equity ratio", "eqr", pctFmt],
];

function SummaryTable({ m, t }: { m: Metrics; t: Trend[] }) {
  if (!t.length) return null;
  const val = (label: string, fy: string) => m[label]?.history?.find((p) => p.fy === fy)?.val ?? null;
  const td = "py-1.5 pl-4 text-right";
  return (
    <section className="rounded-lg border border-line bg-surface p-4">
      <h3 className="font-semibold">Financial summary</h3>
      <p className="text-xs text-muted">USD from 10-K XBRL; ratios derived. CAGR needs positive start and end values.</p>
      <div className="mt-3 overflow-x-auto">
        <table className="num w-full min-w-[560px] text-sm">
          <thead className="text-xs text-muted">
            <tr className="border-b border-line">
              <th className="py-1.5 text-left font-medium">Fiscal year</th>
              {t.map((r) => <th key={r.fy} className={`${td} font-medium`}>FY{r.fy}</th>)}
              <th className={`${td} font-medium`}>CAGR</th>
            </tr>
          </thead>
          <tbody>
            {LABELS.map((label) => (
              <tr key={label} className="border-b border-line">
                <td className="py-1.5 text-ink-2">{label}</td>
                {t.map((r) => <td key={r.fy} className={td}>{usd(val(label, r.fy))}</td>)}
                <td className={`${td} text-ink-2`}>{pct(cagr(m[label]?.history))}</td>
              </tr>
            ))}
            {DERIVED.map(([label, k, fmt], i) => (
              <tr key={label} className={`border-b border-line ${i === 0 ? "border-t-2" : ""}`}>
                <td className="py-1.5 text-ink-2">{label}</td>
                {t.map((r) => {
                  const v = r[k] as number | null;
                  return <td key={r.fy} className={td}>{v === null ? "—" : fmt(v)}</td>;
                })}
                <td className={td} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function Dashboard({ metrics }: { metrics: Metrics }) {
  const pl = byYear(metrics, ["Revenue", "Net Income"]);
  const margin = pl
    .filter((r) => typeof r.Revenue === "number" && typeof r["Net Income"] === "number" && r.Revenue !== 0)
    .map((r) => ({ fy: r.fy, "Net margin": (r["Net Income"] as number) / (r.Revenue as number) }));
  const cap = byYear(metrics, ["Total Liabilities", "Stockholders Equity"]);
  const negMargin = margin.some((r) => r["Net margin"] < 0);
  const t = trend(metrics);
  const growth = t.filter((r) => r.growth !== null).map((r) => ({ fy: r.fy, "Revenue growth": r.growth as number }));
  const returns: Row[] = t
    .filter((r) => r.roe !== null || r.roa !== null)
    .map((r) => ({ fy: r.fy, ...(r.roe !== null && { ROE: r.roe }), ...(r.roa !== null && { ROA: r.roa }) }));
  const lev = t.filter((r) => r.de !== null).map((r) => ({ fy: r.fy, "Debt / Equity": r.de as number }));
  const negReturn = t.some((r) => (r.roe ?? 0) < 0 || (r.roa ?? 0) < 0);

  return (
    <div className="space-y-4">
      <KpiTiles m={metrics} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Revenue and net income" sub="USD, fiscal years from 10-K XBRL" rows={pl.length >= 2 ? pl : []} cols={["Revenue", "Net Income"]} fmt={usd}>
          <ResponsiveContainer>
            <BarChart data={pl} barGap={2} margin={{ left: 4, right: 4 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis dataKey="fy" {...axis} />
              <YAxis {...axis} width={64} tickFormatter={usd} />
              <ReferenceLine y={0} stroke="var(--axis)" />
              <Tooltip content={<Tip fmt={usd} />} cursor={{ fill: "var(--surface-2)" }} />
              <Legend verticalAlign="top" align="left" height={28} iconType="square" iconSize={10} formatter={legend} />
              <Bar dataKey="Revenue" fill="var(--s1)" radius={[4, 4, 0, 0]} maxBarSize={28} />
              <Bar dataKey="Net Income" fill="var(--s2)" radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Net margin" sub="Net income ÷ revenue" rows={margin.length >= 2 ? margin : []} cols={["Net margin"]} fmt={(n) => pct(n)}>
          <ResponsiveContainer>
            <LineChart data={margin} margin={{ left: 4, right: 12, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis dataKey="fy" {...axis} />
              <YAxis {...axis} width={52} tickFormatter={(n) => pct(n, 0)} domain={negMargin ? ["auto", "auto"] : [0, "auto"]} />
              {negMargin && <ReferenceLine y={0} stroke="var(--axis)" />}
              <Tooltip content={<Tip fmt={(n) => pct(n)} />} cursor={{ stroke: "var(--axis)" }} />
              <Line dataKey="Net margin" stroke="var(--s1)" strokeWidth={2} dot={{ r: 4, fill: "var(--s1)", stroke: "var(--surface)", strokeWidth: 2 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Capital structure" sub="Liabilities + equity = total assets (USD)" rows={cap} cols={["Total Liabilities", "Stockholders Equity"]} fmt={usd}>
          <ResponsiveContainer>
            <BarChart data={cap} margin={{ left: 4, right: 4 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis dataKey="fy" {...axis} />
              <YAxis {...axis} width={64} tickFormatter={usd} />
              <Tooltip content={<Tip fmt={usd} />} cursor={{ fill: "var(--surface-2)" }} />
              <Legend verticalAlign="top" align="left" height={28} iconType="square" iconSize={10} formatter={legend} />
              <Bar dataKey="Total Liabilities" name="Liabilities" stackId="cap" fill="var(--s1)" stroke="var(--surface)" strokeWidth={2} maxBarSize={36} />
              <Bar dataKey="Stockholders Equity" name="Equity" stackId="cap" fill="var(--s2)" stroke="var(--surface)" strokeWidth={2} radius={[4, 4, 0, 0]} maxBarSize={36} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Revenue growth" sub="Year-over-year change in revenue" rows={growth.length >= 2 ? growth : []} cols={["Revenue growth"]} fmt={pctFmt}>
          <ResponsiveContainer>
            <BarChart data={growth} margin={{ left: 4, right: 4, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis dataKey="fy" {...axis} />
              <YAxis {...axis} width={52} tickFormatter={(n) => pct(n, 0)} />
              <ReferenceLine y={0} stroke="var(--axis)" />
              <Tooltip content={<Tip fmt={pctFmt} />} cursor={{ fill: "var(--surface-2)" }} />
              <Bar dataKey="Revenue growth" fill="var(--s1)" radius={[4, 4, 0, 0]} maxBarSize={36} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Returns" sub="Net income ÷ equity (ROE) and ÷ total assets (ROA)" rows={returns.length >= 2 ? returns : []} cols={["ROE", "ROA"]} fmt={pctFmt}>
          <ResponsiveContainer>
            <LineChart data={returns} margin={{ left: 4, right: 12, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis dataKey="fy" {...axis} />
              <YAxis {...axis} width={52} tickFormatter={(n) => pct(n, 0)} domain={negReturn ? ["auto", "auto"] : [0, "auto"]} />
              {negReturn && <ReferenceLine y={0} stroke="var(--axis)" />}
              <Tooltip content={<Tip fmt={pctFmt} />} cursor={{ stroke: "var(--axis)" }} />
              <Legend verticalAlign="top" align="left" height={28} iconType="plainline" formatter={legend} />
              <Line dataKey="ROE" stroke="var(--s1)" strokeWidth={2} dot={{ r: 4, fill: "var(--s1)", stroke: "var(--surface)", strokeWidth: 2 }} connectNulls />
              <Line dataKey="ROA" stroke="var(--s2)" strokeWidth={2} dot={{ r: 4, fill: "var(--s2)", stroke: "var(--surface)", strokeWidth: 2 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Leverage" sub="Total liabilities ÷ stockholders' equity (lower is safer)" rows={lev.length >= 2 ? lev : []} cols={["Debt / Equity"]} fmt={xFmt}>
          <ResponsiveContainer>
            <LineChart data={lev} margin={{ left: 4, right: 12, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis dataKey="fy" {...axis} />
              <YAxis {...axis} width={52} tickFormatter={(n) => `${n}x`} domain={[0, "auto"]} />
              <Tooltip content={<Tip fmt={xFmt} />} cursor={{ stroke: "var(--axis)" }} />
              <Line dataKey="Debt / Equity" stroke="var(--s1)" strokeWidth={2} dot={{ r: 4, fill: "var(--s1)", stroke: "var(--surface)", strokeWidth: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <RatioPanel items={ratios(metrics)} />
      <SummaryTable m={metrics} t={t} />
    </div>
  );
}
