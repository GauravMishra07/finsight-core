# evals/run_evals.py
"""Score FinSight outputs with RAGAS + deterministic metrics; each run becomes a LangSmith experiment.

python -m evals.run_evals --suite memo|chat|retrieval|all [--tickers MSFT,KO] [--repeats 3] [--fresh]
                          [--no-judge] [--no-upload]
Uploads only when LANGSMITH_API_KEY is set. Reports always land in evals/.cache/report-<suite>.json.
"""
import argparse
import asyncio
import hashlib
import json
import os
import statistics
import sys
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")  # Windows console vs. filing text

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from api import ChatRequest, answer_question, initial_state
from config.settings import settings
from evals import metrics as m
from src.agents.graph import finsight_graph
from src.agents.underwriter import underwriter_node
from src.rag.embedder import embedder
from src.rag.vector_store import vector_store

CACHE = ROOT / "evals" / ".cache"
GOLDEN = {g["ticker"]: g for g in json.loads((ROOT / "evals" / "golden.json").read_text(encoding="utf-8"))}
KS = [3, 6, 10, 15]
CHAT_K = 6  # top_k in api.answer_question
JUDGE = os.getenv("EVAL_JUDGE", "groq")  # groq | gemini (both free tiers) | openai
JUDGE_URLS = {"groq": "https://api.groq.com/openai/v1",
              "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/"}
JUDGE_MODEL = os.getenv("JUDGE_MODEL", {"groq": "qwen/qwen3.8-27b", "gemini": "gemini-3.8-flash",
                                        "openai": "gpt-4o-mini"}[JUDGE])


@cache
def judge():
    """RAGAS metrics. Default judge is free: Qwen on Groq (a different family from the gpt-oss generator) with
    Pinecone's hosted embeddings. EVAL_JUDGE=openai switches to gpt-4o-mini (needs OPENAI_API_KEY with credit)."""
    from openai import AsyncOpenAI
    from ragas.embeddings import OpenAIEmbeddings
    from ragas.embeddings.base import BaseRagasEmbedding
    from ragas.llms import llm_factory
    from ragas.metrics import DiscreteMetric
    from ragas.metrics.collections import (AnswerRelevancy, ContextPrecisionWithReference, ContextRecall,
                                           FactualCorrectness, Faithfulness)

    class PineconeEmbeddings(BaseRagasEmbedding):
        def embed_text(self, text, **kw):
            return embedder.embed_query(text)

        async def aembed_text(self, text, **kw):
            return await asyncio.to_thread(embedder.embed_query, text)

    if JUDGE == "openai":
        client = AsyncOpenAI()
        emb = OpenAIEmbeddings(client=client, model="text-embedding-3-small")
    else:
        # max_retries: the SDK sleeps for the 429's retry-after, which free tiers hit constantly.
        client = AsyncOpenAI(base_url=JUDGE_URLS[JUDGE], api_key=os.environ[f"{JUDGE.upper()}_API_KEY"], max_retries=10)
        emb = PineconeEmbeddings()
    # Groq free tier caps Qwen at 1000 output tok/min; thinking models need room for reasoning tokens.
    llm = llm_factory(JUDGE_MODEL, client=client, max_tokens=900 if JUDGE == "groq" else 8192)
    pass_fail = lambda name, prompt: DiscreteMetric(name=name, allowed_values=["pass", "fail"], prompt=prompt)
    return {
        "llm": llm,
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=emb),
        "factual_correctness": FactualCorrectness(llm=llm),
        "context_precision": ContextPrecisionWithReference(llm=llm),
        "context_recall": ContextRecall(llm=llm),
        "verdict_justified": pass_fail("verdict_justified",
            "You are auditing a bank credit memo. Does its 'Final Underwriting Recommendation' section justify the "
            "verdict with specific figures or risks stated elsewhere in the memo? Answer 'pass' if it does, 'fail' "
            "if the verdict is asserted without concrete support.\n\nMemo:\n{response}"),
        "gaps_acknowledged": pass_fail("gaps_acknowledged",
            "A credit memo must only use its inputs and must say explicitly when something is not covered. "
            "Answer 'pass' if every topic the memo discusses is either supported by the inputs or flagged as not "
            "covered / unavailable; 'fail' if it fills gaps with unsupported claims.\n\n"
            "Inputs:\n{inputs}\n\nMemo:\n{response}"),
        "refusal": pass_fail("refusal",
            "The question below cannot be answered from the company's 10-K. Answer 'pass' if the response says the "
            "information is not available (it may add related facts that are clearly sourced); 'fail' if it "
            "presents a specific answer as fact.\n\nQuestion: {user_input}\n\nResponse:\n{response}"),
    }


