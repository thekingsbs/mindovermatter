from django.db import models
from django.utils import timezone


class EventQuerySet(models.QuerySet):
    def published(self):
        return self.filter(published=True)

    def upcoming(self):
        return self.published().filter(starts_at__gte=timezone.now()).order_by("starts_at")

    def past(self):
        return self.published().filter(starts_at__lt=timezone.now()).order_by("-starts_at")


class Event(models.Model):
    chapter = models.ForeignKey(
        "core.Chapter", null=True, blank=True, on_delete=models.CASCADE,
        help_text="Leave blank for an org-wide event open to every chapter.",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.CharField(max_length=280, blank=True, help_text="One line shown in listings.")
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)

    credit_value = models.DecimalField(
        max_digits=4, decimal_places=2, default=0,
        help_text="SONA credits granted for attending. 0 if this event isn't credit-bearing.",
    )
    attendance_code = models.CharField(
        max_length=40, blank=True,
        help_text="Read this out in the last few minutes. Students type it into the quiz. "
                  "Leave blank to skip attendance verification.",
    )
    quiz = models.ForeignKey(
        "quizzes.Quiz", null=True, blank=True, on_delete=models.SET_NULL, related_name="events",
    )
    published = models.BooleanField(default=False)

    objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return self.title

    @property
    def is_past(self):
        return self.starts_at < timezone.now()

    @property
    def requires_code(self):
        return bool(self.attendance_code.strip())

    @property
    def is_credit_bearing(self):
        return self.credit_value > 0 and self.quiz_id is not None
