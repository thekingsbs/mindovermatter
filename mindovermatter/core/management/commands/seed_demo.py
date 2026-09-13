"""Fills the database with enough sample content to click through the site.

    python manage.py seed_demo

Safe to re-run. Delete the rows in the admin when you're ready for real data.
"""

from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Chapter, OfficerProfile, Resource
from events.models import Event
from quizzes.models import Choice, Question, Quiz


OFFICER_PERMS = [
    ("events", "event", ["add", "change", "delete", "view"]),
    ("quizzes", "quiz", ["add", "change", "delete", "view"]),
    ("quizzes", "question", ["add", "change", "delete", "view"]),
    ("quizzes", "choice", ["add", "change", "delete", "view"]),
    ("quizzes", "submission", ["change", "view"]),
    ("quizzes", "response", ["view"]),
    ("core", "resource", ["add", "change", "delete", "view"]),
    ("core", "contactmessage", ["change", "view"]),
    ("core", "chapter", ["view"]),
]


def officer_group():
    """The permission set a chapter officer needs. Row-level scoping is
    handled separately by ChapterScopedAdmin.get_queryset."""
    group, _ = Group.objects.get_or_create(name="Chapter officers")
    perms = []
    for app_label, model, actions in OFFICER_PERMS:
        for action in actions:
            perms.append(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    content_type__model=model,
                    codename=f"{action}_{model}",
                )
            )
    group.permissions.set(perms)
    return group


class Command(BaseCommand):
    help = "Create sample chapters, events, and quizzes."

    def handle(self, *args, **options):
        gt, _ = Chapter.objects.update_or_create(
            slug="georgia-tech",
            defaults=dict(name="Georgia Institute of Technology", kind=Chapter.Kind.UNIVERSITY,
                          sona_enabled=True, identifier_label="GT ID",
                          identifier_pattern=r"\d{9}", position=1),
        )
        ksu, _ = Chapter.objects.update_or_create(
            slug="kennesaw-state",
            defaults=dict(name="Kennesaw State University", kind=Chapter.Kind.UNIVERSITY,
                          sona_enabled=True, identifier_label="KSU ID", position=2),
        )
        Chapter.objects.update_or_create(
            slug="north-atlanta-hs",
            defaults=dict(name="North Atlanta High School", kind=Chapter.Kind.HIGH_SCHOOL, position=3),
        )

        quiz, created = Quiz.objects.get_or_create(
            title="Memory and forgetting",
            defaults=dict(scope=Quiz.Scope.GENERAL, pass_threshold=70, published=True,
                          description="Five questions on the material from the memory talk."),
        )
        if created:
            q1 = Question.objects.create(quiz=quiz, prompt="What does the serial position effect describe?", position=1)
            Choice.objects.bulk_create([
                Choice(question=q1, text="Better recall for items at the start and end of a list", is_correct=True, position=1),
                Choice(question=q1, text="Better recall for items in the middle of a list", position=2),
                Choice(question=q1, text="Recall improving with each repetition", position=3),
            ])
            q2 = Question.objects.create(quiz=quiz, prompt="Which of these are forms of long-term memory?",
                                         kind=Question.Kind.MULTI, position=2)
            Choice.objects.bulk_create([
                Choice(question=q2, text="Episodic", is_correct=True, position=1),
                Choice(question=q2, text="Procedural", is_correct=True, position=2),
                Choice(question=q2, text="Iconic", position=3),
            ])
            q3 = Question.objects.create(quiz=quiz, prompt="Name the curve that describes memory decay over time.",
                                         kind=Question.Kind.SHORT, position=3)
            Choice.objects.create(question=q3, text="forgetting curve", is_correct=True)

        ksu_quiz, _ = Quiz.objects.get_or_create(
            title="KSU session check-in",
            defaults=dict(scope=Quiz.Scope.CHAPTER, chapter=ksu, pass_threshold=60, published=True),
        )
        if not ksu_quiz.questions.exists():
            q = Question.objects.create(quiz=ksu_quiz, prompt="Which topic did this session cover?", position=1)
            Choice.objects.bulk_create([
                Choice(question=q, text="Sleep and consolidation", is_correct=True, position=1),
                Choice(question=q, text="Colour perception", position=2),
            ])

        now = timezone.now()
        Event.objects.update_or_create(
            slug="memory-and-forgetting",
            defaults=dict(chapter=gt, title="Memory and forgetting", published=True,
                          summary="Why you remember the first and last thing and nothing in between.",
                          description="An hour on encoding, retrieval, and what actually happens when you cram.",
                          starts_at=now - timedelta(days=3), location="Clough 152",
                          credit_value=1, attendance_code="HIPPO", quiz=quiz),
        )
        Event.objects.update_or_create(
            slug="sleep-and-consolidation",
            defaults=dict(chapter=ksu, title="Sleep and consolidation", published=True,
                          summary="What your brain does with the day after you stop paying attention to it.",
                          starts_at=now + timedelta(days=14), location="Social Sciences 3010",
                          credit_value=1, attendance_code="OWL", quiz=ksu_quiz),
        )

        Resource.objects.update_or_create(
            title="Slides: Memory and forgetting",
            defaults=dict(kind=Resource.Kind.LINK, url="https://example.org/slides", published=True, chapter=gt),
        )

        user, made = User.objects.get_or_create(
            username="gtofficer", defaults=dict(is_staff=True, email="officer@example.org")
        )
        if made:
            user.set_password("changeme123")
            user.save()
        OfficerProfile.objects.update_or_create(user=user, defaults=dict(chapter=gt))
        user.groups.add(officer_group())

        self.stdout.write(self.style.SUCCESS(
            "Seeded. Staff login gtofficer / changeme123 (scoped to Georgia Tech)."
        ))
