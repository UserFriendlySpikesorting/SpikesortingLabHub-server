import copy

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from pipeline_factory.models import Pipeline, PipelineStep
from job_queue.models import get_or_create_step_configs, create_a_job, Job, JobStep


# ============================================================================
# Shared test helpers
# ============================================================================


def create_test_pipeline():
    """Creates a minimal 2-step pipeline (preprocessing + sorting) for test use."""
    pipeline = Pipeline.objects.create(description="Test pipeline")
    preprocessing_hash = get_or_create_step_configs(
        "preprocessing", {"methods": ["highpass or band filtering"]}
    )
    sorting_hash = get_or_create_step_configs("sorting", {"name": "hdsort", "parameters": {}})
    PipelineStep.objects.create(
        pipeline=pipeline,
        config_block_hash_id=preprocessing_hash,
        depends_on=["_RECORDING_"],
    )
    PipelineStep.objects.create(
        pipeline=pipeline,
        config_block_hash_id=sorting_hash,
        depends_on=[preprocessing_hash],
    )
    return pipeline


def create_test_pipeline_with_upload():
    """
    Creates a 1-step pipeline containing only an `upload` step, using the
    old-style frozen config (no `destination`, just `base path` + `suffix`) —
    mirroring a real historical pipeline. Its config must be fully replaced
    by the wizard's Destination step at job-creation time, never reused as-is.
    """
    pipeline = Pipeline.objects.create(description="Test pipeline with upload")
    upload_hash = get_or_create_step_configs(
        "upload", {"suffix": "0001", "base path": "$NAS$"}
    )
    PipelineStep.objects.create(
        pipeline=pipeline,
        config_block_hash_id=upload_hash,
        depends_on=["_RECORDING_"],
    )
    return pipeline


RECORDING_PAYLOAD = {
    "binfile": "/data/test.bin",
    "sampling_rate": 30000,
    "num_channels": 32,
    "gain_to_uV": 0.195,
    "offset_to_uV": 0.0,
    "probe": "/data/probe.json",
    "bad_channels": [],
}


# ============================================================================
# POST /submit-jobs/create-sorting-job/
# ============================================================================


class CreateSortingJobViewTests(APITestCase):
    """Tests for the job creation endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/submit-jobs/create-sorting-job/"
        self.pipeline = create_test_pipeline()

    def _payload(self, **overrides):
        base = {
            "recording": copy.deepcopy(RECORDING_PAYLOAD),
            "pipeline_id": self.pipeline.pipeline_id,
            "environment": "local",
        }
        base.update(overrides)
        return base

    def test_valid_payload_returns_201(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, 201)

    def test_response_includes_job_id(self):
        data = self.client.post(self.url, self._payload(), format="json").json()
        self.assertIn("job_id", data)

    def test_response_includes_recording_identifier(self):
        data = self.client.post(self.url, self._payload(), format="json").json()
        self.assertIn("recording_identifier", data)
        self.assertEqual(len(data["recording_identifier"]), 64)

    def test_job_steps_count_includes_recording_step(self):
        data = self.client.post(self.url, self._payload(), format="json").json()
        self.assertEqual(data["pipeline_steps_count"], 2)
        self.assertEqual(data["job_steps_count"], 3)  # 2 pipeline + 1 recording

    def test_created_job_has_pending_status(self):
        data = self.client.post(self.url, self._payload(), format="json").json()
        self.assertEqual(data["status"], "pending")

    def test_nonexistent_pipeline_id_returns_400(self):
        response = self.client.post(self.url, self._payload(pipeline_id=99999), format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_environment_returns_400(self):
        response = self.client.post(self.url, self._payload(environment="invalid"), format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_binfile_returns_400(self):
        payload = self._payload()
        del payload["recording"]["binfile"]
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_sampling_rate_returns_400(self):
        payload = self._payload()
        del payload["recording"]["sampling_rate"]
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertIn(response.status_code, [401, 403])


# ============================================================================
# POST /submit-jobs/create-sorting-job/  — optional Downsample step
# ============================================================================


class SortingJobDownsampleTests(APITestCase):
    """Tests for the wizard's optional Downsample step."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/submit-jobs/create-sorting-job/"
        self.pipeline = create_test_pipeline()

    def _payload(self, **overrides):
        base = {
            "recording": copy.deepcopy(RECORDING_PAYLOAD),
            "pipeline_id": self.pipeline.pipeline_id,
            "environment": "local",
        }
        base.update(overrides)
        return base

    def test_without_downsample_block_has_no_downsample_step(self):
        data = self.client.post(self.url, self._payload(), format="json").json()
        self.assertEqual(data["job_steps_count"], 3)  # recording + 2 pipeline steps

    def test_with_downsample_block_adds_one_step(self):
        payload = self._payload(downsample={
            "downsample_factor": 30,
            "output_folder": "/data/out",
            "output_name": "session01",
        })
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["job_steps_count"], 4)  # +1 downsample_to_lfp

    def test_downsample_step_reuses_recording_binfile_and_channels(self):
        payload = self._payload(downsample={
            "downsample_factor": 30,
            "output_folder": "/data/out",
            "output_name": "session01",
        })
        self.client.post(self.url, payload, format="json")
        step = JobStep.objects.get(function="downsample_to_lfp")
        config = step.config_block_hash.config_block
        self.assertEqual(config["input files"], ["/data/test.bin"])
        self.assertEqual(config["number of channels"], 32)
        self.assertEqual(config["downsample factor"], 30)
        self.assertTrue(config["output file"].endswith("combined_ds30_session01.h5"))

    def test_missing_downsample_factor_returns_400(self):
        payload = self._payload(downsample={
            "output_folder": "/data/out",
            "output_name": "session01",
        })
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_output_folder_returns_400(self):
        payload = self._payload(downsample={
            "downsample_factor": 30,
            "output_name": "session01",
        })
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 400)


