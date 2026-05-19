from django.test import TestCase

from submit_jobs.models import (
    build_job_steps_from_pipeline,
    resolve_placeholder_dependencies,
    build_job_env_config,
    LOG_STATUS_CHOICES,
)
from pipeline_factory.models import Pipeline, PipelineStep
from job_queue.models import get_or_create_step_configs


# ============================================================================
# build_job_steps_from_pipeline()
# ============================================================================


class BuildJobStepsFromPipelineTests(TestCase):
    """Tests for build_job_steps_from_pipeline() — step ordering and DB loading."""

    def setUp(self):
        self.pipeline = Pipeline.objects.create(description="Test pipeline")
        self.preprocessing_hash = get_or_create_step_configs(
            "preprocessing", {"methods": ["highpass or band filtering"]}
        )
        self.sorting_hash = get_or_create_step_configs("sorting", {"name": "hdsort"})
        PipelineStep.objects.create(
            pipeline=self.pipeline,
            config_block_hash_id=self.preprocessing_hash,
            depends_on=["_RECORDING_"],
        )
        PipelineStep.objects.create(
            pipeline=self.pipeline,
            config_block_hash_id=self.sorting_hash,
            depends_on=[self.preprocessing_hash],
        )
        self.recording_hash = get_or_create_step_configs("recording", {"binfile": "/test.bin"})

    def _build(self):
        return build_job_steps_from_pipeline(self.pipeline.pipeline_id, self.recording_hash)

    def test_recording_step_is_first(self):
        steps = self._build()
        self.assertEqual(steps[0]["function"], "recording")
        self.assertEqual(steps[0]["identifier"], self.recording_hash)

    def test_total_count_is_pipeline_steps_plus_one(self):
        steps = self._build()
        self.assertEqual(len(steps), 3)  # 2 pipeline + 1 recording

    def test_step_order_follows_pipeline_step_id(self):
        steps = self._build()
        self.assertEqual([s["function"] for s in steps], ["recording", "preprocessing", "sorting"])

    def test_each_step_has_required_keys(self):
        for step in self._build():
            for key in ("function", "identifier", "depends"):
                self.assertIn(key, step, f"Step '{step.get('function')}' missing key '{key}'")

    def test_raises_runtime_error_for_nonexistent_pipeline(self):
        with self.assertRaises(RuntimeError):
            build_job_steps_from_pipeline(99999, self.recording_hash)

    def test_recording_step_has_empty_depends(self):
        steps = self._build()
        self.assertEqual(steps[0]["depends"], [])


# ============================================================================
# resolve_placeholder_dependencies()
# ============================================================================


class ResolvePlaceholderDependenciesTests(TestCase):
    """Tests for resolve_placeholder_dependencies() — placeholder replacement logic."""

    RECORDING_HASH = "a" * 64  # Fake 64-char SHA-256 for testing

    def _resolve(self, steps):
        return resolve_placeholder_dependencies(steps, self.RECORDING_HASH)

    def test_resolves_RECORDING_placeholder(self):
        steps = [{"function": "preprocessing", "identifier": "pp", "depends": ["_RECORDING_"]}]
        self._resolve(steps)
        self.assertEqual(steps[0]["depends"], [self.RECORDING_HASH])

    def test_resolves_recording_lowercase_placeholder(self):
        steps = [{"function": "preprocessing", "identifier": "pp", "depends": ["recording"]}]
        self._resolve(steps)
        self.assertEqual(steps[0]["depends"], [self.RECORDING_HASH])

    def test_passes_real_hash_through_unchanged(self):
        real_hash = "b" * 64
        steps = [{"function": "sorting", "identifier": "so", "depends": [real_hash]}]
        self._resolve(steps)
        self.assertEqual(steps[0]["depends"], [real_hash])

    def test_skips_steps_with_empty_depends(self):
        steps = [{"function": "upload", "identifier": "up", "depends": []}]
        self._resolve(steps)
        self.assertEqual(steps[0]["depends"], [])

    def test_returns_same_list_object(self):
        """Function must modify in-place and return the same list."""
        steps = [{"function": "preprocessing", "identifier": "pp", "depends": ["_RECORDING_"]}]
        result = resolve_placeholder_dependencies(steps, self.RECORDING_HASH)
        self.assertIs(result, steps)

    def test_mixed_depends_resolves_only_placeholders(self):
        real_hash = "c" * 64
        steps = [{"function": "analyzer", "identifier": "an", "depends": ["_RECORDING_", real_hash]}]
        self._resolve(steps)
        self.assertEqual(steps[0]["depends"], [self.RECORDING_HASH, real_hash])


# ============================================================================
# build_job_env_config()
# ============================================================================


class BuildJobEnvConfigTests(TestCase):
    """Tests for build_job_env_config() — environment dict structure."""

    def test_returns_dict_with_all_required_keys(self):
        config = build_job_env_config("local")
        for key in ("base_directory", "job_kwargs", "log_level", "REDIRECT"):
            self.assertIn(key, config)

    def test_environment_is_stored_in_job_kwargs(self):
        self.assertEqual(build_job_env_config("gpu")["job_kwargs"]["environment"], "gpu")

    def test_different_environments_produce_different_configs(self):
        self.assertNotEqual(
            build_job_env_config("local")["job_kwargs"]["environment"],
            build_job_env_config("aws")["job_kwargs"]["environment"],
        )

    def test_valid_for_all_supported_environments(self):
        for env in ("local", "gpu", "aws"):
            config = build_job_env_config(env)
            self.assertEqual(config["job_kwargs"]["environment"], env)


# ============================================================================
# LOG_STATUS_CHOICES constant
# ============================================================================


class LogStatusChoicesTests(TestCase):
    """Tests for LOG_STATUS_CHOICES — ensures all expected statuses are present."""

    def test_contains_all_expected_statuses(self):
        values = [choice[0] for choice in LOG_STATUS_CHOICES]
        for expected in ("pending", "success", "failed"):
            self.assertIn(expected, values)

    def test_each_choice_has_display_label(self):
        for value, label in LOG_STATUS_CHOICES:
            self.assertTrue(label, f"Status '{value}' is missing a display label")
