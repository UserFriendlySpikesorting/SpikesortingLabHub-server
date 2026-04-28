from django.test import TestCase
from job_queue.models import (
    compute_fingerprint,
    get_or_create_step_configs,
    create_a_job,
    get_next_job_id,
    Job,
    JobStep,
    StepConfig,
)


# ============================================================================
# compute_fingerprint()
# ============================================================================


class ComputeFingerprintTests(TestCase):
    """Tests for compute_fingerprint() — SHA-256 hash consistency and correctness."""

    def test_same_dict_produces_same_hash(self):
        config = {"param": "value", "nested": {"key": "data"}}
        self.assertEqual(compute_fingerprint(config), compute_fingerprint(config))

    def test_different_dicts_produce_different_hashes(self):
        self.assertNotEqual(
            compute_fingerprint({"param": "value1"}),
            compute_fingerprint({"param": "value2"}),
        )

    def test_key_order_does_not_affect_hash(self):
        """sort_keys=True in json.dumps must make {'a':1,'b':2} == {'b':2,'a':1}."""
        self.assertEqual(
            compute_fingerprint({"z": 100, "a": 1, "m": 50}),
            compute_fingerprint({"a": 1, "m": 50, "z": 100}),
        )

    def test_nested_key_order_does_not_affect_hash(self):
        config_a = {"outer": {"z": 3, "a": 1}, "top": "value"}
        config_b = {"top": "value", "outer": {"a": 1, "z": 3}}
        self.assertEqual(compute_fingerprint(config_a), compute_fingerprint(config_b))

    def test_returns_64_char_sha256_hex(self):
        fp = compute_fingerprint({"key": "value"})
        self.assertEqual(len(fp), 64)
        int(fp, 16)  # raises ValueError if not valid hex

    def test_empty_dict_produces_valid_hash(self):
        self.assertEqual(len(compute_fingerprint({})), 64)

    def test_int_and_float_produce_different_hashes(self):
        """JSON serialises 1 and 1.0 differently — documents expected behaviour."""
        self.assertNotEqual(
            compute_fingerprint({"value": 1}),
            compute_fingerprint({"value": 1.0}),
        )

    def test_string_and_number_produce_different_hashes(self):
        self.assertNotEqual(
            compute_fingerprint({"value": "100"}),
            compute_fingerprint({"value": 100}),
        )

    def test_complex_nested_structure_is_reproducible(self):
        config = {
            "recording": {
                "duration": 60,
                "channels": [0, 1, 2, 3],
                "settings": {"sample_rate": 30000, "gain": 0.195},
            },
            "preprocessing": ["filter", "whitening"],
        }
        self.assertEqual(compute_fingerprint(config), compute_fingerprint(config))


# ============================================================================
# get_or_create_step_configs()
# ============================================================================


class GetOrCreateStepConfigsTests(TestCase):
    """Tests for get_or_create_step_configs() — deduplication and persistence."""

    def test_creates_new_stepconfig(self):
        fp = get_or_create_step_configs("recording", {"binfile": "/data/test.bin"})
        self.assertTrue(StepConfig.objects.filter(config_block_hash=fp).exists())

    def test_returns_existing_stepconfig_without_duplicate(self):
        config = {"duration": 60, "sample_rate": 30000}
        fp1 = get_or_create_step_configs("recording", config)
        count_before = StepConfig.objects.count()
        fp2 = get_or_create_step_configs("recording", config)
        self.assertEqual(fp1, fp2)
        self.assertEqual(StepConfig.objects.count(), count_before)

    def test_returns_64_char_fingerprint(self):
        fp = get_or_create_step_configs("sorting", {"name": "hdsort"})
        self.assertEqual(len(fp), 64)

    def test_stores_function_name(self):
        config = {"method": "bandpass"}
        fp = get_or_create_step_configs("preprocessing", config)
        self.assertEqual(StepConfig.objects.get(config_block_hash=fp).function, "preprocessing")

    def test_different_configs_produce_different_fingerprints(self):
        fp1 = get_or_create_step_configs("recording", {"duration": 60})
        fp2 = get_or_create_step_configs("recording", {"duration": 120})
        self.assertNotEqual(fp1, fp2)


# ============================================================================
# create_a_job()
# ============================================================================


