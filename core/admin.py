"""Admin config. This is where officers actually run the org: create events,
build quizzes, review submissions, export a verified CSV for SONA.

Chapter scoping is enforced in get_queryset for every model that carries a
chapter, so a KSU chapter_admin can't see GT data. Org-wide staff (no chapter
on their profile, or is_superuser) see everything.
"""
import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import (
    Chapter, Choice, Event, Question, Quiz, Response, SchoolRequest,
    StaffProfile, Submission,
)


def staff_chapter(request):
    """The chapter a logged-in user is scoped to, or None for org-wide."""
    if request.user.is_superuser:
        return None
    profile = getattr(request.user, "staff_profile", None)
    return profile.chapter if profile else None


class ChapterScopedAdmin(admin.ModelAdmin):
    """Base class: filters the changelist to the user's chapter. `chapter_path`
    is the ORM lookup from this model to a Chapter (e.g. 'chapter' or
    'quiz__chapter')."""
    chapter_path = "chapter"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        ch = staff_chapter(request)
        if ch is None:
            return qs
        return qs.filter(**{self.chapter_path: ch})


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "collects_submissions", "sona_enabled", "active")
    list_filter = ("kind", "active", "sona_enabled")
    prepopulated_fields = {"slug": ("name",)}


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    show_change_link = True  # click through to add choices


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ("prompt", "quiz", "kind", "position")
    list_filter = ("quiz", "kind")


@admin.register(Quiz)
class QuizAdmin(ChapterScopedAdmin):
    chapter_path = "chapter"
    inlines = [QuestionInline]
    list_display = ("title", "scope", "chapter", "pass_threshold", "published")
    list_filter = ("scope", "published")


@admin.register(Event)
class EventAdmin(ChapterScopedAdmin):
    chapter_path = "chapter"
    list_display = ("title", "chapter", "starts_at", "credit_value", "published")
    list_filter = ("published", "chapter")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "starts_at"


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 0
    can_delete = False
    readonly_fields = ("question", "choice", "text_answer", "is_correct")


@admin.action(description="Export selected to CSV (and mark exported)")
def export_submissions_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="submissions.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "full_name", "email", "school_identifier", "chapter", "event",
        "quiz", "score", "passed", "credit_status", "submitted_at",
    ])
    for s in queryset.select_related("chapter", "event", "quiz"):
        writer.writerow([
            s.full_name, s.email, s.school_identifier,
            s.chapter.name if s.chapter else "",
            s.event.title if s.event else "",
            s.quiz.title, s.score, s.passed, s.credit_status,
            s.submitted_at.isoformat(),
        ])
    # Mark verified rows as exported so you don't hand the same roster in twice.
    queryset.filter(credit_status=Submission.CreditStatus.VERIFIED).update(
        credit_status=Submission.CreditStatus.EXPORTED
    )
    return response


@admin.action(description="Mark selected as verified")
def mark_verified(modeladmin, request, queryset):
    queryset.update(credit_status=Submission.CreditStatus.VERIFIED)


@admin.register(Submission)
class SubmissionAdmin(ChapterScopedAdmin):
    chapter_path = "chapter"
    list_display = ("full_name", "school_identifier", "chapter", "quiz",
                    "score", "passed", "credit_status", "submitted_at")
    list_filter = ("credit_status", "passed", "chapter", "quiz")
    search_fields = ("full_name", "email", "school_identifier")
    readonly_fields = ("quiz", "event", "chapter", "full_name", "email",
                       "school_identifier", "score", "passed",
                       "attendance_code_given", "submitted_at")
    inlines = [ResponseInline]
    actions = [mark_verified, export_submissions_csv]


@admin.register(SchoolRequest)
class SchoolRequestAdmin(admin.ModelAdmin):
    list_display = ("school_name", "email", "created_at")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "chapter", "role")
    list_filter = ("role", "chapter")
