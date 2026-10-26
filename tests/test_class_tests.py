"""Teacher-authored timed tests: roles, deadlines, hidden answers, grading."""

import json
from datetime import datetime, timedelta

from rag_core.class_tests.bank import CODING_BANK, MCQ_BANK
from rag_core.class_tests.grading import score_short
from rag_core.class_tests.harness import runner_tail
from rag_core.class_tests.parse_mcq import parse_mcq_import
from rag_core.create_teacher import create_teacher_account
from tests.conftest import register


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", ""))


def _code(body: str, name: str) -> str:
    return body.rstrip() + "\n" + runner_tail(name)


ADD = _code(
    "def add(a, b):\n    return a + b",
    "add",
)
ALWAYS_THREE = _code(
    "def add(a, b):\n    return 3",
    "add",
)


def _coding_question():
    return {
        "id": "sum",
        "type": "coding",
        "skill": "arrays",
        "prompt": "Return the sum of the two integers.",
        "signature": "def add(a, b):",
        "language": "python",
        "starter_code": ADD,
        "visible_cases": [{"stdin": "[1, 2]", "expected": "3"}],
        "hidden_cases": [
            {"stdin": "[1, 2]", "expected": "3"},
            {"stdin": "[4, 4]", "expected": "8"},
        ],
        "explanation": "Add the two arguments.",
    }


def _mcq(correct="UNIQUE_CORRECT_OPTION"):
    return {
        "id": "pick",
        "type": "mcq",
        "skill": "DBMS",
        "prompt": "Which word names all-or-nothing writes?",
        "options": [correct, "Isolation", "Durability", "Latency"],
        "correct_index": 0,
        "explanation": "Atomicity means every write lands, or none do.",
    }


def _short():
    return {
        "id": "short1",
        "type": "short",
        "skill": "DBMS",
        "prompt": "Name the ACID property that means all-or-nothing.",
        "expected": "atomicity",
        "keywords": ["atomicity"],
        "explanation": "Atomicity is the all-or-nothing property.",
    }


def _test_body(**overrides):
    body = {
        "title": "Friday quiz",
        "description": "A short mixed paper.",
        "topic": "DSA",
        "test_type": "mixed",
        "duration_minutes": 12,
        "published": True,
        "allow_retake": False,
        "show_answers_after_submit": False,
        "questions": [_mcq(), _coding_question(), _short()],
    }
    body.update(overrides)
    return body


async def _teacher(client, email="teacher@school.edu"):
    await create_teacher_account("Ada Rao", email, "password123")
    response = await client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200, response.text
    body = response.json()
    return body, {"Authorization": f"Bearer {body['token']}"}


async def test_roles_and_indexes(client):
    _student, student_headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)

    denied = await client.post("/teacher/class-tests", json=_test_body(), headers=student_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Teacher access required"

    created = await client.post("/teacher/class-tests", json=_test_body(), headers=teacher_headers)
    assert created.status_code == 200, created.text
    test_id = created.json()["id"]

    started = await client.post(f"/class-tests/{test_id}/start", headers=teacher_headers)
    assert started.status_code == 403
    assert started.json()["detail"] == "Student access required"

    from rag_core.mongo import get_db

    db = await get_db()
    test_indexes = await db.class_tests.index_information()
    attempt_indexes = await db.class_attempts.index_information()
    assert "class_tests_created_by" in test_indexes
    assert "class_tests_published" in test_indexes
    assert "class_attempts_test_user" in attempt_indexes
    assert "class_attempts_user_started" in attempt_indexes
    assert "class_attempts_test_status" in attempt_indexes


async def test_students_do_not_see_answers_and_the_deadline_is_server_side(client):
    _student, student_headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)
    created = await client.post("/teacher/class-tests", json=_test_body(), headers=teacher_headers)
    test_id = created.json()["id"]

    listed = await client.get("/class-tests", headers=student_headers)
    assert listed.status_code == 200
    assert listed.json()["tests"][0]["id"] == test_id
    assert "questions" not in listed.json()["tests"][0]

    started = await client.post(f"/class-tests/{test_id}/start", headers=student_headers)
    assert started.status_code == 200, started.text
    body = started.json()
    assert _parse(body["deadline"]) - _parse(body["started_at"]) == timedelta(minutes=12)
    blob = started.text
    # The option text is the choice the student picks. The key, the short-answer
    # expected text, the explanation, and hidden cases stay off the payload.
    assert "correct_index" not in blob
    assert "every write lands" not in blob
    assert "[4, 4]" not in blob
    assert "atomicity" not in blob
    mcq = next(question for question in body["questions"] if question["type"] == "mcq")
    assert mcq["options"][0] == "UNIQUE_CORRECT_OPTION"
    coding = next(question for question in body["questions"] if question["type"] == "coding")
    assert "hidden_cases" not in coding
    assert coding["visible_cases"][0]["stdin"] == "[1, 2]"

    again = await client.post(f"/class-tests/{test_id}/start", headers=student_headers)
    assert again.status_code == 200
    assert again.json()["attempt_id"] == body["attempt_id"]

    teacher_view = await client.get(f"/teacher/class-tests/{test_id}", headers=teacher_headers)
    assert "[4, 4]" in teacher_view.text
    assert teacher_view.json()["questions"][0]["correct_index"] == 0


