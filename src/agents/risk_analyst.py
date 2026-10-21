# src/agents/risk_analyst.py
import os
import json
import gc
from datetime import date

import requests

from src.agents.state import AgentState
from src.mcp.tools.edgar_client import edgar_client
from config.settings import settings
from config.logger import setup_logger
from groq import Groq
import re
from bs4 import BeautifulSoup
from edgar import Company

logger = setup_logger(__name__)
client = Groq(api_key=settings.groq_api_key)

IDENTITY = os.environ.get("EDGAR_IDENTITY", "FinSight Agentic RAG (admin@finsight.local)")

# Each metric tries several tags, because companies tag the same thing differently.
# (label, source, [tags in priority order], is_flow)
METRICS = [
    ("Revenue", "SEC XBRL Income Statement",
     ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
      "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"], True),
    ("Net Income", "SEC XBRL Income Statement", ["NetIncomeLoss", "ProfitLoss"], True),
    ("Total Assets", "SEC XBRL Balance Sheet", ["Assets"], False),
    ("Total Liabilities", "SEC XBRL Balance Sheet", ["Liabilities"], False),
    ("Stockholders Equity", "SEC XBRL Balance Sheet",
     ["StockholdersEquity",
      "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], False),
]

_session = requests.Session()
_cache: dict = {}  # cik -> metrics_dict (in memory, tiny)


HISTORY_YEARS = 5


def _annual_series(rows: list, is_flow: bool) -> list:
    """Last HISTORY_YEARS annual values, oldest first: [{"fy", "end", "val"}].
    One row per period end; restatements resolve to the latest filing."""
    by_end = {}
    for x in rows:
        if x.get("form") not in ("10-K", "10-K/A") or x.get("fp") != "FY":
            continue
        if is_flow:  # keep only ~12-month periods, not stray quarters
            try:
                days = (date.fromisoformat(x["end"]) - date.fromisoformat(x["start"])).days
            except Exception:
                continue
            if not 350 <= days <= 380:
                continue
        prev = by_end.get(x["end"])
        if prev is None or x.get("filed", "") >= prev.get("filed", ""):
            by_end[x["end"]] = x
    ends = sorted(by_end)[-HISTORY_YEARS:]
    return [{"fy": e[:4], "end": e, "val": by_end[e]["val"]} for e in ends]


def _fetch_concept(cik: int, tag: str, is_flow: bool) -> list:
    """Annual (10-K, full-year) USD series for one tag. Response is a few KB."""
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{int(cik):010d}/us-gaap/{tag}.json"
    r = _session.get(url, headers={"User-Agent": IDENTITY}, timeout=20)
    if r.status_code != 200:
        return []
    rows = r.json().get("units", {}).get("USD", [])
    if not isinstance(rows, list) or not rows:
       logger.warning(f"SEC XBRL {tag}: empty payload for CIK {cik}")
       return []
    return _annual_series(rows, is_flow)


def _fmt(v):
    return f"${v:,.0f}" if v is not None else "N/A"

def _sec_get(url: str) -> str:
    r = _session.get(url, headers={"User-Agent": IDENTITY}, timeout=20)
    r.raise_for_status()
    return r.text


def _parse_num(s: str):
    s = s.replace("$", "").replace(",", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").strip()
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def _statement_rows(url: str) -> dict:
    """{label_lower: first numeric value, scaled to dollars} for one statement page."""
    soup = BeautifulSoup(_sec_get(url), "html.parser")
    head = soup.get_text(" ", strip=True)[:500].lower()
    scale = 1_000_000 if "in millions" in head else 1_000 if "in thousands" in head else 1
    rows = {}
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        label = cells[0].lower().strip()
        for c in cells[1:]:
            v = _parse_num(c)
            if v is not None:
                rows.setdefault(label, v * scale)
                break
    return rows


def _pick(rows: dict, patterns: list):
    for pat in patterns:
        for label, v in rows.items():
            if re.match(pat, label):
                return v
    return None


def _metrics_from_filing_pages(ticker: str) -> dict:
    company, filing = edgar_client.get_latest_10k_filing(ticker)
    base = (f"https://www.sec.gov/Archives/edgar/data/{int(company.cik)}/"
            f"{filing.accession_no.replace('-', '')}/")

    summary = BeautifulSoup(_sec_get(base + "FilingSummary.xml"), "html.parser")
    pages = {}
    for rep in summary.find_all("report"):
        name_tag, file_tag = rep.find("shortname"), rep.find("htmlfilename")
        if not name_tag or not file_tag:
            continue
        name = name_tag.get_text().lower()
        if "parenthetical" in name or "comprehensive" in name:
            continue
        url = base + file_tag.get_text(strip=True)
        if re.search(r"balance sheet|financial position|financial condition", name):
            pages.setdefault("bs", url)
        elif re.search(r"statements? of (income|operations|earnings)|income statements?", name):
            pages.setdefault("is", url)

    bs = _statement_rows(pages["bs"]) if "bs" in pages else {}
    inc = _statement_rows(pages["is"]) if "is" in pages else {}

    revenue = _pick(inc, [r"^net (operating )?revenues?", r"^(total )?revenues?",
                          r"^(total )?net sales"])
    net_income = _pick(inc, [r"^net (income|earnings) attributable to (?!non)",
                             r"^(consolidated )?net (income|earnings)"])
    assets = _pick(bs, [r"^total assets"])
    liabilities = _pick(bs, [r"^total liabilities$"])
    equity = _pick(bs, [r"^total (shareowners|shareholders|stockholders)['’]? equity",
                        r"^equity attributable to (shareowners|shareholders|stockholders)",
                        r"^total equity"])
    total_equity = _pick(bs, [r"^total equity",
                              r"^total (shareowners|shareholders|stockholders)['’]? equity"])

    src_is, src_bs = "SEC filing income statement", "SEC filing balance sheet"
    if liabilities is None and assets is not None and total_equity is not None:
        liabilities = assets - total_equity
        src_liab = src_bs + " (derived: assets - total equity)"
    else:
        src_liab = src_bs

    return {
        "Revenue": {"value": _fmt(revenue), "source": src_is, "history": []},
        "Net Income": {"value": _fmt(net_income), "source": src_is, "history": []},
        "Total Assets": {"value": _fmt(assets), "source": src_bs, "history": []},
        "Total Liabilities": {"value": _fmt(liabilities), "source": src_liab, "history": []},
        "Stockholders Equity": {"value": _fmt(equity), "source": src_bs, "history": []},
    }

def _get_metrics(ticker: str) -> dict:
    cik = int(edgar_client.resolve_company(ticker).cik)
    if cik in _cache:
        return _cache[cik]

    out = _xbrl_metrics(cik)

    # Fallback: SEC concept API returned nothing (e.g. KO), so read the filing's statement pages
    if all(m["value"] == "N/A" for m in out.values()):
        logger.warning(f"SEC concept API returned no data for {ticker}; using filing statement pages.")
        try:
            out = _metrics_from_filing_pages(ticker)
        except Exception:
            logger.exception("Filing-page fallback failed")

    if any(m["value"] != "N/A" for m in out.values()):
        _cache[cik] = out
    return out


def peer_metrics(ticker: str):
    """(SEC name, XBRL metrics) for a competitor, or None. No filing-page fallback (too heavy per peer).
    Exact ticker lookup only: the fuzzy name search can return the wrong company."""
    try:
        company = Company(ticker.strip().upper())
        cik = int(company.cik)
    except Exception:
        return None
    m = _cache.get(cik) or _xbrl_metrics(cik)
    return (company.name, m) if any(v["history"] for v in m.values()) else None


def _xbrl_metrics(cik: int) -> dict:
    out = {}
    for label, source, tags, is_flow in METRICS:
        series = []
        for tag in tags:
            try:
                series = _fetch_concept(cik, tag, is_flow)
            except Exception as e:
                logger.warning(f"XBRL fetch failed for {tag}: {e}")
            if series:
                break
        val = series[-1]["val"] if series else None
        out[label] = {"value": _fmt(val), "source": source, "history": series}
    return out


def risk_analyst_node(state: AgentState) -> dict:
    """Node 2: Quantitative Agent. Lightweight XBRL lookups, no RAG."""
    ticker = state.get("ticker")
    logger.info(f"[Quantitative Agent] Fetching audited XBRL financials for {ticker}...")
    gc.collect()  # release leftovers from the extractor before continuing

    metrics_dict = {}
    try:
        metrics_dict = _get_metrics(ticker)
        if all(m["value"] == "N/A" for m in metrics_dict.values()):
            logger.warning("No structured XBRL financials found.")
    except Exception:
        logger.exception("Failed to fetch XBRL financials")

    prompt = f"""
    You are an expert commercial credit underwriter.
    Review these exact audited financial metrics for {ticker}:
    {json.dumps(metrics_dict, indent=2)}

    Write a concise, 2-paragraph analysis of their financial health, leverage, and profitability based ONLY on these numbers.
    Return a single JSON object (not an array) in this format: {{"analysis": "your summary here"}}
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a financial API returning valid JSON."},
                {"role": "user", "content": prompt},
            ],
            model=settings.default_model,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = json.loads(response.choices[0].message.content)
        if isinstance(raw, list):
            raw = next((x for x in raw if isinstance(x, dict)), {})
        analysis = raw.get("analysis") if isinstance(raw, dict) else None
        if isinstance(analysis, (list, dict)):
            analysis = json.dumps(analysis, indent=2)

        return {
            "financial_metrics": metrics_dict,
            "risk_analysis": analysis or "No analysis provided.",
        }
    except Exception as e:
        logger.exception("Quant Agent failed")
        return {"errors": [f"Quant Agent Failed: {e}"]}