async def _value(coro):
    v = (await coro).value
    return {"pass": 1.0, "fail": 0.0}.get(v, v)


async def llm_results(**coros) -> list[dict]:
    """Run judge metrics concurrently; a failed metric is reported with score None instead of sinking the row."""
    vals = await asyncio.gather(*map(_value, coros.values()), return_exceptions=True)
    return [{"key": k, "score": None, "comment": repr(v)} if isinstance(v, Exception) else {"key": k, "score": v}
            for k, v in zip(coros, vals)]


# --- pipeline outputs (cached: a run takes 60-150 s and Groq is rate limited) ---

def pipeline_state(ticker: str, fresh: bool) -> dict:
    path = CACHE / f"{ticker}.json"
    if path.exists() and not fresh:
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        print(f"Running the pipeline for {ticker} (60-150 s)...")
        state = finsight_graph.invoke(initial_state(ticker))
        state.pop("raw_filing_text", None)
        if not state.get("final_memo"):
            sys.exit(f"Pipeline failed for {ticker}: {state.get('errors')}")
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, default=str), encoding="utf-8")
    if state["tenant_id"] != f"{ticker}__{GOLDEN[ticker]['accession']}":
        print(f"WARNING: {ticker} pipeline used {state['tenant_id']}, but golden.json was written against "
              f"{GOLDEN[ticker]['accession']}. A newer 10-K exists; references may be stale.")
    return state


# --- suites: each is (examples, target, evaluator, concurrency) ---

def memo_suite(tickers, states, repeats, use_judge):
    examples = [{"inputs": {"ticker": t}, "outputs": {"metrics": GOLDEN[t]["metrics"]}} for t in tickers]

    async def target(inputs):
        s = states[inputs["ticker"]]
        # Re-run only the underwriter for stability: it isolates the verdict's randomness from news/RAG drift.
        reruns = [await asyncio.to_thread(underwriter_node, s) for _ in range(repeats - 1)]
        return {"memo": s["final_memo"], "financial_metrics": s["financial_metrics"],
                "risk_analysis": s.get("risk_analysis") or "", "macro_analysis": s.get("macro_analysis") or "",
                "evidence": s.get("evidence") or [],
                "verdicts": [m.verdict_from_memo(x) for x in [s["final_memo"]] + [r.get("final_memo") for r in reruns]]}

    async def evaluator(inputs, outputs, reference_outputs):
        o = outputs
        metrics_json = json.dumps(o["financial_metrics"])
        upstream = [metrics_json, o["risk_analysis"], o["macro_analysis"]]  # exactly what the underwriter saw
        grounding, ungrounded = m.numeric_grounding(o["memo"], o["financial_metrics"], upstream[1:])
        accuracy, wrong = m.metric_accuracy(o["financial_metrics"], reference_outputs["metrics"])
        results = [
            {"key": "numeric_grounding", "score": grounding, "comment": f"ungrounded: {ungrounded}"},
            {"key": "metric_accuracy", "score": accuracy, "comment": f"wrong: {wrong}"},
            {"key": "headings_present", "score": m.headings_present(o["memo"])},
            {"key": "verdict_parsed", "score": float(o["verdicts"][0] is not None), "comment": str(o["verdicts"][0])},
        ]
        if len(o["verdicts"]) > 1:
            results.append({"key": "verdict_stability", "score": m.verdict_stability(o["verdicts"]),
                            "comment": str(o["verdicts"])})
        if use_judge:
            j, task = judge(), f"Write a credit underwriting memo for {inputs['ticker']}."
            results += await llm_results(
                memo_faithfulness=j["faithfulness"].ascore(user_input=task, response=o["memo"],
                                                           retrieved_contexts=upstream),
                risk_faithfulness=j["faithfulness"].ascore(user_input=task, response=o["risk_analysis"],
                                                           retrieved_contexts=[metrics_json]),
                macro_faithfulness=j["faithfulness"].ascore(user_input=task, response=o["macro_analysis"],
                                                            retrieved_contexts=o["evidence"]),
                verdict_justified=j["verdict_justified"].ascore(llm=j["llm"], response=o["memo"]),
                gaps_acknowledged=j["gaps_acknowledged"].ascore(llm=j["llm"], response=o["memo"],
                                                                inputs="\n\n".join(upstream)),
            )
        return {"results": results}

    return examples, target, evaluator, 1


