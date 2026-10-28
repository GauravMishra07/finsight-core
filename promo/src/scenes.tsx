import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Database, Download, FileCheck, FileSearch, FileText, Globe, Landmark, PenLine, ShieldCheck, TrendingUp, Workflow, ArrowRight } from "lucide-react";
import { Badge, Browser, C, Caption, Cursor, Shot, Words, fontFamily, glass, useSpring } from "./ui";
import { metricAccuracy, stats, verdicts } from "./data";
import { pct, usd } from "../../finsight-web/lib/finance";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const smooth = Easing.bezier(0.65, 0, 0.35, 1);
const ramp = (f: number, a: number, b: number, from = 0, to = 1) => interpolate(f, [a, b], [from, to], { ...clamp, easing: smooth });

// Browser on the right, swinging in with a 3D tilt and drifting slowly.
const BW = 1120;
const BH = 630;
const Stage: React.FC<{ url: string; children: React.ReactNode }> = ({ url, children }) => {
  const f = useCurrentFrame();
  const s = useSpring(2);
  return (
    <AbsoluteFill style={{ perspective: 2200 }}>
      <div
        style={{
          position: "absolute",
          left: 690,
          top: 202,
          width: BW,
          height: BH + 46,
          opacity: s,
          transform: `translateX(${(1 - s) * 280}px) rotateY(${-24 + 15 * s + f * 0.012}deg) rotateX(${4 - 2 * s}deg)`,
        }}
      >
        <Browser width={BW} height={BH} url={url}>
          {children}
        </Browser>
      </div>
    </AbsoluteFill>
  );
};

export const Hook: React.FC = () => {
  const f = useCurrentFrame();
  const days = useSpring(24);
  const strike = ramp(f, 70, 88);
  const up = ramp(f, 96, 120);
  const big = { fontFamily, fontWeight: 800, letterSpacing: "-0.04em", color: C.ink } as const;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center" }}>
      <div style={{ transform: `translateY(${-120 * up}px) scale(${1 - 0.25 * up})`, opacity: 1 - 0.55 * up }}>
        <div style={{ ...big, fontSize: 96 }}>
          <Words text="Writing one credit memo" delay={4} />
        </div>
        <div style={{ ...big, fontSize: 96, display: "flex", justifyContent: "center" }}>
          <Words text="takes analysts" delay={14} />
          <span
            style={{
              position: "relative",
              display: "inline-block",
              opacity: days,
              transform: `translateY(${(1 - days) * 40}px)`,
              color: strike > 0.5 ? C.muted : C.s2,
            }}
          >
            days.
            <span style={{ position: "absolute", left: -8, top: "54%", height: 10, width: `calc(${strike * 100}% + 16px)`, background: C.crit, borderRadius: 5 }} />
          </span>
        </div>
      </div>
      <div style={{ position: "absolute", top: 600, ...big, fontSize: 110, opacity: f > 100 ? 1 : 0 }}>
        <Words text="FinSight: *about* *2* *minutes.*" delay={104} stagger={5} />
      </div>
    </AbsoluteFill>
  );
};

