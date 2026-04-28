import copy

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from pipeline_factory.models import Pipeline, PipelineStep
from job_queue.models import get_or_create_step_configs, create_a_job, Job


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
# GET /submit-jobs/list/
# ============================================================================


class ListJobsViewTests(APITestCase):
    """Tests for the paginated job list endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/submit-jobs/list/"
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
# GET /submit-jobs/statistics/
# ============================================================================


class JobStatisticsViewTests(APITestCase):
    """Tests for the job statistics endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/submit-jobs/statistics/"

    def test_returns_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_response_includes_total_jobs_and_breakdown(self):
        data = self.client.get(self.url).json()
        self.assertIn("total_jobs", data)
        self.assertIn("status_breakdown", data)

    def test_breakdown_covers_all_five_statuses(self):
        breakdown = self.client.get(self.url).json()["status_breakdown"]
        for s in ("pending", "fetched", "running", "finished", "failed"):
            self.assertIn(s, breakdown)

    def test_total_jobs_matches_sum_of_breakdown(self):
        data = self.client.get(self.url).json()
        self.assertEqual(data["total_jobs"], sum(data["status_breakdown"].values()))


# ============================================================================
# GET /submit-jobs/<job_id>/  (job_detail)
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
        response = self.client.get(f"/submit-jobs/{self.job.job_id}/")
        self.assertEqual(response.status_code, 200)

    def test_returns_correct_job_id(self):
        data = self.client.get(f"/submit-jobs/{self.job.job_id}/").json()
        self.assertEqual(data["job_id"], str(self.job.job_id))

    def test_returns_404_for_nonexistent_job(self):
        response = self.client.get("/submit-jobs/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, 404)
