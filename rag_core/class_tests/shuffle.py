"""Per-attempt question and option order.

The order is chosen once, when the attempt starts, and stored on the attempt.
Grading still uses the option text, so a shuffled MCQ scores the same.
"""

import copy
import hashlib
import random


def build_layout(test: dict, attempt_id: str) -> dict | None:
    """Return a stable permutation, or None when both switches are off."""
    shuffle_questions = bool(test.get("shuffle_questions"))
    shuffle_options = bool(test.get("shuffle_options"))
    if not shuffle_questions and not shuffle_options:
        return None
    seed_src = f"{test.get('_id')}:{attempt_id}".encode()
    seed = int(hashlib.sha256(seed_src).hexdigest()[:16], 16)
    rng = random.Random(seed)
    questions = list(test.get("questions") or [])
    order = [question["id"] for question in questions]
    if shuffle_questions and len(order) > 1:
        rng.shuffle(order)
    option_map: dict[str, list[int]] = {}
    if shuffle_options:
        for question in questions:
            if question.get("type") != "mcq":
                continue
            indexes = list(range(len(question.get("options") or [])))
            if len(indexes) > 1:
                rng.shuffle(indexes)
            option_map[question["id"]] = indexes
    return {"question_order": order, "option_map": option_map}


def present_questions(questions: list[dict], layout: dict | None) -> list[dict]:
    """Copies in attempt order. MCQ ``correct_index`` follows the displayed options."""
    by_id = {question["id"]: question for question in questions}
    if layout:
        order = list(layout.get("question_order") or [])
        option_map = layout.get("option_map") or {}
    else:
        order = []
        option_map = {}
    seen = set()
    ordered_ids = []
    for qid in order:
        if qid in by_id and qid not in seen:
            ordered_ids.append(qid)
            seen.add(qid)
    for question in questions:
        if question["id"] not in seen:
            ordered_ids.append(question["id"])
    presented = []
    for qid in ordered_ids:
        question = by_id.get(qid)
        if question is None:
            continue
        copy_q = copy.deepcopy(question)
        perm = option_map.get(qid)
        options = list(copy_q.get("options") or [])
        if (
            copy_q.get("type") == "mcq"
            and isinstance(perm, list)
            and len(perm) == len(options)
            and sorted(perm) == list(range(len(options)))
        ):
            copy_q["options"] = [options[index] for index in perm]
            correct = copy_q.get("correct_index")
            if isinstance(correct, int) and correct in perm:
                copy_q["correct_index"] = perm.index(correct)
        presented.append(copy_q)
    return presented
