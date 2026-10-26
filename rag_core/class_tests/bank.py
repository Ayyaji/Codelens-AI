"""Original starter questions teachers can drop into a class test.

Coding tasks are function-shaped and graded through the stdin/stdout sandbox.
Nothing here is copied from a published problem set. The stubs do not include
a working solution.
"""

from rag_core.class_tests.harness import starter_for

_NOTE = (
    " Write the function in Python and leave the `if __name__` block as it is. "
    "That block reads a JSON list of arguments from stdin and prints the return value. "
    "Bools print as true or false. Lists print as compact JSON."
)


def _coding(
    *,
    qid: str,
    skill: str,
    signature: str,
    prompt: str,
    visible: list[tuple[str, str]],
    hidden: list[tuple[str, str]],
    explanation: str,
) -> dict:
    return {
        "id": qid,
        "type": "coding",
        "topic": "DSA",
        "skill": skill,
        "prompt": prompt.strip() + _NOTE,
        "signature": signature,
        "language": "python",
        "starter_code": starter_for(signature),
        "visible_cases": [{"stdin": stdin, "expected": expected} for stdin, expected in visible],
        "hidden_cases": [{"stdin": stdin, "expected": expected} for stdin, expected in hidden],
        "explanation": explanation,
    }


def _mcq(
    *,
    qid: str,
    topic: str,
    skill: str,
    prompt: str,
    options: list[str],
    correct_index: int,
    explanation: str,
) -> dict:
    return {
        "id": qid,
        "type": "mcq",
        "topic": topic,
        "skill": skill,
        "prompt": prompt.strip(),
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation,
    }


