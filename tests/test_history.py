# tests/test_history.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.risk_analyst import _annual_series


def _row(end, val, filed, start=None, form="10-K", fp="FY"):
    return {"start": start or f"{int(end[:4]) - 1}{end[4:]}", "end": end, "val": val,
            "filed": filed, "form": form, "fp": fp}


def test_annual_series_filters_dedupes_and_caps():
    rows = [_row(f"{y}-06-30", y, f"{y}-08-01") for y in range(2015, 2024)]
    rows.append(_row("2023-06-30", 999, "2024-08-01"))                       # restated in a later 10-K
    rows.append(_row("2023-03-31", 5, "2023-05-01", start="2023-01-01"))     # stray quarter
    rows.append(_row("2022-12-31", 7, "2023-02-01", form="10-Q", fp="Q2"))   # not annual

    s = _annual_series(rows, is_flow=True)

    assert [x["fy"] for x in s] == ["2019", "2020", "2021", "2022", "2023"]
    assert s[-1]["val"] == 999


def test_balance_sheet_ignores_period_length():
    rows = [{"end": "2023-12-31", "val": 10, "filed": "2024-02-01", "form": "10-K", "fp": "FY"}]
    assert _annual_series(rows, is_flow=False) == [{"fy": "2023", "end": "2023-12-31", "val": 10}]
