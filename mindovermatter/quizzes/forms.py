import re

from django import forms
from django.db.models.functions import Lower

from core.models import Chapter
from events.models import Event

from .models import Question, Quiz, Submission


class QuizSubmissionForm(forms.Form):
    """Validates and grades one quiz attempt.

    Every rule here runs on the server. The quiz page is public and
    unauthenticated, so nothing the browser sends is trusted: not the
    score, not the chapter, not the question set.
    """

    full_name = forms.CharField(max_length=160, required=False, label="Full name")
    email = forms.EmailField(label="Email")
    school_identifier = forms.CharField(max_length=60)
    attendance_code = forms.CharField(max_length=40, required=False)

    def __init__(self, *args, quiz: Quiz, chapter: Chapter, event: Event | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiz = quiz
        self.chapter = chapter
        self.event = event

        self.fields["school_identifier"].label = chapter.identifier_label

        if event is not None and event.requires_code:
            self.fields["attendance_code"].required = True
            self.fields["attendance_code"].label = "Attendance code"
            self.fields["attendance_code"].help_text = "The code announced at the end of the event."
        else:
            del self.fields["attendance_code"]

        self.questions = list(quiz.questions.prefetch_related("choices"))
        for question in self.questions:
            self.fields[question.field_name] = self._build_field(question)

    def _build_field(self, question: Question):
        common = {"label": question.prompt, "required": True}
        if question.kind == Question.Kind.SINGLE:
            return forms.ModelChoiceField(
                queryset=question.choices.all(),
                widget=forms.RadioSelect,
                empty_label=None,
                **common,
            )
        if question.kind == Question.Kind.MULTI:
            return forms.ModelMultipleChoiceField(
                queryset=question.choices.all(),
                widget=forms.CheckboxSelectMultiple,
                **common,
            )
        return forms.CharField(max_length=300, **common)

    def question_fields(self):
        """Yield (question, bound_field) pairs so templates can render them in order."""
        for question in self.questions:
            yield question, self[question.field_name]

    # --- per-field rules -------------------------------------------------

    def clean_school_identifier(self):
        value = self.cleaned_data["school_identifier"].strip()
        pattern = self.chapter.identifier_pattern.strip()
        if pattern and not re.fullmatch(pattern, value):
            raise forms.ValidationError(
                f"That doesn't look like a {self.chapter.identifier_label}. Check and try again."
            )
        return value

    def clean_attendance_code(self):
        given = self.cleaned_data.get("attendance_code", "").strip()
        expected = (self.event.attendance_code if self.event else "").strip()
        if expected and given.casefold() != expected.casefold():
            raise forms.ValidationError(
                "That code doesn't match this event. It was announced at the end of the talk."
            )
        return given

    # --- cross-field rules -----------------------------------------------

    def clean(self):
        cleaned = super().clean()

        if not self.quiz.published:
            raise forms.ValidationError("This quiz isn't open.")

        if not self.chapter.collects_submissions:
            raise forms.ValidationError("This school doesn't take quiz submissions.")

        if self.quiz.scope == Quiz.Scope.CHAPTER and self.quiz.chapter_id != self.chapter.pk:
            raise forms.ValidationError("This quiz belongs to a different school.")

        if self.event is not None:
            if not self.event.published:
                raise forms.ValidationError("This event isn't open.")
            if not self.event.is_past:
                raise forms.ValidationError("This event hasn't happened yet.")
            if self.event.quiz_id != self.quiz.pk:
                raise forms.ValidationError("This quiz doesn't belong to that event.")

        identifier = cleaned.get("school_identifier")
        if identifier and not self.quiz.allow_retake:
            already = (
                Submission.objects.filter(quiz=self.quiz)
                .annotate(ident=Lower("school_identifier"))
                .filter(ident=identifier.casefold())
                .exists()
            )
            if already:
                raise forms.ValidationError(
                    "A submission for this quiz already exists under that ID. "
                    "Email us if you think that's wrong."
                )

        return cleaned
