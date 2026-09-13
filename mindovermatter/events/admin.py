from django.contrib import admin

from core.admin import ChapterScopedAdmin, export_as_csv

from .models import Event


@admin.register(Event)
class EventAdmin(ChapterScopedAdmin):
    list_display = ["title", "chapter", "starts_at", "credit_value", "published"]
    list_filter = ["published", "chapter"]
    date_hierarchy = "starts_at"
    prepopulated_fields = {"slug": ("title",)}
    actions = [export_as_csv]
    fieldsets = [
        (None, {"fields": ["title", "slug", "chapter", "summary", "description", "published"]}),
        ("When and where", {"fields": ["starts_at", "ends_at", "location"]}),
        ("Credit", {
            "fields": ["credit_value", "attendance_code", "quiz"],
            "description": "Read the attendance code out in the last few minutes of the event.",
        }),
    ]
