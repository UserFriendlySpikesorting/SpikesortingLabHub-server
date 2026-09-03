from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from job_queue.models import StepConfig
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


# ============================================================================
# Realistic full-pipeline payloads (derived from sample professor JSONs)
# ============================================================================

# Mirrors 176fo.json: bandpass preprocessing, HDSort sorting, full analyzer,
# phy_export, MATLAB export, and an upload step that depends only on _RECORDING_.
FULL_PIPELINE_PAYLOAD = {
    "description": "Full 6-step pipeline with analyzer",
    "job_steps": [
        {"function": "preprocessing", "identifier": "pp001", "depends": ["_RECORDING_"]},
        {"function": "sorting",       "identifier": "so001", "depends": ["pp001"]},
        {"function": "analyzer",      "identifier": "an001", "depends": ["pp001", "so001"]},
        {"function": "phy_export",    "identifier": "ph001", "depends": ["pp001", "so001"]},
        {"function": "export2matlab", "identifier": "ex001", "depends": ["pp001", "so001", "an001", "ph001"]},
        {"function": "upload",        "identifier": "up001", "depends": ["_RECORDING_"]},
    ],
    "pp001": {
        "methods": ["highpass or band filtering"],
        "highpass or band filtering": {"btype": "bandpass", "band": [100.0, 10000.0]},
    },
    "so001": {
        "name": "hdsort",
        "parameters": {
            "loop_mode": "local_parfor",
            "detect_threshold": 2.8461521921744675,
            "max_el_per_group": 8,
            "min_el_per_group": 2,
        },
        "folder": "sorting-saved",
    },
    "an001": {
        "metrics": {
            "quality_metrics": {
                "qm_params": {"isi_violation": {"isi_threshold_ms": 2.0}},
            },
            "waveforms": {"ms_before": 1.5, "ms_after": 2.5},
            "spike_amplitudes": {"peak_sign": "neg"},
            "spike_locations": {
                "method": "monopolar_triangulation",
                "ms_before": 5.0,
                "ms_after": 5.0,
                "spike_retriver_kwargs": {
                    "channel_from_template": False,
                    "radius_um": 100,
                    "peak_sign": "both",
                },
            },
            "correlograms": {"window_ms": 500.0, "bin_ms": 1.0, "method": "auto"},
            "isi_histograms": {"window_ms": 500.0, "bin_ms": 1.0, "method": "auto"},
            "principal_components": {"n_components": 5, "mode": "by_channel_local", "whiten": False},
        }
    },
    "ph001": {"folder": "phy"},
    "ex001": {"filename": "spikesorting-export.h5"},
    "up001": {"suffix": "0176fo", "base path": "$NAS$"},
}

# Mirrors 165.json: adds local median referencing to preprocessing.
PIPELINE_WITH_REFERENCING_PAYLOAD = {
    "description": "Pipeline with local median referencing (165 config)",
    "job_steps": [
        {"function": "preprocessing", "identifier": "pp001", "depends": ["_RECORDING_"]},
        {"function": "sorting",       "identifier": "so001", "depends": ["pp001"]},
        {"function": "analyzer",      "identifier": "an001", "depends": ["pp001", "so001"]},
        {"function": "phy_export",    "identifier": "ph001", "depends": ["pp001", "so001"]},
        {"function": "export2matlab", "identifier": "ex001", "depends": ["pp001", "so001", "an001", "ph001"]},
        {"function": "upload",        "identifier": "up001", "depends": ["_RECORDING_"]},
    ],
    "pp001": {
        "methods": ["highpass or band filtering", "referensing"],
        "highpass or band filtering": {
            "btype": "bandpass",
            "band": [131.23838233443735, 7891.04780192575],
        },
        "referensing": {
            "reference": "local",
            "operator": "median",
            "groups": None,
            "ref_channel_ids": [],
            "local_radius": [385, 861],
        },
    },
    "so001": {
        "name": "hdsort",
        "parameters": {
            "detect_threshold": 3.794935952354302,
            "max_el_per_group": 6,
            "min_el_per_group": 2,
            "max_distance_within_group": 488,
        },
        "folder": "sorting-saved",
    },
    "an001": {
        "metrics": {
            "correlograms": {"window_ms": 500.0, "bin_ms": 1.0, "method": "auto"},
            "isi_histograms": {"window_ms": 500.0, "bin_ms": 1.0, "method": "auto"},
            "waveforms": {"ms_before": 1.5, "ms_after": 2.5},
        }
    },
    "ph001": {"folder": "phy"},
    "ex001": {"filename": "spikesorting-export.h5"},
    "up001": {"suffix": "0165", "base path": "$NAS$"},
}

