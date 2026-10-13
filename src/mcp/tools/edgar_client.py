
# src/mcp/tools/edgar_client.py
import gc
from edgar import set_identity, Company, find
import polars as pl
from typing import Optional
from config.logger import setup_logger

logger = setup_logger(__name__)

class EdgarDataClient:
    """
    Enterprise client for streaming live SEC EDGAR regulatory data.
    """
    def __init__(self, identity: str = "FinSight Agentic RAG (admin@finsight.local)"):
        """
        Initializes the SEC EDGAR client.
        The SEC strictly requires a declared identity (Name + Email) to prevent rate-limiting.
        """
        try:
            set_identity(identity)
            logger.info(f"Initialized SEC EDGAR client with identity: {identity}")
        except Exception as e:
            logger.error(f"Failed to set EDGAR identity: {str(e)}")
            raise

    def resolve_company(self, identifier: str) -> Company:
        """
        Resolves a ticker, CIK, or company name to a valid SEC Company object.
        """
        clean_identifier = identifier.strip()
        
        # 1. First attempt: Direct lookup by ticker or CIK
        try:
            company = Company(clean_identifier.upper())
            if company and company.name:
                return company
        except Exception:
            pass

        # 2. Fallback: Search SEC registry by company name
        try:
            search_results = find(clean_identifier)
            if search_results and len(search_results) > 0:
                return search_results[0]
        except Exception as e:
            logger.error(f"Error during fallback SEC search for '{clean_identifier}': {e}")

        raise ValueError(f"No SEC registered company found for '{clean_identifier}'.")

    def fetch_latest_10k_text(self, ticker_or_name: str) -> Optional[str]:
        """
        Streams the most recent annual 10-K filing for a given ticker or company name.
        """
        try:
            logger.info(f"Resolving SEC entity for input: {ticker_or_name}")
            company = self.resolve_company(ticker_or_name)
            logger.info(f"Resolved to company: {company.name}")
            
            # Retrieve the filing history filtered by 10-K
            filings = company.get_filings(form="10-K")
            
            if not filings:
                logger.warning(f"No 10-K filings found for {company.name}")
                return None
            
            # Grab the absolute latest filing
            latest_10k = filings[0]
            
            # Stream the plain text parsing
            text_content = latest_10k.text()
            original_len = len(text_content)
            
            # --- MEMORY OPTIMIZATION FOR RENDER FREE TIER ---
            # Cap plain text characters to ~350,000 (~55,000 words)
            MAX_CHARS = 480_000
            if original_len > MAX_CHARS:
                text_content = text_content[:MAX_CHARS]
                logger.info(f"Truncated filing from {original_len} to {MAX_CHARS} characters to prevent OOM.")
            else:
                logger.info(f"Successfully retrieved 10-K ({original_len} characters).")
                
            # Immediately force garbage collection to free unused DOM/Regex memory
            gc.collect()
            
            return text_content
            
        except Exception as e:
            logger.error(f"Failed to fetch 10-K for {ticker_or_name}: {str(e)}")
            return None


    def get_latest_10k_filing(self, ticker_or_name: str):
        """Cheap call: returns (company, filing) without downloading the document body."""
        company = self.resolve_company(ticker_or_name)
        filings = company.get_filings(form="10-K")
        if not filings:
            return company, None
        return company, filings[0]

    def get_filing_text(self, filing) -> Optional[str]:
        """Expensive call: download + parse. Your existing truncation logic goes here."""
        try:
            text_content = filing.text()
            original_len = len(text_content)
            MAX_CHARS = 480_000
            if original_len > MAX_CHARS:
                text_content = text_content[:MAX_CHARS]
                logger.info(f"Truncated filing from {original_len} to {MAX_CHARS} characters.")
            else:
                logger.info(f"Successfully retrieved 10-K ({original_len} characters).")
            gc.collect()
            return text_content
        except Exception as e:
            logger.error(f"Failed to parse filing: {e}")
            return None

# Singleton instance to be injected into the MCP server
edgar_client = EdgarDataClient()