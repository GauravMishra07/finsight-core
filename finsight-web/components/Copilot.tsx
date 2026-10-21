"use client";
import { useEffect, useRef, useState } from "react";
import { Bot, Copy, Loader2, Maximize2, Minimize2, SendHorizontal, Trash2, X } from "lucide-react";
import Markdown from "./Markdown";
import { chat, type ChatMsg } from "@/lib/api";
import { getChat, saveChat } from "@/lib/store";
import type { Report } from "@/lib/finance";

export const CHAT_DEFAULT = 400;
const WIDE = 720;
const STEP = 32;

const SUGGESTIONS = [
  "Summarize the key liquidity and refinancing risks",
  "What debt maturities or covenants does the 10-K disclose?",
  "Which segments drive revenue growth?",
  "Draft an executive summary paragraph for my report",
];

export default function Copilot({ report, open, onClose, width, onResize }: {
  report: Report; open: boolean; onClose: () => void; width: number; onResize: (w: number) => void;
}) {
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMsgs(getChat(report.ticker));
  }, [report.ticker]);
  // Braces matter: newer browsers return a Promise from scrollIntoView, which React rejects as a cleanup.
  useEffect(() => {
    end.current?.scrollIntoView({ block: "end" });
  }, [msgs, busy]);

  // Drag the left edge; the panel's right edge stays put, so width = right − pointer x.
  function startDrag(e: React.PointerEvent<HTMLDivElement>) {
    e.preventDefault();
    const right = e.currentTarget.parentElement!.getBoundingClientRect().right;
    const move = (ev: PointerEvent) => onResize(right - ev.clientX);
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      document.body.style.cursor = document.body.style.userSelect = "";
    };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }
  const wide = width >= WIDE - STEP;

  async function send(text: string) {
    const query = text.trim();
    if (!query || busy) return;
    const history = msgs;
    const next: ChatMsg[] = [...history, { role: "user", content: query }];
    setMsgs(next);
    setQ("");
    setErr(null);
    setBusy(true);
    try {
      const answer = await chat(report, history, query);
      const done: ChatMsg[] = [...next, { role: "assistant", content: answer }];
      setMsgs(done);
      saveChat(report.ticker, done);
    } catch (e) {
      setErr((e as Error).message);
      setMsgs(history);
      setQ(query); // give the question back so it isn't lost
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside
      className={`no-print relative flex-col border-line bg-surface lg:sticky lg:top-14 lg:flex lg:h-[calc(100dvh-3.5rem)] lg:border-l ${
        open ? "fixed inset-x-0 bottom-0 z-40 flex h-[85dvh] rounded-t-2xl border-t shadow-2xl" : "hidden"
      }`}
      aria-label="Research copilot"
    >
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize copilot panel"
        aria-valuenow={width}
        tabIndex={0}
        onPointerDown={startDrag}
        onDoubleClick={() => onResize(CHAT_DEFAULT)}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") onResize(width + STEP);
          else if (e.key === "ArrowRight") onResize(width - STEP);
        }}
        title="Drag to resize · double-click to reset"
        className="group absolute inset-y-0 -left-1.5 z-10 hidden w-3 cursor-col-resize lg:block"
      >
        <span className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-transparent transition-colors group-hover:bg-accent group-focus-visible:bg-accent" />
      </div>
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <Bot size={18} className="text-accent" aria-hidden />
          <div>
            <div className="text-sm font-semibold">Research copilot</div>
            <div className="text-xs text-muted">Grounded in the {report.ticker} 10-K, XBRL metrics and memo</div>
          </div>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => onResize(wide ? CHAT_DEFAULT : WIDE)}
            className="hidden rounded p-1.5 text-muted hover:bg-surface-2 lg:block"
            aria-label={wide ? "Shrink copilot panel" : "Widen copilot panel"}
            title={wide ? "Shrink panel" : "Widen panel"}
          >
            {wide ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          {msgs.length > 0 && (
            <button onClick={() => { setMsgs([]); saveChat(report.ticker, []); }} className="rounded p-1.5 text-muted hover:bg-surface-2" aria-label="Clear conversation">
              <Trash2 size={16} />
            </button>
          )}
          <button onClick={onClose} className="rounded p-1.5 text-muted hover:bg-surface-2 lg:hidden" aria-label="Close copilot">
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="chat @container flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {msgs.length === 0 && (
          <div className="grid gap-2 @xl:grid-cols-2">
            <p className="text-sm text-ink-2 @xl:col-span-2">Ask anything about the filing. Try:</p>
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} className="block w-full rounded-md border border-line px-3 py-2 text-left text-sm hover:border-accent">
                {s}
              </button>
            ))}
          </div>
        )}
        {msgs.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap rounded-lg bg-accent px-3 py-2 text-sm text-white @2xl:max-w-[70%]">
              {m.content}
            </div>
          ) : (
            <div key={i} className="chat-answer">
              <Markdown>{m.content}</Markdown>
              <button
                onClick={() => navigator.clipboard?.writeText(m.content)}
                className="mt-1 flex items-center gap-1 text-xs text-muted hover:text-ink"
              >
                <Copy size={12} aria-hidden /> Copy
              </button>
            </div>
          ),
        )}
        {busy && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 size={14} className="animate-spin" aria-hidden /> Searching the filing…
          </div>
        )}
        {err && <p role="alert" className="rounded-md border border-crit/40 bg-crit/10 px-3 py-2 text-sm">{err}</p>}
        <div ref={end} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(q);
        }}
        className="flex gap-2 border-t border-line p-3"
      >
        <label className="flex-1">
          <span className="sr-only">Ask a follow-up question</span>
          <textarea
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(q);
              }
            }}
            rows={2}
            placeholder="Ask a follow-up question…"
            className="w-full resize-none rounded-md border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-accent"
          />
        </label>
        <button disabled={busy || !q.trim()} className="self-end rounded-md bg-accent p-2.5 text-white disabled:opacity-50" aria-label="Send">
          <SendHorizontal size={16} />
        </button>
      </form>
    </aside>
  );
}
