from django.contrib import messages
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ContactForm, QuizSubmissionForm, SchoolRequestForm
from .models import Chapter, Event, Question, Quiz, Response, Submission
from .services import score_submission


# ---- Static-ish public pages -------------------------------------------------

def home(request):
    next_event = (
        Event.objects.filter(published=True, starts_at__gte=timezone.now())
        .order_by("starts_at").first()
    )
    return render(request, "pages/home.html", {"next_event": next_event})


def about(request):
    return render(request, "pages/about.html")


def resources(request):
    return render(request, "pages/resources.html")


def privacy(request):
    return render(request, "pages/privacy.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Wire to real email in settings; console backend prints it in dev.
        send_mail(
            subject=f"[MoM contact] {form.cleaned_data['name']}",
            message=form.cleaned_data["message"],
            from_email=None,
            recipient_list=["hello@example.org"],
            fail_silently=True,
        )
        messages.success(request, "Thanks — we'll be in touch.")
        return redirect("contact")
    return render(request, "pages/contact.html", {"form": form})


# ---- Events ------------------------------------------------------------------

def event_list(request):
    events = Event.objects.filter(published=True).select_related("chapter")
    upcoming = events.filter(starts_at__gte=timezone.now()).order_by("starts_at")
    past = events.filter(starts_at__lt=timezone.now()).order_by("-starts_at")
    return render(request, "pages/events.html", {"upcoming": upcoming, "past": past})


def event_detail(request, slug):
    event = get_object_or_404(Event.objects.select_related("chapter", "quiz"),
                              slug=slug, published=True)
    return render(request, "pages/event_detail.html", {"event": event})


# ---- Quiz flow ---------------------------------------------------------------

def quiz_landing(request):
    """The box with two options: general quiz vs specific-school quiz."""
    return render(request, "pages/quiz_landing.html")


def quiz_school_picker(request):
    """Search-your-school step. Chapters are fetched once and filtered client
    side (see school-search.js). Every option resolves to a chapter slug — the
    field never submits a free-text school name."""
    chapters = (
        Chapter.objects.filter(active=True, collects_submissions=True)
        .values("slug", "name")
    )
    return render(request, "pages/quiz_school.html", {"chapters": list(chapters)})


def _pick_quiz(*, chapter=None):
    qs = Quiz.objects.filter(published=True)
    if chapter:
        return qs.filter(scope=Quiz.Scope.CHAPTER, chapter=chapter).first()
    return qs.filter(scope=Quiz.Scope.GENERAL).first()


def quiz_take(request, quiz_id):
    quiz = get_object_or_404(
        Quiz.objects.prefetch_related("questions__choices"), pk=quiz_id, published=True
    )
    event = None
    event_id = request.GET.get("event") or request.POST.get("event")
    if event_id:
        event = get_object_or_404(Event, pk=event_id, published=True)

    if request.method != "POST":
        form = QuizSubmissionForm(quiz=quiz, event=event)
        return render(request, "pages/quiz_take.html",
                      {"quiz": quiz, "event": event, "form": form})

    form = QuizSubmissionForm(request.POST, quiz=quiz, event=event)
    if not form.is_valid():
        return render(request, "pages/quiz_take.html",
                      {"quiz": quiz, "event": event, "form": form})

    # Pull per-question answers out of the POST. Field names: q_<question_id>.
    answers = {}
    for q in quiz.questions.all():
        field = f"q_{q.id}"
        if q.kind == Question.Kind.MULTI:
            answers[q.id] = request.POST.getlist(field)
        else:
            answers[q.id] = request.POST.get(field, "")

    # Score server-side — correctness comes from the DB, never the request.
    percentage, per_question = score_submission(quiz, answers)
    passed = percentage >= quiz.pass_threshold

    chapter = quiz.chapter if quiz.scope == Quiz.Scope.CHAPTER else (event.chapter if event else None)

    try:
        with transaction.atomic():
            submission = Submission.objects.create(
                quiz=quiz, event=event, chapter=chapter,
                full_name=form.cleaned_data["full_name"],
                email=form.cleaned_data["email"],
                school_identifier=form.cleaned_data["school_identifier"],
                attendance_code_given=form.cleaned_data.get("attendance_code", ""),
                score=percentage, passed=passed,
                credit_status=Submission.CreditStatus.PENDING,
            )
            Response.objects.bulk_create([
                Response(
                    submission=submission,
                    question_id=qid,
                    choice_id=(data["choice_ids"][0] if data["choice_ids"] else None),
                    text_answer=data["text"],
                    is_correct=data["is_correct"],
                )
                for qid, data in per_question.items()
            ])
    except IntegrityError:
        # Unique constraint hit: already submitted. Clean message, not a 500.
        messages.error(request, "You've already submitted this quiz with that school ID.")
        return render(request, "pages/quiz_take.html",
                      {"quiz": quiz, "event": event, "form": form})

    return redirect("quiz_complete", submission_id=submission.id)


def quiz_complete(request, submission_id):
    submission = get_object_or_404(Submission, pk=submission_id)
    return render(request, "pages/quiz_complete.html", {"submission": submission})


def school_not_listed(request):
    form = SchoolRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thanks — we'll let you know when your school is added.")
        return redirect("quiz_landing")
    return render(request, "pages/school_not_listed.html", {"form": form})


def quiz_for_school(request, slug):
    """Resolve a chapter slug to its published chapter quiz and hand off to the
    take view. Keeps the school picker decoupled from quiz IDs."""
    chapter = get_object_or_404(Chapter, slug=slug, active=True, collects_submissions=True)
    quiz = _pick_quiz(chapter=chapter) or _pick_quiz()  # fall back to general
    if not quiz:
        messages.error(request, "No quiz is open for that school yet.")
        return redirect("quiz_landing")
    return redirect("quiz_take", quiz_id=quiz.id)


def quiz_general(request):
    quiz = _pick_quiz()
    if not quiz:
        messages.error(request, "The general quiz isn't open right now.")
        return redirect("quiz_landing")
    return redirect("quiz_take", quiz_id=quiz.id)
