"""Forms. The submission form carries the server-side validation checks from
the spec. Everything here runs on the server; the client-side quiz is only a
convenience and is assumed to be bypassable."""
import re

from django import forms
from django.utils import timezone

from .models import Chapter, Event, Quiz, SchoolRequest


class ContactForm(forms.Form):
    name = forms.CharField(max_length=200,required=False)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)


class SchoolRequestForm(forms.ModelForm):
    class Meta:
        model = SchoolRequest
        fields = ["email", "school_name"]


class QuizSubmissionForm(forms.Form):
    """Validates identity + attendance + eligibility. Question answers are read
    separately from the POST in the view (their fields are dynamic), then scored
    by services.score_submission. This form guards the gate; it does not grade.
    """
    full_name = forms.CharField(max_length=200, required=False)
    email = forms.EmailField()
    school_identifier = forms.CharField(max_length=100)
    attendance_code = forms.CharField(max_length=40, required=False)

    def __init__(self, *args, quiz: Quiz, event: Event | None = None, **kwargs):
        self.quiz = quiz
        self.event = event
        super().__init__(*args, **kwargs)

    def clean_school_identifier(self):
        value = self.cleaned_data["school_identifier"].strip()
        chapter = self._resolve_chapter()
        if chapter and chapter.identifier_pattern:
            if not re.fullmatch(chapter.identifier_pattern, value):
                raise forms.ValidationError(
                    "That doesn't look like a valid ID for your school. Check the format and try again."
                )
        return value

    def _resolve_chapter(self) -> Chapter | None:
        # A chapter quiz names its chapter; otherwise the event's chapter applies.
        if self.quiz.scope == Quiz.Scope.CHAPTER:
            return self.quiz.chapter
        if self.event:
            return self.event.chapter
        return None

    def clean(self):
        cleaned = super().clean()

        # 1. Quiz must be published.
        if not self.quiz.published:
            raise forms.ValidationError("This quiz isn't open right now.")

        chapter = self._resolve_chapter()

        # 2. Event, if present, must have already started.
        if self.event:
            if self.event.starts_at > timezone.now():
                raise forms.ValidationError("This event hasn't happened yet.")

            # 3. Attendance code must match (case-insensitive, trimmed).
            expected = self.event.attendance_code.strip().lower()
            if expected:
                given = (cleaned.get("attendance_code") or "").strip().lower()
                if not given:
                    self.add_error("attendance_code", "This event needs the code from the talk.")
                elif given != expected:
                    self.add_error("attendance_code", "That code isn't right.")

        # 4. Chapter must accept submissions (blocks high schools / minors).
        if chapter and not chapter.collects_submissions:
            raise forms.ValidationError("This school isn't set up to collect quiz submissions.")

        return cleaned
