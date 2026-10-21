# 🏦 FinSight: AI Credit Underwriter & Copilot

FinSight is an enterprise-grade, multi-agent AI system designed to automate commercial credit underwriting and financial analysis. It ingests live government data (SEC 10-K filings), extracts audited financial metrics, performs semantic vector searches, fetches real-time market news, and synthesizes a professional credit memo. 

The application features a decoupled architecture with a **FastAPI** backend powering a LangGraph state machine, and a **Next.js** frontend (`finsight-web/`) with charts, memo export and a research copilot.

---

## ✨ Key Features
* **100% Accurate Financials:** Bypasses LLM hallucination for numbers by parsing exact, audited XBRL data directly from the SEC.
* **Semantic RAG Search:** Cleans and chunks SEC HTML filings, embedding them into a Pinecone vector database for deep textual retrieval (e.g., finding R&D pipelines and strategic initiatives).
* **Real-Time Web Search:** Injects DuckDuckGo search results into the analysis to contrast historical 10-K data with today's breaking news.
* **Conversational Copilot:** Ask targeted follow-up questions about the company. The chat assistant is grounded in the vector database and the audited XBRL metrics.
* **Decoupled Architecture:** Frontend and backend run as independent services, containerized via Docker for cloud deployment.

---

## 🧠 The Multi-Agent Workflow (LangGraph)

FinSight operates using a directed acyclic graph (DAG) of specialized AI agents. When a stock ticker is submitted, the workflow executes the following pipeline:

### 1. 📥 Extractor Agent (Data Ingestion & RAG Prep)
* Connects to the SEC EDGAR database using `edgartools`.
* Downloads the latest 10-K annual report.
* Strips messy HTML/XBRL tags into clean plain text using `BeautifulSoup`.
* Chunks the text and generates dense embeddings (`all-MiniLM-L6-v2`) via HuggingFace.
* Safely batches and upserts the vectors into a dedicated **Pinecone** namespace for multi-tenant security.

### 2. 📊 Quantitative Agent (Risk Analyst)
* **How it works:** Instead of forcing the LLM to read broken tables, this agent uses Python to extract exact XBRL accounting nodes (Revenue, Net Income, Assets, Liabilities, Equity) directly from the SEC data.
* **Output:** Generates a 100% accurate quantitative profile and uses Groq (Llama 3) to write a brief summary of the leverage and profitability ratios.

### 3. 🌍 Qualitative Agent (Macro Reviewer)
* **How it works:** Performs targeted RAG searches against the Pinecone database to find specific qualitative data (upcoming projects, R&D, strategic initiatives). 
* **Real-Time Injection:** Simultaneously triggers a `DuckDuckGo` web search to pull the top 5 real-time news articles about the company.
* **Output:** Merges the historical SEC strategy with today's news to output a comprehensive analysis of market headwinds, regulatory risks, and competitors.

### 4. ✍️ Underwriter Agent (Synthesis)
* **How it works:** Gathers the outputs from the Quantitative and Qualitative agents.
* **Output:** Drafts the final, professional Credit Underwriting Memo based on all accumulated state data.

---

## 🛠️ Tech Stack

**Backend & AI Pipeline:**
* **Graph Orchestration:** [LangGraph](https://python.langchain.com/docs/langgraph)
* **API Layer:** [FastAPI](https://fastapi.tiangolo.com/) & Uvicorn
* **LLM Engine:** [Groq](https://groq.com/) (openai/gpt-oss-120b)
* **Vector Database:** [Pinecone](https://www.pinecone.io/) (Serverless)
* **Embeddings:** HuggingFace (`sentence-transformers`)
* **Financial Data Engine:** SEC `edgartools`
* **Real-Time Search:** `duckduckgo-search`

**Frontend:**
* **UI Framework:** [Next.js](https://nextjs.org/) (static export) + Tailwind CSS
* **Charts:** Recharts
* **Hosting:** Vercel (frontend), Render (backend)

**DevOps:**
* **Containerization:** Docker & Docker Compose

---

## 📂 Project Structure

```text
finsight-core/
├── api.py                  # FastAPI Backend application
├── config/
│   ├── logger.py           # Standardized application logging
│   └── settings.py         # Centralized .env configuration
├── src/
│   ├── agents/
│   │   ├── extractor.py    # Ingestion & Vectorization logic
│   │   ├── graph.py        # LangGraph workflow definition
│   │   ├── macro_reviewer.py # RAG & DuckDuckGo qualitative analysis
│   │   ├── risk_analyst.py # XBRL quantitative extraction
│   │   ├── state.py        # Shared agent state schema
│   │   └── underwriter.py  # Final memo synthesis
│   └── rag/
│       ├── chunker.py      # HTML cleaning and text splitting
│       ├── embedder.py     # Local HuggingFace embedding model
│       └── vector_store.py # Pinecone connection and batch upserting
├── Dockerfile.api          # Backend container build instructions
├── finsight-web/           # Next.js frontend (deployed to Vercel)
├── docker-compose.yml      # Local backend container
├── requirements.txt        # Python dependencies
└── .env                    # Secret API keys (DO NOT COMMIT)


## RUN BACKEND uvicorn api:app --reload --port 8000  
## RUN FRONTEND: cd finsight-web && npm install && npm run dev        