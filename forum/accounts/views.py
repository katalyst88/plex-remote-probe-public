from django.contrib import messages
from django.db.models import Count
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from boards.models import Post, Thread

from .forms import ProfileForm, SignUpForm
from .models import User


def signup(request):
    if request.user.is_authenticated:
        return redirect("boards:index")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome aboard! Your account is ready.")
        return redirect("boards:index")
    return render(request, "accounts/signup.html", {"form": form})


def profile(request, username):
    member = get_object_or_404(User, username=username, is_active=True)
    threads = (
        Thread.objects.visible_to(request.user)
        .filter(author=member)
        .select_related("category", "author")
        .annotate(reply_count=Count("posts") - 1)
        .order_by("-created_at")[:10]
    )
    posts = (
        Post.objects.filter(author=member, thread__in=Thread.objects.visible_to(request.user))
        .select_related("thread")
        .order_by("-created_at")[:10]
    )
    return render(
        request,
        "accounts/profile.html",
        {
            "member": member,
            "threads": threads,
            "posts": posts,
            "post_count": Post.objects.filter(author=member).count(),
            "likes_received": Post.likes.through.objects.filter(post__author=member).count(),
        },
    )


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect(request.user)
    return render(request, "accounts/edit_profile.html", {"form": form})
