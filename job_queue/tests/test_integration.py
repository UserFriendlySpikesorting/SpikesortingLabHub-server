from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from job_queue.models import get_or_create_step_configs, create_a_job


class WorkerJobLifecycleIntegrationTests(APITestCase):
    """
    Integration tests for the full worker job lifecycle:
    job creation → worker fetch → step-by-step status updates → job completion.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="worker", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.next_job_url = "/job-queue/next-job/"
        self.update_url = "/job-queue/update-status/"

    def _create_two_step_job(self):
        recording_hash = get_or_create_step_configs("recording", {"binfile": "/data/test.bin"})
        sorting_hash = get_or_create_step_configs("sorting", {"name": "hdsort"})
        return create_a_job(
            {"environment": "local"},
            [
                {"function": "recording", "identifier": recording_hash, "depends": []},
                {"function": "sorting",   "identifier": sorting_hash,   "depends": [recording_hash]},
            ],
        )

    def test_full_job_lifecycle(self):
        """pending → fetched → running (per step) → completed."""
        job = self._create_two_step_job()

        # Worker fetches the job
        data = self.client.get(self.next_job_url).json()
        self.assertEqual(data["job_id"], str(job.job_id))
        job.refresh_from_db()
        self.assertEqual(job.status, "fetched")

        # Worker marks job running
        self.client.post(self.update_url, {"job_id": str(job.job_id), "status": "running"}, format="json")
        job.refresh_from_db()
        self.assertEqual(job.status, "running")

        # Worker completes each step
        for step in job.jobstep_set.all():
            self.client.post(
                self.update_url,
                {"job_id": str(job.job_id), "step_id": step.identifier, "status": "completed"},
                format="json",
            )
            step.refresh_from_db()
            self.assertEqual(step.status, "completed")

        # Worker marks job completed
        self.client.post(self.update_url, {"job_id": str(job.job_id), "status": "completed"}, format="json")
        job.refresh_from_db()
        self.assertEqual(job.status, "completed")

    def test_config_blocks_present_in_worker_payload(self):
        """Worker payload must include config blocks keyed by step identifier."""
        self._create_two_step_job()
        data = self.client.get(self.next_job_url).json()
        for step in data["job_steps"]:
            self.assertIn(step["identifier"], data, f"Config block missing for step '{step['function']}'")

    def test_fifo_queue_dispatches_oldest_job_first(self):
        """Two jobs must be dispatched in creation order."""
        recording_hash = get_or_create_step_configs("recording", {"binfile": "/data/test.bin"})
        steps = [{"function": "recording", "identifier": recording_hash, "depends": []}]
        job1 = create_a_job({"environment": "local"}, steps)
        job2 = create_a_job({"environment": "local"}, steps)

        fetch1 = self.client.get(self.next_job_url).json()
        fetch2 = self.client.get(self.next_job_url).json()

        self.assertEqual(fetch1["job_id"], str(job1.job_id))
        self.assertEqual(fetch2["job_id"], str(job2.job_id))

    def test_empty_queue_returns_empty_dict(self):
        response = self.client.get(self.next_job_url)
        self.assertEqual(response.json(), {})

    def test_same_stepconfig_reused_across_jobs(self):
        """Identical config dicts must not create duplicate StepConfig rows."""
        from job_queue.models import StepConfig
        config = {"binfile": "/data/shared.bin"}
        count_before = StepConfig.objects.count()
        get_or_create_step_configs("recording", config)
        get_or_create_step_configs("recording", config)
        self.assertEqual(StepConfig.objects.count(), count_before + 1)
