from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Chapter(models.Model):
    """A campus where Mind Over Matter operates."""

    class Kind(models.TextChoices):
        UNIVERSITY = "university", "University"
        HIGH_SCHOOL = "high_school", "High school"

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.UNIVERSITY)

    # High school chapters never collect participant data. See clean().
    collects_submissions = models.BooleanField(
        default=True,
        help_text="Whether students at this chapter may submit quizzes. Always off for high schools.",
    )
    sona_enabled = models.BooleanField(
        default=False,
        help_text="Turn on once the department's participant pool coordinator has approved credit.",
    )

    identifier_label = models.CharField(
        max_length=60,
        default="Student ID",
        help_text="What this school calls the ID students enter, e.g. 'GT ID' or 'NetID'.",
    )
    identifier_pattern = models.CharField(
        max_length=200,
        blank=True,
        help_text=r"Optional regex the identifier must match, e.g. ^90\d{7}$. Leave blank to accept anything.",
    )

    contact_email = models.EmailField(blank=True)
    active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        if self.kind == self.Kind.HIGH_SCHOOL and self.collects_submissions:
            raise ValidationError(
                {"collects_submissions": "High school chapters cannot collect participant data."}
            )

    def save(self, *args, **kwargs):
        if self.kind == self.Kind.HIGH_SCHOOL:
            self.collects_submissions = False
            self.sona_enabled = False
        super().save(*args, **kwargs)


class OfficerProfile(models.Model):
    """Links a Django user to the chapter whose data they may see."""

    class Role(models.TextChoices):
        OFFICER = "officer", "Officer"
        CHAPTER_ADMIN = "chapter_admin", "Chapter admin"
        OWNER = "owner", "Owner"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="officer_profile"
    )
    chapter = models.ForeignKey(
        Chapter,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Leave blank for org-wide access across every chapter.",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OFFICER)

    def __str__(self):
        return f"{self.user} ({self.chapter or 'org-wide'})"

    @property
    def is_org_wide(self):
        return self.chapter_id is None


class Resource(models.Model):
    class Kind(models.TextChoices):
        LINK = "link", "External link"
        FILE = "file", "Uploaded file"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.LINK)
    url = models.URLField(blank=True)
    file = models.FileField(upload_to="resources/", blank=True)
    chapter = models.ForeignKey(
        Chapter, null=True, blank=True, on_delete=models.CASCADE,
        help_text="Leave blank to show on every chapter's page.",
    )
    published = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "title"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.kind == self.Kind.LINK and not self.url:
            raise ValidationError({"url": "Add a URL, or change the kind to an uploaded file."})
        if self.kind == self.Kind.FILE and not self.file:
            raise ValidationError({"file": "Upload a file, or change the kind to an external link."})

    @property
    def href(self):
        return self.url if self.kind == self.Kind.LINK else self.file.url


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    chapter = models.ForeignKey(Chapter, null=True, blank=True, on_delete=models.SET_NULL)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.name}"


class SchoolRequest(models.Model):
    """Captured when someone's school isn't in the chapter list yet."""

    school_name = models.CharField(max_length=200)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.school_name
