"use client";
import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

// The API is synchronous, so stage timing is an estimate from typical runs, labelled as such.
const STAGES = [
  { name: "Extractor", detail: "Downloading the 10-K and indexing it in Pinecone", until: 40 },
  { name: "Quantitative analyst", detail: "Pulling audited XBRL financials", until: 55 },
  { name: "Macro reviewer", detail: "Searching the filing and live news", until: 85 },
  { name: "Underwriter", detail: "Drafting the credit memo", until: Infinity },
];

export default function AnalysisProgress({ ticker }: { ticker: string }) {
  const [t, setT] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setT((x) => x + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const active = STAGES.findIndex((s) => t < s.until);

  return (
    <div className="mx-auto max-w-xl px-4 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Analysing {ticker}</h1>
      <p className="mt-1 text-sm text-ink-2">
        Usually 1–2 minutes; a first or cold run takes longer. <span className="num">{t}s</span> elapsed.
      </p>
      <ol className="mt-8 space-y-1" aria-live="polite">
        {STAGES.map((s, i) => (
          <li key={s.name} className={`flex gap-3 rounded-lg p-3 ${i === active ? "bg-surface border border-line" : ""}`}>
            <span
              className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full text-xs ${
                i < active ? "bg-accent text-white" : i === active ? "border-2 border-accent text-accent" : "border border-line text-muted"
              }`}
            >
              {i < active ? <Check size={14} aria-hidden /> : i === active ? <Loader2 size={14} className="animate-spin" aria-hidden /> : i + 1}
            </span>
            <div>
              <div className={i > active ? "text-muted" : "font-medium"}>{s.name}</div>
              <div className="text-sm text-muted">{s.detail}</div>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-6 text-xs text-muted">Stage progress is estimated (est.). Keep this tab open.</p>
    </div>
  );
}
