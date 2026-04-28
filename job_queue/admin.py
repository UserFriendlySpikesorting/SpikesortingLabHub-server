from django.contrib import admin
from .models import Job, JobStep, StepConfig

# Expose DRF Token in admin list so token keys are visible to admins
try:
    from rest_framework.authtoken.models import Token

    try:
        admin.site.unregister(Token)
    except Exception:
        # if it wasn't registered yet, ignore
        pass

    @admin.register(Token)
    class TokenAdmin(admin.ModelAdmin):
        list_display = ("key", "user")
        search_fields = ("key", "user__username", "user__email")
        readonly_fields = ("key",)
        ordering = ("-user",)

    # Some installations register a TokenProxy proxy model (name: tokenproxy)
    # which is what the default admin index links to. Try to register it too
    # so the admin link resolves and shows token keys.
    try:
        # TokenProxy may be defined in rest_framework.authtoken.admin
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
        # If TokenProxy isn't available, that's fine — Token itself is registered
        pass
except Exception:
    # rest_framework.authtoken may not be installed in some environments
    pass


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Admin configuration for the Job model."""

    list_display = ("job_id", "status", "created_at")
    search_fields = ("job_id",)
    list_filter = ("status",)
    readonly_fields = ("job_id", "created_at")
    actions = [
        "mark_as_pending",
        "mark_as_fetched",
        "mark_as_running",
        "mark_as_finished",
        "mark_as_failed",
    ]

    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status="pending")
        self.message_user(request, f"{updated} job(s) marked as pending.")

    mark_as_pending.short_description = "Mark selected as Pending"

    def mark_as_fetched(self, request, queryset):
        updated = queryset.update(status="fetched")
        self.message_user(request, f"{updated} job(s) marked as fetched.")

    mark_as_fetched.short_description = "Mark selected as Fetched"

    def mark_as_running(self, request, queryset):
        updated = queryset.update(status="running")
        self.message_user(request, f"{updated} job(s) marked as running.")

    mark_as_running.short_description = "Mark selected as Running"

    def mark_as_finished(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"{updated} job(s) marked as completed.")

    mark_as_finished.short_description = "Mark selected as Completed"

    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status="failed")
        self.message_user(request, f"{updated} job(s) marked as failed.")

    mark_as_failed.short_description = "Mark selected as Failed"


@admin.register(StepConfig)
class StepConfigAdmin(admin.ModelAdmin):
    """Admin configuration for the StepConfig model."""

    # 'config_block_hash' is the primary key now, so use it
    # 'created_at' does NOT exist in StepConfig model, so remove it
    # 'fingerprint' was a conceptual name, the actual field is 'config_block_hash'
    list_display = ("config_block_hash", "config_block")
    # Allow searching by the hash
    search_fields = ("config_block_hash",)
    # Make config_block read-only in admin detail view if you don't want it editable
    # fields = ('config_block_hash', 'config_block')
    # readonly_fields = ('config_block_hash',) # Hash should not be editable


@admin.register(JobStep)
class JobStepAdmin(admin.ModelAdmin):
    """Admin configuration for the JobStep model."""

    list_display = (
        "identifier",
        "job",
        "function",
        "config_block_hash",
        "depends_on",
        "status",
    )
    search_fields = ("identifier", "function")
    list_filter = ("job", "function", "status")
    raw_id_fields = ("job", "config_block_hash")
    readonly_fields = ("identifier", "job")
    actions = [
        "mark_step_as_pending",
        "mark_step_as_running",
        "mark_step_as_completed",
        "mark_step_as_failed",
    ]

    def mark_step_as_pending(self, request, queryset):
        updated = queryset.update(status="pending")
        self.message_user(request, f"{updated} step(s) marked as pending.")

    mark_step_as_pending.short_description = "Mark selected steps as Pending"

    def mark_step_as_running(self, request, queryset):
        updated = queryset.update(status="running")
        self.message_user(request, f"{updated} step(s) marked as running.")

    mark_step_as_running.short_description = "Mark selected steps as Running"

    def mark_step_as_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"{updated} step(s) marked as completed.")

    mark_step_as_completed.short_description = "Mark selected steps as Completed"

    def mark_step_as_failed(self, request, queryset):
        updated = queryset.update(status="failed")
        self.message_user(request, f"{updated} step(s) marked as failed.")

    mark_step_as_failed.short_description = "Mark selected steps as Failed"