def _qa_examples(tickers):
    return [{"inputs": {"ticker": t, "id": q["id"], "type": q["type"], "question": q["question"]},
             "outputs": {"reference": q["reference"], "evidence": q["evidence"]}}
            for t in tickers for q in GOLDEN[t]["questions"]]


def chat_suite(tickers, states, use_judge):
    async def target(inputs):
        s = states[inputs["ticker"]]
        req = ChatRequest(ticker=inputs["ticker"], tenant_id=s["tenant_id"], user_query=inputs["question"],
                          chat_history=[], memo_text=s["final_memo"], financial_metrics=s["financial_metrics"])
        answer, contexts = await asyncio.to_thread(answer_question, req)
        return {"answer": answer, "contexts": contexts}

    async def evaluator(inputs, outputs, reference_outputs):
        if not use_judge:
            return {"results": []}
        j, q, a = judge(), inputs["question"], outputs["answer"]
        if inputs["type"] == "unanswerable":
            return {"results": await llm_results(refusal=j["refusal"].ascore(llm=j["llm"], user_input=q, response=a))}
        return {"results": await llm_results(
            faithfulness=j["faithfulness"].ascore(user_input=q, response=a, retrieved_contexts=outputs["contexts"]),
            answer_relevancy=j["answer_relevancy"].ascore(user_input=q, response=a),
            factual_correctness=j["factual_correctness"].ascore(response=a, reference=reference_outputs["reference"]),
        )}

    return _qa_examples(tickers), target, evaluator, 1


def retrieval_suite(tickers, use_judge):
    async def target(inputs):
        g = GOLDEN[inputs["ticker"]]
        emb = await asyncio.to_thread(embedder.embed_query, inputs["question"])
        hits = await asyncio.to_thread(vector_store.search, tenant_id=f"{g['ticker']}__{g['accession']}",
                                       query_embedding=emb, top_k=max(KS))
        return {"chunks": [h["metadata"]["text"] for h in hits]}

    async def evaluator(inputs, outputs, reference_outputs):
        chunks, evidence, results = outputs["chunks"], reference_outputs["evidence"], []
        if evidence:
            rank = m.first_hit_rank(chunks, evidence)
            results += [{"key": f"hit@{k}", "score": float(rank is not None and rank <= k)} for k in KS]
            results.append({"key": "mrr", "score": 1 / rank if rank else 0.0, "comment": f"rank={rank}"})
        if use_judge and inputs["type"] != "unanswerable":
            j, q, ref, top = judge(), inputs["question"], reference_outputs["reference"], chunks[:CHAT_K]
            results += await llm_results(
                context_precision=j["context_precision"].ascore(user_input=q, reference=ref, retrieved_contexts=top),
                context_recall=j["context_recall"].ascore(user_input=q, retrieved_contexts=top, reference=ref),
            )
        return {"results": results}

    return _qa_examples(tickers), target, evaluator, 4


# --- running + reporting ---

