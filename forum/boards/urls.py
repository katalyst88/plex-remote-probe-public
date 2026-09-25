from django.urls import path

from . import views

app_name = "boards"

urlpatterns = [
    path("", views.index, name="index"),
    path("search/", views.search, name="search"),
    path("c/<slug:slug>/", views.category_detail, name="category"),
    path("c/<slug:slug>/new/", views.new_thread, name="new_thread"),
    path("t/<int:pk>/", views.thread_detail, name="thread_short"),
    path("t/<int:pk>/reply/", views.reply, name="reply"),
    path("t/<int:pk>/mod/<str:action>/", views.moderate_thread, name="moderate"),
    # Keep last among t/ routes: the slug would otherwise swallow "reply".
    path("t/<int:pk>/<slug:slug>/", views.thread_detail, name="thread"),
    path("p/<int:pk>/", views.post_permalink, name="post"),
    path("p/<int:pk>/edit/", views.edit_post, name="edit_post"),
    path("p/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path("p/<int:pk>/like/", views.toggle_like, name="like"),
]
