"""
URL configuration for labhub project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/queue/", include("Queue.urls")),
]
