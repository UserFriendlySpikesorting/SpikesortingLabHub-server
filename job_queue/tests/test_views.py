from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from job_queue.models import Job, JobStep, get_or_create_step_configs, create_a_job


# ============================================================================
# POST /job-queue/auth/login/
# ============================================================================


class LoginViewTests(APITestCase):
    """Tests for the authentication login endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.url = "/job-queue/auth/login/"

    def test_valid_credentials_return_token_and_200(self):
        response = self.client.post(self.url, {"username": "testuser", "password": "testpass"}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertEqual(data["username"], "testuser")
        self.assertIn("user_id", data)

    def test_wrong_password_returns_401(self):
        response = self.client.post(self.url, {"username": "testuser", "password": "wrong"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_unknown_user_returns_401(self):
        response = self.client.post(self.url, {"username": "nobody", "password": "pass"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_missing_password_returns_400(self):
        response = self.client.post(self.url, {"username": "testuser"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_username_returns_400(self):
        response = self.client.post(self.url, {"password": "testpass"}, format="json")
        self.assertEqual(response.status_code, 400)


# ============================================================================
# GET + POST /job-queue/getthenextjob/
# ============================================================================


class GetNextJobViewTests(APITestCase):
    """Tests for the worker job assignment and status update endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="worker", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/job-queue/next-job/"
        self.recording_hash = get_or_create_step_configs("recording", {"binfile": "/test.bin"})

    def _create_job(self):
        return create_a_job(
            {"environment": "local"},
            [{"function": "recording", "identifier": self.recording_hash, "depends": []}],
        )

    # --- GET ---

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_returns_empty_dict_when_no_pending_jobs(self):
        response = self.client.get(self.url)
        self.assertEqual(response.json(), {})

    def test_get_returns_job_id_and_steps(self):
        job = self._create_job()
        data = self.client.get(self.url).json()
        self.assertEqual(data["job_id"], str(job.job_id))
        self.assertIn("job_steps", data)
        self.assertIn("job_evn", data)
        self.assertIn("version", data)
        self.assertIn("si", data)

    def test_get_includes_config_block_keyed_by_identifier(self):
        self._create_job()
        data = self.client.get(self.url).json()
        step_identifier = data["job_steps"][0]["identifier"]
        self.assertIn(step_identifier, data)  # Config block present

    def test_get_marks_job_as_fetched(self):
        job = self._create_job()
        self.client.get(self.url)
        job.refresh_from_db()
        self.assertEqual(job.status, "fetched")

    # --- POST: update job status ---

    def test_post_updates_job_status(self):
        job = self._create_job()
        response = self.client.post(self.url, {"job_id": str(job.job_id), "status": "running"}, format="json")
        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, "running")

    def test_post_updates_step_status(self):
        job = self._create_job()
        step = job.jobstep_set.first()
        response = self.client.post(
            self.url,
            {"job_id": str(job.job_id), "step_id": step.identifier, "status": "completed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        step.refresh_from_db()
        self.assertEqual(step.status, "completed")

    def test_post_missing_job_id_returns_400(self):
        response = self.client.post(self.url, {"status": "running"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_missing_status_returns_400(self):
        job = self._create_job()
        response = self.client.post(self.url, {"job_id": str(job.job_id)}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_invalid_json_returns_400(self):
        response = self.client.post(self.url, data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    # --- Authentication ---

    def test_get_requires_authentication(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [401, 403])

    def test_post_requires_authentication(self):
        job = self._create_job()
        self.client.credentials()
        response = self.client.post(self.url, {"job_id": str(job.job_id), "status": "running"}, format="json")
        self.assertIn(response.status_code, [401, 403])
