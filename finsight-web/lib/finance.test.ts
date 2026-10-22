// Run: node --test lib/finance.test.ts   (Node >= 22.18 strips the types)
import { test } from "node:test";
import assert from "node:assert/strict";
import { byYear, cagr, latest, parseMoney, peerRow, ratios, trend, verdictFromMemo, yoy, type Metrics } from "./finance.ts";

test("parseMoney handles Python's formats", () => {
  assert.equal(parseMoney("$1,234"), 1234);
  assert.equal(parseMoney("$-5,000"), -5000);
  assert.equal(parseMoney("N/A"), null);
  assert.equal(parseMoney(""), null);
});

test("latest prefers history, falls back to the formatted value", () => {
  assert.equal(latest({ value: "$9", source: "", history: [{ fy: "2024", end: "", val: 7 }] }), 7);
  assert.equal(latest({ value: "$9", source: "", history: [] }), 9);
});

test("yoy uses the absolute previous value so a smaller loss reads as improvement", () => {
  const h = (a: number, b: number) => [{ fy: "1", end: "", val: a }, { fy: "2", end: "", val: b }];
  assert.equal(yoy(h(100, 110)), 0.1);
  assert.equal(yoy(h(-100, -50)), 0.5);
  assert.equal(yoy(h(0, 5)), null);
});

test("byYear merges series on fiscal year", () => {
  const m: Metrics = {
    Revenue: { value: "", source: "", history: [{ fy: "2023", end: "", val: 1 }, { fy: "2024", end: "", val: 2 }] },
    "Net Income": { value: "", source: "", history: [{ fy: "2024", end: "", val: 3 }] },
  };
  assert.deepEqual(byYear(m, ["Revenue", "Net Income"]), [{ fy: "2023", Revenue: 1 }, { fy: "2024", Revenue: 2, "Net Income": 3 }]);
});

test("ratios skip negative equity and band leverage", () => {
  const v = (n: number) => ({ value: `$${n}`, source: "" });
  const r = ratios({ Revenue: v(100), "Net Income": v(20), "Total Assets": v(300), "Total Liabilities": v(200), "Stockholders Equity": v(100) });
  assert.equal(r[0].value, 2);
  assert.equal(r[0].band, "Moderate leverage");
  assert.equal(r[1].level, "good");
  const neg = ratios({ "Total Liabilities": v(200), "Stockholders Equity": { value: "$-10", source: "" } });
  assert.equal(neg[0].value, null);
});

test("verdict ignores the heading's option list", () => {
  const memo = "# Memo\n## Final Underwriting Recommendation (Approve, Review, or Decline with justification)\n**Decline** due to leverage. We may review later.";
  assert.equal(verdictFromMemo(memo), "Decline");
  assert.equal(verdictFromMemo("## Final Underwriting Recommendation\nRecommendation: **Approved**"), "Approve");
  assert.equal(verdictFromMemo("no section"), null);
});

const pts = (...v: [string, number][]) => v.map(([fy, val]) => ({ fy, end: "", val }));

test("cagr compounds over fiscal years and refuses sign changes", () => {
  assert.equal(cagr(pts(["2020", 100], ["2022", 121]))?.toFixed(4), "0.1000");
  assert.equal(cagr(pts(["2020", -100], ["2022", 121])), null);
  assert.equal(cagr(pts(["2020", 100])), null);
});

test("trend derives per-year ratios and growth; liabilities fall back to assets − equity", () => {
  const m: Metrics = {
    Revenue: { value: "", source: "", history: pts(["2023", 100], ["2024", 125]) },
    "Net Income": { value: "", source: "", history: pts(["2023", 10], ["2024", 25]) },
    "Total Assets": { value: "", source: "", history: pts(["2024", 200]) },
    "Stockholders Equity": { value: "", source: "", history: pts(["2024", 50]) },
  };
  const [a, b] = trend(m);
  assert.equal(a.growth, null);
  assert.equal(b.growth, 0.25);
  assert.equal(b.margin, 0.2);
  assert.equal(b.de, 3); // (200 − 50) / 50
  const p = peerRow("X", "X", m);
  assert.equal(p.fy, "2024");
  assert.equal(p.de, 3);
});

test("EBITDA margin per year and in peer rows; market cap reads the live value", () => {
  const m: Metrics = {
    Revenue: { value: "", source: "", history: pts(["2023", 100], ["2024", 200]) },
    EBITDA: { value: "", source: "", history: pts(["2024", 50]) },
    "Market Cap": { value: "$1,000", source: "", history: [], as_of: "2026-10-23" },
  };
  const [a, b] = trend(m);
  assert.equal(a.ebitdaMargin, null);
  assert.equal(b.ebitdaMargin, 0.25);
  const p = peerRow("X", "X", m);
  assert.equal(p.ebitda, 50);
  assert.equal(p.ebitdaMargin, 0.25);
  assert.equal(p.mcap, 1000);
  assert.equal(peerRow("Y", "Y", {}).mcap, null); // old cached reports have neither field
});
