import React from "react";
import { AbsoluteFill, Audio, Sequence, getStaticFiles, interpolate, staticFile } from "remotion";
import { TransitionSeries, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { Background, Finish } from "./ui";
import { Agents, CompetitorsScene, CopilotScene, Cta, DashboardScene, Hook, Input, Logo, MemoScene, Why } from "./scenes";
import voice from "./voice.json"; // written by audio.py, one line per scene

const FPS = 60;
const T = 24; // transition overlap
const LEAD = 12; // voice starts this many frames into its scene
// Minimum frames per scene for its animation; scenes stretch to fit their voice line.
const BASE: [React.FC, number][] = [
  [Hook, 200], [Logo, 170], [Input, 260], [Agents, 300], [DashboardScene, 270],
  [MemoScene, 250], [CompetitorsScene, 200], [CopilotScene, 230], [Why, 230], [Cta, 210],
];
const SCENES = BASE.map(([Scene, min], i) => {
  const v = voice.find((l) => l.scene === i);
  // The line must finish before the next scene's line starts (next start = this end - T + LEAD).
  return { Scene, d: Math.max(min, v ? Math.ceil(v.seconds * FPS) + LEAD + T : 0), v };
});
const STARTS = SCENES.map((_, i) => SCENES.slice(0, i).reduce((a, s) => a + s.d - T, 0));
export const TOTAL = SCENES.reduce((a, s) => a + s.d, 0) - T * (SCENES.length - 1);

const timing = springTiming({ config: { damping: 200 }, durationInFrames: T });
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const WINDOWS = SCENES.flatMap((s, i) => (s.v ? [[STARTS[i] + LEAD, STARTS[i] + LEAD + s.v.seconds * FPS]] : []));
// Music sits at 0.45 and ducks to 0.16 under the voice, with 15-frame ramps.
const musicVolume = (f: number) => {
  const free = Math.min(1, ...WINDOWS.map(([a, b]) => (f < a ? (a - f) / 15 : f > b ? (f - b) / 15 : 0)));
  return (0.16 + 0.29 * free) * interpolate(f, [0, 45, TOTAL - 75, TOTAL], [0, 1, 1, 0], clamp);
};
const hasMusic = getStaticFiles().some((f) => f.name === "music.wav");

export const Promo: React.FC = () => (
  <AbsoluteFill>
    <Background />
    <TransitionSeries>
      {SCENES.flatMap(({ Scene, d }, i) => [
        ...(i ? [<TransitionSeries.Transition key={`t${i}`} timing={timing} presentation={i % 3 === 2 ? slide({ direction: "from-right" }) : fade()} />] : []),
        <TransitionSeries.Sequence key={i} durationInFrames={d}>
          <Scene />
        </TransitionSeries.Sequence>,
      ])}
    </TransitionSeries>
    <Finish />
    {hasMusic && <Audio src={staticFile("music.wav")} volume={musicVolume} />}
    {SCENES.map(({ v }, i) =>
      v ? (
        <Sequence key={v.file} from={STARTS[i] + LEAD} durationInFrames={Math.ceil(v.seconds * FPS) + 2}>
          <Audio src={staticFile(v.file)} />
        </Sequence>
      ) : null,
    )}
  </AbsoluteFill>
);
