"""Pure functions with no request/HTTP dependency, so they're unit-testable
on their own. Scoring in particular must never trust anything from the client."""
from decimal import Decimal

from .models import Choice, Question, Quiz


def score_submission(quiz: Quiz, answers: dict) -> tuple[int, dict]:
    """Score a quiz server-side from the Choice table.

    `answers` maps question_id -> value:
      - single: a choice_id (int)
      - multi:  a set/list of choice_ids
      - short:  a string (not auto-graded; treated as correct-if-nonblank here,
                flag for manual review in a later phase)

    Returns (percentage 0-100, per_question) where per_question maps
    question_id -> {"is_correct": bool, "choice_ids": [...], "text": str}.

    Scoring reads is_correct straight from the DB. A tampered request body
    cannot change the outcome because the request never supplies correctness.
    """
    questions = list(quiz.questions.prefetch_related("choices"))
    if not questions:
        return 0, {}

    correct_count = 0
    per_question: dict = {}

    for q in questions:
        entry = {"is_correct": False, "choice_ids": [], "text": ""}
        given = answers.get(q.id)

        if q.kind == Question.Kind.SINGLE:
            correct_ids = {c.id for c in q.choices.all() if c.is_correct}
            chosen = int(given) if given not in (None, "") else None
            entry["choice_ids"] = [chosen] if chosen else []
            entry["is_correct"] = chosen in correct_ids

        elif q.kind == Question.Kind.MULTI:
            correct_ids = {c.id for c in q.choices.all() if c.is_correct}
            chosen = {int(x) for x in (given or [])}
            entry["choice_ids"] = sorted(chosen)
            entry["is_correct"] = chosen == correct_ids and len(correct_ids) > 0

        elif q.kind == Question.Kind.SHORT:
            text = (given or "").strip()
            entry["text"] = text
            entry["is_correct"] = bool(text)  # placeholder: manual grading later

        if entry["is_correct"]:
            correct_count += 1
        per_question[q.id] = entry

    percentage = round(100 * correct_count / len(questions))
    return percentage, per_question
