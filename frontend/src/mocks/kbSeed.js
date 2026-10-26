/**
 * Starter library so each review tab, source, and type has something to show.
 * The interview catalogue is added on top of these ids.
 */

import { catalogue } from "./kbCatalogue";

function note(fields) {
  return {
    tags: [],
    difficulty: "medium",
    type: "concept",
    origin: "teacher",
    reviewed_by: null,
    reviewed_at: null,
    reject_reason: null,
    ...fields,
    query: fields.query === undefined ? fields.title : fields.query,
    updated_at: fields.updated_at || fields.created_at,
  };
}

export function buildKbSeed({ ada, teacher, ago, minutes, hours }) {
  return [
    note({
      id: "kb_none",
      title: "Subscripting None raises TypeError",
      content:
        "Subscripting `None` raises **TypeError** because `None` is not a sequence or a mapping.\n\nThe usual miss is the line above the brackets. A call returned `None` (an implicit return, a missing `return`, or a method that mutates and returns nothing) and the next line indexes it.\n\nCheck the value before using brackets. Editing only the bracket line hides the `None`.",
      topic: "Python",
      tags: ["python", "errors"],
      difficulty: "easy",
      source: "web",
      type: "concept",
      origin: "student",
      status: "pending",
      proposed_by: ada,
      proposer_name: "Ada Lovelace",
      proposer_role: "student",
      created_at: ago(minutes(30)),
    }),
    note({
      id: "kb_where",
      title: "WHERE runs after the join",
      content:
        "`WHERE` filters rows after a join has combined them, and before `GROUP BY`. `HAVING` filters groups.\n\nA condition in the wrong clause keeps the extra joined rows. That shows up as a concept gap on SQL, not as a syntax error.",
      topic: "SQL",
      tags: ["sql", "joins"],
      difficulty: "medium",
      source: "web",
      type: "qa",
      origin: "student",
      status: "pending",
      proposed_by: ada,
      proposer_name: "Ada Lovelace",
      proposer_role: "student",
      query: "When does WHERE run against a join?",
      created_at: ago(hours(3)),
    }),
    note({
      id: "kb_hash_ai",
      title: "A hash map is not sorted",
      content:
        "A hash map answers \"is this key present?\" in expected **O(1)** time. It does not keep keys in sorted order.\n\nCollisions are chained or probed. The worst case is **O(n)** when every key lands in one bucket. Interview answers should say expected O(1), and name the worst case.\n\nUse a tree map only when you need ordered keys.",
      topic: "Hashing",
      tags: ["hashing", "dsa"],
      difficulty: "easy",
      source: "ai",
      type: "concept",
      origin: "ai",
      status: "pending",
      proposed_by: null,
      proposer_name: "CodeLens guide",
      proposer_role: "ai",
      created_at: ago(hours(5)),
    }),
    note({
      id: "kb_arrays",
      title: "Arrays: index arithmetic and contiguous memory",
      content:
        "An array stores elements in one contiguous block. The address of index `i` is `base + i * size`.\n\n- Reading or writing `a[i]` is **O(1)**.\n- Inserting or deleting in the middle shifts later elements, so it is **O(n)**.\n- A dynamic array (`list` in Python, `vector` in C++) appends in amortized **O(1)** because it grows geometrically, not by one slot.\n\nIf the problem says the array is sorted, binary search is the first tool. If it is not sorted, do not pretend that index order is key order.",
      topic: "Arrays",
      tags: ["arrays", "dsa"],
      difficulty: "easy",
      source: "textbook",
      type: "concept",
      origin: "teacher",
      status: "approved",
      proposed_by: teacher,
      proposer_name: "Meera Rao",
      proposer_role: "teacher",
      reviewed_by: teacher,
      reviewed_at: ago(hours(20)),
      created_at: ago(hours(26)),
    }),
    note({
      id: "kb_two",
      title: "Two pointers on a sorted pair",
      content:
        "On a sorted array, put one index at the start and one at the end.\n\n- If the sum is too small, advance the left index.\n- If the sum is too large, retreat the right index.\n- Each step throws away a pair that cannot be the answer, so the scan is **O(n)** after the **O(n log n)** sort.\n\nThis is the right shape for pair-sum and for the container-with-most-water style problems. It is the wrong shape when the array is unsorted and you are not allowed to reorder it: use a hash set then.",
      topic: "Two pointers",
      tags: ["two-pointers", "dsa"],
      difficulty: "easy",
      source: "textbook",
      type: "concept",
      origin: "teacher",
      status: "approved",
      proposed_by: teacher,
      proposer_name: "Meera Rao",
      proposer_role: "teacher",
      reviewed_by: teacher,
      reviewed_at: ago(hours(12)),
      created_at: ago(hours(18)),
    }),
    note({
      id: "kb_append",
      title: "Python append is always linear",
      content:
        "Every `list.append` copies the whole array, so a loop of `n` appends is always **O(n²)**.",
      topic: "Arrays",
      tags: ["python", "arrays"],
      difficulty: "easy",
      source: "web",
      type: "qa",
      origin: "student",
      status: "rejected",
      proposed_by: ada,
      proposer_name: "Ada Lovelace",
      proposer_role: "student",
      reviewed_by: teacher,
      reviewed_at: ago(hours(8)),
      reject_reason: "CPython over-allocates. A single append is amortized O(1), not always O(n). This note would teach the wrong bound.",
      created_at: ago(hours(10)),
    }),
    ...catalogue({ teacher, ago, hours }),
  ];
}
