from rest_framework import serializers
from job_queue.models import Job, JobStep, StepConfig
from pipeline_factory.models import Pipeline
from .models import JobCreationLog


class RecordingConfigSerializer(serializers.Serializer):
    """
    Validates the recording configuration block submitted by the React wizard.
    All file paths and numeric parameters are validated before job creation.
    """

    binfile = serializers.CharField(required=True, min_length=1)
    sampling_rate = serializers.IntegerField(required=True, min_value=1)
    num_channels = serializers.IntegerField(required=True, min_value=1)
    gain_to_uV = serializers.FloatField(required=True)
    offset_to_uV = serializers.FloatField(required=True)
    probe = serializers.CharField(required=False, allow_blank=True)
    remove_channels = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    bad_channels = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )


class CreateSortingJobSerializer(serializers.Serializer):
    """
    Validates the React Sorting Job Wizard payload before job creation.

    Expected input:
        {
          "recording": {"binfile": "...", "sampling_rate": 30000, ...},
          "pipeline_id": 1,
          "environment": "local"
        }
    """

    recording = RecordingConfigSerializer(required=True)
    pipeline_id = serializers.IntegerField(required=True, min_value=1)
    environment = serializers.ChoiceField(
        required=True, choices=["local", "gpu", "aws"]
    )

    def validate_pipeline_id(self, value):
        """Fail-fast: reject the request immediately if the pipeline does not exist."""
        if not Pipeline.objects.filter(pipeline_id=value).exists():
            raise serializers.ValidationError(f"Pipeline {value} does not exist")
        return value


# ============================================================================
# Job Read Serializers
# ============================================================================


class StepConfigSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for a StepConfig record.
    Exposes the hash, the raw config block, and the function name.
    """

    class Meta:
        model = StepConfig
        fields = ["config_block_hash", "config_block", "function"]
        read_only_fields = ["config_block_hash"]


class JobStepSerializer(serializers.ModelSerializer):
    """
    Serializes a JobStep for list and detail views.
    Includes the flat config_block JSON for quick inspection without a nested object.
    """

    config_block = serializers.SerializerMethodField()

    class Meta:
        model = JobStep
        fields = ["identifier", "function", "status", "depends_on", "config_block"]
        read_only_fields = ["identifier", "function", "status", "depends_on"]

    def get_config_block(self, obj):
        """Returns the raw config block JSON from the linked StepConfig."""
        if obj.config_block_hash:
            return obj.config_block_hash.config_block
        return {}


class JobStepWithConfigSerializer(serializers.ModelSerializer):
    """
    Serializes a JobStep with a fully nested StepConfig object.
    Used by JobSerializer where the full config structure is required.
    """

    config = StepConfigSerializer(source="config_block_hash", read_only=True)

    class Meta:
        model = JobStep
        fields = ["identifier", "function", "status", "depends_on", "config"]
        read_only_fields = ["identifier", "function", "status", "depends_on"]


class JobListSerializer(serializers.ModelSerializer):
    """
    Serializes a Job for list and detail views.
    Includes step summary, completion count, and a condensed environment block.
    """

    job_steps = JobStepSerializer(source="jobstep_set", many=True, read_only=True)
    step_count = serializers.SerializerMethodField()
    completed_steps = serializers.SerializerMethodField()
    job_env = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "job_id",
            "status",
            "created_at",
            "job_env",
            "step_count",
            "completed_steps",
            "job_steps",
        ]
        read_only_fields = ["job_id", "status", "created_at"]

    def get_step_count(self, obj):
        """Returns the total number of steps in this job."""
        return obj.jobstep_set.count()

    def get_completed_steps(self, obj):
        return obj.jobstep_set.filter(status="completed").count()

    def get_job_env(self, obj):
        """Extracts the key environment fields from the job_env_config JSON blob."""
        env = obj.job_env_config or {}
        return {
            "environment": env.get("job_kwargs", {}).get("environment", "unknown"),
            "log_level": env.get("log_level", "INFO"),
            "base_directory": env.get("base_directory", "/tmp"),
        }


class JobSerializer(serializers.ModelSerializer):
    """
    Full serializer for a Job, including all steps with their nested StepConfig objects.
    Used where the complete job payload is required (e.g. admin or detailed exports).
    """

    steps = JobStepWithConfigSerializer(source="jobstep_set", many=True, read_only=True)

    class Meta:
        model = Job
        fields = ["job_id", "status", "created_at", "job_env_config", "steps"]
        read_only_fields = ["job_id", "status", "created_at"]


class JobCreationLogSerializer(serializers.ModelSerializer):
    """
    Serializes a JobCreationLog audit record for inspection and debugging.
    """

    class Meta:
        model = JobCreationLog
        fields = [
            "id",
            "job",
            "pipeline_id",
            "recording_config",
            "job_env_preset",
            "created_at",
            "status",
            "error_message",
        ]
        read_only_fields = ["id", "created_at"]