# Mirrors initial-176fo.json: simpler pipeline without analyzer or MATLAB export.
INITIAL_PIPELINE_PAYLOAD = {
    "description": "Initial pipeline (sorting + phy_export only)",
    "job_steps": [
        {"function": "preprocessing", "identifier": "pp001", "depends": ["_RECORDING_"]},
        {"function": "sorting",       "identifier": "so001", "depends": ["pp001"]},
        {"function": "phy_export",    "identifier": "ph001", "depends": ["pp001", "so001"]},
        {"function": "upload",        "identifier": "up001", "depends": ["_RECORDING_"]},
    ],
    "pp001": {
        "methods": ["highpass or band filtering"],
        "highpass or band filtering": {"btype": "bandpass", "band": [100.0, 10000.0]},
    },
    "so001": {
        "name": "hdsort",
        "parameters": {"detect_threshold": 2.8461521921744675, "max_el_per_group": 8},
        "folder": "sorting-saved",
    },
    "ph001": {},  # empty config — phy_export has no parameters in initial pipeline
    "up001": {"suffix": "0176fo", "base path": "$NAS$"},
}


class RealisticPipelineUploadTests(APITestCase):
    """
    Tests using payloads that mirror the three professor-supplied sample JSONs.
    Covers the float coercion bug, multi-step dependency graphs, empty step
    configs, and the upload step that depends only on _RECORDING_.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = "/pipeline-factory/pipelines/"

    # ── Full 6-step pipeline (176fo.json structure) ───────────────────────

    def test_full_pipeline_with_analyzer_returns_201(self):
        response = self.client.post(self.url, FULL_PIPELINE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 201)

    def test_full_pipeline_creates_six_steps(self):
        data = self.client.post(self.url, FULL_PIPELINE_PAYLOAD, format="json").json()
        self.assertEqual(data["step_count"], 6)

    def test_upload_step_depends_only_on_recording_placeholder(self):
        """
        The upload step in the sample JSONs depends only on _RECORDING_, not on any
        processing step. Its dependency must remain as _RECORDING_ (not the recording hash,
        since that isn't known at pipeline-creation time).
        """
        steps = self.client.post(self.url, FULL_PIPELINE_PAYLOAD, format="json").json()["steps"]
        upload = next(s for s in steps if s["function"] == "upload")
        self.assertEqual(upload["depends_on"], ["_RECORDING_"])

    def test_export2matlab_depends_on_four_prior_steps(self):
        """export2matlab in the sample config depends on pp, so, an, and ph."""
        steps = self.client.post(self.url, FULL_PIPELINE_PAYLOAD, format="json").json()["steps"]
        export = next(s for s in steps if s["function"] == "export2matlab")
        self.assertEqual(len(export["depends_on"]), 4)

    # ── Empty step config (initial-176fo.json structure) ─────────────────

    def test_initial_pipeline_with_empty_phy_export_config_returns_201(self):
        response = self.client.post(self.url, INITIAL_PIPELINE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 201)

    def test_empty_step_config_is_stored_and_retrievable(self):
        self.client.post(self.url, INITIAL_PIPELINE_PAYLOAD, format="json")
        # phy_export was stored with an empty dict; it must exist with that config
        self.assertTrue(
            StepConfig.objects.filter(function="phy_export", config_block={}).exists()
        )

    # ── Local median referencing preprocessing (165.json structure) ───────

    def test_pipeline_with_local_referencing_returns_201(self):
        response = self.client.post(self.url, PIPELINE_WITH_REFERENCING_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 201)

    def test_referencing_config_is_stored_correctly(self):
        self.client.post(self.url, PIPELINE_WITH_REFERENCING_PAYLOAD, format="json")
        step = StepConfig.objects.get(function="preprocessing")
        self.assertIn("referensing", step.config_block)
        self.assertEqual(step.config_block["referensing"]["operator"], "median")

    # ── Float coercion round-trip ─────────────────────────────────────────

    def test_integer_window_ms_stored_as_float(self):
        """
        Regression test for the JS float→int bug.
        Uploading window_ms: 500 (int) must be stored as 500.0 (float) so the
        worker sanity check (requires <class 'float'>) does not reject it.
        """
        payload = {
            "description": "Int float regression",
            "job_steps": [
                {"function": "analyzer", "identifier": "an001", "depends": ["_RECORDING_"]},
            ],
            "an001": {
                "metrics": {
                    "correlograms": {
                        "window_ms": 500,   # int — simulates JS JSON.stringify(500.0)
                        "bin_ms": 1,        # int
                        "method": "auto",
                    },
                    "isi_histograms": {
                        "window_ms": 500,   # int
                        "bin_ms": 1,        # int
                        "method": "auto",
                    },
                    "waveforms": {"ms_before": 1, "ms_after": 2},  # ints
                }
            },
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201)

        step = StepConfig.objects.get(function="analyzer")
        correlograms = step.config_block["metrics"]["correlograms"]
        isi = step.config_block["metrics"]["isi_histograms"]
        waveforms = step.config_block["metrics"]["waveforms"]

        self.assertIsInstance(correlograms["window_ms"], float, "window_ms must be float after coercion")
        self.assertIsInstance(correlograms["bin_ms"], float, "bin_ms must be float after coercion")
        self.assertIsInstance(isi["window_ms"], float)
        self.assertIsInstance(isi["bin_ms"], float)
        self.assertIsInstance(waveforms["ms_before"], float)
        self.assertIsInstance(waveforms["ms_after"], float)

        self.assertEqual(correlograms["window_ms"], 500.0)
        self.assertEqual(correlograms["bin_ms"], 1.0)

    def test_float_values_survive_round_trip_unchanged(self):
        """Float values already correctly typed must not be corrupted by coercion."""
        payload = {
            "description": "Float round-trip",
            "job_steps": [
                {"function": "analyzer", "identifier": "an001", "depends": []},
            ],
            "an001": {
                "metrics": {
                    "correlograms": {"window_ms": 500.0, "bin_ms": 1.0, "method": "auto"},
                    "waveforms": {"ms_before": 1.5, "ms_after": 2.5},
                }
            },
        }
        self.client.post(self.url, payload, format="json")
        step = StepConfig.objects.get(function="analyzer")
        self.assertEqual(step.config_block["metrics"]["correlograms"]["window_ms"], 500.0)
        self.assertEqual(step.config_block["metrics"]["waveforms"]["ms_before"], 1.5)

    def test_isi_threshold_ms_coerced_at_upload(self):
        """isi_threshold_ms lives 4 levels deep — regression for recursive coercion."""
        payload = {
            "description": "ISI threshold regression",
            "job_steps": [
                {"function": "analyzer", "identifier": "an001", "depends": []},
            ],
            "an001": {
                "metrics": {
                    "quality_metrics": {
                        "qm_params": {
                            "isi_violation": {"isi_threshold_ms": 2}  # int
                        }
                    }
                }
            },
        }
        self.client.post(self.url, payload, format="json")
        step = StepConfig.objects.get(function="analyzer")
        isi_ms = step.config_block["metrics"]["quality_metrics"]["qm_params"]["isi_violation"]["isi_threshold_ms"]
        self.assertIsInstance(isi_ms, float)
        self.assertEqual(isi_ms, 2.0)

    def test_integer_sorting_params_are_not_coerced(self):
        """
        HDSort parameters like max_el_per_group and n_pc_dims are genuinely ints.
        Coercion must not change them to floats.
        """
        payload = {
            "description": "Sorting int params",
            "job_steps": [
                {"function": "sorting", "identifier": "so001", "depends": []},
            ],
            "so001": {
                "name": "hdsort",
                "parameters": {
                    "max_el_per_group": 6,
                    "min_el_per_group": 2,
                    "n_pc_dims": 2,
                    "freq_min": 50,
                    "freq_max": 10000,
                    "detect_threshold": 3.794935952354302,
                },
            },
        }
        self.client.post(self.url, payload, format="json")
        step = StepConfig.objects.get(function="sorting")
        params = step.config_block["parameters"]
        self.assertIsInstance(params["max_el_per_group"], int)
        self.assertIsInstance(params["min_el_per_group"], int)
        self.assertIsInstance(params["n_pc_dims"], int)
        self.assertIsInstance(params["freq_min"], int)
        self.assertIsInstance(params["freq_max"], int)
        self.assertIsInstance(params["detect_threshold"], float)


class PipelineStepViewSetTests(APITestCase):
    """Tests for GET /pipeline-factory/pipeline-steps/."""

    def setUp(self):
        self.user = User.objects.create_user(username="researcher", password="pass")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_pipeline_steps_returns_200(self):
        response = self.client.get("/pipeline-factory/pipeline-steps/")
        self.assertEqual(response.status_code, 200)
