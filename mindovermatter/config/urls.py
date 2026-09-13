from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Mind Over Matter"
admin.site.site_title = "Mind Over Matter"
admin.site.index_title = "Chapter administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("events/", include("events.urls")),
    path("quiz/", include("quizzes.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
