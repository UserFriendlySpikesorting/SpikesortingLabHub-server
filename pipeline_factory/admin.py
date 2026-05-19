from django.contrib import admin
from .models import Pipeline, PipelineStep


class PipelineStepInline(admin.TabularInline):
    model = PipelineStep
    extra = 1
    fields = ["config_block_hash", "depends_on"]
    # 'depends_on' is a JSONField (pipeline-local identifiers) so it is not
    # suitable for admin autocomplete. Keep config_block_hash as FK autocomplete
    # if StepConfig is registered to support it.
    autocomplete_fields = ["config_block_hash"]


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ["pipeline_id", "description_preview", "created_at", "step_count"]
    list_filter = ["created_at"]
    search_fields = ["description"]
    readonly_fields = ["created_at"]
    inlines = [PipelineStepInline]

    def description_preview(self, obj):
        return (
            obj.description[:100] + "..."
            if len(obj.description) > 100
            else obj.description
        )

    description_preview.short_description = "Description"

    def step_count(self, obj):
        return obj.steps.count()

    step_count.short_description = "Steps"


@admin.register(PipelineStep)
class PipelineStepAdmin(admin.ModelAdmin):
    list_display = ["pipeline_step_id", "pipeline", "config_block_hash", "depends_on"]
    list_filter = ["pipeline"]
    search_fields = [
        "pipeline__description",
        "config_block_hash__config_block_hash",
        "config_block_hash__function",
    ]
    # depends_on is a JSONField and not a FK/M2M, so remove it from autocomplete
    autocomplete_fields = ["pipeline", "config_block_hash"]
    # Execution order is inferred from the step insertion/array order
    ordering = ["pipeline"]

    def step_config_preview(self, obj):
        return f"{obj.config_block_hash.config_block_hash[:12]}..."

    step_config_preview.short_description = "Step Config"
