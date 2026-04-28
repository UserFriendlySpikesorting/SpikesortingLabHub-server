from django.contrib import admin
from .models import JobCreationLog


@admin.register(JobCreationLog)
class JobCreationLogAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "pipeline_id", "status", "created_at"]
    list_filter = ["status", "created_at"]
    readonly_fields = ["created_at"]
    search_fields = ["job__job_id", "pipeline_id"]
