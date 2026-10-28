"use client";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, Check, Copy, Download, MessagesSquare, Printer, RefreshCw } from "lucide-react";
import AnalysisProgress from "./AnalysisProgress";
import Competitors from "./Competitors";
import Copilot, { CHAT_DEFAULT } from "./Copilot";
import Dashboard from "./Dashboard";
import Markdown from "./Markdown";
import VerdictBadge from "./VerdictBadge";
import { analyze, getSample } from "@/lib/api";
import { getReport, saveReport } from "@/lib/store";
import { verdictFromMemo, type Report } from "@/lib/finance";

const TABS = ["Dashboard", "Memo", "Macro & risk", "Competitors", "Pipeline & R&D"] as const;
type Tab = (typeof TABS)[number];

const CHAT_KEY = "finsight:chatWidth";
// Keep the report readable: the copilot never takes more than the viewport minus 480px.
const clampChat = (w: number) => Math.round(Math.max(320, Math.min(w, 960, window.innerWidth - 480)));

const btn = "flex items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50";

export default function ReportView() {
  const ticker = (useSearchParams().get("t") ?? "").trim().toUpperCase();
  const [report, setReport] = useState<Report | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("Dashboard");
  const [chatOpen, setChatOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [chatW, setChatW] = useState(CHAT_DEFAULT);
  useEffect(() => {
    try {
      const w = Number(localStorage.getItem(CHAT_KEY));
      if (w) setChatW(clampChat(w));
    } catch {}
  }, []);
  const resizeChat = useCallback((w: number) => {
    const next = clampChat(w);
    setChatW(next);
    try {
      localStorage.setItem(CHAT_KEY, String(next));
    } catch {}
  }, []);

  const run = useCallback(() => {
    let live = true;
    setRunning(true);
    setError(null);
    analyze(ticker)
      .then((r) => {
        saveReport(r);
        if (live) setReport(getReport(ticker) ?? r);
      })
      .catch((e) => live && setError((e as Error).message))
      .finally(() => live && setRunning(false));
    return () => { live = false; };
  }, [ticker]);

  useEffect(() => {
    if (!ticker) return;
    const cached = getReport(ticker);
    setReport(cached ?? null);
    if (cached) return;
    // Not in this browser yet: a shipped sample opens instantly; anything else runs the pipeline.
    let live = true;
    let stop: (() => void) | undefined;
    getSample(ticker).then((s) => {
      if (!live) return;
      if (s) setReport(s);
      else stop = run();
    });
    return () => {
      live = false;
      stop?.();
    };
  }, [ticker, run]);

  if (!ticker) return <Empty msg="No ticker given." />;
  if (running) return <AnalysisProgress ticker={ticker} />;
  if (error && !report) return <Empty msg={error} retry={run} />;
  if (!report) return null;

  const memo = report.final_memo;
  const accession = report.tenant_id?.split("__")[1];

  const download = () => {
    const url = URL.createObjectURL(new Blob([memo], { type: "text/markdown" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `${ticker}-credit-memo.md` });
    a.click();
    URL.revokeObjectURL(url);
  };
  const print = () => {
    setTab("Memo");
    setTimeout(() => window.print(), 50);
  };

  return (
    <div
      className="mx-auto max-w-[1920px] lg:grid lg:grid-cols-[minmax(0,1fr)_var(--chat-w)]"
      style={{ "--chat-w": `${chatW}px` } as React.CSSProperties}
    >
      <main className="min-w-0 px-4 py-6">
        <div className="no-print flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link href="/" className="flex items-center gap-1 text-xs text-muted hover:text-ink">
              <ArrowLeft size={12} aria-hidden /> All companies
            </Link>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-semibold tracking-tight">{ticker}</h1>
              <VerdictBadge verdict={verdictFromMemo(memo)} />
            </div>
            <p className="mt-1 text-xs text-muted">
              Latest SEC 10-K{accession ? ` · accession ${accession}` : ""}
              {report.savedAt ? ` · generated ${new Date(report.savedAt).toLocaleString()}` : ""}
              {report.sample && " · pre-generated sample, Re-run for a live analysis"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className={btn} onClick={run} title="Runs the full pipeline again (~2 min)">
              <RefreshCw size={14} aria-hidden /> Re-run
            </button>
            <button
              className={btn}
              onClick={() => navigator.clipboard?.writeText(memo).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); })}
            >
              {copied ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />} {copied ? "Copied" : "Copy memo"}
            </button>
            <button className={btn} onClick={download}><Download size={14} aria-hidden /> .md</button>
            <button className={btn} onClick={print}><Printer size={14} aria-hidden /> PDF</button>
          </div>
        </div>

        {error && <p role="alert" className="no-print mt-4 rounded-md border border-crit/40 bg-crit/10 px-3 py-2 text-sm">Re-run failed: {error}</p>}
        {!!report.errors?.length && (
          <div className="no-print mt-4 flex gap-2 rounded-md border border-warn/60 bg-warn/10 px-3 py-2 text-sm">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden />
            <div>
              <div className="font-medium">Some agents reported problems; parts of this report may be incomplete.</div>
              <ul className="mt-1 list-disc pl-4 text-xs text-ink-2">{report.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
            </div>
          </div>
        )}

        <nav className="no-print mt-6 flex gap-1 overflow-x-auto border-b border-line" role="tablist">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm ${tab === t ? "border-accent font-medium text-ink" : "border-transparent text-muted hover:text-ink"}`}
            >
              {t}
            </button>
          ))}
        </nav>

        <div className="mt-6">
          {tab === "Dashboard" && <Dashboard metrics={report.financial_metrics ?? {}} />}
          {tab === "Memo" && (
            <article className="max-w-3xl rounded-lg border border-line bg-surface p-4 sm:p-8 print:border-0 print:p-0">
              <Markdown>{memo}</Markdown>
            </article>
          )}
          {tab === "Macro & risk" && (
            <div className="grid gap-4 xl:grid-cols-2">
              <Panel title="Quantitative risk analysis">{report.risk_analysis}</Panel>
              <Panel title="Macro and sector headwinds">{report.macro_analysis}</Panel>
            </div>
          )}
          {tab === "Competitors" && (
            <Competitors ticker={ticker} metrics={report.financial_metrics ?? {}} competitors={report.competitors} fallback={report.competitor_analysis} />
          )}
          {tab === "Pipeline & R&D" && <Panel title="Upcoming projects and R&D">{report.upcoming_projects}</Panel>}
        </div>
      </main>

      <Copilot report={report} open={chatOpen} onClose={() => setChatOpen(false)} width={chatW} onResize={resizeChat} />
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="no-print fixed bottom-4 right-4 z-30 flex items-center gap-2 rounded-full bg-accent px-4 py-3 text-sm font-medium text-white shadow-lg lg:hidden"
        >
          <MessagesSquare size={16} aria-hidden /> Ask copilot
        </button>
      )}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: string | null | undefined }) {
  return (
    <section className="max-w-3xl rounded-lg border border-line bg-surface p-6">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">{title}</h2>
      <Markdown>{children}</Markdown>
    </section>
  );
}

function Empty({ msg, retry }: { msg: string; retry?: () => void }) {
  return (
    <div className="mx-auto max-w-lg px-4 py-20 text-center">
      <AlertTriangle className="mx-auto text-crit" aria-hidden />
      <p role="alert" className="mt-3 text-ink-2">{msg}</p>
      <div className="mt-6 flex justify-center gap-2">
        {retry && <button className={btn} onClick={retry}><RefreshCw size={14} aria-hidden /> Try again</button>}
        <Link href="/" className={btn}><ArrowLeft size={14} aria-hidden /> Back</Link>
      </div>
    </div>
  );
}
