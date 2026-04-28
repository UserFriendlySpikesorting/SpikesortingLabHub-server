from rest_framework import serializers
from .models import Job, JobStep, StepConfig


class JobCreationPayloadSerializer(serializers.Serializer):
    """
    Validates incoming job creation payload from the worker.
    """
    job_evn = serializers.DictField(required=False, default=dict)
    job_steps = serializers.ListField(child=serializers.DictField(), required=True)

    def validate_job_steps(self, value):
        if not value:
            raise serializers.ValidationError("job_steps cannot be empty.")
        for idx, step in enumerate(value):
            if "identifier" not in step:
                raise serializers.ValidationError(f"Step {idx}: missing 'identifier'.")
            if "function" not in step:
                raise serializers.ValidationError(f"Step {idx}: missing 'function'.")
        return value


class StepConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepConfig
        fields = ["config_block_hash", "config_block", "function"]
        read_only_fields = ["config_block_hash"]


class JobStepSerializer(serializers.ModelSerializer):
    config_block = serializers.SerializerMethodField()

    class Meta:
        model = JobStep
        fields = ["identifier", "function", "status", "depends_on", "config_block"]
        read_only_fields = ["identifier", "function", "status", "depends_on"]

    def get_config_block(self, obj):
        if obj.config_block_hash:
            return obj.config_block_hash.config_block
        return {}


class JobStepWithConfigSerializer(serializers.ModelSerializer):
    config = StepConfigSerializer(source="config_block_hash", read_only=True)

    class Meta:
        model = JobStep
        fields = ["identifier", "function", "status", "depends_on", "config"]
        read_only_fields = ["identifier", "function", "status", "depends_on"]


class JobListSerializer(serializers.ModelSerializer):
    job_steps = JobStepSerializer(source="jobstep_set", many=True, read_only=True)
    step_count = serializers.SerializerMethodField()
    completed_steps = serializers.SerializerMethodField()
    job_env = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = ["job_id", "status", "created_at", "job_env", "step_count", "completed_steps", "job_steps"]
        read_only_fields = ["job_id", "status", "created_at"]

    def get_step_count(self, obj):
        return obj.jobstep_set.count()

    def get_completed_steps(self, obj):
        return obj.jobstep_set.filter(status="completed").count()

    def get_job_env(self, obj):
        env = obj.job_env_config or {}
        return {
            "environment": env.get("job_kwargs", {}).get("environment", "unknown"),
            "log_level": env.get("log_level", "INFO"),
            "base_directory": env.get("base directory", "/tmp"),
        }


class JobSerializer(serializers.ModelSerializer):
    steps = JobStepWithConfigSerializer(source="jobstep_set", many=True, read_only=True)

    class Meta:
        model = Job
        fields = ["job_id", "status", "created_at", "job_env_config", "steps"]
        read_only_fields = ["job_id", "status", "created_at"]
