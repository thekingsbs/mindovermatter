from django.urls import path

from . import views

urlpatterns = [
    path("", views.quiz_choose, name="quiz_choose"),
    path("general/", views.quiz_general, name="quiz_general"),
    path("school/", views.school_search, name="school_search"),
    path("school/<slug:slug>/", views.school_quizzes, name="school_quizzes"),
    path("take/<int:pk>/", views.take_quiz, name="take_quiz"),
    path("done/<int:pk>/", views.quiz_done, name="quiz_done"),
]
