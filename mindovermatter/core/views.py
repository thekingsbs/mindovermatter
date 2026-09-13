from django.contrib import messages
from django.shortcuts import redirect, render

from events.models import Event

from .forms import ContactForm
from .models import Chapter, Resource


def home(request):
    return render(request, "pages/home.html", {
        "next_event": Event.objects.upcoming().first(),
        "upcoming": Event.objects.upcoming()[1:4],
        "chapters": Chapter.objects.filter(active=True),
    })


def about(request):
    return render(request, "pages/about.html", {
        "chapters": Chapter.objects.filter(active=True),
    })


def resources(request):
    return render(request, "pages/resources.html", {
        "resources": Resource.objects.filter(published=True).select_related("chapter"),
    })


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Message sent. We usually reply within a few days.")
        return redirect("contact")
    return render(request, "pages/contact.html", {"form": form})


def privacy(request):
    return render(request, "pages/privacy.html")