export const Logo: React.FC = () => {
  const f = useCurrentFrame();
  const pop = useSpring(4, 11);
  const ring = ramp(f, 6, 60);
  const chips = ["SEC 10-K", "Audited XBRL", "LangGraph agents", "Pinecone RAG", "Live news"];
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily }}>
      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 40 }}>
        <div style={{ position: "relative", width: 150, height: 150 }}>
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: 40,
              border: `3px solid ${C.accent}`,
              transform: `scale(${1 + ring * 1.8})`,
              opacity: 0.7 * (1 - ring),
            }}
          />
          <div
            style={{
              width: 150,
              height: 150,
              borderRadius: 40,
              display: "grid",
              placeItems: "center",
              background: "linear-gradient(145deg, #5aa2f5, #2a78d6 60%, #1d5bb0)",
              boxShadow: "0 0 90px rgba(57,135,229,0.55), inset 0 2px 0 rgba(255,255,255,0.25)",
              transform: `scale(${pop}) rotate(${(1 - pop) * -20}deg)`,
            }}
          >
            <Landmark size={82} color="#fff" strokeWidth={2} />
          </div>
        </div>
        <div style={{ fontSize: 150, fontWeight: 800, letterSpacing: "-0.05em", color: C.ink }}>
          <Words text="FinSight" delay={14} />
        </div>
      </div>
      <div style={{ marginTop: 26, fontSize: 40, color: C.ink2, fontWeight: 500 }}>
        <Words text="AI Credit Underwriter & Research Copilot" delay={34} stagger={3} />
      </div>
      <div style={{ display: "flex", gap: 14, marginTop: 50 }}>
        {chips.map((c, i) => {
          const s = spring({ frame: f - 60 - i * 6, fps: 60, config: { damping: 200 } });
          return (
            <div
              key={c}
              style={{
                opacity: s,
                transform: `translateY(${(1 - s) * 20}px)`,
                padding: "10px 22px",
                borderRadius: 999,
                border: "1px solid rgba(57,135,229,0.4)",
                background: "rgba(57,135,229,0.10)",
                color: C.ink,
                fontSize: 22,
                fontWeight: 500,
              }}
            >
              {c}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Input: React.FC = () => {
  const f = useCurrentFrame();
  const frames: [number, string][] = [
    [0, "home"], [48, "home-type-1"], [58, "home-type-2"], [68, "home-type-3"], [78, "home-type-4"],
    [168, "progress-8"], [196, "progress-45"], [226, "progress-80"],
  ];
  const src = frames.filter(([at]) => f >= at).at(-1)![1];
  const t = ramp(f, 100, 145);
  const press = interpolate(f, [150, 156, 164], [0, 1, 0], clamp);
  const ripple = ramp(f, 152, 180);
  const cursorOn = interpolate(f, [95, 105, 166, 172], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill>
      <Caption step="How it works · 01" title="Type any ticker." sub="FinSight pulls the latest 10-K from SEC EDGAR and starts four AI agents." />
      <Stage url={src.startsWith("progress") ? "finsight-core.vercel.app/report?t=NVDA" : "finsight-core.vercel.app"}>
        <Shot src={src} width={BW} />
        {f > 150 && f < 182 && (
          <div
            style={{
              position: "absolute",
              left: 796 - 60 * ripple - 10,
              top: 222 - 60 * ripple - 10,
              width: 20 + 120 * ripple,
              height: 20 + 120 * ripple,
              borderRadius: "50%",
              border: `3px solid ${C.accent}`,
              opacity: 1 - ripple,
            }}
          />
        )}
        <div style={{ opacity: cursorOn }}>
          <Cursor x={interpolate(t, [0, 1], [980, 790])} y={interpolate(t, [0, 1], [520, 214])} press={press} />
        </div>
      </Stage>
    </AbsoluteFill>
  );
};

type NodeSpec = { id: string; x: number; y: number; w: number; title: string; sub: string; icon: React.FC<{ size?: number; color?: string }>; at: number };
const NODES: NodeSpec[] = [
  { id: "k", x: 220, y: 640, w: 270, title: "SEC 10-K", sub: "Latest filing via EDGAR", icon: FileText, at: 8 },
  { id: "e", x: 600, y: 640, w: 320, title: "Extractor", sub: "Chunks + Pinecone RAG", icon: Database, at: 40 },
  { id: "r", x: 1010, y: 490, w: 320, title: "Risk Analyst", sub: "Audited XBRL metrics", icon: TrendingUp, at: 84 },
  { id: "m", x: 1010, y: 790, w: 320, title: "Macro Reviewer", sub: "Filing search + live news", icon: Globe, at: 84 },
  { id: "u", x: 1420, y: 640, w: 320, title: "Underwriter", sub: "Groq LLM drafts memo", icon: PenLine, at: 150 },
  { id: "o", x: 1770, y: 640, w: 250, title: "Memo", sub: "", icon: FileCheck, at: 198 },
];
const EDGES: [string, string, number][] = [["k", "e", 22], ["e", "r", 62], ["e", "m", 62], ["r", "u", 128], ["m", "u", 128], ["u", "o", 178]];
const node = (id: string) => NODES.find((n) => n.id === id)!;
const bez = (p: number[][], t: number) =>
  [0, 1].map((i) => (1 - t) ** 3 * p[0][i] + 3 * (1 - t) ** 2 * t * p[1][i] + 3 * (1 - t) * t ** 2 * p[2][i] + t ** 3 * p[3][i]);

export const Agents: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const par = useSpring(98);
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <Caption step="How it works · 02" title="Four AI agents go to work." sub="A LangGraph pipeline. Quant and macro agents run in parallel." y={80} width={1300} />
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        {EDGES.map(([a, b, at]) => {
          const A = node(a), B = node(b);
          const x0 = A.x + A.w / 2, x3 = B.x - B.w / 2, dx = x3 - x0;
          const pts = [[x0, A.y], [x0 + dx * 0.5, A.y], [x3 - dx * 0.5, B.y], [x3, B.y]];
          const d = `M${pts[0]} C${pts[1]} ${pts[2]} ${pts[3]}`;
          const p = ramp(f, at, at + 22);
          return (
            <g key={a + b}>
              <path d={d} pathLength={1} fill="none" stroke="rgba(57,135,229,0.25)" strokeWidth={10} strokeDasharray="1" strokeDashoffset={1 - p} />
              <path d={d} pathLength={1} fill="none" stroke={C.accent} strokeWidth={3} strokeDasharray="1" strokeDashoffset={1 - p} />
              {f > at + 22 &&
                [0, 1, 2].map((k) => {
                  const [x, y] = bez(pts, ((f - at - 22) / 50 + k / 3) % 1);
                  return (
                    <g key={k}>
                      <circle cx={x} cy={y} r={12} fill={C.accent} opacity={0.25} />
                      <circle cx={x} cy={y} r={5} fill="#cfe3fb" />
                    </g>
                  );
                })}
            </g>
          );
        })}
      </svg>
      <div
        style={{
          position: "absolute",
          left: 1010 - 120,
          top: 640 - 24,
          width: 240,
          height: 48,
          display: "grid",
          placeItems: "center",
          borderRadius: 999,
          border: `1px dashed ${C.accent}`,
          background: "rgba(57,135,229,0.12)",
          color: C.ink,
          fontSize: 20,
          fontWeight: 600,
          opacity: par,
          transform: `scale(${0.8 + 0.2 * par})`,
        }}
      >
        ⇅ runs in parallel
      </div>
      {NODES.map((n) => {
        const s = spring({ frame: f - n.at, fps, config: { damping: 13 } });
        const work = ramp(f, n.at + 10, n.at + 45);
        const Icon = n.icon;
        return (
          <div
            key={n.id}
            style={{
              ...glass,
              position: "absolute",
              left: n.x - n.w / 2,
              top: n.y - 60,
              width: n.w,
              height: 120,
              padding: "0 20px",
              display: "flex",
              alignItems: "center",
              gap: 16,
              opacity: Math.min(1, s * 1.5),
              transform: `scale(${0.6 + 0.4 * s})`,
              borderColor: `rgba(57,135,229,${0.15 + 0.5 * (1 - work)})`,
              boxShadow: `${glass.boxShadow}, 0 0 ${60 * (1 - work * 0.6)}px rgba(57,135,229,${0.35 * s})`,
            }}
          >
            <div style={{ width: 54, height: 54, flexShrink: 0, borderRadius: 14, display: "grid", placeItems: "center", background: "rgba(57,135,229,0.18)" }}>
              <Icon size={30} color={C.accent} />
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: C.ink, fontSize: 25, fontWeight: 700, whiteSpace: "nowrap" }}>{n.title}</div>
              {n.sub ? (
                <div style={{ color: C.muted, fontSize: 17, marginTop: 4, whiteSpace: "nowrap" }}>{n.sub}</div>
              ) : (
                <div style={{ marginTop: 8, opacity: springAt(f, 214), transform: `scale(${springAt(f, 214, 10)})`, transformOrigin: "left" }}>
                  <Badge verdict={verdicts[0].verdict} size={17} />
                </div>
              )}
            </div>
            <div style={{ position: "absolute", left: 20, right: 20, bottom: 10, height: 3, borderRadius: 2, background: "rgba(255,255,255,0.06)" }}>
              <div style={{ width: `${work * 100}%`, height: "100%", borderRadius: 2, background: C.accent }} />
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
const springAt = (f: number, at: number, damping = 200) => spring({ frame: f - at, fps: 60, config: { damping } });

const StatCard: React.FC<{ label: string; value: (p: number) => string; chip?: string; at: number; y: number }> = ({ label, value, chip, at, y }) => {
  const f = useCurrentFrame();
  const s = useSpring(at);
  const p = ramp(f, at, at + 55);
  return (
    <div
      style={{
        ...glass,
        position: "absolute",
        left: 110,
        top: y,
        width: 500,
        height: 104,
        padding: "0 26px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontFamily,
        opacity: s,
        transform: `translateX(${(1 - s) * -60}px)`,
      }}
    >
      <div>
        <div style={{ color: C.muted, fontSize: 19 }}>{label}</div>
        <div style={{ color: C.ink, fontSize: 42, fontWeight: 800, letterSpacing: "-0.03em", fontVariantNumeric: "tabular-nums" }}>{value(p)}</div>
      </div>
      {chip && (
        <div style={{ color: C.good, background: "rgba(12,163,12,0.14)", border: "1px solid rgba(12,163,12,0.4)", borderRadius: 999, padding: "6px 14px", fontSize: 19, fontWeight: 600 }}>
          {chip}
        </div>
      )}
    </div>
  );
};

export const DashboardScene: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Caption step="03 · Dashboard" title="Audited numbers. Not guesses." sub="Five years of SEC XBRL data, charts and credit ratios." y={130} />
      <StatCard at={60} y={590} label={`Revenue · FY${stats.fy}`} value={(p) => usd(stats.revenue * p)} chip={`▲ ${pct(stats.revenueYoy)}`} />
      <StatCard at={75} y={712} label={`Net income · FY${stats.fy}`} value={(p) => usd(stats.netIncome * p)} chip={`▲ ${pct(stats.netIncomeYoy)}`} />
      <StatCard at={90} y={834} label="EBITDA margin" value={(p) => pct(stats.ebitdaMargin * p)} />
      <Stage url="finsight-core.vercel.app/report?t=MSFT">
        <Shot src="dashboard-full" width={1418} y={ramp(f, 50, 280, 0, 560)} />
      </Stage>
    </AbsoluteFill>
  );
};

export const MemoScene: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <Caption step="04 · Credit memo" title="A lender-ready memo." sub="With a clear verdict. Export to PDF or Markdown in one click." y={150} />
      {verdicts.map((v, i) => {
        const s = spring({ frame: f - 110 - i * 14, fps: 60, config: { damping: 12 } });
        return (
          <div
            key={v.ticker}
            style={{
              ...glass,
              position: "absolute",
              left: 110,
              top: 610 + i * 112,
              width: 500,
              height: 92,
              padding: "0 26px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              opacity: Math.min(1, s * 1.4),
              transform: `scale(${0.7 + 0.3 * s})`,
            }}
          >
            <span style={{ color: C.ink, fontSize: 36, fontWeight: 800 }}>{v.ticker}</span>
            <Badge verdict={v.verdict} size={24} />
          </div>
        );
      })}
      <Stage url="finsight-core.vercel.app/report?t=MSFT">
        <Shot src="memo-full" width={2600} x={-20} y={ramp(f, 30, 270, 290, 1500)} />
      </Stage>
    </AbsoluteFill>
  );
};

export const CompetitorsScene: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Caption step="05 · Competitors" title="Knows the competition." sub="Threat levels for every rival, plus audited peer metrics side by side." y={240} />
      <Stage url="finsight-core.vercel.app/report?t=MSFT">
        <Shot src="competitors-full" width={1418} y={ramp(f, 50, 190, 0, 260)} />
      </Stage>
    </AbsoluteFill>
  );
};

