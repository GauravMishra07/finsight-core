# src/agents/state.py
from typing import TypedDict, Annotated, Dict, Any, Optional, List
import operator

class AgentState(TypedDict):
    tenant_id: str
    ticker: str
    
    raw_filing_text: Optional[str]
    filing_chunks_indexed: bool
    
    financial_metrics: Dict[str, Any]
    risk_analysis: Optional[str]
    
    macro_analysis: Optional[str]
    competitor_analysis: Optional[str] # NEW: Stores competitor intel
    competitors: Optional[List[Dict[str, Any]]]  # structured peers; listed ones carry XBRL history
    upcoming_projects: Optional[str] # NEW: Stores future initiatives
    evidence: Optional[List[str]]  # macro reviewer's SEC excerpts + news, for evals; never sent to the UI

    
    final_memo: Optional[str]
    errors: Annotated[List[str], operator.add]