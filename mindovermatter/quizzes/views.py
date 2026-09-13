from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from core.forms import SchoolRequestForm
from core.models import Chapter
from events.models import Event

from .forms import QuizSubmissionForm
from .models import Question, Quiz, Response, Submission
from .scoring import grade_question, score_submission


def _submitting_chapters():
    return Chapter.objects.filter(active=True, collects_submissions=True)


def quiz_choose(request):
    """The two-option box: general quiz, or find your school."""
    return render(request, "quizzes/choose.html", {
        "general_count": Quiz.objects.filter(scope=Quiz.Scope.GENERAL, published=True).count(),
        "school_count": _submitting_chapters().count(),
    })


def quiz_general(request):
    return render(request, "quizzes/general.html", {
        "quizzes": Quiz.objects.filter(scope=Quiz.Scope.GENERAL, published=True),
        "chapters": _submitting_chapters(),
    })


def school_search(request):
    """Client-side filtering over a fixed chapter list.

    The field resolves to a Chapter, never to free text, so the database
    never accumulates 'GT' / 'Ga Tech' / 'georgia tech' as separate schools.
    """
    form = SchoolRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return render(request, "quizzes/school_requested.html")
    return render(request, "quizzes/school_search.html", {
        "chapters": _submitting_chapters(),
        "form": form,
    })


def school_quizzes(request, slug):
    chapter = get_object_or_404(_submitting_chapters(), slug=slug)
    return render(request, "quizzes/school_quizzes.html", {
        "chapter": chapter,
        "quizzes": Quiz.objects.filter(
            scope=Quiz.Scope.CHAPTER, chapter=chapter, published=True
        ),
    })


def take_quiz(request, pk):
    quiz = get_object_or_404(Quiz.objects.filter(published=True), pk=pk)

    if quiz.scope == Quiz.Scope.CHAPTER:
        chapter = quiz.chapter
    else:
        slug = request.POST.get("school") or request.GET.get("school")
        chapter = _submitting_chapters().filter(slug=slug).first()
        if chapter is None:
            return redirect("quiz_general")

    event = None
    event_slug = request.POST.get("event") or request.GET.get("event")
    if event_slug:
        event = Event.objects.published().filter(slug=event_slug, quiz=quiz).first()

    form = QuizSubmissionForm(
        request.POST or None, quiz=quiz, chapter=chapter, event=event
    )

    if request.method == "POST" and form.is_valid():
        correct, total, passed = score_submission(quiz, form.cleaned_data)
        try:
            with transaction.atomic():
                submission = Submission.objects.create(
                    quiz=quiz,
                    event=event,
                    chapter=chapter,
                    full_name=form.cleaned_data["full_name"],
                    email=form.cleaned_data["email"],
                    school_identifier=form.cleaned_data["school_identifier"],
                    score=correct,
                    total_questions=total,
                    passed=passed,
                    attendance_code_given=form.cleaned_data.get("attendance_code", ""),
                    credit_status=Submission.CreditStatus.PENDING,
                )
                Response.objects.bulk_create(_build_responses(submission, form))
        except IntegrityError:
            form.add_error(
                None,
                "A submission for this quiz already exists under that ID. "
                "Email us if you think that's wrong.",
            )
        else:
            return redirect("quiz_done", pk=submission.pk)

    return render(request, "quizzes/take.html", {
        "quiz": quiz, "chapter": chapter, "event": event, "form": form,
    })


def _build_responses(submission, form):
    for question in form.questions:
        answer = form.cleaned_data.get(question.field_name)
        correct = grade_question(question, answer)
        if question.kind == Question.Kind.MULTI:
            for choice in answer or []:
                yield Response(
                    submission=submission, question=question,
                    choice=choice, is_correct=correct,
                )
        elif question.kind == Question.Kind.SINGLE:
            yield Response(
                submission=submission, question=question,
                choice=answer, is_correct=correct,
            )
        else:
            yield Response(
                submission=submission, question=question,
                text_answer=answer or "", is_correct=correct,
            )


def quiz_done(request, pk):
    submission = get_object_or_404(
        Submission.objects.select_related("quiz", "event", "chapter"), pk=pk
    )
    return render(request, "quizzes/done.html", {"submission": submission})
