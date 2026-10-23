# 🏦 FinSight: AI Credit Underwriter & Copilot

FinSight is a multi-agent AI system that automates commercial credit underwriting and financial analysis. It reads a company's latest SEC 10-K, extracts audited XBRL financials, searches the filing semantically, pulls real-time news, and drafts a professional credit memo in about 2 minutes.

The application has a decoupled architecture: a **FastAPI** backend running a LangGraph pipeline, and a **Next.js** frontend (`finsight-web/`) with a financial dashboard, competitor comparison, memo export and a research copilot.

---

## ✨ Key Features
* **Audited Financials, Not Guesses:** Numbers come straight from the SEC's XBRL data (last 5 fiscal years), never from the LLM.
* **Semantic RAG Search:** Cleans and chunks the 10-K, embeds it with Pinecone hosted inference, and retrieves the passages that matter (projects, R&D, strategy, risks).
* **Real-Time News:** DuckDuckGo news and web results are blended in to contrast the filing with today's headlines.
* **Competitor Benchmarking:** Identifies peers with a threat level, and pulls audited SEC metrics for up to 4 listed competitors.
* **Conversational Copilot:** Ask follow-up questions; answers are grounded in the filing and the audited metrics.
* **Resilient LLM Calls:** If Groq rate-limits the primary model (HTTP 429), requests silently fall back to another model, so users never see the error.
* **Decoupled Architecture:** Frontend and backend deploy independently (Vercel + Render); the backend is containerized with Docker.

---

## 🧠 The Multi-Agent Workflow (LangGraph)

When a ticker is submitted, the graph runs:

```text
extractor → (risk_analyst ∥ macro_reviewer) → underwriter
```

The quantitative and qualitative agents run **in parallel**, then the underwriter combines their results.

### 1. 📥 Extractor Agent (Data Ingestion & RAG Prep)
* Resolves the company and its latest 10-K from SEC EDGAR using `edgartools`.
* Strips HTML into clean text with `BeautifulSoup` and splits it into chunks.
* Embeds the chunks with Pinecone hosted inference (`multilingual-e5-large`, 1024-dim), so no ML model runs on the server.
* Upserts in batches into a per-filing **Pinecone** namespace (`{TICKER}__{accession}`). Already-indexed filings are reused, not re-embedded.

### 2. 📊 Quantitative Agent (Risk Analyst)
* **How it works:** Calls the SEC `companyconcept` XBRL API for exact accounting values (Revenue, Net Income, Assets, Liabilities, Equity and more) with a 5-year history. Falls back to the filing's statement pages if needed.
* **Output:** A precise quantitative profile, plus an LLM-written summary of leverage and profitability.

### 3. 🌍 Qualitative Agent (Macro Reviewer)
* **How it works:** Runs targeted RAG searches against Pinecone for projects, R&D and strategic initiatives, and pulls live news via `ddgs` (DuckDuckGo).
* **Output:** Macro and sector headwinds, upcoming projects, and a structured competitor list (threat level, overlap, notes), with SEC metrics for the top listed peers.

### 4. ✍️ Underwriter Agent (Synthesis)
* **How it works:** Gathers the outputs of the quantitative and qualitative agents.
* **Output:** The final Markdown credit memo, ending in an Approve / Review / Decline recommendation.

---

## 🛠️ Tech Stack

