CodeLens AI (Live Demo:- http://3.104.106.185/ )
Adaptive RAG debug assistant for CS students — adjusts how it answers based on how stuck you are.

The Problem
Every RAG system retrieves context and generates an answer. The response depth never changes — first-time question or fifth attempt at the same bug, you get the same treatment. That's not how good tutors work.

What CodeLens Does Differently
CodeLens adds a judgment layer between retrieval and response. Before generating anything, it reads your session history and decides how to answer, not just what to answer.
Four directives, computed per request:

FULL — First time on this error. Complete explanation + fix.
HINT — Same error, second time. One nudge, no solution.
GENTLE — Same concept within 10 minutes. Reference what you just learned.
BREAK — Same error, 4+ times. Stop. Rest. Come back.


Architecture
POST /ask
  → Router       classify intent (debug / concept / hint / web)
  → Judgment     read session history → compute directive
  → Agent        generate response (debug / concept / hint / web)
  → Logger       write to SQLite (error_type, topic, timestamp)
  → Response     { answer, agent_used, directive }
State lives in SQLite. Each session records student_id, error_type, topic, and timestamp — the four fields the judgment layer needs to compute the next directive.

Quick Start
bashgit clone <repo> && cd codelens-ai/rag_core
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API=your_key_here" > .env
python init_db.py && python build_kb.py
uvicorn api:app --reload --port 8000
Requires Python 3.10+, a Groq API key, and nothing else — SQLite and ChromaDB are bundled or pip-installed.

API
POST /ask
json{ "student_id": "user_123", "query": "Why am I getting IndexError?" }
json{ "answer": "...", "agent_used": "debug", "directive": "hint" }
Teacher endpoints — GET /pending-kb, POST /approve-kb/{id}, POST /reject-kb/{id}. Web search results are staged for teacher approval before entering the knowledge base.

Metrics
RAGAS evaluation, April 2026:

Answer Relevancy: 82.98%
Faithfulness: 47.29% (known gap — target of Phase 3 prompt work)


Status
PhaseWhatStatus1Core RAG pipeline + 4 agents✅ Done2Judgment layer — computes directive✅ Done3Wire directive into agent prompts🔧 In progress4RAGAS evaluation per directive variant⏳ Planned5Web frontend, replace Streamlit⏳ Planned
Known issue: SQLite write-lock fails at ~20 concurrent users. RDS migration (PostgreSQL) pending GitHub Education approval.

Team
  Raghava S. Ayyaji 
  Arjun 
  Nishith J Rao
  Srishant 

VTU / JSS Academy of Technical Education, 2026
