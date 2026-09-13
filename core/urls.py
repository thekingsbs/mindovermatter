from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("events/", views.event_list, name="event_list"),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path("resources/", views.resources, name="resources"),
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy, name="privacy"),

    # Quiz flow
    path("quiz/", views.quiz_landing, name="quiz_landing"),
    path("quiz/school/", views.quiz_school_picker, name="quiz_school"),
    path("quiz/general/", views.quiz_general, name="quiz_general"),
    path("quiz/school/<slug:slug>/", views.quiz_for_school, name="quiz_for_school"),
    path("quiz/school/not-listed/", views.school_not_listed, name="school_not_listed"),
    path("quiz/<int:quiz_id>/", views.quiz_take, name="quiz_take"),
    path("quiz/complete/<int:submission_id>/", views.quiz_complete, name="quiz_complete"),
]
