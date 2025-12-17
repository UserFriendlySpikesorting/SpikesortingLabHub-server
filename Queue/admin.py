from django.contrib import admin
from .models import Job, JobStep, StepConfig

# Expose DRF Token in admin list so token keys are visible to admins
try:
    from rest_framework.authtoken.models import Token

    try:
        admin.site.unregister(Token)
    except Exception:
        pass

    @admin.register(Token)
    class TokenAdmin(admin.ModelAdmin):
        list_display = ("key", "user")
        search_fields = ("key", "user__username", "user__email")
        readonly_fields = ("key",)
        ordering = ("-user",)

    try:
        from rest_framework.authtoken.admin import TokenProxy

        try:
            admin.site.unregister(TokenProxy)
        except Exception:
            pass

        @admin.register(TokenProxy)
        class TokenProxyAdmin(admin.ModelAdmin):
            list_display = ("key", "user")
            search_fields = ("key", "user__username", "user__email")
            readonly_fields = ("key",)
            ordering = ("-user",)

    except Exception:
        pass
except Exception:
    pass


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Admin configuration for the Job model."""

    list_display = ("job_id", "status", "created_at")
    search_fields = ("job_id",)
    list_filter = ("status",)


@admin.register(StepConfig)
class StepConfigAdmin(admin.ModelAdmin):
    """Admin configuration for the StepConfig model."""

    list_display = ("config_block_hash", "function")
    search_fields = ("config_block_hash",)


@admin.register(JobStep)
class JobStepAdmin(admin.ModelAdmin):
    """Admin configuration for the JobStep model."""

    list_display = ("identifier", "job", "function", "config_block_hash", "status")
    search_fields = ("identifier", "function")
    list_filter = ("job", "function", "status")
    raw_id_fields = ("job", "config_block_hash")
