from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=240, blank=True)
    position = models.PositiveIntegerField(default=0)
    staff_only_posting = models.BooleanField(
        default=False, help_text="Only staff can start threads here (e.g. announcements)."
    )
    members_only = models.BooleanField(
        default=False, help_text="Only paying members (and staff) can read or post here."
    )

    class Meta:
        ordering = ("position", "name")
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("boards:category", args=[self.slug])

    def is_readable_by(self, user):
        if not self.members_only:
            return True
        return user.is_authenticated and user.has_active_membership

    def can_start_thread(self, user):
        if not user.is_authenticated or not self.is_readable_by(user):
            return False
        return user.is_staff or not self.staff_only_posting


# Slugs that would collide with the t/<pk>/<action>/ routes.
RESERVED_SLUGS = {"reply"}


class ThreadQuerySet(models.QuerySet):
    def visible_to(self, user):
        if user.is_authenticated and user.has_active_membership:
            return self
        return self.filter(category__members_only=False)


class Thread(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="threads")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads")
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)

    objects = ThreadQuerySet.as_manager()

    class Meta:
        ordering = ("-is_pinned", "-last_activity_at")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:150] or "thread"
            if self.slug in RESERVED_SLUGS:
                self.slug += "-thread"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("boards:thread", args=[self.pk, self.slug])

    def can_reply(self, user):
        if not user.is_authenticated or not self.category.is_readable_by(user):
            return False
        return user.is_staff or not self.is_locked


class Post(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    body = models.TextField(max_length=20000)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_posts", blank=True)

    class Meta:
        ordering = ("created_at", "pk")

    def __str__(self):
        return f"Post {self.pk} in {self.thread}"

    @property
    def is_opening_post(self):
        first = self.thread.posts.order_by("created_at", "pk").values_list("pk", flat=True).first()
        return first == self.pk

    def can_edit(self, user):
        return user.is_authenticated and (user.is_staff or (user == self.author and not self.thread.is_locked))

    def get_absolute_url(self):
        return reverse("boards:post", args=[self.pk])


def search_threads(user, query):
    matching_posts = Post.objects.filter(body__icontains=query).values("thread_id")
    return (
        Thread.objects.visible_to(user)
        .filter(Q(title__icontains=query) | Q(pk__in=matching_posts))
        .select_related("category", "author")
        .annotate(reply_count=models.Count("posts") - 1)
    )
