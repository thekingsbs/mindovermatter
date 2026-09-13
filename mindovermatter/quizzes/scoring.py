"""Server-side scoring. Never trust a score sent by the browser."""

from .models import Question, Quiz


def grade_question(question: Question, answer) -> bool:
    """Return whether `answer` is correct for `question`.

    `answer` is whatever QuizSubmissionForm produced for this question:
      single -> a Choice
      multi  -> a queryset/list of Choice
      short  -> a string
    """
    if question.kind == Question.Kind.SINGLE:
        return bool(answer and answer.is_correct)

    if question.kind == Question.Kind.MULTI:
        chosen = {c.pk for c in (answer or [])}
        correct = set(
            question.choices.filter(is_correct=True).values_list("pk", flat=True)
        )
        return bool(correct) and chosen == correct

    if question.kind == Question.Kind.SHORT:
        given = (answer or "").strip().casefold()
        if not given:
            return False
        accepted = {
            c.text.strip().casefold()
            for c in question.choices.filter(is_correct=True)
        }
        return given in accepted

    return False


def score_submission(quiz: Quiz, cleaned_data: dict) -> tuple[int, int, bool]:
    """Grade a full submission.

    Returns (correct_count, total_questions, passed).
    `passed` compares the percentage against quiz.pass_threshold.
    """
    questions = list(quiz.questions.prefetch_related("choices"))
    correct = sum(
        1
        for q in questions
        if grade_question(q, cleaned_data.get(q.field_name))
    )
    total = len(questions)
    percentage = (100 * correct / total) if total else 0
    return correct, total, percentage >= quiz.pass_threshold
