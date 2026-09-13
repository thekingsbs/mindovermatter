import csv

from django.contrib import admin
from django.http import HttpResponse

from core.admin import ChapterScopedAdmin, export_as_csv

from .models import Choice, Question, Quiz, Response, Submission


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True
    fields = ["position", "prompt", "kind"]


@admin.register(Quiz)
class QuizAdmin(ChapterScopedAdmin):
    list_display = ["title", "scope", "chapter", "question_count", "pass_threshold", "published"]
    list_filter = ["scope", "published", "chapter"]
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["prompt", "quiz", "kind", "position"]
    list_filter = ["quiz", "kind"]
    inlines = [ChoiceInline]


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 0
    can_delete = False
    readonly_fields = ["question", "choice", "text_answer", "is_correct"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.action(description="Export SONA roster for selected submissions")
def export_sona_roster(modeladmin, request, queryset):
    """The handover file. Only verified, passing submissions belong in it."""
    rows = queryset.filter(
        passed=True, credit_status=Submission.CreditStatus.VERIFIED
    ).select_related("chapter", "event")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=sona_roster.csv"
    writer = csv.writer(response)
    writer.writerow(["school", "student_identifier", "full_name", "email",
                     "event", "event_date", "credits", "score_pct", "submitted_at"])
    for s in rows:
        writer.writerow([
            s.chapter.name, s.school_identifier, s.full_name, s.email,
            s.event.title if s.event else "",
            s.event.starts_at.date() if s.event else "",
            s.event.credit_value if s.event else "",
            s.percentage, s.submitted_at.isoformat(),
        ])
    rows.update(credit_status=Submission.CreditStatus.EXPORTED)
    return response


@admin.action(description="Mark selected as verified")
def mark_verified(modeladmin, request, queryset):
    queryset.filter(passed=True).update(credit_status=Submission.CreditStatus.VERIFIED)


@admin.register(Submission)
class SubmissionAdmin(ChapterScopedAdmin):
    list_display = ["full_name", "chapter", "school_identifier", "quiz",
                    "event", "percentage", "passed", "credit_status", "submitted_at"]
    list_filter = ["credit_status", "passed", "chapter", "quiz", "event"]
    search_fields = ["full_name", "email", "school_identifier"]
    date_hierarchy = "submitted_at"
    inlines = [ResponseInline]
    actions = [mark_verified, export_sona_roster, export_as_csv]
    readonly_fields = ["quiz", "event", "chapter", "full_name", "email", "school_identifier",
                       "score", "total_questions", "passed", "attendance_code_given", "submitted_at"]
