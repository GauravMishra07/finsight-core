# src/mcp/tools/edgar_client.py
import os
import gc
import re
import time
from typing import Optional

from edgar import set_identity, Company, find
from config.logger import setup_logger

logger = setup_logger(__name__)

MAX_CHARS = 480_000      # cap to protect Render's 512 MB
MIN_CHARS = 50_000       # real 10-Ks are far larger; rejects partial amendments


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)


class EdgarDataClient:
    """Client for SEC EDGAR filing lookups and text extraction."""

    def __init__(self, identity: Optional[str] = None):
        """
        SEC requires a declared identity (Name + real email).
        Set EDGAR_IDENTITY in your .env and on Render.
        """
        identity = identity or os.environ.get(
            "EDGAR_IDENTITY", "FinSight Agentic RAG (admin@finsight.local)"
        )
        try:
            set_identity(identity)
            logger.info(f"Initialized SEC EDGAR client with identity: {identity}")
        except Exception as e:
            logger.error(f"Failed to set EDGAR identity: {e}")
            raise

    def resolve_company(self, identifier: str) -> Company:
        clean = identifier.strip()
        try:
            company = Company(clean.upper())
            if company and company.name:
                return company
        except Exception:
            pass

        try:
            results = find(clean)
            if results and len(results) > 0:
                return results[0]
        except Exception as e:
            logger.error(f"Error during fallback SEC search for '{clean}': {e}")

        raise ValueError(f"No SEC registered company found for '{clean}'.")

    def get_latest_10k_filing(self, ticker_or_name: str):
        """
        Cheap call: returns (company, filing) without downloading the document.
        Prefers original 10-K filings; falls back to a 10-K/A only if no original exists.
        """
        company = self.resolve_company(ticker_or_name)
        logger.info(f"Resolved to company: {company.name}")

        filings = None
        try:
            filings = company.get_filings(form="10-K", amendments=False)
        except TypeError:
            # Older edgartools without the amendments argument
            all_filings = company.get_filings(form="10-K")
            originals = [f for f in all_filings if getattr(f, "form", "") == "10-K"]
            if originals:
                return company, originals[0]
            filings = all_filings

        if filings and len(filings) > 0:
            return company, filings[0]

        # Last resort: amendments (e.g. a company whose only annual filing is a 10-K/A)
        amended = company.get_filings(form="10-K/A")
        if amended and len(amended) > 0:
            logger.warning(f"No original 10-K for {company.name}; using latest 10-K/A.")
            return company, amended[0]

        logger.warning(f"No 10-K filings found for {company.name}")
        return company, None

    def _text_from_attachments(self, filing) -> Optional[str]:
        """Bypass edgartools' primary-document lookup by picking the main .htm ourselves."""
        docs = [
            a for a in filing.attachments
            if str(getattr(a, "document", "")).lower().endswith((".htm", ".html"))
            and not re.match(r"(?i)^(r\d+|ex)", str(getattr(a, "document", "")))
        ]
        main = next(
            (a for a in docs if str(getattr(a, "document_type", "")).startswith("10-K")),
            None,
        )
        if main is None and docs:
            main = docs[0]
        if main is None:
            return None

        raw = main.download() if hasattr(main, "download") else getattr(main, "content", None)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "ignore")
        return _strip_html(raw)

    def get_filing_text(self, filing) -> Optional[str]:
        """Expensive call: download + parse. Returns capped plain text or None."""
        strategies = [
            ("text", lambda: filing.text()),
            ("attachments", lambda: self._text_from_attachments(filing)),
        ]

        for attempt in range(2):
            for name, getter in strategies:
                try:
                    text = getter()
                except Exception as e:
                    logger.warning(f"Filing parse via '{name}' failed (attempt {attempt + 1}): {e}")
                    continue

                if not text or len(text) < MIN_CHARS:
                    if text:
                        logger.warning(f"'{name}' returned only {len(text)} chars; too short, skipping.")
                    continue

                if len(text) > MAX_CHARS:
                    logger.info(f"Truncated filing from {len(text)} to {MAX_CHARS} characters.")
                    text = text[:MAX_CHARS]
                else:
                    logger.info(f"Retrieved 10-K via '{name}' ({len(text)} characters).")
                gc.collect()
                return text
            time.sleep(2)  # brief pause before retrying, in case of throttling

        return None

    def fetch_latest_10k_text(self, ticker_or_name: str) -> Optional[str]:
        """Backward-compatible wrapper for any code still calling the old method."""
        try:
            _, filing = self.get_latest_10k_filing(ticker_or_name)
            return self.get_filing_text(filing) if filing else None
        except Exception:
            logger.exception(f"Failed to fetch 10-K for {ticker_or_name}")
            return None


edgar_client = EdgarDataClient()