from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token


class PipelineToJobIntegrationTests(APITestCase):
    """
    Integration tests for the full pipeline → job creation → worker fetch flow.
    Verifies that placeholder dependency resolution works end-to-end across apps.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def _create_pipeline(self, extra_steps=None):
        payload = {
            "description": "Integration test pipeline",
            "job_steps": [
                {"function": "preprocessing", "identifier": "pp001", "depends": ["_RECORDING_"]},
                {"function": "sorting",       "identifier": "so001", "depends": ["pp001"]},
            ],
            "pp001": {
                "methods": ["highpass or band filtering"],
                "highpass or band filtering": {"btype": "bandpass", "band": [100.0, 10000.0]},
            },
            "so001": {"name": "hdsort", "parameters": {}},
        }
        if extra_steps:
            payload["job_steps"] += extra_steps
        return self.client.post("/pipeline-factory/pipelines/", payload, format="json")

    def _create_sorting_job(self, pipeline_id):
        return self.client.post(
            "/submit-jobs/create-sorting-job/",
            {
                "recording": {
                    "binfile": "/data/integration_test.bin",
                    "sampling_rate": 30000,
                    "num_channels": 32,
                    "gain": 0.195,
                    "offset": 0.0,
                },
                "pipeline_id": pipeline_id,
                "environment": "local",
            },
            format="json",
        )

    def test_recording_placeholder_resolves_in_worker_payload(self):
        """_RECORDING_ in pipeline depends_on must become the real recording hash."""
        pipeline_id = self._create_pipeline().json()["pipeline_id"]
        job_data = self._create_sorting_job(pipeline_id).json()
        recording_identifier = job_data["recording_identifier"]

        fetched = self.client.get("/job-queue/getthenextjob/").json()
        preprocessing = next(s for s in fetched["job_steps"] if s["function"] == "preprocessing")

        self.assertEqual(
            preprocessing["depends"],
            [recording_identifier],
            "_RECORDING_ must resolve to the actual recording SHA-256 hash",
        )

    def test_all_config_blocks_present_in_worker_payload(self):
        """Every step identifier in job_steps must have a corresponding config block."""
        pipeline_id = self._create_pipeline().json()["pipeline_id"]
        self._create_sorting_job(pipeline_id)
        fetched = self.client.get("/job-queue/getthenextjob/").json()

        for step in fetched["job_steps"]:
            self.assertIn(
                step["identifier"],
                fetched,
                f"Config block missing for step '{step['function']}'",
            )

    def test_identical_recording_config_reuses_stepconfig(self):
        """Two jobs with the same recording config must share one StepConfig record."""
        pipeline_id = self._create_pipeline().json()["pipeline_id"]
        job1 = self._create_sorting_job(pipeline_id).json()
        job2 = self._create_sorting_job(pipeline_id).json()
        self.assertEqual(
            job1["recording_identifier"],
            job2["recording_identifier"],
            "Identical recording configs must produce the same StepConfig hash",
        )

    def test_job_step_count_is_pipeline_steps_plus_one_recording(self):
        """A pipeline with N steps must produce a job with N+1 steps (+ recording)."""
        pipeline_id = self._create_pipeline().json()["pipeline_id"]
        job_data = self._create_sorting_job(pipeline_id).json()
        self.assertEqual(job_data["pipeline_steps_count"], 2)
        self.assertEqual(job_data["job_steps_count"], 3)  # 2 pipeline + 1 recording

    def test_job_status_transitions_pending_to_fetched(self):
        """After the worker fetches a job, its status must change to 'fetched'."""
        pipeline_id = self._create_pipeline().json()["pipeline_id"]
        job_id = self._create_sorting_job(pipeline_id).json()["job_id"]

        status_before = self.client.get(f"/job-queue/{job_id}/").json()["status"]
        self.assertEqual(status_before, "pending")

        self.client.get("/job-queue/next-job/")

        status_after = self.client.get(f"/job-queue/{job_id}/").json()["status"]
        self.assertEqual(status_after, "fetched")
