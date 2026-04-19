import json
import os
import csv
import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from groq import Groq
from datasets import Dataset


load_dotenv()
GROQ_API_KEY = os.getenv("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")
client = Groq(api_key=GROQ_API_KEY)

DB_PATH = "student_profiles.db"
PROFILES_PATH = "evaluation/student_profiles.json"
CHROMA_PATH = "evaluation/student_chromadb"
QUESTIONS_PATH = "evaluation/test_questions.json"

def get_student_context_from_chroma(student_id: str, question: str) -> str:
    """Query per-student ChromaDB for relevant context."""
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.DefaultEmbeddingFunction()
    try:
        collection = chroma_client.get_collection(
            name=f"student_{student_id}",
            embedding_function=ef
        )
        results = collection.query(query_texts=[question], n_results=3)
        docs = results["documents"][0]
        return "\n".join(docs)
    except Exception as e:
        return f"No context available for student {student_id}"

def get_persona_response(question: str, chroma_context: str, student: dict) -> str:
    """Call Groq with enriched ChromaDB context."""
    prompt = f"""You are a Python debugging assistant helping a specific student.

Student Profile:
- Name: {student['name']}
- Learning style: {student['learning_style']}

Student's Past Errors and Weak Areas (from their history):
{chroma_context}

Question: {question}

Give a debugging explanation tailored to this student's weak areas and learning style."""

    try:
        message = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def load_profiles():
    with open(PROFILES_PATH) as f:
        return json.load(f)

def load_questions():
    with open(QUESTIONS_PATH) as f:
        return json.load(f)

def run_ragas(results: list) -> list:
    """Score using local embeddings via Ollama - no API needed."""
    print("Running local embedding evaluation...")
    from langchain_ollama import OllamaEmbeddings
    import numpy as np
    
    embedder = OllamaEmbeddings(model="nomic-embed-text")
    
    for i, result in enumerate(results):
        print(f"Scoring {i+1}/{len(results)}...")
        question = result["question"]
        answer = result["persona_response"]
        context = result["chroma_context"]
        
        try:
            # Faithfulness: how grounded is answer in context
            context_emb = embedder.embed_query(context)
            answer_emb = embedder.embed_query(answer)
            faithfulness = float(np.dot(context_emb, answer_emb) / (
                np.linalg.norm(context_emb) * np.linalg.norm(answer_emb)))
            
            # Answer Relevancy: how relevant is answer to question
            question_emb = embedder.embed_query(question)
            relevancy = float(np.dot(question_emb, answer_emb) / (
                np.linalg.norm(question_emb) * np.linalg.norm(answer_emb)))
            
            result["faithfulness"] = max(0, faithfulness)
            result["answer_relevancy"] = max(0, relevancy)
        except Exception as e:
            print(f"  Error on {i+1}: {e}")
            result["faithfulness"] = 0.0
            result["answer_relevancy"] = 0.0
    
    return results

def main():
    print("STARTING ENRICHED PERSONA EVAL")
    profiles = load_profiles()
    questions = load_questions()
    results = []

    for student in profiles:
        student_id = student["student_id"]

        print(f"\nEvaluating student: {student['name']} ({student_id})")

        for q_obj in questions:
            question = q_obj["question"]
            chroma_context = get_student_context_from_chroma(student_id, question)
            response = get_persona_response(question, chroma_context, student)

            results.append({
                "student_id": student_id,
                "student_name": student["name"],
                "question": question,
                "chroma_context": chroma_context,
                "persona_response": response,
            })

    results = run_ragas(results)

    # Save CSV
    with open("evaluation/enriched_persona_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Calculate averages
    avg_f = sum(r["faithfulness"] for r in results) / len(results)
    avg_ar = sum(r["answer_relevancy"] for r in results) / len(results)

    baseline_f = 0.4729
    baseline_ar = 0.8298

    print("\n--- ENRICHED PERSONA vs BASELINE ---")
    print(f"Faithfulness:      {baseline_f} → {avg_f:.4f}  ({((avg_f-baseline_f)/baseline_f)*100:+.2f}%)")
    print(f"Answer Relevancy:  {baseline_ar} → {avg_ar:.4f}  ({((avg_ar-baseline_ar)/baseline_ar)*100:+.2f}%)")
    print(f"\nSaved to evaluation/enriched_persona_results.csv")

if __name__ == "__main__":
    main()