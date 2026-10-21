import { CircleCheck, CircleHelp, CircleX, type LucideIcon } from "lucide-react";
import type { Verdict } from "@/lib/finance";

// Status colour always ships with an icon + label, never colour alone.
const STYLE: Record<Verdict, { icon: LucideIcon; cls: string }> = {
  Approve: { icon: CircleCheck, cls: "text-good-ink border-good/40 bg-good/10" },
  Review: { icon: CircleHelp, cls: "text-ink border-warn/60 bg-warn/15" },
  Decline: { icon: CircleX, cls: "text-crit border-crit/40 bg-crit/10" },
};

export default function VerdictBadge({ verdict, small }: { verdict: Verdict | null; small?: boolean }) {
  if (!verdict) return <span className="text-xs text-muted">No verdict</span>;
  const { icon: Icon, cls } = STYLE[verdict];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${cls} ${small ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm"}`}>
      <Icon size={small ? 13 : 15} aria-hidden />
      {verdict}
    </span>
  );
}
