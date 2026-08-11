# src/agents/underwriter.py
from src.agents.state import AgentState
from config.settings import settings
from config.logger import setup_logger
from groq import Groq
import json

logger = setup_logger(__name__)
client = Groq(api_key=settings.groq_api_key)

def underwriter_node(state: AgentState) -> dict:
    """
    Node 4: Underwriter Agent
    Synthesizes the financial metrics, risk analysis, and macro analysis into a final Credit Memo.
    """
    ticker = state.get("ticker")
    errors = state.get("errors", [])
    
    logger.info(f"[Underwriter Agent] Initiating final synthesis for {ticker}...")
    
    # 1. Validation: Ensure downstream data exists
    if errors:
        logger.warning(f"[Underwriter Agent] Upstream errors detected: {errors}")
        # We can choose to proceed with warnings or halt. We'll proceed but note it.

    metrics = state.get("financial_metrics", {})
    risk_analysis = state.get("risk_analysis", "Not available.")
    macro_analysis = state.get("macro_analysis", "Not available.")
    
    if not metrics and risk_analysis == "Not available." and macro_analysis == "Not available.":
        error_msg = f"Underwriter Failed: Insufficient data to synthesize memo for {ticker}."
        logger.error(error_msg)
        return {"errors": [error_msg]}

    # 2. Construct the Synthesis Prompt
    prompt = f"""
    You are the Lead Credit Officer for an enterprise commercial bank.
    Your analysts have provided you with reports on {ticker}. You need to synthesize these into a final Credit Underwriting Memo.

    Inputs from your team:
    ---
    1. Financial Metrics:
    {json.dumps(metrics, indent=2)}

    2. Internal Risk Analysis:
    {risk_analysis}

    3. Macro & Sector Analysis:
    {macro_analysis}
    ---

    Task: Write a highly professional, definitive Credit Underwriting Memo.
    Format your response strictly in Markdown using the following structure:
    # Credit Underwriting Memo: {ticker}
    ## Executive Summary
    ## Quantitative Financial Health
    ## Macroeconomic & Sector Headwinds
    ## Final Underwriting Recommendation (Approve, Review, or Decline with justification)

    Maintain a serious, objective, and analytical tone.
    """

    try:
        logger.info(f"[Underwriter Agent] Drafting final Credit Memo via Groq (Model: {settings.default_model})...")
        
        # Temperature is low for a factual, authoritative tone
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a Lead Credit Officer writing Markdown memos."},
                {"role": "user", "content": prompt}
            ],
            model=settings.default_model,
            temperature=0.2 
        )
        
        final_memo = response.choices[0].message.content
        logger.info(f"[Underwriter Agent] Successfully generated Credit Memo for {ticker}.")
        
        # Return the final deliverable to the state
        return {
            "final_memo": final_memo
        }
        
    except Exception as e:
        error_msg = f"Underwriter Failed during Groq inference: {str(e)}"
        logger.error(error_msg)
        return {"errors": [error_msg]}