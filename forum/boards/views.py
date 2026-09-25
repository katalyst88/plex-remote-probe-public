from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PostForm, ThreadForm
from .models import Category, Post, Thread, search_threads


def _require_readable(category, user):
    if not category.is_readable_by(user):
        raise PermissionDenied("members_only")


def _page_of_post(post):
    position = post.thread.posts.filter(created_at__lt=post.created_at).count() + post.thread.posts.filter(
        created_at=post.created_at, pk__lt=post.pk
    ).count()
    return position // settings.FORUM_POSTS_PER_PAGE + 1


def _post_url(post):
    page = _page_of_post(post)
    suffix = f"?page={page}" if page > 1 else ""
    return f"{post.thread.get_absolute_url()}{suffix}#post-{post.pk}"


def index(request):
    categories = Category.objects.annotate(
        thread_count=Count("threads", distinct=True),
        post_count=Count("threads__posts", distinct=True),
        last_activity=Max("threads__last_activity_at"),
    )
    recent = Thread.objects.visible_to(request.user).select_related("category", "author")
    recent = recent.annotate(reply_count=Count("posts") - 1).order_by("-last_activity_at")[:6]
    return render(request, "boards/index.html", {"categories": categories, "recent_threads": recent})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if not category.is_readable_by(request.user):
        return render(request, "boards/members_only.html", {"category": category}, status=403)
    threads = (
        category.threads.select_related("author")
        .annotate(reply_count=Count("posts") - 1)
        .order_by("-is_pinned", "-last_activity_at")
    )
    page = Paginator(threads, settings.FORUM_THREADS_PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "boards/category.html",
        {"category": category, "page": page, "can_post": category.can_start_thread(request.user)},
    )


def thread_detail(request, pk, slug=None):
    thread = get_object_or_404(Thread.objects.select_related("category", "author"), pk=pk)
    if not thread.category.is_readable_by(request.user):
        return render(request, "boards/members_only.html", {"category": thread.category}, status=403)
    if slug != thread.slug:
        return redirect(thread, permanent=True)

    Thread.objects.filter(pk=thread.pk).update(view_count=F("view_count") + 1)
    posts = thread.posts.select_related("author").annotate(like_count=Count("likes"))
    page = Paginator(posts, settings.FORUM_POSTS_PER_PAGE).get_page(request.GET.get("page"))
    liked = set()
    if request.user.is_authenticated:
        liked = set(request.user.liked_posts.filter(thread=thread).values_list("pk", flat=True))
    first_post_id = thread.posts.values_list("pk", flat=True).first()
    return render(
        request,
        "boards/thread.html",
        {
            "thread": thread,
            "page": page,
            "liked": liked,
            "first_post_id": first_post_id,
            "form": PostForm(),
            "can_reply": thread.can_reply(request.user),
        },
    )


def post_permalink(request, pk):
    post = get_object_or_404(Post.objects.select_related("thread__category"), pk=pk)
    _require_readable(post.thread.category, request.user)
    return redirect(_post_url(post))


@login_required
def new_thread(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if not category.can_start_thread(request.user):
        raise PermissionDenied
    form = ThreadForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            thread = form.save(commit=False)
            thread.category = category
            thread.author = request.user
            thread.save()
            Post.objects.create(thread=thread, author=request.user, body=form.cleaned_data["body"])
        messages.success(request, "Thread posted.")
        return redirect(thread)
    return render(request, "boards/new_thread.html", {"category": category, "form": form})


@login_required
@require_POST
def reply(request, pk):
    thread = get_object_or_404(Thread.objects.select_related("category"), pk=pk)
    if not thread.can_reply(request.user):
        raise PermissionDenied
    form = PostForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Your reply couldn't be posted: " + " ".join(form.errors.get("body", [])))
        return redirect(thread)
    with transaction.atomic():
        post = form.save(commit=False)
        post.thread = thread
        post.author = request.user
        post.save()
        Thread.objects.filter(pk=thread.pk).update(last_activity_at=post.created_at)
    return redirect(_post_url(post))


@login_required
def edit_post(request, pk):
    post = get_object_or_404(Post.objects.select_related("thread__category"), pk=pk)
    if not post.can_edit(request.user):
        raise PermissionDenied
    is_opening = post.is_opening_post
    form = PostForm(request.POST or None, instance=post)
    title_error = None
    if request.method == "POST":
        new_title = request.POST.get("title", "").strip() if is_opening else None
        if is_opening and len(new_title) < 5:
            title_error = "Titles need at least 5 characters."
        if form.is_valid() and not title_error:
            with transaction.atomic():
                post = form.save(commit=False)
                post.edited_at = timezone.now()
                post.save()
                if is_opening and new_title != post.thread.title:
                    post.thread.title = new_title
                    post.thread.slug = ""
                    post.thread.save()
            messages.success(request, "Post updated.")
            return redirect(_post_url(post))
    return render(
        request,
        "boards/edit_post.html",
        {"post": post, "form": form, "is_opening": is_opening, "title_error": title_error},
    )


@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post.objects.select_related("thread__category"), pk=pk)
    if not post.can_edit(request.user):
        raise PermissionDenied
    thread = post.thread
    is_opening = post.is_opening_post
    if request.method == "POST":
        if is_opening:
            category = thread.category
            thread.delete()
            messages.success(request, "Thread deleted.")
            return redirect(category)
        with transaction.atomic():
            post.delete()
            latest = thread.posts.order_by("-created_at").values_list("created_at", flat=True).first()
            Thread.objects.filter(pk=thread.pk).update(last_activity_at=latest or thread.created_at)
        messages.success(request, "Reply deleted.")
        return redirect(thread)
    return render(request, "boards/confirm_delete.html", {"post": post, "is_opening": is_opening})


@login_required
@require_POST
def toggle_like(request, pk):
    post = get_object_or_404(Post.objects.select_related("thread__category"), pk=pk)
    _require_readable(post.thread.category, request.user)
    if post.author_id == request.user.pk:
        messages.info(request, "You can't like your own post.")
    elif post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect(_post_url(post))


@login_required
@require_POST
def moderate_thread(request, pk, action):
    if not request.user.is_staff:
        raise PermissionDenied
    thread = get_object_or_404(Thread, pk=pk)
    toggles = {"pin": "is_pinned", "lock": "is_locked"}
    if action not in toggles:
        raise Http404
    field = toggles[action]
    setattr(thread, field, not getattr(thread, field))
    thread.save(update_fields=[field])
    return redirect(thread)


def search(request):
    query = request.GET.get("q", "").strip()
    page = None
    if len(query) >= 2:
        results = search_threads(request.user, query).order_by("-last_activity_at")
        page = Paginator(results, settings.FORUM_THREADS_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "boards/search.html", {"query": query, "page": page})
