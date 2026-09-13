from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from core.models import Chapter, Choice, Event, Question, Quiz, Submission
from core.services import score_submission


class ScoringTests(TestCase):
    def setUp(self):
        self.quiz = Quiz.objects.create(title="T", scope=Quiz.Scope.GENERAL,
                                        pass_threshold=50, published=True)
        self.q = Question.objects.create(quiz=self.quiz, prompt="?",
                                         kind=Question.Kind.SINGLE, position=1)
        self.right = Choice.objects.create(question=self.q, text="right", is_correct=True)
        self.wrong = Choice.objects.create(question=self.q, text="wrong", is_correct=False)

    def test_correct_answer_scores_100(self):
        pct, _ = score_submission(self.quiz, {self.q.id: self.right.id})
        self.assertEqual(pct, 100)

    def test_wrong_answer_scores_0(self):
        pct, _ = score_submission(self.quiz, {self.q.id: self.wrong.id})
        self.assertEqual(pct, 0)

    def test_client_cannot_inject_correctness(self):
        # Even a garbage/nonexistent choice id can't score points.
        pct, _ = score_submission(self.quiz, {self.q.id: 999999})
        self.assertEqual(pct, 0)


class SubmissionFlowTests(TestCase):
    def setUp(self):
        self.chapter = Chapter.objects.create(name="GT")
        self.quiz = Quiz.objects.create(title="T", scope=Quiz.Scope.GENERAL,
                                        pass_threshold=50, published=True)
        self.q = Question.objects.create(quiz=self.quiz, prompt="?",
                                         kind=Question.Kind.SINGLE, position=1)
        self.right = Choice.objects.create(question=self.q, text="r", is_correct=True)
        self.event = Event.objects.create(title="E", chapter=self.chapter,
            starts_at=timezone.now() - timedelta(days=1),
            attendance_code="CODE1", quiz=self.quiz, published=True)

    def _post(self, **override):
        data = {"full_name": "A", "email": "a@b.com", "school_identifier": "111",
                "attendance_code": "CODE1", "event": self.event.id,
                f"q_{self.q.id}": self.right.id}
        data.update(override)
        url = reverse("quiz_take", args=[self.quiz.id]) + f"?event={self.event.id}"
        return self.client.post(url, data)

    def test_wrong_attendance_code_rejected(self):
        r = self._post(attendance_code="NOPE")
        self.assertEqual(Submission.objects.count(), 0)
        self.assertContains(r, "isn&#x27;t right")

    def test_duplicate_identifier_rejected(self):
        self._post()
        self.assertEqual(Submission.objects.count(), 1)
        self._post()  # same school_identifier again
        self.assertEqual(Submission.objects.count(), 1)

    def test_high_school_chapter_forces_no_submissions(self):
        hs = Chapter.objects.create(name="HS", kind=Chapter.Kind.HIGH_SCHOOL)
        self.assertFalse(hs.collects_submissions)
