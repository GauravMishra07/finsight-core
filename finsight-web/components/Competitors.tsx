"use client";
import { CircleAlert, CircleCheck, CircleMinus, type LucideIcon } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { axis, Tip } from "./Dashboard";
import Markdown from "./Markdown";
import { pct, peerRow, usd, type Competitor, type Metrics, type PeerRow, type Threat } from "@/lib/finance";

// Status colour always ships with an icon + label.
const THREAT: Record<Threat, { icon: LucideIcon; cls: string }> = {
  High: { icon: CircleAlert, cls: "text-crit border-crit/40 bg-crit/10" },
  Medium: { icon: CircleMinus, cls: "text-ink border-warn/60 bg-warn/15" },
  Low: { icon: CircleCheck, cls: "text-good-ink border-good/40 bg-good/10" },
};

function ThreatBadge({ threat }: { threat: Threat | null }) {
  if (!threat) return <span className="text-xs text-muted">Threat not rated</span>;
  const { icon: Icon, cls } = THREAT[threat];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}>
      <Icon size={12} aria-hidden /> {threat} threat
    </span>
  );
}

const x = (n: number | null) => (n === null ? "N/A" : `${n.toFixed(2)}x`);
const COLS: [string, (r: PeerRow) => string][] = [
  ["FY", (r) => r.fy ?? "—"],
  ["Revenue", (r) => usd(r.rev)],
  ["Rev. YoY", (r) => pct(r.growth)],
  ["Net margin", (r) => pct(r.margin)],
  ["ROE", (r) => pct(r.roe)],
  ["Debt / Equity", (r) => x(r.de)],
  ["Equity ratio", (r) => pct(r.eqr)],
];

function PeerChart({ title, rows, k, fmt, tick }: {
  title: string; rows: PeerRow[]; k: keyof PeerRow; fmt: (n: number) => string; tick: (n: number) => string;
}) {
  const data = rows.filter((r) => typeof r[k] === "number").map((r) => ({ label: r.ticker ?? r.name, v: r[k] as number, subject: r.subject }));
  if (data.length < 2) return null;
  return (
    <section className="rounded-lg border border-line bg-surface p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-2" style={{ height: 28 * data.length + 36 }}>
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{ left: 0, right: 16 }}>
            <CartesianGrid horizontal={false} stroke="var(--line)" />
            <XAxis type="number" {...axis} tickFormatter={tick} />
            <YAxis type="category" dataKey="label" {...axis} width={56} />
            <ReferenceLine x={0} stroke="var(--axis)" />
            <Tooltip content={<Tip fmt={fmt} head={(l) => l} />} cursor={{ fill: "var(--surface-2)" }} />
            <Bar dataKey="v" name={title} radius={4} maxBarSize={18}>
              {data.map((d) => <Cell key={d.label} fill={d.subject ? "var(--s1)" : "var(--muted)"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default function Competitors({ ticker, metrics, competitors, fallback }: {
  ticker: string; metrics: Metrics;
  competitors: Competitor[] | undefined; fallback: string | null | undefined;
}) {
  if (!competitors?.length)
    return (
      <section className="max-w-3xl rounded-lg border border-line bg-surface p-6">
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-muted">Market competitors</h2>
        <p className="mb-3 text-xs text-muted">Re-run the report to get threat ratings and peer financials.</p>
        <Markdown>{fallback}</Markdown>
      </section>
    );

  const peers = competitors.filter((c) => c.metrics).map((c) => peerRow(c.name, c.ticker, c.metrics!));
  const rows = [peerRow(ticker, ticker, metrics, true), ...peers];
  const pctTick = (n: number) => pct(n, 0);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
        {competitors.map((c) => (
          <article key={c.name} className="rounded-lg border border-line bg-surface p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold">{c.name}</h3>
                <p className="text-xs text-muted">
                  {c.ticker ?? "Private or non-US listed"}
                  {c.sec_name && c.sec_name.toLowerCase() !== c.name.toLowerCase() ? ` · SEC: ${c.sec_name}` : ""}
                </p>
              </div>
              <ThreatBadge threat={c.threat} />
            </div>
            {c.overlap && <p className="mt-3 inline-block rounded bg-surface-2 px-2 py-0.5 text-xs text-ink-2">Competes in: {c.overlap}</p>}
            <p className="mt-2 text-sm text-ink-2">{c.note}</p>
          </article>
        ))}
      </div>

      {peers.length > 0 ? (
        <>
          <section className="rounded-lg border border-line bg-surface p-4">
            <h3 className="font-semibold">Peer comparison</h3>
            <p className="text-xs text-muted">Latest fiscal year from each company&apos;s own 10-K XBRL. Fiscal year ends differ by company.</p>
            <div className="mt-3 overflow-x-auto">
              <table className="num w-full min-w-[640px] text-sm">
                <thead className="text-xs text-muted">
                  <tr className="border-b border-line">
                    <th className="py-1.5 text-left font-medium">Company</th>
                    {COLS.map(([h]) => <th key={h} className="py-1.5 pl-4 text-right font-medium">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.name} className={`border-b border-line ${r.subject ? "bg-surface-2 font-medium" : ""}`}>
                      <td className="py-1.5 pl-1">{r.subject ? `${r.name} (subject)` : r.ticker ? `${r.name} · ${r.ticker}` : r.name}</td>
                      {COLS.map(([h, f]) => <td key={h} className="py-1.5 pl-4 text-right">{f(r)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <p className="flex items-center gap-3 text-xs text-ink-2">
            <span className="flex items-center gap-1"><span className="size-2.5 rounded-sm bg-[var(--s1)]" aria-hidden /> {ticker}</span>
            <span className="flex items-center gap-1"><span className="size-2.5 rounded-sm bg-muted" aria-hidden /> Peers</span>
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            <PeerChart title="Revenue, latest FY" rows={rows} k="rev" fmt={usd} tick={usd} />
            <PeerChart title="Revenue growth, YoY" rows={rows} k="growth" fmt={(n) => pct(n)} tick={pctTick} />
            <PeerChart title="Net margin" rows={rows} k="margin" fmt={(n) => pct(n)} tick={pctTick} />
            <PeerChart title="Debt / Equity" rows={rows} k="de" fmt={(n) => x(n)} tick={(n) => `${n}x`} />
          </div>
        </>
      ) : (
        <p className="text-sm text-muted">No listed peers with SEC XBRL data, so there is no financial comparison.</p>
      )}
    </div>
  );
}
