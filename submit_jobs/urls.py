from django.urls import path
from . import views

app_name = "submit_jobs"

urlpatterns = [
    path("create-sorting-job/", views.create_sorting_job, name="create_sorting_job"),
    path("browse/", views.browse_data_files, name="browse_data_files"),
]