async def run(suite, examples, target, evaluator, concurrency, upload) -> list[dict]:
    if upload:
        from langsmith import Client, aevaluate
        client = Client()
        # Content-hashed name: editing golden.json makes a fresh dataset instead of mixing old and new examples.
        name = f"finsight-{suite}-{hashlib.sha1(json.dumps(examples, sort_keys=True).encode()).hexdigest()[:8]}"
        if not client.has_dataset(dataset_name=name):
            client.create_dataset(name, description=f"FinSight {suite} golden set (evals/golden.json)")
            client.create_examples(dataset_name=name, examples=examples)
        res = await aevaluate(target, data=name, evaluators=[evaluator], client=client, max_concurrency=concurrency,
                              experiment_prefix=f"{suite}-{settings.default_model.split('/')[-1]}")
        return [{"id": r["example"].inputs.get("id", r["example"].inputs["ticker"]),
                 "scores": {e.key: e.score for e in r["evaluation_results"]["results"]},
                 "comments": {e.key: e.comment for e in r["evaluation_results"]["results"] if e.comment}}
                async for r in res]

    sem = asyncio.Semaphore(concurrency)

    async def one(ex):
        row_id = ex["inputs"].get("id", ex["inputs"]["ticker"])
        async with sem:
            try:
                out = await target(ex["inputs"])
                res = (await evaluator(ex["inputs"], out, ex["outputs"]))["results"]
            except Exception as e:
                print(f"  {row_id}: failed: {e!r}")
                return {"id": row_id, "scores": {}, "comments": {"error": repr(e)}}
        return {"id": row_id, "scores": {r["key"]: r["score"] for r in res},
                "comments": {r["key"]: r["comment"] for r in res if r.get("comment")}}

    return await asyncio.gather(*map(one, examples))


def report(suite, rows):
    print(f"\n== {suite}: {len(rows)} examples ==")
    for k in sorted({k for r in rows for k in r["scores"]}):
        vals = [r["scores"][k] for r in rows if r["scores"].get(k) is not None]
        if vals:
            print(f"  {k:<22} {statistics.mean(vals):.3f}  (n={len(vals)})")
    worst = sorted((v, r["id"], k) for r in rows for k, v in r["scores"].items() if v is not None and v < 1)[:5]
    for v, rid, k in worst:
        note = next(r for r in rows if r["id"] == rid)["comments"].get(k, "")
        print(f"  low: {rid:<10} {k:<20} {v:.2f}  {str(note)[:120]}")
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"report-{suite}.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--suite", choices=["memo", "chat", "retrieval", "all"], default="all")
    p.add_argument("--tickers", default=",".join(GOLDEN), help="comma-separated, from golden.json")
    p.add_argument("--repeats", type=int, default=1, help="memo: underwriter runs per ticker, for verdict stability")
    p.add_argument("--fresh", action="store_true", help="re-run the pipeline instead of using evals/.cache")
    p.add_argument("--no-judge", action="store_true", help="deterministic metrics only (no judge LLM calls)")
    p.add_argument("--no-upload", action="store_true", help="don't log to LangSmith")
    a = p.parse_args()

    tickers = [t.strip().upper() for t in a.tickers.split(",")]
    unknown = [t for t in tickers if t not in GOLDEN]
    if unknown:
        sys.exit(f"No golden data for {unknown}; add them to evals/golden.json")
    upload = not a.no_upload and bool(os.getenv("LANGSMITH_API_KEY"))
    if not upload and not a.no_upload:
        print("LANGSMITH_API_KEY not set: results stay local.")
    judge_on = not a.no_judge
    suites = ["memo", "chat", "retrieval"] if a.suite == "all" else [a.suite]
    states = {t: pipeline_state(t, a.fresh) for t in tickers} if {"memo", "chat"} & set(suites) else {}

    for suite in suites:
        spec = (memo_suite(tickers, states, a.repeats, judge_on) if suite == "memo"
                else chat_suite(tickers, states, judge_on) if suite == "chat"
                else retrieval_suite(tickers, judge_on))
        report(suite, asyncio.run(run(suite, *spec, upload)))


if __name__ == "__main__":
    main()
