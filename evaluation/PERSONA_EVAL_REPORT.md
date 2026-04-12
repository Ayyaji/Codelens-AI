# CodeLens AI — Persona Layer RAGAS Evaluation Report

## Experiment Setup
- **Dataset:** 25 test questions × 5 synthetic student profiles = 125 evaluations
- **Model:** Groq mixtral-8x7b-32768
- **Metrics:** RAGAS Faithfulness + Answer Relevancy
- **Persona Injection:** Student weak areas + learning style injected into prompt

## Results

### Baseline (RAG only, no persona)
| Metric | Score |
|--------|-------|
| Faithfulness | 0.4729 |
| Answer Relevancy | 0.8298 |

### Persona Layer (RAG + Student Context)
| Metric | Score | vs Baseline |
|--------|-------|-------------|
| Faithfulness | 0.5480 | **+15.88%** ✅ |
| Answer Relevancy | 0.5500 | **-33.72%** ⚠️ |

## Key Finding

**Persona context improves answer faithfulness but reduces relevancy.**

Injecting student weak areas + learning style helps LLM give more accurate explanations (+15.88%).
However, without actual per-student error history from ChromaDB, answers become less relevant to student needs (-33.72%).

## Interpretation

- ✅ **Faithfulness improvement:** System correctly understands student weaknesses
- ⚠️ **Relevancy drop:** Generic persona tags insufficient — need real student KB with past errors

## Next Phase

Build per-student ChromaDB storing:
1. Session error logs (actual NameError, IndexError, etc.)
2. Error frequency patterns
3. Student performance timeline

Re-inject enriched persona context and measure RAGAS again.

## Viva Answer (Q5)

*"How did persona improve your RAGAS scores?"*

"Persona improved faithfulness by 15.88% — the system now gives more accurate explanations tailored to student weaknesses. However, answer relevancy dropped 33.72% because generic persona tags aren't enough. We need per-student ChromaDB storing actual session errors. Once we enrich persona with real student history, relevancy will improve significantly."

---

**Evaluation Date:** April 12, 2026
**Evaluator:** M4 (Nishith J Rao)
**Status:** ✅ Complete