CODING_BANK: list[dict] = [
    _coding(
        qid="dsa_second_largest",
        skill="arrays",
        signature="def second_largest(nums):",
        prompt=(
            "Return the second largest distinct value in `nums`. "
            "If fewer than two distinct values exist, return -1. "
            "`[4, 1, 4, 3]` has distinct values 4, 1, and 3, so the answer is 3."
        ),
        visible=[("[[4, 1, 4, 3]]", "3")],
        hidden=[("[[5]]", "-1"), ("[[9, 9, 8, 1]]", "8"), ("[[2, 2, 2]]", "-1")],
        explanation="One pass can track the largest value and the next distinct value.",
    ),
    _coding(
        qid="dsa_rotate_left",
        skill="arrays",
        signature="def rotate_left(nums, k):",
        prompt=(
            "Return a new list with `nums` rotated left by `k` places. "
            "`k` may be larger than the length. An empty list stays empty. "
            "Rotating `[1, 2, 3, 4]` left by 1 gives `[2, 3, 4, 1]`."
        ),
        visible=[("[[1, 2, 3, 4], 1]", "[2,3,4,1]")],
        hidden=[("[[1, 2, 3, 4], 5]", "[2,3,4,1]"), ("[[], 3]", "[]"), ("[[7, 8], 2]", "[7,8]")],
        explanation="Reduce k modulo the length, then split the list at that index.",
    ),
    _coding(
        qid="dsa_is_palindrome",
        skill="strings",
        signature="def is_palindrome(text):",
        prompt=(
            "Return true when `text` reads the same forwards and backwards "
            "after ignoring case and every character that is not a letter or digit. "
            "`A man, a plan, a canal: Panama` is a palindrome."
        ),
        visible=[('["A man, a plan, a canal: Panama"]', "true")],
        hidden=[('["race a car"]', "false"), ('["0P"]', "false"), ('["Was it a rat I saw?"]', "true")],
        explanation="Filter to lowercase letters and digits, then compare with the reverse.",
    ),
    _coding(
        qid="dsa_reverse_words",
        skill="strings",
        signature="def reverse_words(text):",
        prompt=(
            "Return the words of `text` in reverse order, separated by a single space. "
            "Treat any run of whitespace as one separator. "
            "`hello world` becomes `world hello`."
        ),
        visible=[('["hello world"]', "world hello")],
        hidden=[('["  a  b "]', "b a"), ('["solo"]', "solo"), ('["one two three"]', "three two one")],
        explanation="Split on whitespace, reverse the word list, and join with one space.",
    ),
    _coding(
        qid="dsa_two_sum",
        skill="hashing",
        signature="def two_sum(nums, target):",
        prompt=(
            "Return the indexes of the first two values in `nums` that add up to `target`. "
            "Each index may be used once. If no pair exists, return an empty list. "
            "`[2, 7, 11, 15]` and target 9 give `[0, 1]`."
        ),
        visible=[("[[2, 7, 11, 15], 9]", "[0,1]")],
        hidden=[("[[3, 2, 4], 6]", "[1,2]"), ("[[1, 2, 3], 7]", "[]"), ("[[0, 4, 3, 0], 0]", "[0,3]")],
        explanation="A map from value to index finds the complement in one pass.",
    ),
    _coding(
        qid="dsa_first_unique",
        skill="hashing",
        signature="def first_unique(text):",
        prompt=(
            "Return the first character of `text` that appears exactly once. "
            "If every character repeats, return an empty string. "
            "`aabbc` yields `c`."
        ),
        visible=[('["aabbc"]', "c")],
        hidden=[('["aabb"]', ""), ('["leetcode"]', "l"), ('["abba"]', "")],
        explanation="Count characters, then scan again for the first count of one.",
    ),
    _coding(
        qid="dsa_has_pair",
        skill="two pointers",
        signature="def has_pair(nums, target):",
        prompt=(
            "`nums` is sorted ascending. Return true when two different indexes add up to `target`. "
            "`[1, 2, 4, 6]` and 8 is true because 2 + 6 = 8."
        ),
        visible=[("[[1, 2, 4, 6], 8]", "true")],
        hidden=[("[[1, 2, 3], 6]", "false"), ("[[1, 1], 2]", "true"), ("[[1, 3, 5, 7], 10]", "true")],
        explanation="Move the left pointer up when the sum is too small, and the right pointer down when it is too large.",
    ),
    _coding(
        qid="dsa_unique_count",
        skill="two pointers",
        signature="def unique_count(nums):",
        prompt=(
            "`nums` is sorted ascending. Return how many distinct values it contains. "
            "`[1, 1, 2, 3, 3]` contains 3 distinct values."
        ),
        visible=[("[[1, 1, 2, 3, 3]]", "3")],
        hidden=[("[[]]", "0"), ("[[5, 5, 5]]", "1"), ("[[1, 2, 3]]", "3")],
        explanation="Walk the sorted list and count a value only when it differs from the one before it.",
    ),
    _coding(
        qid="dsa_valid_parens",
        skill="stacks",
        signature="def valid_parens(text):",
        prompt=(
            "Return true when every bracket in `text` is closed in order by the matching opener. "
            "The pairs are `()`, `[]`, and `{}`. An empty string is valid. "
            "`([])` is valid and `(]` is not."
        ),
        visible=[('["([])"]', "true")],
        hidden=[('["(]"]', "false"), ('[""]', "true"), ('["([)]"]', "false"), ('["()[]{}"]', "true")],
        explanation="Push opening brackets. A closer is valid only when it matches the top of the stack.",
    ),
    _coding(
        qid="dsa_next_greater_count",
        skill="stacks",
        signature="def next_greater_count(nums):",
        prompt=(
            "Return how many values have a strictly greater value somewhere to their right. "
            "In `[2, 1, 2, 4]` the first three do and the last does not, so the answer is 3."
        ),
        visible=[("[[2, 1, 2, 4]]", "3")],
        hidden=[("[[5, 4, 3]]", "0"), ("[[1, 2, 3]]", "2"), ("[[]]", "0")],
        explanation="A decreasing stack can find the next greater element for each index in linear time.",
    ),
    _coding(
        qid="dsa_find_index",
        skill="binary search",
        signature="def find_index(nums, target):",
        prompt=(
            "`nums` is sorted ascending and may contain duplicates. "
            "Return the first index of `target`, or -1 if it is missing. "
            "`[1, 3, 5, 7]` and 5 give 2."
        ),
        visible=[("[[1, 3, 5, 7], 5]", "2")],
        hidden=[("[[1, 3, 5, 7], 4]", "-1"), ("[[1, 1, 1], 1]", "0"), ("[[2, 4, 6, 8], 8]", "3")],
        explanation="Binary search, and when the middle matches, keep searching the left half for an earlier index.",
    ),
    _coding(
        qid="dsa_first_at_least",
        skill="binary search",
        signature="def first_at_least(nums, target):",
        prompt=(
            "`nums` is sorted ascending. Return the smallest index whose value is greater than or equal to `target`. "
            "If every value is smaller, return -1. "
            "`[1, 2, 2, 4]` and 2 give 1."
        ),
        visible=[("[[1, 2, 2, 4], 2]", "1")],
        hidden=[("[[1, 2, 2, 4], 3]", "3"), ("[[1, 2, 2, 4], 5]", "-1"), ("[[1, 2, 2, 4], 1]", "0")],
        explanation="This is the lower bound. Shrink the right side when the middle is already large enough.",
    ),
    _coding(
        qid="dsa_reverse_values",
        skill="linked list",
        signature="def reverse_values(nums):",
        prompt=(
            "`nums` holds the values of a singly linked list from head to tail. "
            "Return those values after reversing the list. "
            "`[1, 2, 3]` becomes `[3, 2, 1]`. Do not mutate the caller's list if you can avoid it."
        ),
        visible=[("[[1, 2, 3]]", "[3,2,1]")],
        hidden=[("[[]]", "[]"), ("[[8]]", "[8]"), ("[[1, 2, 3, 4]]", "[4,3,2,1]")],
        explanation="Walk the nodes once, pointing each next link at the previous node, and return the new head.",
    ),
    _coding(
        qid="dsa_tree_height",
        skill="trees",
        signature="def tree_height(node):",
        prompt=(
            "A node is `[value, left, right]` or null. "
            "Return the number of nodes on the longest path from this node down to a leaf. "
            "Null has height 0. A single node `[1, null, null]` has height 1. "
            "`[1, [2, null, null], [3, [4, null, null], null]]` has height 3."
        ),
        visible=[("[[1, [2, null, null], [3, [4, null, null], null]]]", "3")],
        hidden=[("[null]", "0"), ("[[1, null, null]]", "1"), ("[[5, [4, [3, null, null], null], null]]", "3")],
        explanation="The height is one plus the larger of the two children. A missing child contributes 0.",
    ),
    _coding(
        qid="dsa_climb_ways",
        skill="dynamic programming",
        signature="def climb_ways(n):",
        prompt=(
            "You climb a staircase of `n` steps and may take 1 or 2 steps at a time. "
            "Return how many distinct orders of steps reach the top. "
            "`n` is at least 0. There is 1 way to climb 1 step and 5 ways to climb 4."
        ),
        visible=[("[4]", "5")],
        hidden=[("[1]", "1"), ("[2]", "2"), ("[5]", "8"), ("[0]", "1")],
        explanation="The ways to reach step n are the ways to reach n-1 plus the ways to reach n-2. Keep only the last two counts.",
    ),
]


