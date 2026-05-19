from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token


class SortingJobEndToEndTests(APITestCase):
    """
    Integration tests for the full sorting job lifecycle across all three apps:
    pipeline_factory → submit_jobs → job_queue (worker fetch).
    """

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def _create_pipeline(self):
        return self.client.post(
            "/pipeline-factory/pipelines/",
            {
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
            },
            format="json",
        ).json()["pipeline_id"]

    def _create_job(self, pipeline_id):
        return self.client.post(
            "/submit-jobs/create-sorting-job/",
            {
                "recording": {
                    "binfile": "/data/integration_test.bin",
                    "sampling_rate": 30000,
                    "num_channels": 32,
                    "gain_to_uV": 0.195,
                    "offset_to_uV": 0.0,
                },
                "pipeline_id": pipeline_id,
                "environment": "local",
            },
            format="json",
        ).json()

    def test_recording_placeholder_resolves_to_real_hash_in_worker_payload(self):
        """_RECORDING_ in pipeline must become the SHA-256 of the submitted recording config."""
        pipeline_id = self._create_pipeline()
        job_data = self._create_job(pipeline_id)
        recording_hash = job_data["recording_identifier"]

        fetched = self.client.get("/job-queue/next-job/").json()
        preprocessing = next(s for s in fetched["job_steps"] if s["function"] == "preprocessing")

        self.assertEqual(preprocessing["depends"], [recording_hash])

    def test_all_config_blocks_present_in_worker_payload(self):
        """Every step in job_steps must have a config block keyed by its identifier."""
        pipeline_id = self._create_pipeline()
        self._create_job(pipeline_id)
        fetched = self.client.get("/job-queue/next-job/").json()

        for step in fetched["job_steps"]:
            self.assertIn(step["identifier"], fetched,
                          f"Config block missing for step '{step['function']}'")

    def test_identical_recording_reuses_stepconfig(self):
        """Two jobs with the same recording config must share a single StepConfig."""
        pipeline_id = self._create_pipeline()
        job1 = self._create_job(pipeline_id)
        job2 = self._create_job(pipeline_id)
        self.assertEqual(job1["recording_identifier"], job2["recording_identifier"])

    def test_job_status_transitions_correctly(self):
        """Job must move: pending → fetched → running → completed."""
        pipeline_id = self._create_pipeline()
        job_id = self._create_job(pipeline_id)["job_id"]
        status_url = f"/job-queue/{job_id}/"
        next_job_url = "/job-queue/next-job/"
        update_url = "/job-queue/update-status/"

        self.assertEqual(self.client.get(status_url).json()["status"], "pending")

        self.client.get(next_job_url)
        self.assertEqual(self.client.get(status_url).json()["status"], "fetched")

        self.client.post(update_url, {"job_id": job_id, "status": "running"}, format="json")
        self.assertEqual(self.client.get(status_url).json()["status"], "running")

        self.client.post(update_url, {"job_id": job_id, "status": "completed"}, format="json")
        self.assertEqual(self.client.get(status_url).json()["status"], "completed")

    def test_job_step_count_is_pipeline_steps_plus_recording(self):
        pipeline_id = self._create_pipeline()
        job_data = self._create_job(pipeline_id)
        self.assertEqual(job_data["pipeline_steps_count"], 2)
        self.assertEqual(job_data["job_steps_count"], 3)
