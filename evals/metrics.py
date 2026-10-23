# evals/metrics.py
"""Deterministic (no LLM) metrics for FinSight outputs."""
import re
from itertools import combinations, permutations

# Must match the headings the underwriter prompt asks for (src/agents/underwriter.py).
HEADINGS = ["Executive Summary", "Quantitative Financial Health",
            "Macroeconomic & Sector Headwinds", "Final Underwriting Recommendation"]

SCALE = {"trillion": 1e12, "tn": 1e12, "t": 1e12, "billion": 1e9, "bn": 1e9, "b": 1e9,
         "million": 1e6, "mm": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}
_DOLLAR = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(trillion|billion|million|thousand|tn|bn|mm|[tbmk])?\b", re.I)
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s?(?:%|percent\b)", re.I)


def _num(raw: str, unit: str | None) -> tuple[float, float]:
    """(value, tolerance): tolerance is half a unit of the last digit written, so '$331.8 billion' matches 331,839M."""
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    scale = SCALE[unit.lower()] if unit else 1
    return float(raw.replace(",", "")) * scale, 0.5 * 10 ** -decimals * scale


def dollar_amounts(text: str) -> list[tuple[str, float, float]]:
    return [(m.group(0), *_num(m.group(1), m.group(2))) for m in _DOLLAR.finditer(text or "")]


def percents(text: str) -> list[tuple[str, float, float]]:
    return [(m.group(0), *_num(m.group(1), None)) for m in _PCT.finditer(text or "")]


def _metric_values(financial_metrics: dict) -> dict[str, list[float]]:
    """label -> values oldest first. Falls back to the formatted value ('$1,234') when there's no history."""
    out = {}
    for label, m in (financial_metrics or {}).items():
        vals = [p["val"] for p in m.get("history") or []]
        if not vals and m.get("value", "N/A") != "N/A":
            vals = [float(m["value"].replace("$", "").replace(",", ""))]
        if vals:
            out[label] = vals
    return out


def numeric_grounding(memo: str, financial_metrics: dict, contexts: list[str]) -> tuple[float | None, list[str]]:
    """Share of $ and % figures in the memo found in the metrics, ratios/YoY derived from them, or the upstream texts.
    Returns (score, ungrounded figures); score is None when the memo has no figures."""
    series = _metric_values(financial_metrics)
    dollars = [v for vals in series.values() for v in vals]
    latest = [vals[-1] for vals in series.values()]
    pcts = [a / b * 100 for a, b in permutations(latest, 2) if b]
    pcts += [(b / a - 1) * 100 for vals in series.values() for a, b in combinations(vals, 2) if a]  # any-year growth
    for c in contexts:
        dollars += [v for _, v, _ in dollar_amounts(c)]
        pcts += [v for _, v, _ in percents(c)]

    def grounded(x, tol, pool):
        return any(abs(x - abs(v)) <= tol for v in pool)  # memo writes "fell 3%", sources may say -3

    found = [(raw, grounded(x, tol, dollars)) for raw, x, tol in dollar_amounts(memo)]
    found += [(raw, grounded(x, tol, pcts)) for raw, x, tol in percents(memo)]
    if not found:
        return None, []
    return sum(ok for _, ok in found) / len(found), [raw for raw, ok in found if not ok]


def metric_accuracy(financial_metrics: dict, golden: dict) -> tuple[float, list[str]]:
    """Share of golden metrics whose latest extracted value is within 0.5%. Returns (score, wrong labels)."""
    series = _metric_values(financial_metrics)
    wrong = [k for k, v in golden.items() if k not in series or abs(series[k][-1] - v) > 0.005 * abs(v)]
    return 1 - len(wrong) / len(golden), wrong


def headings_present(memo: str) -> float:
    # Numbered headings ("## 4. Final ...") count, as in the frontend's verdict parser.
    return sum(bool(re.search(rf"^#+\s*(\d+\.\s*)?{re.escape(h)}", memo or "", re.I | re.M))
               for h in HEADINGS) / len(HEADINGS)


def verdict_from_memo(memo: str | None) -> str | None:
    """Python port of verdictFromMemo in finsight-web/lib/finance.ts; keep the two in sync."""
    if not memo:
        return None
    m = re.search(r"#+\s*(\d+\.\s*)?Final Underwriting Recommendation", memo, re.I)
    if not m:
        return None
    body = "\n".join(memo[m.start():].split("\n")[1:])  # skip the heading, which lists all three options
    hit = re.search(r"\b(approve|approved|approval|decline|declined|review)\b", body, re.I)
    if not hit:
        return None
    w = hit.group(1).lower()
    return "Approve" if w.startswith("appro") else "Decline" if w.startswith("decl") else "Review"


def verdict_stability(verdicts: list[str | None]) -> float:
    """Share of runs that agree with the most common verdict."""
    return max(verdicts.count(v) for v in set(verdicts)) / len(verdicts)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).lower()


def first_hit_rank(chunks: list[str], evidence: str) -> int | None:
    """1-based rank of the first retrieved chunk containing the evidence phrase (whitespace/case-insensitive)."""
    e = _norm(evidence)
    return next((i for i, c in enumerate(chunks, 1) if e in _norm(c)), None)
