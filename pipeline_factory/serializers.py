from django.db import transaction
from rest_framework import serializers

from .models import Pipeline, PipelineStep
from job_queue.models import get_or_create_step_configs


# ============================================================================
# Pipeline Creation Helper Functions
# ============================================================================


def _coerce_band_floats(config: dict) -> dict:
    """Ensures band values in highpass/bandpass filter configs are floats, not ints."""
    for _, value in config.items():
        if isinstance(value, dict) and "band" in value:
            value["band"] = [float(v) for v in value["band"]]
    return config


def _resolve_step_config(step_data: dict, raw_data: dict) -> tuple:
    """
    Extracts the function name and config block for a single pipeline step.
    Handles two JSON formats:
      - Embedded:  step_data contains a 'config' key with the config dict inline
      - External:  config is stored in raw_data under the step's 'identifier' key

    Args:
        step_data: A single step dict from the job_steps/steps array
        raw_data: The full raw request payload (contains external config blocks)

    Returns:
        tuple[str, dict]: (function_name, config_block)

    Raises:
        serializers.ValidationError: If the 'function' field is missing
    """
    function = step_data.get("function")
    if not function:
        raise serializers.ValidationError("Step must have a 'function' field")

    # Prefer inline config; fall back to external key lookup via identifier
    config = step_data.get("config") or {}
    if not config and "identifier" in step_data:
        identifier = step_data["identifier"]
        config = raw_data.get(identifier) or {}  # External config block keyed by short identifier

    return function, _coerce_band_floats(config)


def _build_placeholder_map(steps_data: list, raw_data: dict) -> dict:
    """
    First pass over pipeline steps: creates all StepConfig records and builds
    a mapping from each step's short placeholder identifier to its real SHA-256
    config_block_hash. This map is used in the second pass to resolve dependencies.

    Args:
        steps_data: List of step dicts from the pipeline JSON
        raw_data: Full raw request payload for external config block lookup

    Returns:
        dict: Maps placeholder identifier (e.g. '754fed71') -> SHA-256 hash string

    Raises:
        serializers.ValidationError: If any step is missing 'function' or a DB write fails
    """
    placeholder_to_hash = {}

    for idx, step_data in enumerate(steps_data):
        try:
            function, config = _resolve_step_config(step_data, raw_data)
            config_block_hash = get_or_create_step_configs(function, config)

            # Map the short placeholder identifier to the real SHA-256 hash
            placeholder = step_data.get("identifier")
            if placeholder:
                placeholder_to_hash[placeholder] = config_block_hash

        except serializers.ValidationError:
            raise  # Re-raise validation errors with original message
        except Exception as e:
            raise serializers.ValidationError(
                f"Error creating StepConfig for step {idx + 1}: {str(e)}"
            )

    return placeholder_to_hash


def _create_pipeline_steps(
    pipeline: Pipeline,
    steps_data: list,
    raw_data: dict,
    placeholder_to_hash: dict,
) -> None:
    """
    Second pass over pipeline steps: creates all PipelineStep records.
    Resolves dependency placeholder identifiers to real SHA-256 hashes using
    the map produced by _build_placeholder_map. Unknown placeholders pass through
    unchanged (e.g. '_RECORDING_' is preserved for resolution at job-creation time).

    Args:
        pipeline: The Pipeline instance to attach steps to
        steps_data: List of step dicts from the pipeline JSON
        raw_data: Full raw request payload for external config block lookup
        placeholder_to_hash: Maps short placeholder identifiers to real config_block_hash values

    Raises:
        serializers.ValidationError: If any PipelineStep fails to create
    """
    for idx, step_data in enumerate(steps_data):
        try:
            function, config = _resolve_step_config(step_data, raw_data)
            config_block_hash = get_or_create_step_configs(function, config)

            # Resolve each dependency: replace known placeholders with real hashes
            raw_depends = step_data.get("depends_on") or step_data.get("depends", [])
            resolved_depends = [
                placeholder_to_hash.get(dep, dep)  # Use real hash if known, else keep as-is
                for dep in raw_depends
            ]

            PipelineStep.objects.create(
                pipeline=pipeline,
                config_block_hash_id=config_block_hash,
                depends_on=resolved_depends,
            )

        except serializers.ValidationError:
            raise  # Re-raise validation errors with original message
        except Exception as e:
            raise serializers.ValidationError(
                f"Error creating PipelineStep for step {idx + 1}: {str(e)}"
            )


# ============================================================================
# Serializers
# ============================================================================


class PipelineStepSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for a single PipelineStep.
    Exposes the function name and config hash via the linked StepConfig.
    """

    config_hash = serializers.CharField(
        source="config_block_hash.config_block_hash", read_only=True
    )
    function = serializers.CharField(
        source="config_block_hash.function", read_only=True
    )
    depends_on = serializers.JSONField(read_only=True)

    class Meta:
        model = PipelineStep
        fields = ["pipeline_step_id", "function", "config_hash", "depends_on"]


class PipelineSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for a Pipeline, including its ordered steps and step count.
    """

    steps = PipelineStepSerializer(many=True, read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = ["pipeline_id", "description", "created_at", "steps", "step_count"]
        read_only_fields = ["pipeline_id", "created_at"]

    def get_step_count(self, obj):
        """Returns the total number of steps in this pipeline."""
        return obj.steps.count()


class PipelineCreateSerializer(serializers.Serializer):
    """
    Write serializer for creating a Pipeline from a JSON payload.
    Supports both 'steps' and 'job_steps' field names for the step array.
    Config blocks may be embedded inline per step or stored as top-level keys
    in the payload, keyed by the step's short placeholder identifier.
    """

    description = serializers.CharField(required=False, allow_blank=True)
    steps = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=False
    )
    job_steps = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=False
    )

    def create(self, validated_data):
        """
        Creates a Pipeline and all its PipelineSteps atomically.
        Uses a two-pass approach:
          Pass 1 (_build_placeholder_map): creates StepConfigs, builds identifier→hash map
          Pass 2 (_create_pipeline_steps): creates PipelineSteps with resolved dependencies

        Args:
            validated_data: Validated dict containing description + steps or job_steps

        Returns:
            Pipeline: The fully created Pipeline instance

        Raises:
            serializers.ValidationError: If any step is invalid or a DB write fails
        """
        steps_data = validated_data.get("steps") or validated_data.get("job_steps")
        description = validated_data.get("description", "Pipeline from JSON")
        raw_data = self.initial_data if hasattr(self, "initial_data") else {}

        with transaction.atomic():  # All-or-nothing: pipeline + all steps created together
            pipeline = Pipeline.objects.create(description=description)
            placeholder_to_hash = _build_placeholder_map(steps_data, raw_data)
            _create_pipeline_steps(pipeline, steps_data, raw_data, placeholder_to_hash)

        return pipeline
