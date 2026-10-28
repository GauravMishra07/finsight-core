// Captures 2x stills of the local FinSight frontend (npm run dev in finsight-web/) for the promo.
// Reports come from the cached pipeline runs in evals/.cache, so no backend or API quota is used.
import { chromium } from "playwright";
import { readFileSync, mkdirSync } from "node:fs";

const APP = "http://localhost:3000";
const OUT = "public/captures";
mkdirSync(OUT, { recursive: true });

const reports = ["MSFT", "KO", "TSLA"].map((t, i) => {
  const { evidence, ...r } = JSON.parse(readFileSync(`../evals/.cache/${t}.json`, "utf8"));
  return { ...r, savedAt: Date.now() - i * 3600_000 };
});
const chat = [
  { role: "user", content: "How leveraged is Microsoft, and should that worry a lender?" },
  {
    role: "assistant",
    content:
      "Not much. Per the FY2026 10-K XBRL data, total liabilities are **$316.0B** against stockholders' equity of **$442.4B**, a debt-to-equity of about **0.71x**, down from 1.19x in FY2022.\n\n" +
      "| Metric | FY2022 | FY2026 |\n|---|---|---|\n| Total liabilities | $198.3B | $316.0B |\n| Equity | $166.5B | $442.4B |\n| EBITDA | $96.0B | $189.5B |\n\n" +
      "EBITDA of $189.5B covers liabilities well, so leverage is a low credit risk. The memo's **Approve** recommendation reflects this.",
  },
];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, colorScheme: "dark" });
await ctx.addInitScript(
  ([reports, chat]) => {
    localStorage.setItem("finsight:theme", "dark");
    localStorage.setItem("finsight:reports", JSON.stringify(reports));
    localStorage.setItem("finsight:chat:MSFT", JSON.stringify(chat));
    // Hide the Next.js dev badge in the shots.
    addEventListener("DOMContentLoaded", () =>
      document.head.append(Object.assign(document.createElement("style"), { textContent: "nextjs-portal{display:none!important}" })),
    );
  },
  [reports, chat],
);
// Backend stand-in: healthy, analyze never answers (keeps the progress screen up), anything else is logged.
await ctx.route("http://localhost:8000/**", (route) => {
  const url = route.request().url();
  if (url.endsWith("/health")) return route.fulfill({ json: { status: "ok" } });
  if (url.includes("/analyze")) return; // left pending on purpose
  console.warn("unexpected backend call:", url);
  return route.abort();
});

const page = await ctx.newPage();
const shot = (name, opts = {}) => page.screenshot({ path: `${OUT}/${name}.png`, ...opts });
const settle = () => page.waitForTimeout(1500);
// fullPage screenshots resize the page, which restarts the chart animations; grow the viewport and let them finish first.
async function fullShot(pg, name) {
  const h = await pg.evaluate(() => document.documentElement.scrollHeight);
  await pg.setViewportSize({ width: 1920, height: h });
  await pg.waitForTimeout(2500);
  await pg.screenshot({ path: `${OUT}/${name}-full.png` });
  await pg.setViewportSize({ width: 1920, height: 1080 });
  await pg.waitForTimeout(2500);
}

// Home + typing frames
await page.goto(APP);
await page.waitForLoadState("networkidle");
await settle();
await shot("home");
const input = page.getByPlaceholder(/Ticker or company/);
for (const [i, ch] of [..."MSFT"].entries()) {
  await input.press(ch);
  await page.waitForTimeout(200);
  await shot(`home-type-${i + 1}`);
}

// Progress screen, fast-forwarding the stage timer
await page.clock.install();
await page.goto(`${APP}/report?t=NVDA`);
await page.waitForSelector("text=Analysing NVDA");
let elapsed = 0;
for (const s of [8, 45, 80]) {
  await page.clock.runFor((s - elapsed) * 1000);
  elapsed = s;
  await page.waitForTimeout(300);
  await shot(`progress-${s}`);
}
await page.close();

// Report workspace for MSFT (fresh page: real clock for recharts animations)
const p = await ctx.newPage();
await p.goto(`${APP}/report?t=MSFT`);
await p.waitForSelector("text=Credit ratios");
await p.waitForTimeout(2500); // recharts entry animations
await p.screenshot({ path: `${OUT}/dashboard.png` });
await fullShot(p, "dashboard");
for (const [tab, name] of [["Memo", "memo"], ["Competitors", "competitors"], ["Macro & risk", "macro"]]) {
  await p.getByRole("tab", { name: tab }).click();
  await p.waitForTimeout(2000);
  await p.screenshot({ path: `${OUT}/${name}.png` });
  await fullShot(p, name);
}
await browser.close();
console.log("done");
