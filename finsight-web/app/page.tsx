"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, FileSearch, LineChart, MessagesSquare, Search } from "lucide-react";
import VerdictBadge from "@/components/VerdictBadge";
import { listReports } from "@/lib/store";
import { verdictFromMemo, type Report } from "@/lib/finance";

const PRESETS = [
  ["MSFT", "Microsoft"],
  ["AAPL", "Apple"],
  ["NVDA", "Nvidia"],
  ["TSLA", "Tesla"],
  ["NFLX", "Netflix"],
  ["ADBE", "Adobe"],
];

const FEATURES = [
  { icon: FileSearch, title: "Reads the latest 10-K", body: "Pulls the filing from SEC EDGAR and indexes it for retrieval." },
  { icon: LineChart, title: "Audited XBRL numbers", body: "Five-year trends and credit ratios straight from SEC data, not the LLM." },
  { icon: MessagesSquare, title: "Research copilot", body: "Ask follow-ups grounded in the filing, metrics and live news." },
];

export default function Home() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [recent, setRecent] = useState<Report[]>([]);
  useEffect(() => {
    setRecent(listReports());
  }, []);

  const go = (t: string) => {
    const ticker = t.trim().toUpperCase();
    if (ticker) router.push(`/report?t=${encodeURIComponent(ticker)}`);
  };

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:py-20">
      <p className="text-sm font-medium text-accent">Built for equity research and credit teams</p>
      <h1 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl">
        From annual report to credit memo in about 2 minutes.
      </h1>
      <p className="mt-4 max-w-2xl text-ink-2">
        Enter a ticker or company name. FinSight reads the latest SEC 10-K, extracts audited financials, checks the news,
        and drafts an underwriting memo you can question, edit and export.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          go(q);
        }}
        className="mt-8 flex flex-col gap-2 sm:flex-row"
      >
        <label className="relative flex-1">
          <span className="sr-only">Ticker or company name</span>
          <Search size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ticker or company, e.g. PLTR or Palantir"
            className="h-12 w-full rounded-lg border border-line bg-surface pl-10 pr-3 text-base outline-none focus:border-accent focus:ring-2 focus:ring-accent/25"
            autoFocus
          />
        </label>
        <button
          disabled={!q.trim()}
          className="flex h-12 items-center justify-center gap-2 rounded-lg bg-accent px-5 font-medium text-white disabled:opacity-50"
        >
          Generate memo <ArrowRight size={16} aria-hidden />
        </button>
      </form>

      <div className="mt-4 flex flex-wrap gap-2">
        {PRESETS.map(([t, name]) => (
          <button
            key={t}
            onClick={() => go(t)}
            className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm hover:border-accent"
          >
            <span className="font-semibold">{t}</span> <span className="text-muted">{name}</span>
          </button>
        ))}
      </div>

      {recent.length > 0 && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Recent reports</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {recent.map((r) => (
              <Link
                key={r.ticker}
                href={`/report?t=${r.ticker}`}
                className="flex items-center justify-between rounded-lg border border-line bg-surface p-4 hover:border-accent"
              >
                <div>
                  <div className="font-semibold">{r.ticker}</div>
                  <div className="text-xs text-muted">{r.savedAt ? new Date(r.savedAt).toLocaleString() : ""}</div>
                </div>
                <VerdictBadge verdict={verdictFromMemo(r.final_memo)} small />
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="mt-14 grid gap-4 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <div key={title} className="rounded-lg border border-line bg-surface p-5">
            <Icon size={20} className="text-accent" aria-hidden />
            <h3 className="mt-3 font-semibold">{title}</h3>
            <p className="mt-1 text-sm text-ink-2">{body}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
