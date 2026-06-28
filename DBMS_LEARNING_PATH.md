# DBMS Learning Path for CodeLens AI

## Why DBMS Matters for CodeLens

You're using **SQLite** (`codelens.db`) to track:
- Student sessions (queries, errors, topics, timestamps)
- Error patterns (to detect when stuck)
- Query velocity (5 queries in 10 mins = stuck?)

**The gap**: You're doing it right, but inefficiently.

---

## 1. Current State Analysis

### What you have:
```
codelens.db (SQLite)
├── sessions (student_id, query, agent_used, response_time, error_type, topic, timestamp)
└── kb_pending (query, content, source, status)  [human curation]
```

### Current bottlenecks:
1. **Full table scan on `get_student_context()`**
   - `SELECT * FROM sessions WHERE student_id = ? AND timestamp > ?`
   - You're fetching ALL sessions, then filtering in Python
   - Should index on `(student_id, timestamp)` for fast range queries

2. **Error counting in Python**
   ```python
   error_counts = {}
   for _, _, error_type, topic, _ in sessions:
       if error_type:
           error_counts[error_type] = error_counts.get(error_type, 0) + 1
   ```
   - This is slow. SQLite can do `COUNT()` + `GROUP BY` in O(1)

3. **No query optimization**
   - Every `log_session()` does a fresh `sqlite3.connect()` (expensive)
   - Should use connection pooling

---

## 2. DBMS Concepts You NEED (in order)

### Level 1: Foundations (Days 1-2)
**What**: Indexes, Query Planning, EXPLAIN PLAN

**Why for CodeLens**:
- Your judgment layer queries the DB on every request
- Without indexes, it scans the entire table

**Do this**:
```sql
-- BAD (full table scan):
SELECT * FROM sessions WHERE student_id = 'student_1' AND timestamp > '2026-06-06T00:00:00';

-- GOOD (indexed):
CREATE INDEX idx_student_timestamp ON sessions(student_id, timestamp DESC);
EXPLAIN QUERY PLAN 
SELECT * FROM sessions WHERE student_id = 'student_1' AND timestamp > '2026-06-06T00:00:00';
```

**Learn**: https://www.sqlite.org/queryplanner.html
- Read: EXPLAIN output (line by line)
- Practice: Compare full table scan vs. index scan

---

### Level 2: Aggregations & Grouping (Days 3-4)
**What**: GROUP BY, COUNT, SUM, aggregate functions

**Why for CodeLens**:
- Instead of `error_counts = {}` in Python, move to SQL:

```sql
-- Current (Python loop):
for error_type in sessions:
    error_counts[error_type] += 1

-- Better (SQL):
SELECT error_type, COUNT(*) as count 
FROM sessions 
WHERE student_id = ? AND timestamp > ?
GROUP BY error_type;
```

**Do this**:
- Move `get_student_context()` logic to SQL
- Compare speed (should be 10x faster)

---

### Level 3: JOINs & Relationships (Days 5-6)
**Why for CodeLens Phase 2**:
- Currently: `sessions` table is flat (no relationships)
- Future: You'll want to link `sessions` → `students` → `class` → `teacher`
- JOINs become critical

**Learn**: INNER JOIN, LEFT JOIN, self-joins
**Example for CodeLens**:
```sql
SELECT 
    s.student_id,
    s.query,
    st.name,
    cl.class_name,
    COUNT(s.id) as query_count
FROM sessions s
LEFT JOIN students st ON s.student_id = st.id
LEFT JOIN classes cl ON st.class_id = cl.id
GROUP BY s.student_id
HAVING query_count > 5;
```

---

### Level 4: Transactions & Concurrency (Days 7-8)
**What**: ACID, BEGIN/COMMIT, isolation levels

**Why for CodeLens**:
- Currently: Each `log_session()` opens/closes connection independently
- Problem: Race condition if two students query simultaneously

**Fix**:
```python
# Current (UNSAFE):
conn = sqlite3.connect(DB_PATH)
cursor.execute("INSERT INTO sessions...")
conn.commit()
conn.close()

# Better (with transaction safety):
conn = sqlite3.connect(DB_PATH)
try:
    cursor.execute("BEGIN TRANSACTION")
    cursor.execute("INSERT INTO sessions...")
    cursor.execute("INSERT INTO kb_pending...")  # atomic
    cursor.execute("COMMIT")
except:
    cursor.execute("ROLLBACK")
finally:
    conn.close()
```

---

### Level 5: Schema Design (Days 9-10)
**What**: Normalization, Primary Keys, Foreign Keys, Data Types

