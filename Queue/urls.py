from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import JobViewSet, login, get_next_job, job_list
from . import views

app_name = "Queue"
router = DefaultRouter()
router.register(r"jobs", JobViewSet, basename="job")

urlpatterns = [
    path("job_list/", job_list, name="job_list"),
    path("getthenextjob/", get_next_job, name="get_next_job"),
    path("auth/login/", login, name="login"),
    path("", include(router.urls)),
]
