from django.test import TestCase
from .models import (
    compute_fingerprint,
    get_or_create_step_configs,
    create_a_job,
    get_next_job_id,
    Job,
    JobStep,
    StepConfig,
)


class TestComputeFingerprint(TestCase):
    """
    Test suite for compute_fingerprint() function.
    Tests SHA-256 hash consistency and deduplication capabilities.
    """

    def setUp(self):
        """Create test configs before each test."""
        self.complex_config = {
            "recording": {
                "duration": 60,
                "channels": [0, 1, 2, 3],
                "settings": {"sample_rate": 30000, "gain": 0.195},
            },
            "preprocessing": ["filter", "whitening"],
        }

    def test_same_dict_produces_same_hash(self):
        """Test: Same dictionary always produces the same hash."""
        config = {"param": "value", "nested": {"key": "data"}}

        hash1 = compute_fingerprint(config)
        hash2 = compute_fingerprint(config)

        self.assertEqual(hash1, hash2, "Same dict should produce identical hashes")

    def test_different_dict_produces_different_hash(self):
        """Test: Different dictionaries produce different hashes."""
        config1 = {"param": "value1"}
        config2 = {"param": "value2"}

        hash1 = compute_fingerprint(config1)
        hash2 = compute_fingerprint(config2)

        self.assertNotEqual(hash1, hash2, "Different dicts should produce different hashes")

    def test_key_order_doesnt_matter(self):
        """Test: Dictionary key ordering doesn't affect the hash."""
        config1 = {"z": 100, "a": 1, "m": 50}
        config2 = {"a": 1, "m": 50, "z": 100}

        hash1 = compute_fingerprint(config1)
        hash2 = compute_fingerprint(config2)

        self.assertEqual(hash1, hash2, "Key ordering should not affect hash")

    def test_nested_dict_key_order_doesnt_matter(self):
        """Test: Nested dictionary key ordering doesn't affect the hash."""
        config1 = {"outer": {"z": 3, "a": 1, "m": 2}, "top": "value"}
        config2 = {"top": "value", "outer": {"a": 1, "m": 2, "z": 3}}

        hash1 = compute_fingerprint(config1)
        hash2 = compute_fingerprint(config2)

        self.assertEqual(hash1, hash2, "Nested key ordering should not affect hash")

    def test_hash_is_64_chars_long(self):
        """Test: SHA-256 hash is always 64 characters (hex format)."""
        config = {"test": "data"}
        hash_value = compute_fingerprint(config)

        self.assertEqual(len(hash_value), 64, "SHA-256 hex digest should be 64 characters")

    def test_hash_is_hexadecimal(self):
        """Test: Hash contains only valid hexadecimal characters."""
        config = {"test": "data"}
        hash_value = compute_fingerprint(config)

        try:
            int(hash_value, 16)
            is_hex = True
        except ValueError:
            is_hex = False

        self.assertTrue(is_hex, "Hash should be valid hexadecimal")

    def test_empty_dict_produces_hash(self):
        """Test: Empty dictionary produces a valid hash."""
        config = {}
        hash_value = compute_fingerprint(config)

        self.assertEqual(len(hash_value), 64, "Empty dict should still produce 64-char hash")

    def test_complex_nested_structure(self):
        """Test: Complex nested structures with lists, dicts, and primitives."""
        config = {
            "recording": {
                "duration": 60,
                "channels": [0, 1, 2, 3],
                "settings": {"sample_rate": 30000, "gain": 0.195},
            },
            "preprocessing": ["filter", "whitening"],
        }

        hash_value = compute_fingerprint(config)
        self.assertEqual(len(hash_value), 64, "Complex structure should produce valid hash")

        hash_value2 = compute_fingerprint(config)
        self.assertEqual(hash_value, hash_value2, "Same complex structure should produce same hash")

    def test_numeric_types_matter(self):
        """Test: Integer 1 and float 1.0 produce different hashes."""
        config1 = {"value": 1}
        config2 = {"value": 1.0}

        hash1 = compute_fingerprint(config1)
        hash2 = compute_fingerprint(config2)

        self.assertNotEqual(hash1, hash2, "JSON distinguishes int from float")

    def test_string_vs_number(self):
        """Test: Strings and numbers with same value produce different hashes."""
        config1 = {"value": "100"}
        config2 = {"value": 100}

        hash1 = compute_fingerprint(config1)
        hash2 = compute_fingerprint(config2)

        self.assertNotEqual(hash1, hash2, "String and number should have different hashes")


