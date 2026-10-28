import React from "react";
import { Composition } from "remotion";
import { Promo, TOTAL } from "./Promo";

export const Root: React.FC = () => (
  <Composition id="FinSightPromo" component={Promo} durationInFrames={TOTAL} fps={60} width={1920} height={1080} />
);
