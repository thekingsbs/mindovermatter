from django.shortcuts import get_object_or_404, render

from .models import Event


def event_list(request):
    return render(request, "events/list.html", {
        "upcoming": Event.objects.upcoming().select_related("chapter"),
        "past": Event.objects.past().select_related("chapter")[:20],
    })


def event_detail(request, slug):
    event = get_object_or_404(
        Event.objects.published().select_related("chapter", "quiz"), slug=slug
    )
    return render(request, "events/detail.html", {"event": event})
