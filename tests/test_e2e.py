# tests/test_e2e.py
import sys
import os
import json

# Ensure Python can find the src directory when running from the root folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.graph import finsight_graph
from config.logger import setup_logger

logger = setup_logger("E2E_Test")

def run_test(ticker: str):
    """
    Executes the FinSight pipeline for a given ticker.
    """
    logger.info(f"=== STARTING END-TO-END TEST FOR {ticker.upper()} ===")
    
    # Define the initial state injected into the LangGraph network
    initial_state = {
        "tenant_id": "tenant_test_9921",
        "ticker": ticker.upper(),
        "raw_filing_text": None,
        "filing_chunks_indexed": False,
        "financial_metrics": {},
        "risk_analysis": None,
        "macro_analysis": None,
        "final_memo": None,
        "errors": []
    }
    
    # Execute the compiled graph
    try:
        # .invoke() runs the graph synchronously from start to END
        final_state = finsight_graph.invoke(initial_state)
        
        logger.info("=== PIPELINE EXECUTION COMPLETE ===")
        
        # Check for pipeline errors
        if final_state.get("errors"):
            logger.error(f"Pipeline encountered errors: {final_state['errors']}")
            return

        # Print the outputs for verification
        print("\n" + "="*50)
        print("1. EXTRACTED METRICS (JSON):")
        print("="*50)
        print(json.dumps(final_state.get("financial_metrics"), indent=2))
        
        print("\n" + "="*50)
        print(f"2. FINAL CREDIT MEMO ({ticker}):")
        print("="*50)
        print(final_state.get("final_memo"))
        
    except Exception as e:
        logger.error(f"Test failed with exception: {str(e)}")

if __name__ == "__main__":
    # Test with Microsoft (MSFT). You can change this to AAPL, TSLA, NVDA, etc.
    run_test("MSFT")