class TestGetOrCreateStepConfigs(TestCase):
    """Test suite for get_or_create_step_configs() function."""

    def test_creates_new_config_if_not_exists(self):
        """Test: Creates new StepConfig when fingerprint doesn't exist."""
        config = {"duration": 60, "sample_rate": 30000}
        function_name = "recording"

        fingerprint = get_or_create_step_configs(function_name, config)

        self.assertTrue(
            StepConfig.objects.filter(config_block_hash=fingerprint).exists(),
            "StepConfig should be created",
        )

    def test_reuses_existing_config(self):
        """Test: Returns fingerprint without creating if config already exists."""
        config = {"duration": 60, "sample_rate": 30000}
        function_name = "recording"

        fingerprint1 = get_or_create_step_configs(function_name, config)
        initial_count = StepConfig.objects.count()

        fingerprint2 = get_or_create_step_configs(function_name, config)
        final_count = StepConfig.objects.count()

        self.assertEqual(fingerprint1, fingerprint2, "Should return same fingerprint")
        self.assertEqual(initial_count, final_count, "Should not create duplicate")

    def test_stores_function_name(self):
        """Test: Stores the function name in StepConfig."""
        config = {"duration": 60}
        function_name = "kilosort"

        fingerprint = get_or_create_step_configs(function_name, config)
        step_config = StepConfig.objects.get(config_block_hash=fingerprint)

        self.assertEqual(step_config.function, function_name, "Function name should be stored")

    def test_different_configs_different_fingerprints(self):
        """Test: Different configs produce different fingerprints."""
        config1 = {"duration": 60}
        config2 = {"duration": 120}

        fingerprint1 = get_or_create_step_configs("recording", config1)
        fingerprint2 = get_or_create_step_configs("recording", config2)

        self.assertNotEqual(fingerprint1, fingerprint2, "Different configs should have different fingerprints")


class TestCreateAJob(TestCase):
    """Test suite for create_a_job() function."""

    def setUp(self):
        """Create test configs before each test."""
        self.config1 = {"duration": 60, "sample_rate": 30000}
        self.config2 = {"method": "kilosort2", "threshold": 0.5}

        self.fingerprint1 = get_or_create_step_configs("recording", self.config1)
        self.fingerprint2 = get_or_create_step_configs("kilosort", self.config2)

    def test_creates_job_with_single_step(self):
        """Test: Creates job with a single step."""
        job_env = {"timeout": 3600}
        job_steps = [
            {"identifier": self.fingerprint1, "function": "recording", "depends": []}
        ]

        job = create_a_job(job_env, job_steps)

        self.assertIsNotNone(job.job_id, "Job should have ID")
        self.assertEqual(job.status, "pending", "Job should start as pending")
        self.assertEqual(job.jobstep_set.count(), 1, "Job should have 1 step")

    def test_creates_job_with_multiple_steps(self):
        """Test: Creates job with multiple steps."""
        job_env = {"timeout": 3600}
        job_steps = [
            {"identifier": self.fingerprint1, "function": "recording", "depends": []},
            {
                "identifier": self.fingerprint2,
                "function": "kilosort",
                "depends": [self.fingerprint1],
            },
        ]

        job = create_a_job(job_env, job_steps)

        self.assertEqual(job.jobstep_set.count(), 2, "Job should have 2 steps")

    def test_fails_if_steps_empty(self):
        """Test: Raises error if job_steps is empty."""
        job_env = {}
        job_steps = []

        with self.assertRaises(RuntimeError):
            create_a_job(job_env, job_steps)

    def test_fails_if_step_not_dict(self):
        """Test: Raises error if step is not a dictionary."""
        job_env = {}
        job_steps = ["not a dict"]

        with self.assertRaises(RuntimeError):
            create_a_job(job_env, job_steps)

    def test_fails_if_missing_required_field(self):
        """Test: Raises error if step missing required field."""
        job_env = {}
        job_steps = [{"identifier": self.fingerprint1}]

        with self.assertRaises(RuntimeError):
            create_a_job(job_env, job_steps)

    def test_fails_if_config_not_exists(self):
        """Test: Raises error if StepConfig doesn't exist."""
        job_env = {}
        job_steps = [
            {
                "identifier": "nonexistent_hash_12345",
                "function": "recording",
                "depends": [],
            }
        ]

        with self.assertRaises(RuntimeError):
            create_a_job(job_env, job_steps)

    def test_preserves_dependencies(self):
        """Test: Stores dependencies correctly."""
        job_env = {}
        dependencies = ["step1", "step2"]
        job_steps = [
            {
                "identifier": self.fingerprint1,
                "function": "recording",
                "depends": dependencies,
            }
        ]

        job = create_a_job(job_env, job_steps)
        step = job.jobstep_set.first()

        self.assertEqual(step.depends_on, dependencies, "Dependencies should be preserved")


