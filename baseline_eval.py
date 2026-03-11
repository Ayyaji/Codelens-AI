"""
CodeLens AI — M4 Baseline Evaluation Script
============================================
Calls Groq API directly (no RAG, no ChromaDB, no agents).
Runs all 25 questions from test_questions.json.
Saves results to baseline_results.csv.
Computes RAGAS: Faithfulness + Answer Relevancy.

Usage:
    pip install ragas langchain datasets groq --break-system-packages
    $env:GROQ_API_KEY="your_key_here"   (PowerShell)
    python baseline_eval.py
"""

import os
import json
import csv
import time
from groq import Groq

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL        = "llama-3.3-70b-versatile"
INPUT_FILE   = "evaluation/test_questions.json"
OUTPUT_CSV   = "evaluation/baseline_results.csv"
RAGAS_OUTPUT = "evaluation/baseline_ragas_scores.json"

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY not set.\n"
        "PowerShell: $env:GROQ_API_KEY=\"gsk_your_key\"\n"
        "Mac/Linux:  export GROQ_API_KEY=gsk_your_key"
    )

client = Groq(api_key=GROQ_API_KEY)


# ── Step 1: Load questions ────────────────────────────────────────────────────
print("Loading test questions...")
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

print(f"Loaded {len(questions)} questions.\n")


# ── Step 2: Call Groq for each question (no RAG) ─────────────────────────────
def ask_groq(question: str, code_snippet: str) -> str:
    """Send question directly to Groq LLM. No retrieval, no context."""
    prompt = f"""You are a Python debugging assistant for engineering students.
A student has the following error or question:

Question: {question}

Code:
{code_snippet}

Provide a clear, concise explanation of what is wrong and how to fix it."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


results = []

print("Running baseline evaluation (plain LLM, no RAG)...")
print("-" * 60)

for i, item in enumerate(questions):
    print(f"[{i+1}/{len(questions)}] {item['category']} | Q{item['id']}: {item['question'][:60]}...")

    start_time = time.time()
    answer = ask_groq(item["question"], item.get("code_snippet", ""))
    elapsed = round(time.time() - start_time, 2)

    results.append({
        "id":              item["id"],
        "category":        item["category"],
        "in_kb":           item["in_kb"],
        "question":        item["question"],
        "expected_answer": item["expected_answer"],
        "baseline_answer": answer,
        "response_time_s": elapsed,
    })

    print(f"    ✓ Done in {elapsed}s\n")
    time.sleep(0.5)  # avoid rate limiting

print("-" * 60)
print(f"All {len(results)} questions answered.\n")


# ── Step 3: Save to CSV ───────────────────────────────────────────────────────
os.makedirs("evaluation", exist_ok=True)

fieldnames = ["id", "category", "in_kb", "question",
              "expected_answer", "baseline_answer", "response_time_s"]

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print(f"Results saved to: {OUTPUT_CSV}\n")


# ── Step 4: Run RAGAS ────────────────────────────────────────────────────────
print("Running RAGAS evaluation...")

try:
    import pandas as pd
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy
    from langchain_groq import ChatGroq
    from langchain_community.embeddings import HuggingFaceEmbeddings

    ragas_data = {
        "question":     [r["question"] for r in results],
        "answer":       [r["baseline_answer"] for r in results],
        "contexts":     [[r["expected_answer"]] for r in results],
        "ground_truth": [r["expected_answer"] for r in results],
    }

    dataset = Dataset.from_dict(ragas_data)

    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name=MODEL,
        temperature=0,
    )
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    score = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=llm,
        embeddings=embeddings,
    )

    # Safely extract scores via DataFrame
    score_df = score.to_pandas()
    faith_score     = float(score_df["faithfulness"].mean())
    relevancy_score = float(score_df["answer_relevancy"].mean())

    ragas_scores = {
        "faithfulness":     round(faith_score, 4),
        "answer_relevancy": round(relevancy_score, 4),
        "model":            MODEL,
        "mode":             "baseline_no_rag",
        "total_questions":  len(results),
    }

    with open(RAGAS_OUTPUT, "w") as f:
        json.dump(ragas_scores, f, indent=2)

    print("\n" + "=" * 60)
    print("BASELINE RAGAS RESULTS")
    print("=" * 60)
    print(f"  Faithfulness:     {ragas_scores['faithfulness']}")
    print(f"  Answer Relevancy: {ragas_scores['answer_relevancy']}")
    print(f"  Mode:             No RAG (plain LLM)")
    print(f"  Model:            {MODEL}")
    print("=" * 60)
    print(f"\nScores saved to: {RAGAS_OUTPUT}")
    print("\nNext step: run RAG evaluation via M1's /ask endpoint")
    print("and compare these scores against RAG scores.")

except ImportError as e:
    print(f"\nRAGAS import error: {e}")
    print("Run: pip install ragas langchain langchain-groq langchain-community sentence-transformers pandas --break-system-packages")

except Exception as e:
    print(f"\nRAGAS evaluation failed: {e}")
    print("CSV results are still saved. Fix the error and re-run RAGAS separately.")
