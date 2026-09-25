from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class ForumUserAdmin(UserAdmin):
    list_display = ("username", "email", "display_name", "membership_tier", "membership_expires_at", "is_staff")
    list_filter = UserAdmin.list_filter + ("membership_tier",)
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("display_name", "location", "bio")}),
        ("Membership", {"fields": ("membership_tier", "membership_expires_at")}),
    )
