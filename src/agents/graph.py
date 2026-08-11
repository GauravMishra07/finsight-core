# src/agents/graph.py
from langgraph.graph import StateGraph, END
from src.agents.state import AgentState
from src.agents.extractor import extractor_node
from src.agents.risk_analyst import risk_analyst_node
from src.agents.macro_reviewer import macro_reviewer_node
from src.agents.underwriter import underwriter_node
from config.logger import setup_logger

logger = setup_logger(__name__)

def build_finsight_graph():
    """
    Constructs and compiles the FinSight multi-agent workflow graph.
    
    Flow:
    [Start] -> Extractor -> Risk Analyst -> Macro Reviewer -> Underwriter -> [END]
    """
    logger.info("Initializing FinSight multi-agent StateGraph...")
    
    # 1. Initialize StateGraph with our custom AgentState schema
    workflow = StateGraph(AgentState)
    
    # 2. Register Nodes (Agents)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("risk_analyst", risk_analyst_node)
    workflow.add_node("macro_reviewer", macro_reviewer_node)
    workflow.add_node("underwriter", underwriter_node)
    
    # 3. Define Entry Point
    workflow.set_entry_point("extractor")
    
    # 4. Define Linear Edges
    # Data flows strictly sequentially down the processing pipeline
    workflow.add_edge("extractor", "risk_analyst")
    workflow.add_edge("risk_analyst", "macro_reviewer")
    workflow.add_edge("macro_reviewer", "underwriter")
    workflow.add_edge("underwriter", END)
    
    logger.info("Graph edges connected. Compiling state network...")
    
    # 5. Compile Graph
    app = workflow.compile()
    
    logger.info("FinSight multi-agent network successfully compiled.")
    return app

# Expose a ready-to-run compiled graph instance
finsight_graph = build_finsight_graph()