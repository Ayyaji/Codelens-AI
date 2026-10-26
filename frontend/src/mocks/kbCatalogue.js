/** Approved interview notes and JSSATE Bengaluru entries. College text cites the public site or is marked as a placeholder. */

export function catalogue({ teacher, ago, hours }) {
  const at = (days) => ago(hours(24 * days));
  function item({ days = 3, ...fields }) {
    const created_at = at(days);
    return {
      tags: [],
      difficulty: "medium",
      type: "concept",
      source: "textbook",
      origin: "teacher",
      status: "approved",
      proposed_by: teacher,
      proposer_name: "Meera Rao",
      proposer_role: "teacher",
      reviewed_by: teacher,
      reviewed_at: created_at,
      reject_reason: null,
      created_at,
      updated_at: created_at,
      ...fields,
      query: fields.title,
    };
  }

  return [
    item({
      id: "kb_strings",
      days: 4,
      title: "Strings: index, slice, and immutability",
      topic: "Strings",
      tags: ["strings", "dsa"],
      difficulty: "easy",
      content: `A string is a sequence of characters with **O(1)** indexing and **O(k)** slicing of a length-k piece.

In Python and Java the string itself is immutable. Concatenating in a loop copies the growing result and becomes **O(n²)**. Build with a buffer (\`list\` plus \`join\`, or \`StringBuilder\`) and you stay linear.

Two string problems that are not the same:

- Anagrams care about character counts. A length-26 count, or a sort, is enough.
- A subsequence keeps order and can skip. A substring cannot skip.

Comparing strings is **O(n)** in the worst case, not **O(1)**, even when the language hides the loop.`,
    }),
    item({
      id: "kb_hash_map",
      days: 5,
      title: "Hash maps: expected constant time",
      topic: "Hashing",
      tags: ["hashing", "dsa"],
      difficulty: "medium",
      content: `A hash map stores a key by \`hash(key) mod capacity\`. A good hash plus a load factor kept under a constant gives **expected O(1)** for insert, lookup, and delete.

Collisions are real. Chaining puts several keys in one bucket. Open addressing probes other slots. Either way the **worst case is O(n)** when every key collides. Say "expected O(1)" in an interview, and name the worst case if they ask.

A hash map does not keep keys sorted. Range queries ("smallest key ≥ x") want a balanced tree. A hash set answers membership. It does not answer "what is next".

Do not hash a mutable object and then change the fields that went into the hash. The entry becomes unreachable.`,
    }),
    item({
      id: "kb_window",
      days: 6,
      title: "Sliding window on a contiguous range",
      topic: "Sliding window",
      tags: ["sliding-window", "dsa"],
      difficulty: "medium",
      content: `A sliding window is a contiguous subarray or substring, with a left and a right index.

The invariant is what the window currently satisfies: a sum, a distinct-character count, or a frequency map. Move \`right\` to grow. Move \`left\` only while the invariant is broken. Each index enters once and leaves once, so the scan is **O(n)** after the map updates, which are expected O(1) per step.

Fixed length (size k) is the easy case: add \`a[right]\`, remove \`a[right - k]\`. Variable length is the one people under-move. If \`left\` jumps by k instead of by one, you skip feasible windows.

The window is the wrong tool when the elements you want are not contiguous. That is a subsequence problem, usually DP or two pointers after sorting.`,
    }),
    item({
      id: "kb_recursion",
      days: 7,
      title: "Recursion: a smaller call and a base case",
      topic: "Recursion",
      tags: ["recursion", "dsa"],
      difficulty: "easy",
      content: `A recursive function must do two things. It must stop on a base case. It must call itself on a strictly smaller input, or it never reaches that base case.

The call stack stores every frame. Depth n uses **O(n)** extra memory even when the "algorithm" looks like it uses none. A skewed tree or a list walked by recursion can overflow the stack. An explicit stack makes the same control flow visible and bounded by the heap.

Naive Fibonacci (\`F(n) = F(n-1) + F(n-2)\` with no memory) is exponential because the same arguments are solved again. Memoizing each n, or filling an array from the bottom, makes it **O(n)**. Recursion is not slow. Repeated work is slow.`,
    }),
    item({
      id: "kb_trees",
      days: 8,
      title: "Binary trees: depth, height, and traversals",
      topic: "Trees",
      tags: ["trees", "dsa"],
      difficulty: "easy",
      content: `A binary tree node has at most two children. Depth of the root is 0. The height of a node is the number of edges on the longest path down to a leaf, so a leaf has height 0.

- Preorder: node, left, right. Useful for copying a tree.
- Inorder: left, node, right. On a BST this visits keys in sorted order.
- Postorder: left, right, node. Useful when children must be finished first (delete, evaluate).
- Level order: a queue, one depth at a time. That is BFS.

A full walk is **O(n)**. Recursing down a skewed tree uses **O(n)** stack. A balanced tree uses **O(log n)** stack.

"Balanced" is a property you have to maintain (AVL, red-black) or accept that you do not have (a plain BST).`,
    }),
    item({
      id: "kb_bst",
      days: 9,
      title: "BST search follows one child",
      topic: "Trees",
      tags: ["trees", "bst", "dsa"],
      difficulty: "medium",
      content: `Search property: every key in the left subtree is less than the node, and every key in the right subtree is greater. Pick one side for duplicates and keep that rule everywhere.

Lookup then compares and throws away half the tree only when the tree is balanced. The cost is **O(h)**, and h is **O(log n)** only for a balanced tree. Inserting sorted keys into a plain BST produces a linked list, and lookup becomes **O(n)**.

Deletion has three cases: a leaf, one child, or two children. With two children, replace the node with its inorder successor (leftmost of the right subtree) or predecessor, then delete that node, which has at most one child.

Inorder traversal of a BST yields the sorted keys. If your answer needs the sorted order and you already have a BST, you do not sort again.`,
    }),
    item({
      id: "kb_graphs",
      days: 10,
      title: "Graphs: lists, BFS, and DFS",
      topic: "Graphs",
      tags: ["graphs", "dsa"],
      difficulty: "medium",
      content: `A graph is vertices plus edges. Use an adjacency list unless the graph is tiny and dense, where a matrix makes edge tests **O(1)**. A list uses **O(n + m)** memory. A matrix uses **O(n²)**.

BFS uses a queue. On an unweighted graph the first time you reach a node is a shortest path in hops. DFS uses a stack (or recursion). It does not give shortest paths.

Always keep a visited set, or a cycle will not terminate. On a directed graph, a node on the current recursion stack is a back edge (a cycle). A node that is finished is not. Three colours (unseen, in stack, done) make that check obvious.

Connected components on an undirected graph are a BFS or DFS from every unvisited node. Topological order exists only for a directed acyclic graph.`,
    }),
    item({
      id: "kb_dp",
      days: 11,
      title: "Dynamic programming is cached recurrence",
      topic: "Dynamic programming",
      tags: ["dp", "dsa"],
      difficulty: "hard",
      content: `DP applies when a problem has **optimal substructure** (the best answer uses best answers of smaller problems) and **overlapping subproblems** (the same smaller problem appears more than once).

Write the state first. Example, 0/1 knapsack: \`dp[i][w]\` is the best value using the first i items with capacity w.

\`dp[i][w] = max(dp[i-1][w], dp[i-1][w - weight[i]] + value[i])\` when the item fits, else the skip branch.

Top-down memo and bottom-up loops compute the same states. Bottom-up makes the order explicit. The time is the number of states times the work per state. For this knapsack that is **O(nW)**, which is not polynomial in the number of bits of W.

If there is no overlap, DP only adds a table. If the greedy choice can be proved, the table is unnecessary.`,
    }),
    item({
      id: "kb_bsearch",
      days: 12,
      title: "Binary search on a monotonic predicate",
      topic: "Binary search",
      tags: ["binary-search", "dsa"],
      difficulty: "medium",
      content: `Binary search needs a predicate that flips once from false to true (or the reverse) as the index grows. A sorted array is the common case. "Minimum speed such that we finish in time" is the same shape.

Keep an invariant. One form: the answer is in \`[lo, hi)\`, \`mid = lo + (hi - lo) // 2\` (the sum avoids overflow in fixed-width integers), and each step shrinks the range. Stop when \`lo == hi\`.

Off-by-one errors come from mixing inclusive and exclusive ends, or from returning \`mid\` before the range has collapsed. Test the empty range, a single element, the target at both ends, and a missing target.

The cost is **O(log n)** comparisons. It does not sort for you. If the array is unsorted, sort first or do not use it.`,
    }),
    item({
      id: "kb_lists",
      days: 13,
      title: "Linked lists trade index speed for splices",
      topic: "Linked lists",
      tags: ["linked-lists", "dsa"],
      difficulty: "easy",
      content: `A singly linked node holds a value and a \`next\` pointer. There is no index. Reaching the k-th node is **O(k)**.

Inserting or deleting after a node you already hold is **O(1)**: rewire two pointers. That is the only thing a list does better than a dynamic array. If you had to walk to that node first, the walk dominates.

A dummy head simplifies "delete the first real node" and "insert at the front" because the head pointer itself never needs a special case.

Reversing in place uses three pointers (previous, current, next). Cache \`next\` before you overwrite \`current.next\`. Losing that pointer loses the rest of the list.

A doubly linked list adds \`prev\`, which makes "delete this node" **O(1)** without a predecessor walk. It costs an extra pointer per node.`,
    }),
    item({
      id: "kb_heap",
      days: 14,
      title: "A binary heap is a complete tree in an array",
      topic: "Heaps",
      tags: ["heaps", "dsa"],
      difficulty: "medium",
      content: `A binary heap is a complete binary tree. Store it in an array. For a 0-based index i, the parent is \`(i - 1) // 2\` and the children are \`2i + 1\` and \`2i + 2\`.

A min-heap keeps every parent ≤ its children. The minimum is at index 0. It is not sorted anywhere else. Insert sifts up. Delete-min swaps the root with the last leaf and sifts down. Both are **O(log n)**.

Building a heap from n items by sifting down from the middle is **O(n)**, not **O(n log n)**. Heap sort then does n delete-mins and is **O(n log n)**.

Use a heap for "current best of many" (Dijkstra with a binary heap, merging k lists, top k). Use a sorted array only when you need the full order after every update.`,
    }),
    item({
      id: "kb_stack",
      days: 15,
      title: "Stacks are LIFO, queues are FIFO",
      topic: "Stacks",
      tags: ["stacks", "queues", "dsa"],
      difficulty: "easy",
      content: `A stack pushes and pops the same end. The last item in is the first item out. Call stacks, undo, DFS, and bracket matching are stacks.

A queue enqueues at one end and dequeues at the other. BFS, task schedulers, and producer/consumer buffers are queues. A ring buffer of fixed capacity does both ends in **O(1)** without shifting.

Two stacks implement a queue: push onto the inbox, and pop from the outbox. When the outbox is empty, pour the inbox over. Each element is moved at most once, so the amortized cost of a dequeue is **O(1)**.

Do not use a stack when the problem says "the oldest waiting item". That sentence is a queue.`,
    }),
    item({
      id: "kb_oop_encap",
      days: 16,
      title: "Encapsulation hides the representation",
      topic: "OOP",
      tags: ["oop", "encapsulation"],
      difficulty: "easy",
      content: `Encapsulation means other code cannot depend on how a value is stored. It depends on what the object lets it do.

A private field with a getter that returns the live internal list is not encapsulation. The caller can append to that list and break the object's invariant. Return a copy, or return a method that answers the question (\`size\`, \`contains\`) instead of the storage.

The point of the invariant is the set of states the object is allowed to be in. Constructors and mutators establish it. If every field is public, every caller is a mutator and the invariant cannot be stated.

This is separate from security. A private field in a typical language is a compile-time boundary, not a lock against a determined caller in the same process.`,
    }),
    item({
      id: "kb_oop_poly",
      days: 17,
      title: "Polymorphism is a runtime choice of method",
      topic: "OOP",
      tags: ["oop", "polymorphism"],
      difficulty: "medium",
      content: `Subtype polymorphism: code holds a base type (or an interface) and calls a method. The method that runs is the one on the **runtime** object, not the one written next to the variable's declared type.

Overloading is a different mechanism. The compiler picks an overload from the declared types of the arguments. It is resolved before the program runs. Calling it polymorphism in an interview without that distinction is how people lose the point.

A classic shape: a list of \`Shape\`, each with \`area()\`. The loop does not branch on the class name. Adding a new shape does not edit the loop. That is the open/closed idea in its small form.

If the branches are on a type tag you maintain yourself (\`if kind == "circle"\`), you have reimplemented the dispatch, and a forgotten tag is a bug the compiler will not see.`,
    }),
    item({
      id: "kb_dbms_acid",
      days: 18,
      title: "ACID is four promises of one transaction",
      topic: "DBMS",
      tags: ["dbms", "transactions"],
      difficulty: "medium",
      content: `A transaction is a unit of work the database treats as one.

- **Atomicity.** Every change in the transaction is kept, or none are. A crash in the middle does not leave a half-transfer.
- **Consistency.** The transaction moves the database from one valid state to another. The rules (keys, checks, foreign keys) hold at the boundaries.
- **Isolation.** Concurrent transactions do not see each other's half-finished work, up to the isolation level you actually set. Serializable is the strict reading. It is not what every engine uses as the default.
- **Durability.** Once the database acknowledges the commit, the result survives a crash. That acknowledgement waits for the log, not for a convenient moment.

ACID is about one database's transactions. It does not, by itself, describe a workflow spread across two services.`,
    }),
    item({
      id: "kb_dbms_index",
      days: 19,
      title: "Indexes speed reads and slow writes",
      topic: "DBMS",
      tags: ["dbms", "indexes"],
      difficulty: "medium",
      content: `An index is a second structure that maps a key to a row location. A B+ tree supports equality and range. A hash index supports equality. The table is still the source of the row.

A lookup that can walk the index is **O(log n)** in the index instead of a scan of the heap. The write path maintains every index on that table, so inserts, updates of indexed columns, and deletes get more expensive as indexes pile up.

A composite index \`(a, b, c)\` can serve a predicate on \`a\`, or on \`a\` then \`b\`. It does not serve a predicate on \`b\` alone. That is the leftmost-prefix rule.

An index is not free storage and it is not a constraint, except when you declare it unique. Unique is a constraint that happens to be implemented with an index.`,
    }),
    item({
      id: "kb_dbms_norm",
      days: 20,
      title: "Normalization removes a specific update bug",
      topic: "DBMS",
      tags: ["dbms", "normalization"],
      difficulty: "medium",
      content: `Normalize to stop the same fact being stored in two places that can disagree.

- **1NF.** Each column holds one value, and rows of a table have the same shape. A comma-separated list in a cell breaks this.
- **2NF.** No non-key column depends on only part of a composite key. Split the columns that depend on one piece of the key.
- **3NF.** No non-key column depends on another non-key column. If department name depends on department id, store the name once, in the department table.

Boyce-Codd is the stricter sibling of 3NF when a key overlaps a dependency. You can mention it. You do not need it to justify the first split.

Denormalize when a measured join is too slow and you accept the job of keeping the copies in sync. Doing it before the measurement is a guess.`,
    }),
    item({
      id: "kb_os_sched",
      days: 21,
      title: "A scheduler picks the next runnable thread",
      topic: "Operating systems",
      tags: ["os", "scheduling"],
      difficulty: "medium",
      content: `A runnable thread is one that could use the CPU now. A blocked thread is waiting for I/O, a lock, or a timer. The scheduler chooses which runnable thread runs on a core.

CPU-bound work uses the core for long stretches. I/O-bound work runs briefly and then waits. A time slice stops one thread from holding the core until it blocks.

Names worth keeping separate:

- **Waiting time.** Time spent runnable but not running.
- **Turnaround time.** From arrival to completion.
- **Response time.** From arrival to first run.

Round robin with a tiny quantum improves response and spends more time in context switches. A long quantum does the opposite. There is no universal quantum. Linux's general policy has changed over the years; describe the tradeoff, not a version number, unless the question names one.`,
    }),
    item({
      id: "kb_os_sync",
      days: 22,
      title: "A mutex has an owner. A semaphore has a count.",
      topic: "Operating systems",
      tags: ["os", "concurrency"],
      difficulty: "medium",
      content: `A mutex protects a critical section. The thread that locks it is the owner, and that thread unlocks it. It is not a counter for strangers to signal each other.

A semaphore is an integer with wait and signal. Wait decrements and blocks at zero. Signal increments and wakes a waiter. A counting semaphore tracks how many units of a resource remain. There is no owner.

A binary semaphore looks like a mutex and is not one, because any thread may signal it. Using it as a lock loses the "who may unlock" rule and makes errors harder to see.

Deadlock needs a cycle of waits. The usual four conditions are mutual exclusion, hold and wait, no preemption, and circular wait. Breaking any one of them is a prevention strategy. A lock order (always take A before B) breaks circular wait.`,
    }),
    item({
      id: "kb_os_mem",
      days: 23,
      title: "Virtual memory maps pages, it does not add RAM",
      topic: "Operating systems",
      tags: ["os", "memory"],
      difficulty: "medium",
      content: `Each process sees its own virtual addresses. The MMU, with a page table, turns a virtual page into a physical frame. Two processes can use the same virtual address for different frames.

A page fault happens when the mapping is missing or not resident. The OS may load the page from disk, or it may kill the process if the address was never valid. A fault is not automatically a bug in the program. A fault on an unmapped address usually is.

Thrashing is when the working set does not fit in RAM, so the machine spends its time moving pages instead of doing the work. Adding virtual address space does not fix that. Adding RAM, or touching less memory, does.

The TLB caches recent translations. That is why walking a huge array with a huge stride gets slower: you miss the TLB, not just the data cache.`,
    }),
    item({
      id: "kb_cn_tcp",
      days: 24,
      title: "TCP is a byte stream. UDP is a datagram.",
      topic: "Computer networks",
      tags: ["cn", "tcp", "udp"],
      difficulty: "easy",
      content: `TCP gives a connection and a reliable, ordered byte stream. Lost segments are retransmitted. The receiver's window and the sender's congestion window both limit how much may be in flight. Bytes are not messages: a single \`write\` can arrive as two reads, and two writes can arrive as one.

UDP sends datagrams. The network may drop, reorder, or duplicate them. There is no handshake and no congestion control in UDP itself. DNS queries and many real-time media flows use it because a late retransmission is useless or because the application has its own reliability.

"TCP is slower" is not a useful sentence. TCP spends packets on reliability and on not overwhelming the path. If you need those, you will rebuild them on top of UDP, which is what QUIC does.`,
    }),
    item({
      id: "kb_cn_http",
      days: 25,
      title: "HTTP is a request and a response",
      topic: "Computer networks",
      tags: ["cn", "http"],
      difficulty: "easy",
      content: `An HTTP exchange is a request (method, target, headers, optional body) and a response (status, headers, optional body). The status code is the server's classification: 2xx success, 3xx redirect, 4xx the client's request, 5xx the server failed while trying.

HTTP/1.1 and HTTP/2 run on TCP. HTTP/3 runs on QUIC, which runs on UDP. Saying "HTTP is TCP" is wrong for HTTP/3 and incomplete for the others: HTTP is the message format, TCP or QUIC is the transport.

Methods worth not mixing up: GET should not change server state. PUT replaces the resource at a known URL. POST sends a body to a handler, often creating something whose URL the server chooses. Idempotent means repeating the request leaves the same result. PUT and DELETE are defined that way. POST is not.

Headers are metadata. The body is the document. \`Content-Type\` says how to read the body.`,
    }),
    item({
      id: "kb_cn_dns",
      days: 26,
      title: "DNS looks up a name. It does not route the packet.",
      topic: "Computer networks",
      tags: ["cn", "dns"],
      difficulty: "easy",
      content: `DNS maps a name to records. An A record is an IPv4 address. An AAAA record is an IPv6 address. A CNAME is an alias to another name, which still has to be resolved.

A stub resolver on the laptop asks a recursive resolver. That resolver walks from the root to the TLD to the authoritative server unless the answer is cached. The TTL on the record is how long a cache may keep it. A long TTL makes renames slow. A tiny TTL makes the authoritative server busy.

Routing is a separate system. Once the address is known, routers forward the packet by their forwarding tables. Fixing a DNS record does not repair a route, and a routing change does not change what name a client resolves.

Most classic DNS queries use UDP port 53. Larger answers and transfers use TCP. DNSSEC adds signatures. It does not encrypt the lookup. DoH and DoT are the encrypted transports, and they are a different topic.`,
    }),
    item({
      id: "kb_sql_join",
      days: 27,
      title: "A WHERE on the outer side can erase a LEFT JOIN",
      topic: "SQL",
      tags: ["sql", "joins"],
      difficulty: "medium",
      type: "qa",
      content: `\`INNER JOIN\` keeps pairs that match. Rows on either side with no partner disappear.

\`LEFT JOIN\` keeps every left row. When the right side has no partner, the right columns are NULL.

The trap: a condition on a right-hand column in the \`WHERE\` clause runs after the join. \`WHERE right.id IS NOT NULL\`, or \`WHERE right.status = 'open'\`, throws away the unmatched left rows. The left join has become an inner join. Put that test in the \`ON\` clause if you still want the unmatched left rows.

\`WHERE\` filters rows after the join and before grouping. \`HAVING\` filters groups. A \`COUNT\` of a left-joined table should count a right-hand key, not \`COUNT(*)\`, or the unmatched left row counts as one.`,
    }),
    item({
      id: "kb_sql_sarg",
      days: 28,
      title: "A predicate the index cannot see",
      topic: "SQL",
      tags: ["sql", "indexes"],
      difficulty: "medium",
      content: `A B-tree index on \`created_at\` can serve \`created_at >= '2026-01-01'\`. It cannot serve \`YEAR(created_at) = 2026\` in the usual engines, because the index stores the column, not the function of the column. The planner scans.

The same idea: \`LIKE '%smith'\` cannot walk a normal name index, because the useful prefix is missing. \`LIKE 'smith%'\` can.

\`OR\` across two different columns often cannot be satisfied by one composite index. Two indexes combined, or a rewrite as \`UNION\`, is the usual way out. \`OR\` on the same column (\`status IN (...)\`) is a different, easier case.

Sargable means "the predicate can be answered by the index as it is stored." If you wrap the column, assume you turned the index off, then check the plan.`,
    }),
    item({
      id: "kb_sd_latency",
      days: 29,
      title: "Latency and throughput are different complaints",
      topic: "System design",
      tags: ["system-design"],
      difficulty: "easy",
      content: `Latency is how long one request waits. Throughput is how many requests finish per second. A system can have high throughput and terrible latency (a big batch that runs twice a day). It can have low latency and tiny throughput (one fast handler, no parallelism).

The tail matters more than the mean. If one dependency in the path has a 99th percentile of two seconds, users feel that, even when the average is 40 ms. Timeouts and retries that ignore this make the tail worse: everyone retries the same slow call.

Name the bottleneck before you add machines. If every request takes a lock on one row, more application servers wait in the same line. If the work is CPU on independent requests, more servers do help.

State the numbers you were given. If the prompt has no QPS and no payload size, say you are assuming them instead of inventing a precise capacity.`,
    }),
    item({
      id: "kb_sd_cache",
      days: 30,
      title: "A cache is a copy with a lifetime",
      topic: "System design",
      tags: ["system-design", "caching"],
      difficulty: "medium",
      content: `A cache holds a copy so the next reader skips the slow store. A hit is the copy. A miss loads the store and fills the cache. The TTL, or an explicit delete, bounds how stale the copy may be.

The hard part is invalidation. Write-through updates the store and the cache together. Write-behind updates the cache and flushes later, which can lose the write. Cache-aside is what most app code does: the app checks the cache, and on a miss reads the database and writes the cache.

A stampede is many misses for the same key at once, all hitting the database. A lock per key, or a short-lived "I am loading this" marker, collapses them into one load.

Do not cache something whose correct answer changes on every call (a one-time nonce, an authorization decision you are not allowed to reuse) just because the cache exists.`,
    }),
    item({
      id: "kb_sd_lb",
      days: 31,
      title: "A load balancer spreads load. It does not create it.",
      topic: "System design",
      tags: ["system-design"],
      difficulty: "easy",
      content: `A load balancer sends each connection or request to one of several healthy backends. Health checks take a dead backend out of rotation. Round robin, least connections, and hashing on a client key are policies, not virtues. Hashing matters when the same client should land on the same machine (a sticky session). Sticky sessions matter less when the session lives in a shared store.

The balancer is not capacity. If the database is the limit, balancing ten app servers does not raise the database's limit. If the app servers are stateless and the database can take the extra reads, it does.

Put TLS termination in one place on purpose. Terminating at the balancer lets it route on the HTTP path. Passing TCP through leaves TLS to the app. Either is valid. Say which one you mean.

One balancer is a single point of failure. A second one, with a shared virtual address or DNS, is the usual fix. Two balancers in front of one database still leave you with one database.`,
    }),
    item({
      id: "kb_qa_two_sum",
      days: 32,
      title: "Two sum: hash set or two pointers",
      topic: "Interview Q&A",
      tags: ["interview", "hashing", "two-pointers"],
      difficulty: "easy",
      type: "qa",
      content: `**Question.** Find two indexes whose values sum to a target.

If you may not reorder, and you need the indexes: one pass with a hash map from value to index. For each x, look up \`target - x\`. Expected **O(n)** time, **O(n)** memory.

If the array is sorted and you need any pair of values: left and right pointers. Advance the side that makes the sum too small or too large. **O(n)** after the sort, **O(1)** extra memory if you sort in place.

Do not use two pointers on an unsorted array unless you are allowed to sort it and you do not need the original indexes. Sorting destroys them unless you sort pairs of (value, index).`,
    }),
    item({
      id: "kb_qa_reverse",
      days: 33,
      title: "Reverse a linked list in place",
      topic: "Interview Q&A",
      tags: ["interview", "linked-lists"],
      difficulty: "easy",
      type: "qa",
      content: `**Question.** Reverse a singly linked list without a second list.

Keep \`prev = null\`, \`cur = head\`. While \`cur\` is not null: cache \`nxt = cur.next\`, point \`cur.next\` at \`prev\`, then step both forward (\`prev = cur\`, \`cur = nxt\`). Return \`prev\`.

The empty list and the one-node list both fall out of the loop correctly. The bug to avoid is overwriting \`cur.next\` before you have saved it.

Time **O(n)**, extra memory **O(1)**. The recursive version is the same rewiring and uses **O(n)** stack. Say that out loud if you pick recursion.`,
    }),
    item({
      id: "kb_qa_cycle",
      days: 34,
      title: "Floyd's cycle check uses two speeds",
      topic: "Interview Q&A",
      tags: ["interview", "linked-lists"],
      difficulty: "medium",
      type: "qa",
      content: `**Question.** Does this linked list contain a cycle, using O(1) extra memory?

Move \`slow\` one step and \`fast\` two steps. If there is no cycle, \`fast\` reaches null. If there is a cycle, \`fast\` laps \`slow\` and they meet.

To find the start of the cycle, reset one pointer to the head and advance both one step at a time. They meet at the start. The proof is the usual modular arithmetic: the meeting point is a multiple of the cycle length away from the head's entry.

A hash set of seen nodes also works and uses **O(n)** memory. Offer it first if the interviewer did not constrain memory, then give Floyd when they do.`,
    }),
    item({
      id: "kb_qa_brackets",
      days: 35,
      title: "Balanced brackets are a stack of expectations",
      topic: "Interview Q&A",
      tags: ["interview", "stacks"],
      difficulty: "easy",
      type: "qa",
      content: `**Question.** Are these brackets balanced?

Scan left to right. An opening bracket pushes the closing bracket you now expect. A closing bracket must equal the top of the stack, which you then pop. The string is balanced when the stack is empty at the end and you never mismatched.

\`([]{})\` works. \`([)]\` fails when \`)\` arrives and the top expects \`]\`. A leftover opening bracket fails the empty-stack check.

Time **O(n)**, memory **O(n)** in the worst case (all openers). A counter is enough only for a single bracket type. Mixed types need the stack, or \`([)]\` looks balanced to three independent counters.`,
    }),
    item({
      id: "kb_qa_lru",
      days: 36,
      title: "An LRU cache is a map plus an order",
      topic: "Interview Q&A",
      tags: ["interview", "hashing", "system-design"],
      difficulty: "medium",
      type: "qa",
      content: `**Question.** Design a cache with O(1) get and put that evicts the least recently used key.

You need two structures. A hash map gives O(1) lookup from key to node. A doubly linked list keeps usage order: the head is most recent, the tail is least recent.

Get: find the node, move it to the head. Put: update or insert at the head. If the size exceeds capacity, remove the tail and delete that key from the map. A dummy head and tail remove the edge cases.

Expected time **O(1)** per operation because the map is a hash map and the list rewires a constant number of pointers. One structure alone is not enough: a hash map has no order, and a list has no O(1) lookup.`,
    }),
    item({
      id: "kb_qa_deadlock",
      days: 37,
      title: "Deadlock is a cycle of waits",
      topic: "Interview Q&A",
      tags: ["interview", "os"],
      difficulty: "medium",
      type: "qa",
      content: `**Question.** What is a deadlock, and how do you avoid one?

A deadlock is a set of threads that each hold something another in the set needs, so none can run. All four of these are present: mutual exclusion, hold and wait, no preemption of the lock, and a circular wait.

Prevention that interviews expect: acquire locks in a global order, so a cycle cannot form. The alternative of "try-lock and back off" is deadlock avoidance by giving up, and it needs a story for livelock (everyone backing off together).

Detection is a wait-for graph and a cycle check. It does not by itself unblock anyone. You still have to abort a waiter.

A single lock cannot deadlock with itself unless the lock is not reentrant and the same thread takes it twice. Say which lock you mean.`,
    }),
    item({
      id: "kb_qa_rest",
      days: 38,
      title: "PUT replaces. POST submits.",
      topic: "Interview Q&A",
      tags: ["interview", "http"],
      difficulty: "easy",
      type: "qa",
      content: `**Question.** When do you use PUT, and when POST?

PUT targets a URL that already names the resource and replaces that resource with the body. Sending the same PUT again leaves the same resource. That is idempotent.

POST targets a handler. The server decides what to do, often creating a new resource and returning its URL. Sending the same POST again may create a second resource. It is not idempotent.

PATCH is a partial change. It is not "the small PUT". Whether a given PATCH is idempotent depends on the patch format (\`set status = closed\` is; \`increment count\` is not).

GET must be safe to retry. If a GET charges a card, the bug is the method, not the client that retried.`,
    }),
    item({
      id: "kb_qa_isolation",
      days: 39,
      title: "Isolation levels name which anomalies remain",
      topic: "Interview Q&A",
      tags: ["interview", "dbms"],
      difficulty: "hard",
      type: "qa",
      content: `**Question.** What do read phenomena have to do with isolation?

Under weak locking, concurrent transactions can:

- **Dirty read** a row another transaction has changed and not committed.
- **Non-repeatable read** the same row twice and see two committed values.
- **Phantom read** the same predicate twice and see a new row appear.

Read committed forbids dirty reads and still allows the other two. Repeatable read, in the textbook definition, also stabilizes rows you already read. Serializable forbids all three.

Engines do not all use the textbook names the same way. PostgreSQL's repeatable read is snapshot isolation and already prevents phantoms in the SQL-standard sense. If you name an engine, name its behaviour. If you do not, give the textbook definitions and stop.`,
    }),
    item({
      id: "kb_col_identity",
      days: 2,
      title: "JSSATE Bengaluru: what the public site states",
      topic: "College",
      tags: ["jssateb", "college"],
      difficulty: "easy",
      type: "college",
      source: "web",
      content: `JSS Academy of Technical Education, Bengaluru (JSSATEB) states the following on its public homepage.

- Established in 1997 in Bengaluru, under JSS Mahavidyapeetha, Mysuru.
- The homepage credits the institution to the vision of its President, His Holiness Jagadguru Sri Shivarathri Deshikendra Mahaswamiji.
- Approved by AICTE, New Delhi. Recognized under UGC 2(f). Affiliated to Visvesvaraya Technological University (VTU), Belagavi. Recognized by the Government of Karnataka.
- The campus is described as 21.17 acres on the south-western edge of Bengaluru.

Homepage vision: "To be among the finest Institutions providing Engineering and Management Education empowered with research, innovation and entrepreneurship."

Homepage mission: excellence in teaching and learning and personality development; research, innovation and entrepreneurship; highest ethical standards.

Source: [jssateb.ac.in](https://www.jssateb.ac.in/). Quote the page again before you treat a ranking or an accreditation window as still current. The homepage lists several of those with their own dates.`,
    }),
    item({
      id: "kb_col_campus",
      days: 2,
      title: "JSSATE Bengaluru: campus address and phones",
      topic: "College",
      tags: ["jssateb", "college"],
      difficulty: "easy",
      type: "college",
      source: "web",
      content: `Address printed on the public homepage:

JSS Academy of Technical Education, JSSATE-B Campus, Dr. Vishnuvardhan Road, Uttarahalli–Kengeri Main Road, Srinivaspura Post, Bengaluru 560060, Karnataka, India.

Phones printed there: 080-2861 2565 and 080-2861 1702. Fax: 080-2861 2706 and 080-2861 2646.

Email addresses printed there: info@jssateb.ac.in and principal@jssateb.ac.in.

Admissions 2026–27 contacts printed on the same homepage: 9448234414, 9900928583, 9916253458, and also +91 97420 26363 and +91 99162 53458.

The homepage also says lecture halls have LED projectors and internet, the library has an e-learning facility, there are four auditoriums, hostel and transport on selected routes, and labs in the departments. It does not list lab inventories on that page.

Source: [jssateb.ac.in](https://www.jssateb.ac.in/).`,
    }),
    item({
      id: "kb_col_programs",
      days: 3,
      title: "JSSATE Bengaluru: programs named on the homepage",
      topic: "College",
      tags: ["jssateb", "college", "programs"],
      difficulty: "easy",
      type: "college",
      source: "web",
      content: `The homepage says JSSATEB offers B.E. courses in 8 branches: Civil, CSE, CSE (AI & ML), ECE, EIE, ISE, RA, and Mechanical. In that sentence the site writes "RA" and does not spell the abbreviation out. Do not expand it in a student answer unless a department page does.

It says six disciplines are NBA accredited, and it also prints dated windows, including EIE up to 30.06.2025 and CSE, ECE, ISE, Civil, and Mechanical from 01.07.2020 to 30.06.2023. Those windows are not all current. Check the latest NBA letter before you tell a student a branch is accredited today.

PG courses named there: MBA, M.Tech in VLSI Design and Embedded Systems, M.Tech in Thermal Engineering, M.Tech in Data Science, and MCA.

VTU-recognized research centres named there: CSE, ME, IEM, ECE, EIE, Civil, MBA, Mathematics, Physics, and Chemistry, leading to Ph.D. and M.S. (Engg). The page says 32 research scholars had been awarded a Ph.D. as of that text.

A highlights line says 78 faculty with Ph.D.s, average faculty experience of more than 15 years, and 300 Mbps internet, in three academic blocks.

Source: [jssateb.ac.in](https://www.jssateb.ac.in/).`,
    }),
    item({
      id: "kb_col_place_process",
      days: 3,
      title: "JSSATE Bengaluru: what the placement page says happens",
      topic: "College",
      tags: ["jssateb", "college", "placements"],
      difficulty: "easy",
      type: "college",
      source: "web",
      content: `The Training and Placement page says the cell helps students build careers in companies in India and abroad, and that it handles campus placements for UG and PG graduating students.

It says the infrastructure supports written tests, group discussions, pre-placement talks, and interviews, according to what each company needs.

Facilities it states in numbers:

- Computer labs with 300 systems and 150 webcams for webcam-proctored online tests.
- Two seminar halls that can each seat 200 students for pre-placement presentations.

Activities it lists: aptitude training, soft skills, group discussions, talks by company staff, mock interviews, company-specific training for final-year students before MNC visits, and workshops on personality, communication, time, and memory. It also says the cell arranges expert lectures with HODs, and industrial or professional tours for pre-final and final-year students.

On internships, the page says the cell shares openings in organisations associated with the institute, and that departments have signed MoUs. It does not name those companies in the text.

It does not publish a CGPA cutoff, a backlog rule, or a registration deadline on this page. Use the eligibility placeholder for those. Do not invent them.

Source: [jssateb.ac.in/placement](https://www.jssateb.ac.in/placement).`,
    }),
    item({
      id: "kb_col_place_office",
      days: 4,
      title: "JSSATE Bengaluru: placement office as published",
      topic: "College",
      tags: ["jssateb", "college", "placements"],
      difficulty: "easy",
      type: "college",
      source: "web",
      content: `The placement page names Dr. Sharana Basavana Gowda as Placement Officer and Training and Placement Officer. The committee table lists him as Associate Professor, CSE.

Contacts printed on that page:

- Mobile 9448771562
- Phone 080-28612565 / 28611702, extension 174 / 700
- placements@jssateb.ac.in
- jssate.placement@gmail.com

The advisory board table on the same page names Dr. P Mallu (Principal, JSSATE Bengaluru), Mrs. Gurpreeth Jaggi (BETSOL), Mrs. Parameshwari (NextFirst Engineering Technologies), Er. Mohan Rao (INSTRUCT), Mr. Girish Hiremath (GINSERV), Mrs. Anitha Kale (SIEC), Dr. Sharana Basavana Gowda, and two third-year students, Ms. Merllin M (CSE) and Mr. Abhishek N (CE).

The training and placement committee table lists coordinators for ME, CSE, ISE, ECE, IEM, EIE, CE, and MBA. Copy a name from that table when you need it. Do not add people who are not on it.

Source: [jssateb.ac.in/placement](https://www.jssateb.ac.in/placement).`,
    }),
    item({
      id: "kb_col_stats_placeholder",
      days: 1,
      title: "Placeholder: placement statistics",
      topic: "College",
      tags: ["jssateb", "college", "placeholder", "placements"],
      difficulty: "easy",
      type: "college",
      source: "teacher",
      content: `**Placeholder. Do not invent counts.**

The public placement page shows summary counters for companies, offers, and placement percentage that render as 0 in the page text, next to a highest-package line. That banner is not a reliable statistic. The same page links to "Placement Statistics" for 2023, 2018, and 2017 without putting those tables in the article text.

Fill this note from the current statistics file the placement office publishes. Until then, leave the numbers blank.

- Academic year:
- Students eligible:
- Students placed:
- Offers:
- Median or average package, if the document actually prints one:
- Highest package, if the document actually prints one:
- Source file and date you copied:

Source to open: [jssateb.ac.in/placement](https://www.jssateb.ac.in/placement).`,
    }),
    item({
      id: "kb_col_eligibility_placeholder",
      days: 1,
      title: "Placeholder: placement eligibility rules",
      topic: "College",
      tags: ["jssateb", "college", "placeholder", "placements"],
      difficulty: "easy",
      type: "college",
      source: "teacher",
      content: `**Placeholder. The public placement page does not state a CGPA cutoff, a backlog limit, or a registration rule.**

Do not copy a cutoff from another college or from memory. Ask the placement office and paste the current rule.

- Who may register (batch, program, backlogs):
- Minimum CGPA or percentage, if one exists:
- What happens when a student already holds an offer:
- Dream or core policy, if the office has one in writing:
- Last date to register:
- Document you copied, and the date:

The page does say the cell handles UG and PG graduating students, and that company-specific training is run for final-year students. That is not an eligibility rule.

Source to check: [jssateb.ac.in/placement](https://www.jssateb.ac.in/placement).`,
    }),
    item({
      id: "kb_col_recruiters_placeholder",
      days: 1,
      title: "Placeholder: recruiter patterns",
      topic: "College",
      tags: ["jssateb", "college", "placeholder", "placements"],
      difficulty: "easy",
      type: "college",
      source: "teacher",
      content: `**Placeholder. Do not turn alumni testimonials into a recruiter list.**

The homepage has a "Top recruiters" band of images. The text of the page does not name those companies. The placement page includes student testimonials that mention employers. A testimonial is one person's account, not the office's list, and it is not a pattern.

Paste the list the placement office actually maintains.

- Academic year:
- Company:
- Role or domain:
- Programs they interviewed:
- Rounds they used (the page's general list is written test, group discussion, pre-placement talk, interview):
- Source document and date:

Until this table is filled, tell students to look at the current placement brochure rather than at a chat answer.`,
    }),
    item({
      id: "kb_col_syllabus_placeholder",
      days: 1,
      title: "Placeholder: semester to topic map",
      topic: "College",
      tags: ["jssateb", "college", "placeholder", "syllabus"],
      difficulty: "easy",
      type: "college",
      source: "teacher",
      content: `**Placeholder. Map subjects from the current VTU scheme. Do not guess course codes.**

JSSATEB is affiliated to VTU, Belagavi. The homepage names the programs. It does not print the semester-wise syllabus. Fill one row per subject you actually teach or can point at in the scheme PDF.

- Program (for example CSE):
- Scheme year:
- Semester:
- Course code and title, copied from the scheme:
- KB topics that match it (arrays, SQL, operating systems, …):
- Link to the scheme PDF:

Suggested buckets, which are not a syllabus: programming and DSA, DBMS and SQL, operating systems, computer networks, OOP, and the placement aptitude the T&P page already describes.

Source for the affiliation: [jssateb.ac.in](https://www.jssateb.ac.in/).`,
    }),
    item({
      id: "kb_col_faq",
      days: 5,
      title: "JSSATE Bengaluru: department FAQ from the public pages",
      topic: "College",
      tags: ["jssateb", "college", "faq"],
      difficulty: "easy",
      type: "college",
      source: "web",
      content: `Answers below are only what the public homepage or placement page states. Anything else belongs in a placeholder, not in a guess.

**Which university awards the degree?** The homepage says the college is affiliated to VTU, Belagavi.

**Which undergraduate branches does the homepage list?** Civil, CSE, CSE (AI & ML), ECE, EIE, ISE, RA, and Mechanical.

**Does the site list a robotics expansion of "RA"?** Not in the sentence that lists the eight branches. Leave the abbreviation as printed.

**Where is the campus?** Dr. Vishnuvardhan Road, Uttarahalli–Kengeri Main Road, Srinivaspura Post, Bengaluru 560060.

**Who do employers write to?** placements@jssateb.ac.in, and the placement page also prints jssate.placement@gmail.com. The officer named there is Dr. Sharana Basavana Gowda.

**What should a student not expect this note to know?** Current CGPA cutoffs, this year's recruiter list, live NBA status past the dated windows, and fee tables. Those are not in the pages this note cites.

Sources: [jssateb.ac.in](https://www.jssateb.ac.in/) and [jssateb.ac.in/placement](https://www.jssateb.ac.in/placement).`,
    }),
  ];
}
