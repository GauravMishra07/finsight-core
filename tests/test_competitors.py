# tests/test_competitors.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents import macro_reviewer as mr


def test_competitors_normalises_llm_output():
    real, mr.peer_metrics = mr.peer_metrics, lambda t: ("WALT DISNEY CO", {"Revenue": {"history": [1]}}) if t == "DIS" else None
    try:
        _check()
    finally:
        mr.peer_metrics = real


def _check():
    rows = mr._competitors([
        {"name": "Walt Disney", "ticker": " dis ", "threat": "high", "overlap": "Streaming", "note": "Disney+."},
        {"name": "Private Co", "ticker": None, "threat": "weird", "note": "x"},
        "Just a string",
        {"bad": 1},
    ])
    assert [r["name"] for r in rows] == ["Walt Disney", "Private Co", "Just a string"]
    assert rows[0]["ticker"] == "DIS" and rows[0]["threat"] == "High" and rows[0]["sec_name"] == "WALT DISNEY CO"
    assert rows[1]["threat"] is None and "metrics" not in rows[1]
    assert mr._competitors("not a list") == []


def test_competitor_text_is_markdown_bullets():
    text = mr._competitor_text([{"name": "A", "ticker": "AA", "threat": "Low", "overlap": "Ads", "note": "n"}])
    assert text == "- **A** (AA) — Low threat — Ads: n"
    assert mr._competitor_text([]) == "No competitor data found."


if __name__ == "__main__":
    test_competitors_normalises_llm_output()
    test_competitor_text_is_markdown_bullets()
    print("ok")