export const CopilotScene: React.FC = () => {
  const f = useCurrentFrame();
  const s = useSpring(0);
  const reveal = f < 80 ? ramp(f, 14, 34, 0, 33) : ramp(f, 80, 175, 33, 100);
  const dots = f > 40 && f < 82;
  const chips = ["SEC 10-K", "XBRL metrics", "Credit memo"];
  return (
    <AbsoluteFill style={{ fontFamily, perspective: 2200 }}>
      <div
        style={{
          ...glass,
          position: "absolute",
          left: 190,
          top: 150,
          width: 600,
          height: 752,
          overflow: "hidden",
          padding: 0,
          opacity: s,
          transform: `translateY(${(1 - s) * 80 + Math.sin(f / 40) * 6}px) rotateY(${10 - 4 * s}deg)`,
          boxShadow: `${glass.boxShadow}, 0 0 120px rgba(57,135,229,0.2)`,
        }}
      >
        <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 0 ${100 - reveal}% 0)` }}>
          <Shot src="dashboard" width={2891} x={-2291} y={87} />
        </div>
        {dots && (
          <div style={{ position: "absolute", left: 22, top: 250, display: "flex", gap: 8 }}>
            {[0, 1, 2].map((i) => (
              <div key={i} style={{ width: 12, height: 12, borderRadius: 6, background: C.accent, opacity: 0.35 + 0.65 * Math.abs(Math.sin((f - i * 6) / 8)) }} />
            ))}
          </div>
        )}
      </div>
      <Caption step="06 · Research copilot" title="Ask follow-ups. Get grounded answers." sub="Answers come from the filing, the audited metrics and the memo, never thin air." x={900} y={250} width={880} />
      <div style={{ position: "absolute", left: 900, top: 720, display: "flex", gap: 14 }}>
        {chips.map((c, i) => {
          const k = spring({ frame: f - 60 - i * 8, fps: 60, config: { damping: 200 } });
          return (
            <div key={c} style={{ opacity: k, transform: `translateY(${(1 - k) * 20}px)`, padding: "10px 22px", borderRadius: 999, border: "1px solid rgba(57,135,229,0.4)", background: "rgba(57,135,229,0.10)", color: C.ink, fontSize: 22 }}>
              {c}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const WHY = [
  { icon: ShieldCheck, title: "Audited numbers", body: "Straight from SEC XBRL. The LLM never invents a figure." },
  { icon: FileSearch, title: "Grounded in the filing", body: "Semantic search over the full 10-K, blended with live news." },
  { icon: Workflow, title: "Parallel AI agents", body: "Four LangGraph agents take a ticker to a memo in ~2 minutes." },
  { icon: Download, title: "Ready to share", body: "Dashboard, memo and peers. Export to PDF or Markdown." },
];

export const Why: React.FC = () => {
  const f = useCurrentFrame();
  const p = ramp(f, 120, 190);
  const nums = [
    [`${Math.round(metricAccuracy * 100 * p)}%`, "metric accuracy on the golden eval set"],
    [`~${Math.max(1, Math.round(2 * p))} min`, "from ticker to credit memo"],
    [`${Math.round(5 * p)} years`, "of audited history per company"],
  ];
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <div style={{ position: "absolute", top: 110, width: "100%", textAlign: "center", fontSize: 92, fontWeight: 800, letterSpacing: "-0.04em", color: C.ink }}>
        <Words text="Why *FinSight?*" delay={2} stagger={6} />
      </div>
      <div style={{ position: "absolute", top: 320, left: 135, display: "flex", gap: 30 }}>
        {WHY.map(({ icon: Icon, title, body }, i) => {
          const s = spring({ frame: f - 22 - i * 10, fps: 60, config: { damping: 14 } });
          return (
            <div key={title} style={{ ...glass, width: 390, height: 300, padding: 34, opacity: Math.min(1, s * 1.4), transform: `translateY(${(1 - s) * 80}px)` }}>
              <div style={{ width: 66, height: 66, borderRadius: 18, display: "grid", placeItems: "center", background: "linear-gradient(145deg, #5aa2f5, #2a78d6)", boxShadow: "0 0 40px rgba(57,135,229,0.45)" }}>
                <Icon size={34} color="#fff" />
              </div>
              <div style={{ color: C.ink, fontSize: 32, fontWeight: 700, marginTop: 30 }}>{title}</div>
              <div style={{ color: C.ink2, fontSize: 22, lineHeight: 1.45, marginTop: 12 }}>{body}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", top: 740, width: "100%", display: "flex", justifyContent: "center", gap: 120 }}>
        {nums.map(([n, label], i) => {
          const s = spring({ frame: f - 110 - i * 8, fps: 60, config: { damping: 200 } });
          return (
            <div key={label} style={{ textAlign: "center", opacity: s, transform: `translateY(${(1 - s) * 30}px)` }}>
              <div style={{ fontSize: 84, fontWeight: 800, color: C.accent, letterSpacing: "-0.03em", fontVariantNumeric: "tabular-nums", textShadow: "0 0 50px rgba(57,135,229,0.5)" }}>{n}</div>
              <div style={{ fontSize: 22, color: C.ink2, marginTop: 4 }}>{label}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Cta: React.FC = () => {
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const logo = useSpring(0, 12);
  const pill = useSpring(60);
  const out = ramp(f, durationInFrames - 30, durationInFrames);
  const pulse = 0.5 + 0.5 * Math.sin(f / 12);
  return (
    <AbsoluteFill style={{ fontFamily, alignItems: "center", justifyContent: "center", textAlign: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 24, transform: `scale(${logo})` }}>
        <div style={{ width: 92, height: 92, borderRadius: 26, display: "grid", placeItems: "center", background: "linear-gradient(145deg, #5aa2f5, #2a78d6 60%, #1d5bb0)", boxShadow: "0 0 70px rgba(57,135,229,0.55)" }}>
          <Landmark size={50} color="#fff" />
        </div>
        <span style={{ fontSize: 92, fontWeight: 800, letterSpacing: "-0.05em", color: C.ink }}>FinSight</span>
      </div>
      <div style={{ marginTop: 40, width: 1700, fontSize: 60, fontWeight: 700, letterSpacing: "-0.03em", color: C.ink, lineHeight: 1.15 }}>
        <Words text="From annual report to credit memo in about *2* *minutes.*" delay={18} stagger={3} />
      </div>
      <div
        style={{
          marginTop: 56,
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "20px 40px",
          borderRadius: 999,
          background: C.accent,
          color: "#fff",
          fontSize: 34,
          fontWeight: 700,
          opacity: pill,
          transform: `translateY(${(1 - pill) * 30}px)`,
          boxShadow: `0 0 ${50 + 40 * pulse}px rgba(57,135,229,${0.4 + 0.3 * pulse})`,
        }}
      >
        finsight-core.vercel.app <ArrowRight size={32} />
      </div>
      <div style={{ marginTop: 40, fontSize: 22, color: C.muted, opacity: pill }}>
        LangGraph · Groq · Pinecone · SEC EDGAR · Next.js
      </div>
      <AbsoluteFill style={{ background: "#000", opacity: out }} />
    </AbsoluteFill>
  );
};