async def test_window_hides_unpublished_and_future_tests(client):
    _student, student_headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)
    future = await client.post(
        "/teacher/class-tests",
        json=_test_body(title="Later", available_from="2099-01-01T00:00:00Z"),
        headers=teacher_headers,
    )
    draft = await client.post(
        "/teacher/class-tests",
        json=_test_body(title="Draft", published=False),
        headers=teacher_headers,
    )
    assert future.status_code == 200 and draft.status_code == 200
    listed = await client.get("/class-tests", headers=student_headers)
    assert listed.json()["tests"] == []
    teacher_list = await client.get("/teacher/class-tests", headers=teacher_headers)
    titles = {item["title"] for item in teacher_list.json()["tests"]}
    assert titles == {"Later", "Draft"}
    assert (await client.post(f"/class-tests/{future.json()['id']}/start", headers=student_headers)).status_code == 404


async def test_grading_autosave_deadline_and_retake(client, monkeypatch):
    _student, student_headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)
    created = await client.post(
        "/teacher/class-tests",
        json=_test_body(
            questions=[_mcq(), _coding_question()],
            show_answers_after_submit=False,
        ),
        headers=teacher_headers,
    )
    test_id = created.json()["id"]
    started = await client.post(f"/class-tests/{test_id}/start", headers=student_headers)
    attempt = started.json()
    questions = {question["id"]: question for question in attempt["questions"]}

    saved = await client.put(
        f"/class-tests/{test_id}/answers",
        json={
            "answers": [
                {"question_id": "pick", "selected": "UNIQUE_CORRECT_OPTION"},
                {"question_id": "sum", "code": ALWAYS_THREE, "language": "python"},
            ]
        },
        headers=student_headers,
    )
    assert saved.status_code == 200, saved.text

    ran = await client.post(
        f"/class-tests/{test_id}/run",
        json={"question_id": "sum", "code": ALWAYS_THREE, "language": "python"},
        headers=student_headers,
    )
    assert ran.status_code == 200, ran.text
    assert ran.json()["cases"][0]["passed"] is True
    assert "[4, 4]" not in ran.text

    monkeypatch.setattr("rag_core.class_tests.service.utcnow", lambda: datetime(2099, 1, 2))
    late_save = await client.put(
        f"/class-tests/{test_id}/answers",
        json={"answers": [{"question_id": "pick", "selected": "Isolation"}]},
        headers=student_headers,
    )
    assert late_save.status_code == 409
    assert late_save.json()["detail"] == "Time is up"

    submitted = await client.post(
        f"/class-tests/{test_id}/submit",
        json={"answers": [{"question_id": "pick", "selected": "Isolation"}, {"question_id": "sum", "code": ADD}]},
        headers=student_headers,
    )
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()
    # Saved MCQ was correct (1) and the saved code passes 1 of 2 hidden cases (0.5).
    assert result["score"] == 75.0
    assert result["status"] == "expired"
    assert result["show_answers"] is False
    assert "correct_index" not in submitted.text
    assert "every write lands" not in submitted.text
    by_id = {item["question_id"]: item for item in result["results"]}
    assert by_id["pick"]["correct"] is True
    assert by_id["sum"]["credit"] == 0.5
    assert questions["pick"]["prompt"]

    blocked = await client.post(f"/class-tests/{test_id}/start", headers=student_headers)
    assert blocked.status_code == 409

    opened = await client.put(
        f"/teacher/class-tests/{test_id}",
        json={"allow_retake": True, "show_answers_after_submit": True},
        headers=teacher_headers,
    )
    assert opened.status_code == 200, opened.text
    monkeypatch.setattr("rag_core.class_tests.service.utcnow", lambda: datetime(2099, 1, 3))
    # The window is open and retakes are allowed, but the previous attempt is already closed.
    retake = await client.post(f"/class-tests/{test_id}/start", headers=student_headers)
    assert retake.status_code == 200, retake.text
    assert retake.json()["attempt_id"] != result["attempt_id"]

    finished = await client.post(
        f"/class-tests/{test_id}/submit",
        json={
            "answers": [
                {"question_id": "pick", "selected": "Isolation"},
                {"question_id": "sum", "code": ADD, "language": "python"},
            ]
        },
        headers=student_headers,
    )
    assert finished.status_code == 200, finished.text
    # MCQ wrong, coding passes both hidden cases. 50, and the key is visible.
    assert finished.json()["score"] == 50.0
    assert finished.json()["show_answers"] is True
    assert finished.json()["questions"][0]["correct_option"] == "UNIQUE_CORRECT_OPTION"
    assert "every write lands" in finished.text
    assert finished.json()["questions"][0]["correct_index"] == 0

    report = await client.get(f"/teacher/class-tests/{test_id}/attempts", headers=teacher_headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["count"] == 2
    assert body["attempts"][0]["student"]["email"] == "student@example.com"
    assert body["attempts"][0]["time_taken_seconds"] is not None
    assert {item["score"] for item in body["attempts"]} == {75.0, 50.0}

    persona = await client.get("/me/persona", headers=student_headers)
    assert "DBMS" in persona.json()["weak_topics"] or "arrays" in persona.json()["weak_topics"]

    removed = await client.delete(f"/teacher/class-tests/{test_id}", headers=teacher_headers)
    assert removed.status_code == 409


async def test_mcq_test_type_bank_and_bulk_import(client):
    assert len(CODING_BANK) >= 15
    assert len(MCQ_BANK) >= 25
    skills = {item["skill"] for item in CODING_BANK}
    assert {"arrays", "strings", "hashing", "two pointers", "stacks", "binary search", "linked list", "trees", "dynamic programming"} <= skills
    topics = {item["topic"] for item in MCQ_BANK}
    assert {"DSA", "complexity", "OOP", "DBMS", "OS", "CN", "aptitude"} <= topics

    _teacher_body, teacher_headers = await _teacher(client)
    bank = await client.get("/teacher/question-bank?kind=mcq", headers=teacher_headers)
    assert bank.status_code == 200
    assert bank.json()["totals"]["mcq"] >= 25
    assert all(item["type"] == "mcq" for item in bank.json()["questions"])
    coding = await client.get("/teacher/question-bank?kind=coding&topic=arrays", headers=teacher_headers)
    assert coding.json()["questions"]
    assert all(item["skill"] == "arrays" for item in coding.json()["questions"])

    rejected = await client.post(
        "/teacher/class-tests",
        json=_test_body(test_type="mcq", questions=[_mcq(), _coding_question()]),
        headers=teacher_headers,
    )
    assert rejected.status_code == 422

    pure = await client.post(
        "/teacher/class-tests",
        json=_test_body(test_type="mcq", title="MCQ only", questions=[_mcq(), MCQ_BANK[0]]),
        headers=teacher_headers,
    )
    assert pure.status_code == 200, pure.text
    assert pure.json()["test_type"] == "mcq"
    assert pure.json()["question_count"] == 2

    imported = await client.post(
        "/teacher/question-bank/import",
        json={
            "text": json.dumps(
                [
                    {
                        "prompt": "How many pens?",
                        "options": ["30", "18", "12", "6"],
                        "answer": "A",
                        "skill": "aptitude",
                        "explanation": "The first option.",
                    }
                ]
            )
        },
        headers=teacher_headers,
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["questions"][0]["correct_index"] == 0

    pasted = await client.post(
        "/teacher/question-bank/import",
        json={
            "text": "\n".join(
                [
                    "Q: Which layer carries HTTP?",
                    "A) Application",
                    "B) Physical",
                    "C) A voltage",
                    "D) None",
                    "Answer: A",
                    "Explanation: HTTP is an application protocol.",
                    "Skill: CN",
                ]
            )
        },
        headers=teacher_headers,
    )
    assert pasted.status_code == 200, pasted.text
    assert pasted.json()["questions"][0]["correct_index"] == 0
    assert pasted.json()["questions"][0]["skill"] == "CN"

    student_headers = (await register(client, email="other@example.com"))[1]
    assert (await client.get("/teacher/question-bank", headers=student_headers)).status_code == 403


def test_short_answer_keywords_and_optional_model(monkeypatch):
    question = _short()
    assert score_short(question, "It is atomicity.")["correct"] is True
    assert score_short(question, "isolation")["correct"] is False

    monkeypatch.setattr("rag_core.class_tests.grading.llm_available", lambda: True)
    monkeypatch.setattr("rag_core.llm.complete_json", lambda *_args, **_kwargs: {"correct": True})
    judged = score_short(question, "all or nothing writes")
    assert judged["correct"] is True
    assert judged["detail"] == "Model accepted the wording"


def test_bank_cases_match_reference_solutions():
    solutions = {
        "dsa_second_largest": lambda nums: _second(nums),
        "dsa_rotate_left": lambda nums, k: (nums[k % len(nums) :] + nums[: k % len(nums)]) if nums else [],
        "dsa_is_palindrome": lambda text: [ch.lower() for ch in text if ch.isalnum()] == [ch.lower() for ch in text if ch.isalnum()][::-1],
        "dsa_reverse_words": lambda text: " ".join(text.split()[::-1]),
        "dsa_two_sum": _two_sum,
        "dsa_first_unique": _first_unique,
        "dsa_has_pair": _has_pair,
        "dsa_unique_count": _unique_count,
        "dsa_valid_parens": _valid_parens,
        "dsa_next_greater_count": lambda nums: sum(any(other > value for other in nums[i + 1 :]) for i, value in enumerate(nums)),
        "dsa_find_index": _find_index,
        "dsa_first_at_least": _first_at_least,
        "dsa_reverse_values": lambda nums: list(reversed(nums)),
        "dsa_tree_height": _tree_height,
        "dsa_climb_ways": _climb,
    }
    assert set(solutions) == {item["id"] for item in CODING_BANK}
    for question in CODING_BANK:
        fn = solutions[question["id"]]
        for case in question["visible_cases"] + question["hidden_cases"]:
            args = json.loads(case["stdin"])
            value = fn(*args)
            expected = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"))
            assert expected == case["expected"], (question["id"], case["stdin"], expected, case["expected"])
        assert "NotImplementedError" in question["starter_code"]


def _second(nums):
    first = second = None
    for value in nums:
        if first is None or value > first:
            second = first
            first = value
        elif value != first and (second is None or value > second):
            second = value
    return -1 if second is None else second


def _two_sum(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        need = target - value
        if need in seen:
            return [seen[need], index]
        seen[value] = index
    return []


def _first_unique(text):
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in text:
        if counts[ch] == 1:
            return ch
    return ""


def _has_pair(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        total = nums[left] + nums[right]
        if total == target:
            return True
        if total < target:
            left += 1
        else:
            right -= 1
    return False


def _unique_count(nums):
    if not nums:
        return 0
    count = 1
    for index in range(1, len(nums)):
        if nums[index] != nums[index - 1]:
            count += 1
    return count


def _valid_parens(text):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in text:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


def _find_index(nums, target):
    lo, hi, answer = 0, len(nums) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            answer = mid
            hi = mid - 1
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return answer


def _first_at_least(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo if lo < len(nums) else -1


def _tree_height(node):
    if not node:
        return 0
    left = node[1] if len(node) > 1 else None
    right = node[2] if len(node) > 2 else None
    return 1 + max(_tree_height(left), _tree_height(right))


def _climb(n):
    if n < 0:
        return 0
    a = b = 1
    for _ in range(n):
        a, b = b, a + b
    return a