MCQ_BANK: list[dict] = [
    _mcq(
        qid="mcq_dsa_hash",
        topic="DSA",
        skill="hashing",
        prompt="After a hash table is built, looking up one key that is present is expected to take how long?",
        options=[
            "Constant time on average",
            "Linear time in the number of keys, always",
            "Logarithmic time, always",
            "Quadratic time, because of collisions",
        ],
        correct_index=0,
        explanation="A good hash spreads keys so a lookup inspects one bucket on average. Worst-case chains can be longer.",
    ),
    _mcq(
        qid="mcq_dsa_two_pointers",
        topic="DSA",
        skill="two pointers",
        prompt="A sorted array holds integers. Which task fits a pair of pointers that move toward each other?",
        options=[
            "Finding whether two values add up to a target, in linear time",
            "Building a heap from the array",
            "Counting inversions with a divide-and-conquer sort",
            "Printing every subset of the array",
        ],
        correct_index=0,
        explanation="If the sum is too small the left pointer moves right; if it is too large the right pointer moves left.",
    ),
    _mcq(
        qid="mcq_dsa_stack",
        topic="DSA",
        skill="stacks",
        prompt="Which job is a stack built for?",
        options=[
            "Checking that brackets close in the right order",
            "Always removing the smallest remaining item",
            "Looking up a key in constant time",
            "Serving requests in the order they arrived",
        ],
        correct_index=0,
        explanation="The most recent unmatched opener is the one a closer must match, which is last-in first-out.",
    ),
    _mcq(
        qid="mcq_dsa_binary",
        topic="DSA",
        skill="binary search",
        prompt="Binary search on an array is valid only when which property holds?",
        options=[
            "The array is sorted in the order the search uses",
            "The array length is a power of two",
            "Every value is unique",
            "The array is stored as a linked list",
        ],
        correct_index=0,
        explanation="Each probe throws away one half. That is safe only when the order tells you which half can still hold the target.",
    ),
    _mcq(
        qid="mcq_dsa_tree",
        topic="DSA",
        skill="trees",
        prompt="A balanced binary search tree stores n keys. The number of nodes on a path from the root to a leaf grows like what?",
        options=["O(log n)", "O(1)", "O(n)", "O(n log n)"],
        correct_index=0,
        explanation="Each step discards about half the remaining keys, so the height stays logarithmic.",
    ),
    _mcq(
        qid="mcq_time_nested",
        topic="complexity",
        skill="time complexity",
        prompt="A loop `i` runs n times, and inside it a loop `j` runs i times. The number of inner steps is on the order of what?",
        options=["O(n^2)", "O(n)", "O(log n)", "O(n log n)"],
        correct_index=0,
        explanation="The inner body runs 1 + 2 + ... + n times, which is n(n+1)/2, still quadratic.",
    ),
    _mcq(
        qid="mcq_space_copy",
        topic="complexity",
        skill="space complexity",
        prompt="An algorithm copies an input list of n items into a second list and then scans that copy. The extra memory is on the order of what?",
        options=["O(n)", "O(1)", "O(log n)", "O(n^2)"],
        correct_index=0,
        explanation="The second list holds n references. A few index variables do not change that linear extra space.",
    ),
    _mcq(
        qid="mcq_time_merge",
        topic="complexity",
        skill="time complexity",
        prompt="What is the worst-case running time of merge sort on n comparable items?",
        options=["O(n log n)", "O(n)", "O(n^2)", "O(log n)"],
        correct_index=0,
        explanation="Each level of merges does linear work, and there are log n levels, including the worst case.",
    ),
    _mcq(
        qid="mcq_time_append",
        topic="complexity",
        skill="time complexity",
        prompt="Appending one item to the end of a Python list is which cost, most of the time?",
        options=[
            "Amortized constant time",
            "Always linear in the current length",
            "Always logarithmic",
            "Quadratic, because the list is copied every time",
        ],
        correct_index=0,
        explanation="The list sometimes allocates a larger buffer and copies, but those copies are rare enough that each append averages out to constant time.",
    ),
    _mcq(
        qid="mcq_oop_encap",
        topic="OOP",
        skill="OOP",
        prompt="Encapsulation in an object-oriented design means which of these?",
        options=[
            "Keeping an object's fields behind methods that decide how they change",
            "A function calling itself until a base case",
            "Storing rows so that a key lookup is fast",
            "Two processes waiting on each other's locks",
        ],
        correct_index=0,
        explanation="Callers use the methods. They do not reach in and rewrite the fields on their own.",
    ),
    _mcq(
        qid="mcq_oop_inherit",
        topic="OOP",
        skill="OOP",
        prompt="Inheritance is best described as which relationship?",
        options=[
            "A class reuses another class's fields and methods and may add its own",
            "Two classes that never share a name",
            "A function that is passed as a value",
            "A table that references its own primary key",
        ],
        correct_index=0,
        explanation="The subclass starts from the superclass and extends or overrides behaviour.",
    ),
    _mcq(
        qid="mcq_oop_poly",
        topic="OOP",
        skill="OOP",
        prompt="Which sentence is polymorphism?",
        options=[
            "The same method call can run a different implementation depending on the object's class",
            "Every class has exactly one method",
            "A list may hold only integers",
            "A query returns rows in primary-key order",
        ],
        correct_index=0,
        explanation="Callers depend on the method name. The class of the object picks the body that runs.",
    ),
    _mcq(
        qid="mcq_oop_static",
        topic="OOP",
        skill="OOP",
        prompt="A helper needs no data from a particular object. Where does it belong?",
        options=[
            "A static method, or a plain function, that does not take the instance",
            "An instance method that ignores self but still requires an object",
            "The constructor, so it runs on every object",
            "A private field, because methods cannot be shared",
        ],
        correct_index=0,
        explanation="If there is no instance to read, requiring one only makes the call harder.",
    ),
    _mcq(
        qid="mcq_dbms_pk",
        topic="DBMS",
        skill="DBMS",
        prompt="What does a primary key guarantee for each row?",
        options=[
            "The value is unique and not null",
            "The row is stored in a hash index only",
            "Other tables cannot reference the row",
            "The column is updated on every write",
        ],
        correct_index=0,
        explanation="A primary key identifies one row. Null would leave that identity unknown, and a duplicate would not identify one row.",
    ),
    _mcq(
        qid="mcq_dbms_3nf",
        topic="DBMS",
        skill="DBMS",
        prompt="Third normal form is mainly concerned with removing which kind of dependency?",
        options=[
            "A non-key column that depends on another non-key column",
            "Any join between two tables",
            "Every index on a foreign key",
            "Duplicate rows that an application inserted on purpose",
        ],
        correct_index=0,
        explanation="After second normal form, third normal form removes transitive dependencies so non-key facts describe the key.",
    ),
    _mcq(
        qid="mcq_dbms_index",
        topic="DBMS",
        skill="DBMS",
        prompt="A B-tree index on a column most directly speeds up which work?",
        options=[
            "Equality and range lookups on that column",
            "Every full-table scan, by skipping the heap",
            "Inserts, which never touch the index",
            "Sorting an unrelated column with no extra work",
        ],
        correct_index=0,
        explanation="The tree finds a key or a range without reading every row. Writes have to maintain the tree, so they can get slower.",
    ),
    _mcq(
        qid="mcq_dbms_acid",
        topic="DBMS",
        skill="DBMS",
        prompt="In ACID, the A is atomicity. What does that promise?",
        options=[
            "A transaction's writes all land, or none of them do",
            "The database picks a serial order that ignores the transaction",
            "Committed data is erased when the session ends",
            "Two transactions may overwrite each other freely",
        ],
        correct_index=0,
        explanation="Atomicity is all-or-nothing. Isolation, consistency, and durability are the other three promises.",
    ),
    _mcq(
        qid="mcq_os_switch",
        topic="OS",
        skill="OS",
        prompt="A context switch is which action?",
        options=[
            "Saving one thread's registers and restoring another's so it can run",
            "Compiling a source file into an executable",
            "Moving a row from one table to another",
            "Opening a TCP connection to a DNS server",
        ],
        correct_index=0,
        explanation="The CPU runs one thread at a time. Switching means putting the current state aside and loading the next.",
    ),
    _mcq(
        qid="mcq_os_deadlock",
        topic="OS",
        skill="OS",
        prompt="Which condition is required before a deadlock can exist?",
        options=[
            "A cycle of threads, each waiting for a resource the next one holds",
            "Every thread running at the same priority",
            "A disk that is more than half full",
            "More than one CPU in the machine",
        ],
        correct_index=0,
        explanation="Circular wait is one of the classic deadlock conditions, together with mutual exclusion, hold-and-wait, and no preemption.",
    ),
    _mcq(
        qid="mcq_os_virtual",
        topic="OS",
        skill="OS",
        prompt="Virtual memory lets a process do which of these?",
        options=[
            "Use a larger address space than the physical RAM it currently occupies",
            "Skip system calls when it reads a file",
            "Share its registers with every other process",
            "Disable page faults for the whole machine",
        ],
        correct_index=0,
        explanation="Pages that are not in RAM can live on disk. The process still sees one contiguous address space.",
    ),
    _mcq(
        qid="mcq_cn_tcp",
        topic="CN",
        skill="CN",
        prompt="What does TCP add on top of an unreliable network?",
        options=[
            "A byte stream that is delivered reliably and in order",
            "A guarantee that packets take the shortest physical path",
            "Encryption of every bit, with no extra protocol",
            "A replacement for IP addresses",
        ],
        correct_index=0,
        explanation="TCP retransmits lost data and puts bytes back in order. It does not choose the geographic path, and it is not itself TLS.",
    ),
    _mcq(
        qid="mcq_cn_dns",
        topic="CN",
        skill="CN",
        prompt="DNS is used to do which lookup?",
        options=[
            "Turn a host name into an address",
            "Choose the window size of a TCP connection",
            "Store the rows of a relational table",
            "Schedule which thread runs next",
        ],
        correct_index=0,
        explanation="Resolvers ask DNS for the address that belongs to a name such as a website host.",
    ),
    _mcq(
        qid="mcq_cn_http",
        topic="CN",
        skill="CN",
        prompt="HTTP sits at which layer of the usual network stack?",
        options=[
            "Application",
            "Link, next to Ethernet frames",
            "Physical, as a voltage level",
            "It replaces IP and has no layer",
        ],
        correct_index=0,
        explanation="HTTP is an application protocol. TCP usually carries it, and IP carries TCP.",
    ),
    _mcq(
        qid="mcq_apt_train",
        topic="aptitude",
        skill="aptitude",
        prompt="A train 120 metres long moves at 18 km/h. How long does it take to pass a signal pole?",
        options=["24 seconds", "12 seconds", "6 seconds", "36 seconds"],
        correct_index=0,
        explanation="18 km/h is 5 m/s. Passing a pole takes the length of the train, 120 / 5 = 24 seconds.",
    ),
    _mcq(
        qid="mcq_apt_pens",
        topic="aptitude",
        skill="aptitude",
        prompt="Three pens cost 18. At the same price, what do five pens cost?",
        options=["30", "21", "36", "15"],
        correct_index=0,
        explanation="One pen costs 6, so five cost 30.",
    ),
]


def bank_questions() -> list[dict]:
    """Copies, so a caller can edit a picked question without changing the bank."""
    import copy

    return copy.deepcopy(CODING_BANK + MCQ_BANK)


def bank_totals() -> dict:
    return {"coding": len(CODING_BANK), "mcq": len(MCQ_BANK)}
