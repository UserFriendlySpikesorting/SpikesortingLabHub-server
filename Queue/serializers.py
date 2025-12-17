from rest_framework import serializers
from .models import Job, JobStep, StepConfig


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = "__all__"


class JobCreationPayloadSerializer(serializers.Serializer):
    """
    Serializer for validating incoming job creation payload from React.
    Ensures all required fields are present and correctly formatted.
    """

    job_evn = serializers.DictField(required=False, default=dict)
    job_steps = serializers.ListField(child=serializers.DictField(), required=True)

    def validate_job_steps(self, value):
        """
        Validates that each job step has required fields.
        """
        if not value:
            raise serializers.ValidationError("job_steps cannot be empty.")

        for idx, step in enumerate(value):
            if "identifier" not in step:
                raise serializers.ValidationError(f"Step {idx}: missing 'identifier'.")
            if "function" not in step:
                raise serializers.ValidationError(f"Step {idx}: missing 'function'.")

        return value
