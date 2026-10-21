"use client";
import { useCallback, useEffect, useState } from "react";
import { wake } from "@/lib/api";

type S = "waking" | "online" | "offline";

const LABEL: Record<S, string> = {
  waking: "Waking server (free tier, up to ~60 s)",
  online: "Server online",
  offline: "Server unreachable — retry",
};
const DOT: Record<S, string> = { waking: "bg-warn animate-pulse", online: "bg-good", offline: "bg-crit" };

export default function ServerStatus() {
  const [s, setS] = useState<S>("waking");
  const ping = useCallback(() => {
    setS("waking");
    wake().then(() => setS("online"), () => setS("offline"));
  }, []);
  useEffect(ping, [ping]);

  return (
    <button
      onClick={s === "offline" ? ping : undefined}
      disabled={s !== "offline"}
      aria-live="polite"
      className="flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs text-ink-2 enabled:hover:bg-surface-2"
    >
      <span className={`size-2 rounded-full ${DOT[s]}`} aria-hidden />
      <span className="max-w-[46vw] truncate">{LABEL[s]}</span>
    </button>
  );
}
