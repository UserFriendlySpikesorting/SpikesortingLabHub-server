from django.db import models
from job_queue.models import Job


# Choices for the 'status' field in JobCreationLog model
LOG_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("success", "Success"),
    ("failed", "Failed"),
]


def _validate_pipeline_exists(pipeline_id: int) -> None:
    """Raises RuntimeError if the pipeline does not exist."""
    from pipeline_factory.models import (
        Pipeline,
    )  # Avoid circular imports at module level

    if not Pipeline.objects.filter(pipeline_id=pipeline_id).exists():
        raise RuntimeError(f"Pipeline {pipeline_id} does not exist")


def _fetch_pipeline_steps(pipeline_id: int):
    """Returns ordered PipelineStep queryset for the given pipeline."""
    from pipeline_factory.models import (
        PipelineStep,
    )  # Avoid circular imports at module level

    return PipelineStep.objects.filter(pipeline_id=pipeline_id).order_by(
        "pipeline_step_id"
    )  # Preserve step order defined in pipeline


def build_job_steps_from_pipeline(pipeline_id: int, recording_identifier: str) -> list:
    """
    Loads a Pipeline's steps from the database and assembles the ordered job_steps
    list required by create_a_job. The recording step is always prepended first.

    Args:
        pipeline_id: Primary key of the Pipeline to load
        recording_identifier: SHA-256 hash of the recording StepConfig

    Returns:
        list[dict]: Ordered job_steps, each dict containing:
                    - function: step function name (e.g., 'sorting', 'analyzer')
                    - identifier: config_block_hash SHA-256 string
                    - depends: list of dependency identifiers (may contain placeholders)

    Raises:
        RuntimeError: If the pipeline does not exist
    """
    _validate_pipeline_exists(pipeline_id)
    pipeline_steps = _fetch_pipeline_steps(pipeline_id)

    # Recording step is always first — it is the root dependency for all other steps
    job_steps = [
        {"function": "recording", "identifier": recording_identifier, "depends": []}
    ]

    # Append each pipeline step, using its pre-existing config_block_hash from StepConfig
    for step in pipeline_steps:
        job_steps.append(
            {
                "function": step.config_block_hash.function,
                "identifier": step.config_block_hash.config_block_hash,
                "depends": step.depends_on if step.depends_on else [],
            }
        )

    return job_steps


def resolve_placeholder_dependencies(
    job_steps: list, recording_identifier: str
) -> list:
    """
    Resolves placeholder dependency references to real config_block_hash identifiers.
    Replaces the special '_RECORDING_' and 'recording' string placeholders with the
    actual recording identifier. All other identifiers are passed through unchanged.

    Args:
        job_steps: Ordered list of step dicts (as returned by build_job_steps_from_pipeline)
        recording_identifier: SHA-256 hash of the recording StepConfig

    Returns:
        list[dict]: Same job_steps list with all placeholders replaced by real identifiers
    """
    for job_step in job_steps:
        if not job_step["depends"]:  # Skip steps with no dependencies
            continue

        resolved = []
        for dep in job_step["depends"]:
            if dep in (
                "_RECORDING_",
                "recording",
            ):  # Recording placeholder — resolve to real hash
                resolved.append(recording_identifier)
            else:
                resolved.append(
                    dep
                )  # Already a real identifier — pass through unchanged
        job_step["depends"] = resolved

    return job_steps


# Fallback values used when no JobEnvironmentDefault row exists for the
# requested environment (e.g. fresh database, row deleted by mistake) — keeps
# job submission working even if the defaults table is empty. Mirrors the
# 'default' row's values so behavior stays consistent either way.
_HARDCODED_JOB_ENV_DEFAULTS = {
    "base_directory": "$LOCAL$/$JOB_ID$",
    "n_jobs": 40,
    "total_memory": "30G",
    "chunk_duration": "60s",
    "progress_bar": True,
    "log_level": "DEBUG",
    "redirect_log": "$NAS$/SORTING_LOGS/$JOB_ID$/run.log",
    "redirect_out": "$NAS$/SORTING_LOGS/$JOB_ID$/run.out",
    "redirect_err": "$NAS$/SORTING_LOGS/$JOB_ID$/run.err",
}


