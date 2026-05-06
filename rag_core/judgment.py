import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

DB_PATH = "./codelens.db"

# Simple keyword extraction patterns
ERROR_PATTERNS = {
    "NameError": r"NameError|name.*not defined|undefined variable",
    "IndexError": r"IndexError|index out of range|list index",
    "TypeError": r"TypeError|unsupported operand|type mismatch",
    "ValueError": r"ValueError|invalid value|cannot convert",
    "SyntaxError": r"SyntaxError|invalid syntax|parsing error",
    "IndentationError": r"IndentationError|unexpected indent|indentation",
    "AttributeError": r"AttributeError|has no attribute",
    "KeyError": r"KeyError|key not found|missing key",
    "ImportError": r"ImportError|ModuleNotFoundError|cannot import",
}

TOPIC_PATTERNS = {
    "recursion": r"recursion|recursive|factorial|fibonacci",
    "loops": r"loop|for loop|while loop|iteration",
    "lists": r"list|array|append|index",
    "dictionaries": r"dict|dictionary|key|value",
    "functions": r"function|def|parameter|argument|return",
    "classes": r"class|object|method|attribute|self",
    "strings": r"string|str|concatenat|split|join",
    "files": r"file|open|read|write|close",
}

def extract_error_type(query: str) -> Optional[str]:
    """Extract error type from query using pattern matching"""
    query_lower = query.lower()
    for error_type, pattern in ERROR_PATTERNS.items():
        if re.search(pattern, query_lower, re.IGNORECASE):
            return error_type
    return None

def extract_topic(query: str) -> Optional[str]:
    """Extract topic from query using pattern matching"""
    query_lower = query.lower()
    for topic, pattern in TOPIC_PATTERNS.items():
        if re.search(pattern, query_lower, re.IGNORECASE):
            return topic
    return None

def get_student_context(student_id: str, lookback_minutes: int = 30) -> Dict:
    """
    Get recent context for a student.
    
    Returns:
    - recent_sessions: list of last N sessions
    - error_counts: dict of error types and counts
    - topic_counts: dict of topics and counts
    - time_span: minutes between first and last query
    - is_stuck: boolean indicating if student appears stuck
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get sessions from last N minutes
    cutoff_time = (datetime.now() - timedelta(minutes=lookback_minutes)).isoformat()
    
    cursor.execute("""
        SELECT query, agent_used, error_type, topic, timestamp
        FROM sessions
        WHERE student_id = ? AND timestamp > ?
        ORDER BY timestamp DESC
    """, (student_id, cutoff_time))
    
    sessions = cursor.fetchall()
    conn.close()
    
    if not sessions:
        return {
            "recent_sessions": [],
            "error_counts": {},
            "topic_counts": {},
            "time_span_minutes": 0,
            "is_stuck": False,
            "session_count": 0
        }
    
    # Count error types and topics
    error_counts = {}
    topic_counts = {}
    
    for _, _, error_type, topic, _ in sessions:
        if error_type:
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        if topic:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    # Calculate time span
    first_timestamp = datetime.fromisoformat(sessions[-1][4])
    last_timestamp = datetime.fromisoformat(sessions[0][4])
    time_span = (last_timestamp - first_timestamp).total_seconds() / 60
    
    # Detect if stuck: same error 3+ times or 5+ queries in 10 minutes
    is_stuck = (
        any(count >= 3 for count in error_counts.values()) or
        (len(sessions) >= 5 and time_span < 10)
    )
    
    return {
        "recent_sessions": [
            {"query": s[0], "agent": s[1], "error": s[2], "topic": s[3], "time": s[4]}
            for s in sessions
        ],
        "error_counts": error_counts,
        "topic_counts": topic_counts,
        "time_span_minutes": round(time_span, 1),
        "is_stuck": is_stuck,
        "session_count": len(sessions)
    }

def judge_response_level(query: str, agent_name: str, student_context: Dict) -> str:
    """
    Decide response level based on student context.
    
    Returns directive: "full", "hint", "gentle", "break"
    """
    
    # Fresh student - no history
    if student_context["session_count"] == 0:
        return "full"
    
    # Extract current query metadata
    current_error = extract_error_type(query)
    current_topic = extract_topic(query)
    
    # Rule 1: Student is deeply stuck (same error 3+ times or 5+ queries in 10 min)
    if student_context["is_stuck"]:
        # If same error 4+ times, give full answer + suggest break
        if current_error and student_context["error_counts"].get(current_error, 0) >= 4:
            return "break"
        # Otherwise give full answer with encouragement
        return "full"
    
    # Rule 2: Second occurrence of same error - give hint instead
    if current_error and student_context["error_counts"].get(current_error, 0) >= 1:
        return "hint"
    
    # Rule 3: Building on recent concept - reference earlier conversation
    if current_topic:
        # Check if they asked about this topic in last 10 minutes
        recent_on_topic = [
            s for s in student_context["recent_sessions"][:3]  # Last 3 queries
            if s["topic"] == current_topic
        ]
        if recent_on_topic:
            return "gentle"  # Gentle nudge referencing earlier learning
    
    # Rule 4: If hint was explicitly requested, always give hint
    if agent_name == "hint":
        return "hint"
    
    # Default: full answer
    return "full"


# Test functions
if __name__ == "__main__":
    print("Testing judgment layer components\n" + "="*60)
    
    # Test error extraction
    test_queries = [
        "I'm getting NameError: name 'x' is not defined",
        "IndexError when accessing my list",
        "What is recursion in Python?",
        "How do I use a for loop?",
    ]
    
    print("\n1. Error & Topic Extraction:")
    for q in test_queries:
        error = extract_error_type(q)
        topic = extract_topic(q)
        print(f"Query: {q[:50]}...")
        print(f"  Error: {error}, Topic: {topic}\n")
    
    # Test context retrieval
    print("\n2. Student Context:")
    context = get_student_context("test_student", lookback_minutes=30)
    print(f"Session count: {context['session_count']}")
    print(f"Error counts: {context['error_counts']}")
    print(f"Is stuck: {context['is_stuck']}")
    
    print("\n✅ Judgment layer tests complete")