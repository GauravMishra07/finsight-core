import React from "react";
import { AbsoluteFill, Img, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { Lock } from "lucide-react";

export const { fontFamily } = loadFont("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] });

// Dark tokens from finsight-web/app/globals.css
export const C = {
  bg: "#07090d",
  surface: "#141414",
  ink: "#f0efec",
  ink2: "#c3c2b7",
  muted: "#898781",
  accent: "#3987e5",
  s2: "#d95926",
  good: "#0ca30c",
  warn: "#fab219",
  crit: "#d03b3b",
};
export const glass: React.CSSProperties = {
  background: "linear-gradient(180deg, rgba(30,32,36,0.92), rgba(18,19,22,0.92))",
  border: "1px solid rgba(255,255,255,0.09)",
  borderRadius: 20,
  boxShadow: "0 30px 80px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.06)",
};

export function useSpring(delay = 0, damping = 200) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping } });
}

export const Background: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 60;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(1000px 700px at ${28 + 10 * Math.sin(t * 0.4)}% ${30 + 8 * Math.cos(t * 0.3)}%, rgba(57,135,229,0.30), transparent 70%),
            radial-gradient(900px 650px at ${78 + 8 * Math.cos(t * 0.35)}% ${78 + 6 * Math.sin(t * 0.5)}%, rgba(217,89,38,0.16), transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          backgroundPosition: `0 ${(f * 0.4) % 64}px`,
          maskImage: "radial-gradient(ellipse at center, black 25%, transparent 80%)",
        }}
      />
    </AbsoluteFill>
  );
};

export const Finish: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55))", pointerEvents: "none" }} />
      <AbsoluteFill style={{ opacity: 0.06, mixBlendMode: "overlay", pointerEvents: "none" }}>
        <svg width="100%" height="100%">
          <filter id="grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={Math.floor(f / 2)} stitchTiles="stitch" />
          </filter>
          <rect width="100%" height="100%" filter="url(#grain)" />
        </svg>
      </AbsoluteFill>
    </>
  );
};

// Words rise in one by one; *word* renders in the accent colour.
export const Words: React.FC<{ text: string; delay?: number; stagger?: number; style?: React.CSSProperties }> = ({
  text,
  delay = 0,
  stagger = 4,
  style,
}) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <span style={style}>
      {text.split(" ").map((w, i) => {
        const s = spring({ frame: f - delay - i * stagger, fps, config: { damping: 200 } });
        const hi = w.startsWith("*") && w.endsWith("*");
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity: s,
              transform: `translateY(${(1 - s) * 40}px)`,
              filter: `blur(${(1 - s) * 8}px)`,
              marginRight: "0.25em",
              ...(hi && { color: C.accent, textShadow: "0 0 40px rgba(57,135,229,0.6)" }),
            }}
          >
            {hi ? w.slice(1, -1) : w}
          </span>
        );
      })}
    </span>
  );
};

export const Caption: React.FC<{ step: string; title: string; sub: string; x?: number; y?: number; width?: number }> = ({
  step,
  title,
  sub,
  x = 110,
  y = 220,
  width = 560,
}) => {
  const s = useSpring(0);
  return (
    <div style={{ position: "absolute", left: x, top: y, width, fontFamily }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14, opacity: s, transform: `translateX(${(1 - s) * -30}px)` }}>
        <div style={{ width: 44 * s, height: 3, background: C.accent, borderRadius: 2 }} />
        <span style={{ color: C.accent, fontSize: 22, fontWeight: 700, letterSpacing: "0.18em", textTransform: "uppercase" }}>{step}</span>
      </div>
      <div style={{ fontSize: 66, lineHeight: 1.05, fontWeight: 800, color: C.ink, letterSpacing: "-0.035em", marginTop: 18 }}>
        <Words text={title} delay={4} />
      </div>
      <div style={{ fontSize: 27, lineHeight: 1.45, color: C.ink2, marginTop: 22 }}>
        <Words text={sub} delay={16} stagger={2} />
      </div>
    </div>
  );
};

export const Browser: React.FC<{ width: number; height: number; url: string; children: React.ReactNode; style?: React.CSSProperties }> = ({
  width,
  height,
  url,
  children,
  style,
}) => (
  <div
    style={{
      position: "absolute",
      width,
      height: height + 46,
      borderRadius: 18,
      overflow: "hidden",
      background: "#0d0d0d",
      border: "1px solid rgba(255,255,255,0.12)",
      boxShadow: "0 50px 140px rgba(0,0,0,0.7), 0 0 120px rgba(57,135,229,0.18)",
      fontFamily,
      ...style,
    }}
  >
    <div style={{ height: 46, background: "#171717", display: "flex", alignItems: "center", padding: "0 18px", gap: 8, borderBottom: "1px solid #262626" }}>
      {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
        <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />
      ))}
      <div
        style={{
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "#0f0f0f",
          border: "1px solid #2a2a2a",
          borderRadius: 8,
          padding: "5px 18px",
          color: C.muted,
          fontSize: 15,
        }}
      >
        <Lock size={12} /> {url}
      </div>
    </div>
    <div style={{ position: "relative", height, overflow: "hidden" }}>{children}</div>
  </div>
);

// A capture drawn at `width`, shifted by x/y in display pixels.
export const Shot: React.FC<{ src: string; width: number; x?: number; y?: number }> = ({ src, width, x = 0, y = 0 }) => (
  <Img src={staticFile(`captures/${src}.png`)} style={{ position: "absolute", left: x, top: -y, width, height: "auto", maxWidth: "none" }} />
);

export const Cursor: React.FC<{ x: number; y: number; press: number }> = ({ x, y, press }) => (
  <svg
    width={34}
    height={34}
    viewBox="0 0 24 24"
    style={{ position: "absolute", left: x, top: y, transform: `scale(${1 - press * 0.18})`, transformOrigin: "0 0", filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.6))" }}
  >
    <path d="M4 2 L4 20 L9 15 L12.5 22 L15.5 20.5 L12 13.5 L19 13.5 Z" fill="#fff" stroke="#000" strokeWidth={1.2} strokeLinejoin="round" />
  </svg>
);

export const Badge: React.FC<{ verdict: string; size?: number }> = ({ verdict, size = 22 }) => {
  const col = verdict === "Approve" ? C.good : verdict === "Decline" ? C.crit : C.warn;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: `${size * 0.3}px ${size * 0.75}px`,
        borderRadius: 999,
        border: `2px solid ${col}`,
        background: `${col}22`,
        color: col,
        fontSize: size,
        fontWeight: 700,
        boxShadow: `0 0 30px ${col}44`,
      }}
    >
      {verdict === "Approve" ? "✓" : verdict === "Decline" ? "✕" : "?"} {verdict}
    </span>
  );
};