class CreateAJobTests(TestCase):
    """Tests for create_a_job() — validation, atomicity, and correct step creation."""

    def setUp(self):
        self.recording_hash = get_or_create_step_configs("recording", {"binfile": "/test.bin"})
        self.sorting_hash = get_or_create_step_configs("sorting", {"name": "hdsort"})

    def _steps(self):
        return [
            {"function": "recording", "identifier": self.recording_hash, "depends": []},
            {"function": "sorting",   "identifier": self.sorting_hash,   "depends": [self.recording_hash]},
        ]

    def test_creates_job_with_correct_status(self):
        job = create_a_job({"environment": "local"}, self._steps())
        self.assertIsInstance(job, Job)
        self.assertEqual(job.status, "pending")

    def test_creates_all_job_steps(self):
        job = create_a_job({"environment": "local"}, self._steps())
        self.assertEqual(job.jobstep_set.count(), 2)

    def test_steps_have_correct_functions(self):
        job = create_a_job({"environment": "local"}, self._steps())
        functions = set(job.jobstep_set.values_list("function", flat=True))
        self.assertEqual(functions, {"recording", "sorting"})

    def test_step_dependencies_are_preserved(self):
        job = create_a_job({"environment": "local"}, self._steps())
        sorting_step = job.jobstep_set.get(function="sorting")
        self.assertEqual(sorting_step.depends_on, [self.recording_hash])

    def test_raises_for_empty_steps(self):
        with self.assertRaises(RuntimeError):
            create_a_job({}, [])

    def test_raises_for_non_dict_step(self):
        with self.assertRaises(RuntimeError):
            create_a_job({}, ["not_a_dict"])

    def test_raises_for_missing_identifier_field(self):
        with self.assertRaises(RuntimeError):
            create_a_job({}, [{"function": "recording", "depends": []}])

    def test_raises_for_missing_function_field(self):
        with self.assertRaises(RuntimeError):
            create_a_job({}, [{"identifier": self.recording_hash, "depends": []}])

    def test_raises_for_nonexistent_stepconfig(self):
        with self.assertRaises(RuntimeError):
            create_a_job({}, [{"function": "recording", "identifier": "bad_hash", "depends": []}])

    def test_creation_is_atomic(self):
        """If one step references a bad hash, no Job or JobStep should be created."""
        count_before = Job.objects.count()
        with self.assertRaises(RuntimeError):
            create_a_job({}, [
                {"function": "recording", "identifier": self.recording_hash, "depends": []},
                {"function": "sorting",   "identifier": "nonexistent_hash", "depends": []},
            ])
        self.assertEqual(Job.objects.count(), count_before)


# ============================================================================
# get_next_job_id()
# ============================================================================


class GetNextJobIdTests(TestCase):
    """Tests for get_next_job_id() — FIFO queue ordering and status transitions."""

    def setUp(self):
        self.recording_hash = get_or_create_step_configs("recording", {"binfile": "/test.bin"})

    def _create_job(self):
        return create_a_job(
            {"environment": "local"},
            [{"function": "recording", "identifier": self.recording_hash, "depends": []}],
        )

    def test_returns_none_when_queue_empty(self):
        self.assertIsNone(get_next_job_id())

    def test_returns_oldest_pending_job_first(self):
        job1 = self._create_job()
        self._create_job()
        fetched = get_next_job_id()
        self.assertEqual(fetched.job_id, job1.job_id)

    def test_marks_fetched_job_as_fetched(self):
        job = self._create_job()
        get_next_job_id()
        job.refresh_from_db()
        self.assertEqual(job.status, "fetched")

    def test_skips_non_pending_jobs(self):
        job_running = Job.objects.create(job_env_config={}, status="running")
        job_pending = self._create_job()
        fetched = get_next_job_id()
        self.assertEqual(fetched.job_id, job_pending.job_id)

    def test_fifo_order_across_multiple_fetches(self):
        job1 = self._create_job()
        job2 = self._create_job()
        job3 = self._create_job()
        self.assertEqual(get_next_job_id().job_id, job1.job_id)
        self.assertEqual(get_next_job_id().job_id, job2.job_id)
        self.assertEqual(get_next_job_id().job_id, job3.job_id)
        self.assertIsNone(get_next_job_id())


# ============================================================================
# Model constraints
# ============================================================================


class ModelConstraintTests(TestCase):
    """Tests for model field defaults, relationships, and data integrity."""

    def test_job_status_defaults_to_pending(self):
        job = Job.objects.create(job_env_config={})
        self.assertEqual(job.status, "pending")

    def test_job_env_config_round_trips_through_db(self):
        config = {"timeout": 3600, "nested": {"key": "value"}}
        job = Job.objects.create(job_env_config=config)
        job.refresh_from_db()
        self.assertEqual(job.job_env_config, config)

    def test_job_created_at_is_set_automatically(self):
        job = Job.objects.create(job_env_config={})
        self.assertIsNotNone(job.created_at)

    def test_stepconfig_hash_is_primary_key(self):
        fp = compute_fingerprint({"test": "data"})
        StepConfig.objects.create(config_block_hash=fp, function="recording", config_block={"test": "data"})
        retrieved = StepConfig.objects.get(config_block_hash=fp)
        self.assertEqual(retrieved.config_block_hash, fp)

    def test_jobstep_status_defaults_to_pending(self):
        fp = get_or_create_step_configs("recording", {"binfile": "/test.bin"})
        job = Job.objects.create(job_env_config={})
        step = JobStep.objects.create(job=job, identifier="s1", function="recording", config_block_hash_id=fp)
        self.assertEqual(step.status, "pending")

    def test_jobstep_cascade_delete_with_job(self):
        fp = get_or_create_step_configs("recording", {"binfile": "/test.bin"})
        job = Job.objects.create(job_env_config={})
        JobStep.objects.create(job=job, identifier="s1", function="recording", config_block_hash_id=fp)
        job_id = job.job_id
        job.delete()
        self.assertEqual(JobStep.objects.filter(job_id=job_id).count(), 0)

    def test_job_status_can_transition_through_lifecycle(self):
        job = Job.objects.create(job_env_config={})
        for next_status in ["fetched", "running", "finished"]:
            job.status = next_status
            job.save()
            job.refresh_from_db()
            self.assertEqual(job.status, next_status)
