# app.py
import streamlit as st
import requests

# URL of our new FastAPI Backend
API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="FinSight | AI Credit Underwriter", page_icon="🏦", layout="wide")
st.title("🏦 FinSight: AI Credit Underwriter & Copilot")

AVAILABLE_STOCKS = {
    "MSFT": "Microsoft", "AAPL": "Apple", "NVDA": "Nvidia", "TSLA": "Tesla",
    "JPM": "JPMorgan Chase", "HDB": "HDFC Bank", "INFY": "Infosys"
}

with st.sidebar:
    st.header("⚙️ Configuration")
    selected_option = st.selectbox("Select Target Company:", [f"{k} - {v}" for k, v in AVAILABLE_STOCKS.items()])
    ticker = selected_option.split(" - ")[0]
    generate_btn = st.button("🚀 Generate Credit Memo", type="primary", use_container_width=True)

# State Management
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "final_state" not in st.session_state:
    st.session_state.final_state = {}
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "current_ticker" not in st.session_state:
    st.session_state.current_ticker = ""

# --- CALL THE GENERATE API ---
if generate_btn:
    if st.session_state.current_ticker != ticker:
        st.session_state.chat_messages = []
        st.session_state.current_ticker = ticker

    with st.status(f"Sending Request to Backend API for {ticker}...", expanded=True) as status:
        try:
            # Making an HTTP POST request to our FastAPI backend
            response = requests.post(f"{API_BASE_URL}/analyze", json={"ticker": ticker})
            response.raise_for_status()
            
            st.session_state.final_state = response.json()
            st.session_state.analysis_done = True
            status.update(label="API Request Complete!", state="complete", expanded=False)
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to backend API: {e}")
            status.update(label="API Request Failed!", state="error")

# --- UI RENDERING ---
if st.session_state.analysis_done:
    state = st.session_state.final_state
    tab1, tab2 = st.tabs(["📄 Underwriting Memo & Metrics", "💬 Interactive SEC Assistant"])
    
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Audited Financial Metrics")
            for key, data in state.get("financial_metrics", {}).items():
                value = data.get("value", "N/A") if isinstance(data, dict) else data
                st.metric(label=key, value=value)
                
            st.divider()
            st.subheader("Market Competitors")
            st.info(state.get("competitor_analysis", "N/A"))
            st.subheader("Upcoming Projects & R&D")
            st.success(state.get("upcoming_projects", "N/A"))

        with col2:
            st.subheader("Final Credit Underwriting Memo")
            with st.container(border=True):
                st.markdown(state.get("final_memo", "No memo generated."))

    with tab2:
        chat_container = st.container(height=500)
        with chat_container:
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if user_query := st.chat_input("Ask a follow-up question..."):
            st.session_state.chat_messages.append({"role": "user", "content": user_query})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(user_query)
                with st.chat_message("assistant"):
                    with st.spinner("Asking API..."):
                        # --- CALL THE CHAT API ---
                        payload = {
                            "ticker": ticker,
                            "tenant_id": state.get("tenant_id"),
                            "user_query": user_query,
                            "chat_history": st.session_state.chat_messages[:-1], # Everything except the current query
                            "memo_text": state.get("final_memo", ""),
                            "financial_metrics": state.get("financial_metrics", {})
                        }
                        chat_res = requests.post(f"{API_BASE_URL}/chat", json=payload)
                        if chat_res.status_code == 200:
                            answer = chat_res.json().get("answer")
                            st.markdown(answer)
                            st.session_state.chat_messages.append({"role": "assistant", "content": answer})
                        else:
                            st.error("API Error")
            st.rerun()