**Your current schema**:
```sql
CREATE TABLE sessions (
    student_id TEXT,
    query TEXT,
    agent_used TEXT,
    response_time FLOAT,
    timestamp TEXT,
    error_type TEXT,
    topic TEXT
);
```

**Problems**:
- No primary key (inserting duplicates is possible)
- `agent_used`, `error_type`, `topic` repeat strings (wasteful)
- `timestamp` is TEXT (harder to query)

**Better schema**:
```sql
CREATE TABLE students (
    id TEXT PRIMARY KEY,
    name TEXT,
    class_id INTEGER,
    created_at DATETIME
);

CREATE TABLE agents (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    error_type TEXT,
    topic TEXT,
    response_time REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX idx_student_timestamp ON sessions(student_id, timestamp);
CREATE INDEX idx_timestamp ON sessions(timestamp);
```

---

## 3. Practical Learning Plan

### Week 1: Speed Up CodeLens Now
**Day 1-2**: Add indexes to current schema
```bash
sqlite3 codelens.db
CREATE INDEX idx_student_timestamp ON sessions(student_id, timestamp);
```

**Day 3-4**: Rewrite `get_student_context()` to use SQL aggregations
- Move `error_counts` logic to SQL
- Measure speed improvement (should see 5-10x)

**Day 5**: Connection pooling
```python
from sqlite3 import connect
import threading

class DBPool:
    def __init__(self, db_path, pool_size=5):
        self.db_path = db_path
        self.connections = [connect(db_path) for _ in range(pool_size)]
        self.lock = threading.Lock()
    
    def acquire(self):
        with self.lock:
            return self.connections.pop()
    
    def release(self, conn):
        with self.lock:
            self.connections.append(conn)
```

---

### Week 2: Learn Deeply
**Resources**:
1. **SQLite official docs**: https://www.sqlite.org/docs.html
   - Focus: Query Planner, Indexes, EXPLAIN
   
2. **SQL Practice**: https://www.sqlzoo.net/ or https://sqlbolt.com/
   - Do exercises 1-15 (covers GROUP BY, JOINs)

3. **Your codebase**: Run EXPLAIN PLAN on every query in CodeLens
   - `SELECT EXPLAIN QUERY PLAN SELECT ... FROM sessions`
   - Check if it uses your index

---

## 4. Interview Angle

**For job applications** (from me.md):

You'll say: *"I optimized CodeLens judgment layer from 5.5s to 2s by understanding database indexing and moving aggregations to SQL. Added 3 indexes on (student_id, timestamp) and rewrote error-counting logic as GROUP BY queries."*

This shows:
- ✅ You understand DBMS fundamentals
- ✅ You optimize for real performance
- ✅ You don't just write code, you measure it

---

## 5. Next Steps After Learning

### Phase 3 of CodeLens (wiring directive to prompts):
You'll need better schema to track:
- `response_directives` table (HINT vs FULL decisions)
- `student_mistakes` table (track repeated errors)
- `learning_path` table (topic progression)

These require proper foreign keys, normalization, and indexing. You'll understand all of it by then.

---

## Quick Wins (Do These Today)

1. **Index your current schema**:
   ```bash
   sqlite3 codelens.db
   CREATE INDEX idx_student_timestamp ON sessions(student_id, timestamp);
   ```

2. **Replace Python loop** (in judgment.py):
   ```python
   # From:
   error_counts = {}
   for _, _, error_type, topic, _ in sessions:
       if error_type:
           error_counts[error_type] = error_counts.get(error_type, 0) + 1
   
   # To:
   cursor.execute("""
       SELECT error_type, COUNT(*) FROM sessions 
       WHERE student_id = ? AND timestamp > ?
       GROUP BY error_type
   """, (student_id, cutoff_time))
   error_counts = {row[0]: row[1] for row in cursor.fetchall()}
   ```

3. **Measure before/after**:
   - Time `get_student_context()` before indexing
   - Time after
   - Log it in your project notes

**Expected result**: 10-50x speedup on judgment layer.

---

## Resources

| Topic | Resource | Time |
|-------|----------|------|
| Indexes | https://www.sqlite.org/optoverview.html | 30 min |
| GROUP BY | https://sqlzoo.net/wiki/SELECT_Reference | 1 hour |
| JOINs | https://sqlzoo.net/wiki/SELECT_from_World_Tutorial | 2 hours |
| ACID | https://en.wikipedia.org/wiki/ACID | 20 min |
| Schema Design | https://www.sqlite.org/bestpractices.html | 1 hour |

**Total**: ~5 hours to get solid understanding + apply to CodeLens.