class TestGetNextJobId(TestCase):
    """Test suite for get_next_job_id() function."""

    def test_returns_none_if_no_pending_jobs(self):
        """Test: Returns None if no pending jobs exist."""
        job = get_next_job_id()
        self.assertIsNone(job, "Should return None if no pending jobs")

    def test_fetches_oldest_pending_job(self):
        """Test: Fetches the oldest pending job first (FIFO)."""
        job1 = Job.objects.create(job_env_config={}, status="pending")
        job2 = Job.objects.create(job_env_config={}, status="pending")

        fetched_job = get_next_job_id()
        self.assertEqual(fetched_job.job_id, job1.job_id, "Should fetch oldest job first")

    def test_marks_job_as_fetched(self):
        """Test: Marks job as 'fetched' after retrieval."""
        job = Job.objects.create(job_env_config={}, status="pending")

        fetched_job = get_next_job_id()
        fetched_job.refresh_from_db()
        self.assertEqual(fetched_job.status, "fetched", "Job should be marked as fetched")

    def test_skips_non_pending_jobs(self):
        """Test: Skips jobs that are not pending."""
        job1 = Job.objects.create(job_env_config={}, status="running")
        job2 = Job.objects.create(job_env_config={}, status="pending")

        fetched_job = get_next_job_id()

        self.assertEqual(fetched_job.job_id, job2.job_id, "Should skip non-pending jobs")

    def test_fifo_order_with_multiple_jobs(self):
        """Test: Returns jobs in FIFO order."""
        job1 = Job.objects.create(job_env_config={}, status="pending")
        job2 = Job.objects.create(job_env_config={}, status="pending")
        job3 = Job.objects.create(job_env_config={}, status="pending")

        fetched1 = get_next_job_id()
        fetched2 = get_next_job_id()
        fetched3 = get_next_job_id()

        self.assertEqual(fetched1.job_id, job1.job_id, "First fetched should be job1")
        self.assertEqual(fetched2.job_id, job2.job_id, "Second fetched should be job2")
        self.assertEqual(fetched3.job_id, job3.job_id, "Third fetched should be job3")


