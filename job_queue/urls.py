from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

app_name = "job_queue"
router = DefaultRouter()
router.register(r"jobs", views.JobViewSet, basename="job")

urlpatterns = [
    # Worker endpoints
    path("next-job/", views.get_next_job, name="get_next_job"),
    path("update-status/", views.update_status, name="update_status"),
    path("cancel-job/", views.cancel_job, name="cancel_job"),
    path("resume-job/", views.resume_job, name="resume_job"),

    # Authentication
    path("auth/login/", views.login, name="login"),

    # Job management (moved from submit_jobs)
    path("list/", views.list_jobs, name="list_jobs"),
    path("statistics/", views.job_statistics, name="job_statistics"),
    path("all/", views.get_all_jobs, name="get_all_jobs"),
    path("<str:job_id>/", views.job_detail, name="job_detail"),

    # DRF router (jobs viewset)
    path("", include(router.urls)),
]
