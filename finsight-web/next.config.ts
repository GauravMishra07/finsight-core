import type { NextConfig } from "next";

// Static export: no Node server at runtime, so the free tier has nothing to run out of memory.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
