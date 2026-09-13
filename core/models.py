"""
Data model for the Mind Over Matter site.

Design notes:
- Enums are TextChoices so the DB stores readable strings and Django gives you
  .get_FOO_display() in templates for free.
- The duplicate-submission rule lives in the DATABASE (see Submission.Meta),
  not in a view. With no student login, that constraint is the only thing that
  actually stops one person submitting twice.
- Chapters of kind HIGH_SCHOOL are forced to collects_submissions=False in
  clean(). Minors never get a data-collection flow; that's structural, not a
  thing anyone has to remember.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils.text import slugify


class Chapter(models.Model):
    class Kind(models.TextChoices):
        UNIVERSITY = "university", "University"
        HIGH_SCHOOL = "high_school", "High school"

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.UNIVERSITY)
    # University chapters collect quiz submissions; high schools (minors) do not.
    collects_submissions = models.BooleanField(default=True)
    sona_enabled = models.BooleanField(default=False)
    # Regex a school_identifier must match for this chapter, e.g. GT ID format.
    # Blank = accept anything non-empty. Kept per-chapter because every school differs.
    identifier_pattern = models.CharField(
        max_length=200, blank=True,
        help_text=r"Optional regex the school ID must match, e.g. ^\d{9}$ for a 9-digit ID.",
    )
    contact_email = models.EmailField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        # High schools involve minors: never collect submissions from them.
        if self.kind == self.Kind.HIGH_SCHOOL:
            self.collects_submissions = False
            self.sona_enabled = False

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)


class Quiz(models.Model):
    class Scope(models.TextChoices):
        GENERAL = "general", "General"
        CHAPTER = "chapter", "Chapter-specific"

    title = models.CharField(max_length=200)
    scope = models.CharField(max_length=10, choices=Scope.choices, default=Scope.GENERAL)
    # Required when scope=CHAPTER, null when scope=GENERAL. Enforced in clean().
    chapter = models.ForeignKey(
        Chapter, null=True, blank=True, on_delete=models.CASCADE, related_name="quizzes"
    )
    pass_threshold = models.PositiveIntegerField(
        default=70, help_text="Minimum percentage (0-100) required to pass."
    )
    allow_retake = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "quizzes"

    def __str__(self):
        return self.title

    def clean(self):
        if self.scope == self.Scope.CHAPTER and self.chapter is None:
            raise ValidationError({"chapter": "A chapter-specific quiz needs a chapter."})
        if self.scope == self.Scope.GENERAL and self.chapter is not None:
            raise ValidationError({"chapter": "A general quiz must not be tied to a chapter."})
        if not (0 <= self.pass_threshold <= 100):
            raise ValidationError({"pass_threshold": "Must be between 0 and 100."})


class Question(models.Model):
    class Kind(models.TextChoices):
        SINGLE = "single", "Single choice"
        MULTI = "multi", "Multiple choice"
        SHORT = "short", "Short answer"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SINGLE)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"Q{self.position}: {self.prompt[:60]}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.text


class Event(models.Model):
    # chapter null = org-wide event shown to everyone.
    chapter = models.ForeignKey(
        Chapter, null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    credit_value = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    # Announced at the end of the talk; a submission must echo it back. Blank = no code required.
    attendance_code = models.CharField(max_length=40, blank=True)
    quiz = models.ForeignKey(
        Quiz, null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Submission(models.Model):
    class CreditStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        EXPORTED = "exported", "Exported"
        REJECTED = "rejected", "Rejected"

    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="submissions")
    event = models.ForeignKey(
        Event, null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions"
    )
    chapter = models.ForeignKey(
        Chapter, null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions"
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    school_identifier = models.CharField(max_length=100)
    score = models.PositiveIntegerField(default=0, help_text="Percentage 0-100.")
    passed = models.BooleanField(default=False)
    attendance_code_given = models.CharField(max_length=40, blank=True)
    credit_status = models.CharField(
        max_length=10, choices=CreditStatus.choices, default=CreditStatus.PENDING
    )
    credit_note = models.CharField(max_length=300, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            # One submission per person per quiz, case-insensitive on the ID.
            # This is the real duplicate defense, enforced by the database.
            models.UniqueConstraint(
                "quiz", Lower("school_identifier"),
                name="unique_submission_per_quiz_identifier",
            )
        ]

    def __str__(self):
        return f"{self.full_name} — {self.quiz} ({self.score}%)"


class Response(models.Model):
    """One row per question answered. Stored as rows, not a JSON blob on the
    submission, so you can run item analysis ('which question does everyone
    miss?') with a plain GROUP BY later."""
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.submission_id} / {self.question_id}"


class SchoolRequest(models.Model):
    """Captured when someone picks 'my school isn't listed'. Kept apart from
    submissions so a stray free-text school name never pollutes chapters."""
    email = models.EmailField()
    school_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.school_name


class StaffProfile(models.Model):
    """Links a Django auth user to a chapter for admin scoping. chapter null =
    org-wide (can see everything)."""
    class Role(models.TextChoices):
        OFFICER = "officer", "Officer"
        CHAPTER_ADMIN = "chapter_admin", "Chapter admin"
        OWNER = "owner", "Owner"

    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="staff_profile")
    chapter = models.ForeignKey(Chapter, null=True, blank=True, on_delete=models.SET_NULL)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OFFICER)

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"
