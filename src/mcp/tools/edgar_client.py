# src/mcp/tools/edgar_client.py
from edgar import set_identity, Company
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

    def fetch_latest_10k_text(self, ticker: str) -> Optional[str]:
        """
        Streams the most recent annual 10-K filing for a given ticker.
        """
        try:
            logger.info(f"Requesting latest 10-K filing for ticker: {ticker.upper()}")
            company = Company(ticker)
            
            # Retrieve the filing history filtered by 10-K
            filings = company.get_filings(form="10-K")
            
            if not filings:
                logger.warning(f"No 10-K filings found for {ticker.upper()}")
                return None
            
            # Grab the absolute latest filing
            latest_10k = filings[0]
            
            # Stream the raw text parsing
            text_content = latest_10k.text()
            logger.info(f"Successfully retrieved 10-K for {ticker.upper()} ({len(text_content)} characters)")
            
            return text_content
            
        except Exception as e:
            logger.error(f"Failed to fetch 10-K for {ticker}: {str(e)}")
            return None

# Singleton instance to be injected into the MCP server
edgar_client = EdgarDataClient()