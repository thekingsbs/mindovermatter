from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


class Quiz(models.Model):
    class Scope(models.TextChoices):
        GENERAL = "general", "General"
        CHAPTER = "chapter", "School-specific"

    scope = models.CharField(max_length=10, choices=Scope.choices, default=Scope.GENERAL)
    chapter = models.ForeignKey(
        "core.Chapter", null=True, blank=True, on_delete=models.CASCADE,
        help_text="Required when the scope is school-specific.",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pass_threshold = models.PositiveIntegerField(
        default=70, help_text="Percentage of questions that must be correct to pass."
    )
    allow_retake = models.BooleanField(default=False)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "quizzes"

    def __str__(self):
        return self.title

    def clean(self):
        if self.scope == self.Scope.CHAPTER and self.chapter_id is None:
            raise ValidationError({"chapter": "Pick a school, or change the scope to general."})
        if self.scope == self.Scope.GENERAL and self.chapter_id is not None:
            raise ValidationError({"chapter": "A general quiz must not be tied to a school."})

    @property
    def question_count(self):
        return self.questions.count()


class Question(models.Model):
    class Kind(models.TextChoices):
        SINGLE = "single", "One correct answer"
        MULTI = "multi", "Several correct answers"
        SHORT = "short", "Short written answer"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SINGLE)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.prompt[:70]

    @property
    def field_name(self):
        return f"question_{self.pk}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.text


class Submission(models.Model):
    class CreditStatus(models.TextChoices):
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified"
        EXPORTED = "exported", "Exported to SONA"
        REJECTED = "rejected", "Rejected"

    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="submissions")
    event = models.ForeignKey(
        "events.Event", null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions"
    )
    chapter = models.ForeignKey("core.Chapter", on_delete=models.PROTECT, related_name="submissions")

    full_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField()
    school_identifier = models.CharField(max_length=60)

    score = models.PositiveIntegerField(default=0, help_text="Number of questions answered correctly.")
    total_questions = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    attendance_code_given = models.CharField(max_length=40, blank=True)

    credit_status = models.CharField(
        max_length=12, choices=CreditStatus.choices, default=CreditStatus.PENDING
    )
    credit_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                "quiz",
                Lower("school_identifier"),
                name="one_submission_per_student_per_quiz",
            )
        ]

    def __str__(self):
        return f"{self.full_name} - {self.quiz}"

    @property
    def percentage(self):
        if not self.total_questions:
            return 0
        return round(100 * self.score / self.total_questions)


class Response(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["question__position"]
