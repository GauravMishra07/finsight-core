"""Pre-generates reports for the home-page preset tickers so they open instantly on the static frontend,
even while the Render backend is asleep. Re-run after a new 10-K season, then commit and push.

Usage (from the repo root): .venv/Scripts/python -m scripts.build_samples [TICKER ...]
Hits SEC, Pinecone and Groq like a normal /analyze call. A ticker that fails keeps its previous sample.
"""
import json
import sys
import time
from pathlib import Path

from fastapi import HTTPException

from api import AnalyzeRequest, generate_memo

PRESETS = ["MSFT", "AAPL", "NVDA", "TSLA", "NFLX", "ADBE"]  # keep in sync with PRESETS in finsight-web/app/page.tsx
OUT = Path(__file__).resolve().parents[1] / "finsight-web" / "public" / "samples"


def main(tickers: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    failed = []
    for t in tickers:
        start = time.time()
        try:
            report = generate_memo(AnalyzeRequest(ticker=t))
        except HTTPException as e:
            print(f"{t}: FAILED ({e.detail})")
            failed.append(t)
            continue
        report.update(ticker=t, sample=True, savedAt=int(time.time() * 1000))
        (OUT / f"{t}.json").write_text(json.dumps(report, default=str), encoding="utf-8")
        print(f"{t}: ok in {time.time() - start:.0f}s, errors={report.get('errors')}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main([t.upper() for t in sys.argv[1:]] or PRESETS))
