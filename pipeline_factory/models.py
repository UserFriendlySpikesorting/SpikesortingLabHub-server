from django.db import models
from job_queue.models import StepConfig


class Pipeline(models.Model):
    """
    Represents a named pipeline configuration submitted by a researcher.
    Groups a set of ordered PipelineSteps into a reusable template.
    """

    pipeline_id = models.AutoField(primary_key=True)  # Auto-incrementing primary key
    description = models.TextField()  # Human-readable description of the pipeline
    created_at = models.DateTimeField(
        auto_now_add=True
    )  # Timestamp set automatically on creation

    class Meta:
        db_table = "pipeline_pipeline"
        ordering = ["-created_at"]
        verbose_name = "Pipeline"
        verbose_name_plural = "Pipelines"

    def __str__(self):
        """String representation for a Pipeline object."""
        return f"Pipeline {self.pipeline_id}: {self.description[:50]}"


class PipelineStep(models.Model):
    """
    Represents a single step within a Pipeline.
    Links to a StepConfig for its configuration and declares
    dependencies on other steps via their config_block_hash identifiers.
    """

    pipeline_step_id = models.AutoField(primary_key=True)  # Auto-incrementing primary key

    # ForeignKey to the parent Pipeline; deleting the pipeline cascades to all its steps
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    # ForeignKey to StepConfig; links this step to its unique hashed configuration block
    # Access config data via config_block_hash.config_block and function via config_block_hash.function
    config_block_hash = models.ForeignKey(
        StepConfig,
        to_field="config_block_hash",
        on_delete=models.CASCADE,
        related_name="pipeline_steps",
    )

    # List of config_block_hash identifiers this step depends on (prerequisite steps)
    depends_on = models.JSONField(null=True, blank=True, default=list)

    class Meta:
        db_table = "pipeline_pipelinestep"

    def __str__(self):
        """String representation for a PipelineStep object."""
        return f"Pipeline {self.pipeline_id} - Step {self.pipeline_step_id} ({self.config_block_hash_id})"
