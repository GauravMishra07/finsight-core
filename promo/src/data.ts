// Every number on screen comes from the cached pipeline runs and the app's own finance helpers.
import msft from "../../evals/.cache/MSFT.json";
import ko from "../../evals/.cache/KO.json";
import tsla from "../../evals/.cache/TSLA.json";
import memoEval from "../../evals/.cache/report-memo.json";
import { latest, trend, verdictFromMemo, yoy, type Metrics } from "../../finsight-web/lib/finance";

const m = msft.financial_metrics as Metrics;
const t = trend(m);

export const stats = {
  revenue: latest(m.Revenue)!,
  revenueYoy: yoy(m.Revenue.history)!,
  netIncome: latest(m["Net Income"])!,
  netIncomeYoy: yoy(m["Net Income"].history)!,
  ebitdaMargin: t[t.length - 1].ebitdaMargin!,
  fy: m.Revenue.history!.at(-1)!.fy,
};

export const verdicts = [msft, ko, tsla].map((r) => ({ ticker: r.ticker, verdict: verdictFromMemo(r.final_memo)! }));

const acc = memoEval.map((r) => r.scores.metric_accuracy).filter((x): x is number => typeof x === "number");
export const metricAccuracy = acc.reduce((a, b) => a + b, 0) / acc.length;
