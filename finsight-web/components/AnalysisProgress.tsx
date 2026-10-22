"use client";
import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

// The API is synchronous, so stage timing is an estimate from typical runs, labelled as such.
// Quant and macro run in parallel on the backend (src/agents/graph.py), so their windows overlap.
const STAGES = [
  { name: "Extractor", detail: "Downloading the 10-K and indexing it in Pinecone", from: 0, until: 40 },
  { name: "Quantitative analyst", detail: "Pulling audited XBRL financials", from: 40, until: 50, parallel: true },
  { name: "Macro reviewer", detail: "Searching the filing and live news", from: 40, until: 70, parallel: true },
  { name: "Underwriter", detail: "Drafting the credit memo", from: 70, until: Infinity },
];

export default function AnalysisProgress({ ticker }: { ticker: string }) {
  const [t, setT] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setT((x) => x + 1), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="mx-auto max-w-xl px-4 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Analysing {ticker}</h1>
      <p className="mt-1 text-sm text-ink-2">
        Usually 1–2 minutes; a first or cold run takes longer. <span className="num">{t}s</span> elapsed.
      </p>
      <ol className="mt-8 space-y-1" aria-live="polite">
        {STAGES.map((s, i) => {
          const done = t >= s.until;
          const active = !done && t >= s.from;
          return (
            <li key={s.name} className={`flex gap-3 rounded-lg p-3 ${active ? "bg-surface border border-line" : ""}`}>
              <span
                className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full text-xs ${
                  done ? "bg-accent text-white" : active ? "border-2 border-accent text-accent" : "border border-line text-muted"
                }`}
              >
                {done ? <Check size={14} aria-hidden /> : active ? <Loader2 size={14} className="animate-spin" aria-hidden /> : i + 1}
              </span>
              <div>
                <div className={done || active ? "font-medium" : "text-muted"}>
                  {s.name}
                  {s.parallel && <span className="ml-2 text-xs font-normal text-muted">runs in parallel</span>}
                </div>
                <div className="text-sm text-muted">{s.detail}</div>
              </div>
            </li>
          );
        })}
      </ol>
      <p className="mt-6 text-xs text-muted">Stage progress is estimated (est.). Keep this tab open.</p>
    </div>
  );
}
