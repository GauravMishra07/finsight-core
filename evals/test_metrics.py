# evals/test_metrics.py — offline checks for evals/metrics.py. Run: python -m evals.test_metrics
from evals.metrics import (first_hit_rank, headings_present, metric_accuracy, numeric_grounding,
                           verdict_from_memo, verdict_stability)

METRICS = {
    "Revenue": {"value": "$245,122,000,000", "history": [{"fy": "2024", "end": "", "val": 211915000000},
                                                         {"fy": "2025", "end": "", "val": 245122000000}]},
    "Net Income": {"value": "$88,136,000,000", "history": [{"fy": "2025", "end": "", "val": 88136000000}]},
    "Total Liabilities": {"value": "$70,541,000,000", "history": []},  # filing-page fallback shape
    "Market Cap": {"value": "N/A", "history": []},
}


def test_numeric_grounding():
    assert numeric_grounding("Revenue was $245,122,000,000.", METRICS, []) == (1.0, [])
    assert numeric_grounding("Revenue of $245.1 billion and liabilities of $70.5B.", METRICS, [])[0] == 1.0
    assert numeric_grounding("Net margin 36.0%, revenue grew 15.7%.", METRICS, [])[0] == 1.0  # ratio + YoY
    assert numeric_grounding("Fined $2 billion.", METRICS, ["regulators fined it $2 billion"])[0] == 1.0
    assert numeric_grounding("Up 15.7% over two years.", {"Revenue": {"history": [
        {"val": 100}, {"val": 110}, {"val": 115.7}]}}, [])[0] == 1.0  # non-consecutive years
    score, bad = numeric_grounding("Revenue $245.1B but debt $9.9B.", METRICS, [])
    assert score == 0.5 and bad == ["$9.9B"]
    assert numeric_grounding("Revenue was $246.0 billion.", METRICS, [])[0] == 0.0  # outside rounding
    assert numeric_grounding("No figures here.", METRICS, []) == (None, [])


def test_metric_accuracy():
    assert metric_accuracy(METRICS, {"Revenue": 245122000000, "Total Liabilities": 70541000000}) == (1.0, [])
    assert metric_accuracy(METRICS, {"Revenue": 1, "EBITDA": 5}) == (0.0, ["Revenue", "EBITDA"])


def test_verdict_and_headings():
    memo = ("# Credit Underwriting Memo: X\n## Executive Summary\n## Quantitative Financial Health\n"
            "## Macroeconomic & Sector Headwinds\n"
            "## Final Underwriting Recommendation (Approve, Review, or Decline with justification)\n"
            "**Decline** due to leverage. We may review later.")
    assert verdict_from_memo(memo) == "Decline"
    assert verdict_from_memo("## Final Underwriting Recommendation\nRecommendation: **Approved**") == "Approve"
    assert verdict_from_memo("no section") is None
    assert headings_present(memo) == 1.0
    assert headings_present("## Executive Summary") == 0.25
    numbered = "## 1. Executive Summary\n## 4. Final Underwriting Recommendation\n**Approve**"
    assert headings_present(numbered) == 0.5
    assert verdict_from_memo(numbered) == "Approve"
    assert verdict_stability(["Approve", "Approve", "Review"]) == 2 / 3


def test_first_hit_rank():
    chunks = ["noise", "We  operate as two\nreportable segments: auto", "more"]
    assert first_hit_rank(chunks, "we operate as two reportable segments") == 2
    assert first_hit_rank(chunks, "absent phrase") is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("evals metrics: all checks passed")
