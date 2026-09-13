from django import forms

from .models import Chapter, ContactMessage, SchoolRequest


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "chapter", "subject", "body"]
        labels = {"body": "Message", "chapter": "School (optional)"}
        widgets = {"body": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chapter"].queryset = Chapter.objects.filter(active=True)
        self.fields["chapter"].required = False


class SchoolRequestForm(forms.ModelForm):
    class Meta:
        model = SchoolRequest
        fields = ["school_name", "email"]
        labels = {"school_name": "Your school"}
