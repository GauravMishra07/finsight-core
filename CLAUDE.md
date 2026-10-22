# FinSight — AI Credit Underwriter & Research Copilot

Reads a company's latest SEC 10-K, extracts audited XBRL financials, combines filing RAG with live news, and drafts a credit underwriting memo. A chat copilot answers follow-up questions grounded in the filing. Users: equity researchers and report writers.

## Layout (one repo: GitHub `finsight-core`)
- Repo root — Python backend: FastAPI (`api.py`) + LangGraph pipeline. Deployed on **Render free tier (512 MB RAM)**.
- `finsight-web/` — Next.js 15 (App Router, TS, Tailwind v4, Recharts) frontend, **static export** (`output: "export"`) deployed on Vercel Hobby with Root Directory `finsight-web`. No Node server at runtime; the browser calls Render directly. Excluded from the backend image via `.dockerignore`.

## Run
```bash
# backend (from repo root, uses .venv)
uvicorn api:app --reload --port 8000
# frontend (from finsight-web/)
npm run dev            # http://localhost:3000
npm run build          # must succeed: produces out/
```

## Env vars
Backend (`.env` at repo root locally, never commit it; set the same keys in the Render dashboard for production): `GROQ_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` (default `finsight-enterprise`), `DEFAULT_MODEL` (default `openai/gpt-oss-120b` on Groq; all LLM calls go through `config/llm.py:chat`, which silently falls back to `qwen/qwen3.8-27b` then `openai/gpt-oss-20b` on a 429), `EDGAR_IDENTITY` (SEC requires "Name email"), `ALLOWED_ORIGINS` (comma-separated exact origins, no trailing slash; default `http://localhost:3000`).
Frontend: `NEXT_PUBLIC_API_BASE_URL` (e.g. `https://<service>.onrender.com/api/v1`). It is inlined at **build** time, so it must be set in the Vercel dashboard (redeploy after changing it) or in `finsight-web/.env.local` locally. The backend `.env` is not read by Next.js.

## Pipeline (`src/agents/graph.py`)
extractor → (risk_analyst ∥ macro_reviewer, run in parallel) → underwriter. Shared state: `src/agents/state.py` (`AgentState`; `errors` is append-only via `operator.add`).
- **extractor**: resolves the latest 10-K (`src/mcp/tools/edgar_client.py`), chunks it, embeds with Pinecone hosted inference (`multilingual-e5-large`, 1024-dim), and upserts to namespace `{TICKER}__{accession}`. Cache hit = `{doc}_chunk_0` exists, and chunk 0 is written **last**, so keep the reversed batch order.
- **risk_analyst**: SEC `companyconcept` XBRL API → `financial_metrics[label] = {value: "$1,234", source, history: [{fy, end, val}]}` (last 5 FYs, oldest first). Falls back to scraping the statement pages (`history: []`). Then Groq writes a summary.
- **macro_reviewer**: Pinecone search + DuckDuckGo (`ddgs`) news → macro, competitors, projects (JSON mode). `competitors` is a list of `{name, ticker, threat: High|Medium|Low|null, overlap, note}`; the first `MAX_PEERS` (4) with a ticker also get `sec_name` + `metrics` (same shape as `financial_metrics`, exact-ticker lookup only, no filing-page fallback). `competitor_analysis` is the Markdown rendering of that list.
- **underwriter**: Markdown memo with fixed headings. The frontend parses the verdict from `## Final Underwriting Recommendation`, so keep that heading.

## API contract (`api.py`)
- `GET /health` → `{status: "ok"}` (frontend wake-up ping; keep it free of work).
- `POST /api/v1/analyze {ticker}` → AgentState minus `raw_filing_text`; 502 if the filing can't be ingested. Synchronous, takes 60–150 s.
- `POST /api/v1/chat {ticker, tenant_id, user_query, chat_history, memo_text, financial_metrics}` → `{answer}`. Uses only the last 6 history messages and `memo_text[:3000]`.
Changing these shapes means updating `finsight-web/lib/finance.ts` (types) and `lib/api.ts`.

## Free-tier memory rules (backend OOM is the main production risk)
- No local ML models or torch: embeddings use Pinecone's hosted inference.
- Filing text is capped at `MAX_CHARS` (480k) and embedded in batches of 50, with `del` + `gc.collect()`. Don't load whole filings into lists of objects.
- Run one uvicorn worker; each extra worker duplicates memory.
- Don't return large blobs from the API.
- Frontend side: cache reports in localStorage (last 5, `lib/store.ts`), dedupe in-flight analyze calls (`lib/api.ts`), and never auto-trigger a re-run.

## Frontend notes
- `components/ReportView.tsx` is the workspace: tabs, export (copy, .md, print-to-PDF) and the docked `Copilot`. `components/Dashboard.tsx` holds the KPI tiles, charts and ratio panel. All finance math is in `lib/finance.ts`.
- Colours are CSS tokens in `app/globals.css` (dataviz reference palette, separate dark steps). Charts use `var(--s1)`/`var(--s2)` only. Status colours (good/warn/crit) always come with an icon and a label. No dual-axis charts.
- Everything is a client component. Static export means no API routes, no server actions and no `next/image` optimisation.

## Tests
```bash
# backend (from repo root)
.venv/Scripts/python -m pytest tests/test_history.py   # or call the test functions directly; pytest isn't in requirements
.venv/Scripts/python tests/test_competitors.py         # offline; peer lookup is stubbed
python tests/test_e2e.py                               # live: hits SEC, Pinecone, Groq
# frontend (from finsight-web/)
node --test lib/finance.test.ts                        # Node >= 22.18
npm run lint && npm run build
```
