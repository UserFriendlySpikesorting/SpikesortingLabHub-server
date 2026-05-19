from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from pipeline_factory.models import Pipeline, PipelineStep


# Reusable minimal pipeline payload
PIPELINE_PAYLOAD = {
    "description": "Test pipeline",
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


class PipelineViewSetTests(APITestCase):
    """Tests for POST and GET /pipeline-factory/pipelines/."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/pipeline-factory/pipelines/"

    # --- POST: create ---

    def test_create_returns_201(self):
        response = self.client.post(self.url, PIPELINE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 201)

    def test_create_returns_pipeline_id(self):
        response = self.client.post(self.url, PIPELINE_PAYLOAD, format="json")
        self.assertIn("pipeline_id", response.json())

    def test_create_stores_correct_step_count(self):
        data = self.client.post(self.url, PIPELINE_PAYLOAD, format="json").json()
        self.assertEqual(data["step_count"], 2)
        self.assertEqual(len(data["steps"]), 2)

    def test_create_resolves_inter_step_dependencies_to_sha256(self):
        """pp001 → _RECORDING_ must stay as-is; so001 → pp001 must become a 64-char hash."""
        steps = self.client.post(self.url, PIPELINE_PAYLOAD, format="json").json()["steps"]
        preprocessing = next(s for s in steps if s["function"] == "preprocessing")
        sorting = next(s for s in steps if s["function"] == "sorting")

        # _RECORDING_ has no config block in the payload → stored as-is
        self.assertEqual(preprocessing["depends_on"], ["_RECORDING_"])
        # pp001 has a config block → resolved to its 64-char SHA-256 hash
        self.assertEqual(len(sorting["depends_on"]), 1)
        self.assertEqual(len(sorting["depends_on"][0]), 64)

    def test_create_is_atomic_bad_step_rolls_back_pipeline(self):
        """A step with no 'function' must trigger a 400 and leave DB unchanged."""
        bad_payload = {
            "description": "Bad",
            "job_steps": [{"function": "", "identifier": "abc", "depends": []}],
            "abc": {},
        }
        count_before = Pipeline.objects.count()
        response = self.client.post(self.url, bad_payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Pipeline.objects.count(), count_before)

    def test_create_supports_job_steps_field_name(self):
        """Accepts 'job_steps' (as well as 'steps') without error."""
        response = self.client.post(self.url, PIPELINE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 201)

    def test_create_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(self.url, PIPELINE_PAYLOAD, format="json")
        self.assertIn(response.status_code, [401, 403])

    # --- GET: list ---

    def test_list_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_list_returns_created_pipelines(self):
        self.client.post(self.url, PIPELINE_PAYLOAD, format="json")
        self.client.post(self.url, {**PIPELINE_PAYLOAD, "description": "Second"}, format="json")
        data = self.client.get(self.url).json()
        # DRF ModelViewSet returns paginated results with 'results' key
        results = data if isinstance(data, list) else data.get("results", [])
        self.assertGreaterEqual(len(results), 2)

    def test_list_requires_authentication(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [401, 403])


class PipelineStepViewSetTests(APITestCase):
    """Tests for GET /pipeline-factory/pipeline-steps/."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_pipeline_steps_returns_200(self):
        response = self.client.get("/pipeline-factory/pipeline-steps/")
        self.assertEqual(response.status_code, 200)
