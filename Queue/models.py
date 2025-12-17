import uuid
import hashlib
import json
from django.db import models, transaction

# Choices for the 'status' field in Job and JobStep models
STATUS_CHOICES = [
    ("pending", "Pending"),
    ("fetched", "Fetched"),
    ("running", "Running"),
    ("finished", "Finished"),
    ("failed", "Failed"),
]


def compute_fingerprint(config_block: dict) -> str:
    """
    Generates a SHA-256 hash (fingerprint) for a given configuration block.
    Uses json.dumps with sorted keys to ensure consistent hash for identical content.

    Args:
        config_block (dict): Configuration dictionary to hash

    Returns:
        str: SHA-256 hex digest of the config block

    Example:
        >>> config = {'param': 'value', 'nested': {'key': 'data'}}
        >>> fp = compute_fingerprint(config)
        >>> print(len(fp))  # 64 (SHA-256 hex)
        64
    """
    json_str = json.dumps(config_block, sort_keys=True)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def get_or_create_step_configs(stepfunction: str, step_config: dict) -> str:
    """
    Gets or creates a StepConfig record in the database.
    Computes a fingerprint (SHA-256 hash) of the config block for deduplication.
    If the config already exists (same fingerprint), returns the existing fingerprint.
    Otherwise, creates a new StepConfig record and returns its fingerprint.

    Args:
        stepfunction: The name/type of the step function (e.g., 'recording', 'sorting')
        step_config: Dictionary containing the step configuration data

    Returns:
        str: SHA-256 fingerprint (hash) of the config block

    Raises:
        RuntimeError: If database operation fails
    """
    fingerprint = compute_fingerprint(step_config)
    if not StepConfig.objects.filter(config_block_hash=fingerprint).exists():
        try:
            stepconf = StepConfig(
                config_block_hash=fingerprint,
                config_block=step_config,
                function=stepfunction,
            )
            stepconf.save()
        except BaseException as e:
            raise RuntimeError(
                f"Cannot create a record in step database for function {stepfunction}: {e}"
            )
    return fingerprint


def create_a_job(job_evn: dict, job_steps: list) -> "Job":
    """
    Creates a Job with its associated JobSteps.
    Assumes all StepConfigs already exist in the database.

    Args:
        job_evn: Environment configuration dictionary for the job
        job_steps: List of step dictionaries, each containing:
                   - identifier: The config_block_hash (FK to StepConfig)
                   - function: The step function name
                   - depends: List of step identifiers this step depends on

    Returns:
        Job: The created Job object

    Raises:
        RuntimeError: If job_steps is empty or invalid
    """
    if not len(job_steps):
        raise RuntimeError("job_steps are empty")

    for setpid, step in enumerate(job_steps):
        if not isinstance(step, dict):
            raise RuntimeError(f"step #{setpid} is not a dictionary")

        for required_field in ["function", "identifier", "depends"]:
            if required_field not in step:
                raise RuntimeError(
                    f"step #{setpid} does not have '{required_field}' key"
                )

        identifier = step["identifier"]
        if not StepConfig.objects.filter(config_block_hash=identifier).exists():
            raise RuntimeError(
                f"step #{setpid}: StepConfig with hash '{identifier}' does not exist. "
                f"Create the config first before creating the job."
            )

    with transaction.atomic():
        job = Job.objects.create(job_env_config=job_evn, status="pending")

        job_steps_objects = []
        for step in job_steps:
            job_steps_objects.append(
                JobStep(
                    identifier=step.get("identifier"),
                    job=job,
                    function=step.get("function"),
                    depends_on=step.get("depends", []),
                    config_block_hash_id=step.get("identifier"),
                    status="pending",
                )
            )

        JobStep.objects.bulk_create(job_steps_objects)

    return job


def get_next_job_id() -> "Job | None":
    """
    Fetches the next pending job and marks it as fetched (in progress).
    Uses row-level locking to prevent race conditions when multiple workers call this simultaneously.

    Returns:
        Job | None: The next pending job in FIFO order, or None if queue is empty
    """
    with transaction.atomic():
        job_to_process = (
            Job.objects.select_for_update()
            .filter(status="pending")
            .order_by("created_at")
            .first()
        )

        if job_to_process:
            job_to_process.status = "fetched"
            job_to_process.save()
        else:
            job_to_process = None
    return job_to_process


class Job(models.Model):
    """
    Represents a main job with its overall environment configuration.
    The 'job_id' serves as the primary key, ensuring uniqueness.
    """

    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_env_config = models.JSONField()
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.job_id)


class StepConfig(models.Model):
    """
    Stores unique configuration blocks for individual job steps.
    The SHA-256 hash of the configuration JSON serves as its primary key,
    enabling efficient deduplication and lookup.
    """

    config_block_hash = models.CharField(primary_key=True, max_length=64)
    config_block = models.JSONField()
    function = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return self.config_block_hash


class JobStep(models.Model):
    """
    Represents an individual step within a larger job.
    It links to its parent Job and to a specific, unique StepConfig.
    """

    identifier = models.CharField(max_length=64)
    job = models.ForeignKey(Job, to_field="job_id", on_delete=models.CASCADE)
    function = models.CharField(max_length=64)
    depends_on = models.JSONField(null=True, blank=True)
    config_block_hash = models.ForeignKey(
        "StepConfig", to_field="config_block_hash", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="pending"
    )

    class Meta:
        unique_together = ("job", "identifier")

    def __str__(self):
        return f"{self.job.job_id} - {self.identifier} ({self.function})"