# ============================================================================
# POST /submit-jobs/create-sorting-job/  — Destination step / `upload` override
# ============================================================================


class SortingJobDestinationTests(APITestCase):
    """Tests for the wizard's Destination step overriding a pipeline's `upload` step."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/submit-jobs/create-sorting-job/"
        self.pipeline = create_test_pipeline_with_upload()

    def _payload(self, **overrides):
        base = {
            "recording": copy.deepcopy(RECORDING_PAYLOAD),
            "pipeline_id": self.pipeline.pipeline_id,
            "environment": "local",
        }
        base.update(overrides)
        return base

    def test_missing_destination_returns_400(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("destination", response.json()["error"])

    def test_with_destination_returns_201(self):
        payload = self._payload(destination={"folder": "/data/results", "name": "session01"})
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_upload_config_overrides_stale_pipeline_default(self):
        payload = self._payload(destination={"folder": "/data/results", "name": "session01"})
        self.client.post(self.url, payload, format="json")
        step = JobStep.objects.get(function="upload")
        config = step.config_block_hash.config_block
        # The old `base path`-only shape must be completely gone, not merged with it.
        self.assertNotIn("base path", config)
        self.assertEqual(config["destination"], "/data/results/session01")

    def test_keep_base_directory_defaults_false(self):
        payload = self._payload(destination={"folder": "/data/results", "name": "session01"})
        self.client.post(self.url, payload, format="json")
        step = JobStep.objects.get(function="upload")
        self.assertFalse(step.config_block_hash.config_block["keep_base_directory"])

    def test_keep_base_directory_can_be_set_true(self):
        payload = self._payload(destination={
            "folder": "/data/results", "name": "session01", "keep_base_directory": True,
        })
        self.client.post(self.url, payload, format="json")
        step = JobStep.objects.get(function="upload")
        self.assertTrue(step.config_block_hash.config_block["keep_base_directory"])

    def test_pipeline_without_upload_step_does_not_require_destination(self):
        other_pipeline = create_test_pipeline()  # no upload step
        payload = {
            "recording": copy.deepcopy(RECORDING_PAYLOAD),
            "pipeline_id": other_pipeline.pipeline_id,
            "environment": "local",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201)


# ============================================================================
# GET /submit-jobs/list/
# ============================================================================


class ListJobsViewTests(APITestCase):
    """Tests for the paginated job list endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/job-queue/list/"
        recording_hash = get_or_create_step_configs("recording", {"binfile": "/test.bin"})
        steps = [{"function": "recording", "identifier": recording_hash, "depends": []}]
        create_a_job({"environment": "local"}, steps)
        create_a_job({"environment": "local"}, steps)

    def test_returns_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_response_includes_pagination_fields(self):
        data = self.client.get(self.url).json()
        for field in ("total_count", "count", "limit", "offset", "jobs"):
            self.assertIn(field, data)

    def test_status_filter_returns_only_matching_jobs(self):
        data = self.client.get(f"{self.url}?status=pending").json()
        for job in data["jobs"]:
            self.assertEqual(job["status"], "pending")

    def test_limit_parameter_caps_results(self):
        data = self.client.get(f"{self.url}?limit=1").json()
        self.assertEqual(data["count"], 1)

    def test_offset_parameter_skips_results(self):
        all_data = self.client.get(self.url).json()
        offset_data = self.client.get(f"{self.url}?offset=1").json()
        self.assertEqual(offset_data["count"], all_data["total_count"] - 1)

    def test_requires_authentication(self):
        self.client.credentials()
        self.assertIn(self.client.get(self.url).status_code, [401, 403])


# ============================================================================
# GET /job-queue/statistics/
# ============================================================================


class JobStatisticsViewTests(APITestCase):
    """Tests for the job statistics endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/job-queue/statistics/"

    def test_returns_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_response_includes_total_jobs_and_breakdown(self):
        data = self.client.get(self.url).json()
        self.assertIn("total_jobs", data)
        self.assertIn("status_breakdown", data)

    def test_breakdown_covers_all_five_statuses(self):
        breakdown = self.client.get(self.url).json()["status_breakdown"]
        for s in ("pending", "fetched", "running", "completed", "failed"):
            self.assertIn(s, breakdown)

    def test_total_jobs_matches_sum_of_breakdown(self):
        data = self.client.get(self.url).json()
        self.assertEqual(data["total_jobs"], sum(data["status_breakdown"].values()))


# ============================================================================
# GET /job-queue/<job_id>/  (job_detail)
# ============================================================================


class JobDetailViewTests(APITestCase):
    """Tests for the single-job detail endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        recording_hash = get_or_create_step_configs("recording", {"binfile": "/test.bin"})
        self.job = create_a_job(
            {"environment": "local"},
            [{"function": "recording", "identifier": recording_hash, "depends": []}],
        )

    def test_returns_200_for_existing_job(self):
        response = self.client.get(f"/job-queue/{self.job.job_id}/")
        self.assertEqual(response.status_code, 200)

    def test_returns_correct_job_id(self):
        data = self.client.get(f"/job-queue/{self.job.job_id}/").json()
        self.assertEqual(data["job_id"], str(self.job.job_id))

    def test_returns_404_for_nonexistent_job(self):
        response = self.client.get("/job-queue/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, 404)
