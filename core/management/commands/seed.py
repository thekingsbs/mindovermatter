"""Populate the DB with realistic sample data so you can click through the site
immediately. Run: python manage.py seed"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (Chapter, Choice, Event, Question, Quiz, StaffProfile)


class Command(BaseCommand):
    help = "Load sample chapters, events, and a quiz."

    def handle(self, *args, **opts):
        gt, _ = Chapter.objects.get_or_create(
            name="Georgia Tech", defaults=dict(kind=Chapter.Kind.UNIVERSITY,
            sona_enabled=True, contact_email="gt@example.org"))
        ksu, _ = Chapter.objects.get_or_create(
            name="Kennesaw State", defaults=dict(kind=Chapter.Kind.UNIVERSITY,
            sona_enabled=True, contact_email="ksu@example.org"))
        hs, _ = Chapter.objects.get_or_create(
            name="Midtown High School", defaults=dict(kind=Chapter.Kind.HIGH_SCHOOL))

        quiz, created = Quiz.objects.get_or_create(
            title="Intro to Cognitive Bias", defaults=dict(
                scope=Quiz.Scope.GENERAL, pass_threshold=60, published=True))
        if created:
            q1 = Question.objects.create(quiz=quiz, prompt="Confirmation bias is the tendency to…",
                kind=Question.Kind.SINGLE, position=1)
            Choice.objects.create(question=q1, text="Seek information that confirms what we already believe", is_correct=True, position=1)
            Choice.objects.create(question=q1, text="Always change our minds when shown new data", position=2)
            Choice.objects.create(question=q1, text="Remember the last thing we heard best", position=3)

            q2 = Question.objects.create(quiz=quiz, prompt="Which of these are System 1 (fast) processes?",
                kind=Question.Kind.MULTI, position=2)
            Choice.objects.create(question=q2, text="Recognizing a friend's face", is_correct=True, position=1)
            Choice.objects.create(question=q2, text="Reacting to a loud noise", is_correct=True, position=2)
            Choice.objects.create(question=q2, text="Solving 17 × 24 in your head", position=3)

        gt_event, _ = Event.objects.get_or_create(
            title="Why We Believe Weird Things", defaults=dict(
                chapter=gt, starts_at=timezone.now() - timedelta(days=1),
                location="Clough 152", credit_value="1.00",
                attendance_code="OWL2024", quiz=quiz, published=True))
        Event.objects.get_or_create(
            title="The Science of Habit", defaults=dict(
                chapter=ksu, starts_at=timezone.now() + timedelta(days=10),
                location="Social Sciences 1021", credit_value="1.00",
                quiz=quiz, published=True))

        if not User.objects.filter(username="admin").exists():
            u = User.objects.create_superuser("admin", "admin@example.org", "admin12345")
            StaffProfile.objects.create(user=u, chapter=None, role=StaffProfile.Role.OWNER)
            self.stdout.write(self.style.SUCCESS("Superuser: admin / admin12345"))

        self.stdout.write(self.style.SUCCESS("Seeded chapters, a quiz, and events."))