**Backend & AI Pipeline:**
* **Graph Orchestration:** [LangGraph](https://langchain-ai.github.io/langgraph/)
* **API Layer:** [FastAPI](https://fastapi.tiangolo.com/) & Uvicorn
* **LLM Engine:** [Groq](https://groq.com/): `openai/gpt-oss-120b`, falling back to `qwen/qwen3.8-27b` then `openai/gpt-oss-20b` on rate limits
* **Vector Database:** [Pinecone](https://www.pinecone.io/) (Serverless)
* **Embeddings:** Pinecone hosted inference (`multilingual-e5-large`)
* **Financial Data Engine:** SEC `edgartools` + SEC XBRL API
* **Real-Time Search:** `ddgs` (DuckDuckGo)

**Frontend:**
* **UI Framework:** [Next.js 15](https://nextjs.org/) (static export) + Tailwind CSS v4
* **Charts:** Recharts
* **Features:** KPI dashboard, 5-year trend charts, ratio panel, competitor comparison, copilot chat, export to Markdown / PDF, light and dark themes
* **Hosting:** Vercel (frontend), Render (backend)

**DevOps:**
* **Containerization:** Docker & Docker Compose

---

## 📂 Project Structure

```text
finsight-core/
├── api.py                    # FastAPI app: /health, /api/v1/analyze, /api/v1/chat
├── config/
│   ├── llm.py                # Groq chat helper with rate-limit model fallback
│   ├── logger.py             # Standardized application logging
│   └── settings.py           # Centralized .env configuration
├── src/
│   ├── agents/
│   │   ├── extractor.py      # 10-K ingestion & vectorization
│   │   ├── graph.py          # LangGraph workflow definition
│   │   ├── macro_reviewer.py # RAG, news & competitor analysis
│   │   ├── risk_analyst.py   # XBRL quantitative extraction
│   │   ├── state.py          # Shared agent state schema
│   │   └── underwriter.py    # Final memo synthesis
│   ├── mcp/tools/
│   │   └── edgar_client.py   # SEC EDGAR client
│   └── rag/
│       ├── chunker.py        # HTML cleaning and text splitting
│       ├── embedder.py       # Pinecone hosted embeddings
│       └── vector_store.py   # Pinecone connection and batch upserting
├── tests/                    # Backend tests (offline + live e2e)
├── finsight-web/             # Next.js frontend (deployed to Vercel)
├── Dockerfile.api            # Backend container build instructions
├── docker-compose.yml        # Local backend container
├── requirements.txt          # Python dependencies
└── .env                      # Secret API keys (DO NOT COMMIT)
```

---

## 🔑 Environment Variables

Backend (`.env` at the repo root; set the same keys on Render):
`GROQ_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` (default `finsight-enterprise`), `DEFAULT_MODEL` (default `openai/gpt-oss-120b`), `EDGAR_IDENTITY` ("Name email", required by the SEC), `ALLOWED_ORIGINS` (comma-separated frontend origins).

Frontend (`finsight-web/.env.local`, or the Vercel dashboard):
`NEXT_PUBLIC_API_BASE_URL` (e.g. `http://localhost:8000/api/v1`). It is baked in at build time, so redeploy after changing it.

---

## 🚀 Run Locally

```bash
# Backend (from the repo root, using the venv at .venv\Scripts\python.exe)
uvicorn api:app --reload --port 8000

# Frontend
cd finsight-web && npm install && npm run dev   # http://localhost:3000
```

## 🧪 Tests

```bash
.venv/Scripts/python -m pytest tests/test_history.py   # offline (pip install pytest)
.venv/Scripts/python tests/test_competitors.py   # offline
python tests/test_e2e.py                         # live: hits SEC, Pinecone, Groq
cd finsight-web && node --test lib/finance.test.ts
```

## 📏 Evals (RAGAS + LangSmith)

`evals/` scores the three outputs users see against a hand-checked golden set (`evals/golden.json`: MSFT, KO, TSLA; 10 questions each, numbers verified against SEC XBRL, text answers tied to a verbatim 10-K phrase).

| Suite | Metrics |
|---|---|
| `memo` | numeric grounding, metric accuracy, headings, verdict parsed/stability (deterministic); memo / risk / macro faithfulness, verdict justified, gaps acknowledged (RAGAS judge) |
| `chat` | faithfulness, answer relevancy, factual correctness; refusal on unanswerable questions |
| `retrieval` | hit@3/6/10/15, MRR (deterministic); context precision, context recall (RAGAS judge) |

```bash
.venv/Scripts/python -m pip install -r evals/requirements-eval.txt
.venv/Scripts/python -m evals.test_metrics                       # offline checks
.venv/Scripts/python -m evals.run_evals --suite all              # full run
.venv/Scripts/python -m evals.run_evals --suite retrieval --no-judge   # deterministic only, fastest
```

Flags: `--tickers MSFT,KO`, `--repeats 3` (re-runs the underwriter for verdict stability), `--fresh` (re-run the pipeline instead of using `evals/.cache/`), `--no-judge`, `--no-upload`.
Judge: free by default, `qwen/qwen3.8-27b` on Groq (reuses `GROQ_API_KEY`; the free tier is slow, about 1k output tokens/min, and shares quota with the app) with Pinecone embeddings. `EVAL_JUDGE=gemini` uses `gemini-3.8-flash` on Google AI Studio's free tier (`GEMINI_API_KEY`, no card needed, but only 20 requests/day: enough for a `--tickers` subset, not a full run). `EVAL_JUDGE=openai` switches to `gpt-4o-mini` (needs `OPENAI_API_KEY` with credit); `JUDGE_MODEL` overrides the model. Env (local `.env` only): optionally `LANGSMITH_API_KEY` + `LANGSMITH_TRACING=true` + `LANGSMITH_PROJECT=finsight` to log each run as a LangSmith experiment and trace every agent step. Reports are written to `evals/.cache/report-<suite>.json`.
Starting targets: faithfulness ≥ 0.85, numeric grounding = 1.0, context recall ≥ 0.8, hit@6 ≥ 0.8.
