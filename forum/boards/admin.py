from django.contrib import admin

from .models import Category, Post, Thread


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "position", "staff_only_posting", "members_only")
    list_editable = ("position", "staff_only_posting", "members_only")
    prepopulated_fields = {"slug": ("name",)}


class PostInline(admin.TabularInline):
    model = Post
    extra = 0
    fields = ("author", "body", "created_at")
    raw_id_fields = ("author",)


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "last_activity_at", "is_pinned", "is_locked", "view_count")
    list_filter = ("category", "is_pinned", "is_locked")
    search_fields = ("title",)
    raw_id_fields = ("author",)
    inlines = [PostInline]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("pk", "thread", "author", "created_at")
    search_fields = ("body",)
    raw_id_fields = ("author", "thread")
    filter_horizontal = ("likes",)