def build_job_env_config(environment: str) -> dict:
    """
    Constructs the standard job environment configuration dictionary passed to create_a_job.

    Values are loaded from the JobEnvironmentDefault table for the given environment
    so they can be tuned without a code change/deploy. Falls back to hardcoded
    defaults if no row exists for the environment.

    Args:
        environment: Target execution environment. 'default' is the standard
            environment for this rig; additional named environments can be
            hand-added in Django admin for one-off tuning (e.g. a recording
            that needs different memory/worker limits).

    Returns:
        dict: Job environment config with base directory, job_kwargs, log_level, and REDIRECT
    """
    from submit_jobs.models import JobEnvironmentDefault  # Avoid import-order issues

    defaults = JobEnvironmentDefault.objects.filter(environment=environment).first()
    values = (
        {
            "base_directory": defaults.base_directory,
            "n_jobs": defaults.n_jobs,
            "total_memory": defaults.total_memory,
            "chunk_duration": defaults.chunk_duration,
            "progress_bar": defaults.progress_bar,
            "log_level": defaults.log_level,
            "redirect_log": defaults.redirect_log,
            "redirect_out": defaults.redirect_out,
            "redirect_err": defaults.redirect_err,
        }
        if defaults is not None
        else _HARDCODED_JOB_ENV_DEFAULTS
    )

    return {
        "base directory": values["base_directory"],
        "job_kwargs": {
            "n_jobs": values["n_jobs"],
            "total_memory": values["total_memory"],
            "chunk_duration": values["chunk_duration"],
            "progress_bar": values["progress_bar"],
        },
        "log_level": values["log_level"],
        "REDIRECT": {
            "log": values["redirect_log"],
            "out": values["redirect_out"],
            "err": values["redirect_err"],
        },
    }


class JobEnvironmentDefault(models.Model):
    """
    Tunable default job_env values (worker resource limits, log paths) per
    execution environment. Lets operators adjust these without a code
    change/deploy — e.g. lowering total_memory or n_jobs after a worker
    crash caused by an oversized sorting job.
    """

    environment = models.CharField(
        max_length=50, unique=True
    )  # 'default' is the standard environment; others are hand-added for one-off tuning
    base_directory = models.CharField(max_length=255, default="$LOCAL$/$JOB_ID$")
    n_jobs = models.IntegerField(default=40)
    total_memory = models.CharField(
        max_length=20, default="128G"
    )  # spikeinterface job_kwargs format, e.g. '128G'
    chunk_duration = models.CharField(max_length=20, default="60s")
    progress_bar = models.BooleanField(default=True)
    log_level = models.CharField(max_length=20, default="DEBUG")
    redirect_log = models.CharField(
        max_length=255, default="$NAS$/SORTING_LOGS/$JOB_ID$/run.log"
    )
    redirect_out = models.CharField(
        max_length=255, default="$NAS$/SORTING_LOGS/$JOB_ID$/run.out"
    )
    redirect_err = models.CharField(
        max_length=255, default="$NAS$/SORTING_LOGS/$JOB_ID$/run.err"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jobs_jobenvironmentdefault"
        ordering = ["environment"]

    def __str__(self):
        """String representation for a JobEnvironmentDefault object."""
        return f"JobEnvironmentDefault - {self.environment}"


class JobCreationLog(models.Model):
    """
    Audit log for every job creation request submitted via the sorting wizard.
    Records the pipeline used, recording config, environment preset, final outcome,
    and any error message — enabling debugging of failed submissions.
    """

    # OneToOne link to the created Job; null when job creation itself failed
    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name="creation_log",
        null=True,
        blank=True,
    )
    pipeline_id = models.IntegerField()  # ID of the pipeline selected for this job
    recording_config = (
        models.JSONField()
    )  # Recording configuration submitted by the researcher
    job_env_preset = (
        models.JSONField()
    )  # Environment preset submitted by the researcher
    created_at = models.DateTimeField(
        auto_now_add=True
    )  # Timestamp set automatically on creation
    status = models.CharField(
        max_length=20, choices=LOG_STATUS_CHOICES, default="pending"
    )  # Outcome of the job creation attempt
    error_message = models.TextField(
        null=True, blank=True
    )  # Populated only when status is 'failed'

    class Meta:
        db_table = "jobs_jobcreationlog"
        ordering = ["-created_at"]

    def __str__(self):
        """String representation for a JobCreationLog object."""
        return f"JobCreationLog - Pipeline {self.pipeline_id} - {self.status}"
