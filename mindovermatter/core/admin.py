import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import Chapter, ContactMessage, OfficerProfile, Resource, SchoolRequest


class ChapterScopedAdmin(admin.ModelAdmin):
    """Restricts a chapter officer to their own chapter's rows.

    Set `chapter_lookup` to the ORM path from this model to a Chapter.
    Superusers and officers with no chapter set see everything.
    """

    chapter_lookup = "chapter"

    def _viewer_chapter(self, request):
        if request.user.is_superuser:
            return None
        profile = getattr(request.user, "officer_profile", None)
        return profile.chapter if profile else None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        chapter = self._viewer_chapter(request)
        if chapter is None:
            return qs
        return qs.filter(**{self.chapter_lookup: chapter})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        chapter = self._viewer_chapter(request)
        if db_field.name == "chapter" and chapter is not None:
            kwargs["queryset"] = Chapter.objects.filter(pk=chapter.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


def export_as_csv(modeladmin, request, queryset):
    fields = [f.name for f in modeladmin.model._meta.fields]
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f"attachment; filename={modeladmin.model._meta.model_name}.csv"
    )
    writer = csv.writer(response)
    writer.writerow(fields)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in fields])
    return response


export_as_csv.short_description = "Export selected rows to CSV"


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "collects_submissions", "sona_enabled", "active"]
    list_filter = ["kind", "active", "sona_enabled"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(OfficerProfile)
class OfficerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "chapter", "role"]
    list_filter = ["role", "chapter"]


@admin.register(Resource)
class ResourceAdmin(ChapterScopedAdmin):
    list_display = ["title", "kind", "chapter", "published"]
    list_filter = ["kind", "published", "chapter"]


@admin.register(ContactMessage)
class ContactMessageAdmin(ChapterScopedAdmin):
    list_display = ["subject", "name", "email", "chapter", "created_at", "handled"]
    list_filter = ["handled", "chapter"]
    readonly_fields = ["name", "email", "chapter", "subject", "body", "created_at"]
    actions = [export_as_csv]


@admin.register(SchoolRequest)
class SchoolRequestAdmin(admin.ModelAdmin):
    list_display = ["school_name", "email", "created_at"]
    actions = [export_as_csv]
