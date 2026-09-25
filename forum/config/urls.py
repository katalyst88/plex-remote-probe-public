from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Forum admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("boards.urls")),
]