class TestModelRules(TestCase):
    """
    Test suite for validating model constraints and business rules.
    Ensures data integrity and proper model relationships.
    """

    def test_job_status_starts_as_pending(self):
        """Test: New Job always starts with status='pending'."""
        job = Job.objects.create(job_env_config={"timeout": 3600})
        self.assertEqual(job.status, "pending", "New job should have pending status")

    def test_job_env_config_stored_as_json(self):
        """Test: job_env_config is stored and retrieved as JSON."""
        config = {"timeout": 3600, "retry": 3, "params": {"key": "value"}}
        job = Job.objects.create(job_env_config=config)
        job.refresh_from_db()
        self.assertEqual(job.job_env_config, config, "Config should round-trip through DB")

    def test_stepconfig_created_with_hash_and_function(self):
        """Test: StepConfig requires config_block_hash and function."""
        config_hash = compute_fingerprint({"duration": 60})
        step_config = StepConfig.objects.create(
            config_block_hash=config_hash,
            function="recording",
            config_block={"duration": 60},
        )
        self.assertIsNotNone(step_config.config_block_hash)
        self.assertEqual(step_config.function, "recording")

    def test_jobstep_links_to_job_and_config(self):
        """Test: JobStep properly links to Job and StepConfig."""
        config_hash = compute_fingerprint({"duration": 60})
        step_config = StepConfig.objects.create(
            config_block_hash=config_hash,
            function="recording",
            config_block={"duration": 60},
        )
        job = Job.objects.create(job_env_config={}, status="pending")

        job_step = JobStep.objects.create(
            job=job,
            identifier="step1",
            function="recording",
            config_block_hash=step_config,
            status="pending",
        )

        self.assertEqual(job_step.job, job, "JobStep should link to Job")
        self.assertEqual(job_step.config_block_hash, step_config, "JobStep should link to StepConfig")

    def test_jobstep_status_defaults_to_pending(self):
        """Test: JobStep status defaults to 'pending' if not specified."""
        config_hash = compute_fingerprint({"duration": 60})
        step_config = StepConfig.objects.create(
            config_block_hash=config_hash,
            function="recording",
            config_block={"duration": 60},
        )
        job = Job.objects.create(job_env_config={}, status="pending")

        job_step = JobStep.objects.create(
            job=job,
            identifier="step1",
            function="recording",
            config_block_hash=step_config,
        )

        self.assertEqual(job_step.status, "pending", "JobStep should default to pending")

    def test_stepconfig_hash_is_primary_key(self):
        """Test: config_block_hash is the primary key for StepConfig."""
        config_hash = compute_fingerprint({"duration": 60})
        step_config = StepConfig.objects.create(
            config_block_hash=config_hash,
            function="recording",
            config_block={"duration": 60},
        )

        retrieved = StepConfig.objects.get(config_block_hash=config_hash)
        self.assertEqual(retrieved.config_block_hash, config_hash)

    def test_job_timestamps_created_automatically(self):
        """Test: Job creation timestamps are set automatically."""
        job = Job.objects.create(job_env_config={}, status="pending")
        self.assertIsNotNone(job.created_at, "created_at should be set automatically")

    def test_multiple_jobsteps_per_job(self):
        """Test: One Job can have multiple JobSteps."""
        config_hash = compute_fingerprint({"duration": 60})
        step_config = StepConfig.objects.create(
            config_block_hash=config_hash,
            function="recording",
            config_block={"duration": 60},
        )
        job = Job.objects.create(job_env_config={}, status="pending")

        step1 = JobStep.objects.create(
            job=job,
            identifier="step1",
            function="recording",
            config_block_hash=step_config,
        )
        step2 = JobStep.objects.create(
            job=job,
            identifier="step2",
            function="kilosort",
            config_block_hash=step_config,
        )

        self.assertEqual(job.jobstep_set.count(), 2, "Job should have 2 steps")

    def test_jobstep_depends_on_stored_as_list(self):
        """Test: JobStep depends_on field stores list of dependencies."""
        config_hash = compute_fingerprint({"duration": 60})
        step_config = StepConfig.objects.create(
            config_block_hash=config_hash,
            function="recording",
            config_block={"duration": 60},
        )
        job = Job.objects.create(job_env_config={}, status="pending")

        dependencies = ["step1", "step2", "step3"]
        job_step = JobStep.objects.create(
            job=job,
            identifier="step4",
            function="merge",
            config_block_hash=step_config,
            depends_on=dependencies,
        )

        self.assertEqual(job_step.depends_on, dependencies, "Dependencies should be preserved")

    def test_stepconfig_config_block_stored_as_json(self):
        """Test: StepConfig config_block is stored and retrieved as JSON."""
        config_dict = {"duration": 60, "sample_rate": 30000, "nested": {"key": "value"}}
        config_hash = compute_fingerprint(config_dict)

        step_config = StepConfig.objects.create(
            config_block_hash=config_hash,
            function="recording",
            config_block=config_dict,
        )
        step_config.refresh_from_db()

        self.assertEqual(step_config.config_block, config_dict, "config_block should round-trip through DB")

    def test_job_can_transition_statuses(self):
        """Test: Job status can be updated through its lifecycle."""
        job = Job.objects.create(job_env_config={}, status="pending")

        job.status = "fetched"
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.status, "fetched")

        job.status = "running"
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.status, "running")

        job.status = "finished"
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.status, "finished")
