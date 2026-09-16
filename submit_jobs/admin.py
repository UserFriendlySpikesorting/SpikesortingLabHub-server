from django.contrib import admin
from .models import JobCreationLog, JobEnvironmentDefault


@admin.register(JobCreationLog)
class JobCreationLogAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "pipeline_id", "status", "created_at"]
    list_filter = ["status", "created_at"]
    readonly_fields = ["created_at"]
    search_fields = ["job__job_id", "pipeline_id"]


@admin.register(JobEnvironmentDefault)
class JobEnvironmentDefaultAdmin(admin.ModelAdmin):
    list_display = ["environment", "n_jobs", "total_memory", "chunk_duration", "updated_at"]
    readonly_fields = ["updated_at"]
    search_fields = ["environment"]
