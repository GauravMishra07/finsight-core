# src/agents/risk_analyst.py
from src.agents.state import AgentState
from config.settings import settings
from config.logger import setup_logger
from edgar import Company
from groq import Groq
import json

logger = setup_logger(__name__)
client = Groq(api_key=settings.groq_api_key)

def risk_analyst_node(state: AgentState) -> dict:
    """
    Node 2: Quantitative Agent
    Bypasses RAG entirely for numbers. Uses XBRL parsing for 100% accurate financial metrics.
    """
    ticker = state.get("ticker")
    logger.info(f"[Quantitative Agent] Fetching audited XBRL financials for {ticker}...")
    
    metrics_dict = {}
    
    try:
        # 1. Fetch exact numbers directly from SEC XBRL data
        company = Company(ticker)
        financials = company.get_financials()
        
        if financials:
            metrics_dict = {
                "Revenue": {"value": f"${financials.get_revenue():,.0f}" if financials.get_revenue() else "N/A", "source": "SEC XBRL Income Statement"},
                "Net Income": {"value": f"${financials.get_net_income():,.0f}" if financials.get_net_income() else "N/A", "source": "SEC XBRL Income Statement"},
                "Total Assets": {"value": f"${financials.get_total_assets():,.0f}" if financials.get_total_assets() else "N/A", "source": "SEC XBRL Balance Sheet"},
                "Total Liabilities": {"value": f"${financials.get_total_liabilities():,.0f}" if financials.get_total_liabilities() else "N/A", "source": "SEC XBRL Balance Sheet"},
                "Stockholders Equity": {"value": f"${financials.get_stockholders_equity():,.0f}" if financials.get_stockholders_equity() else "N/A", "source": "SEC XBRL Balance Sheet"}
            }
        else:
            logger.warning("No structured XBRL financials found.")
            
    except Exception as e:
        logger.error(f"Failed to parse XBRL financials: {str(e)}")

    # 2. Use Groq ONLY to write a brief summary of the exact numbers we just pulled
    prompt = f"""
    You are an expert commercial credit underwriter. 
    Review these exact audited financial metrics for {ticker}:
    {json.dumps(metrics_dict, indent=2)}
    
    Write a concise, 2-paragraph analysis of their financial health, leverage, and profitability based ONLY on these numbers.
    Format response strictly as JSON: {{"analysis": "your summary here"}}
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a financial API returning valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model=settings.default_model,
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        result_json = json.loads(response.choices[0].message.content)
        
        return {
            "financial_metrics": metrics_dict,
            "risk_analysis": result_json.get("analysis", "No analysis provided.")
        }
    except Exception as e:
        return {"errors": [f"Quant Agent Failed: {str(e)}"]}