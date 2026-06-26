from django.test import SimpleTestCase

from pipeline_factory.serializers import _coerce_floats


# ============================================================================
# _coerce_floats()
# ============================================================================


class CoerceFloatsTests(SimpleTestCase):
    """
    Unit tests for _coerce_floats().

    This function fixes a JS float→int precision loss that occurs when the
    browser re-serializes an uploaded JSON file: JSON.stringify(500.0) → "500".
    The worker sanity check requires true float types for timing fields such as
    window_ms and bin_ms, so they must be coerced back before storage.
    """

    # ── Individual field coercion ──────────────────────────────────────────

    def test_window_ms_int_coerced_to_float(self):
        config = {"correlograms": {"window_ms": 500, "bin_ms": 1.0, "method": "auto"}}
        _coerce_floats(config)
        self.assertIsInstance(config["correlograms"]["window_ms"], float)
        self.assertEqual(config["correlograms"]["window_ms"], 500.0)

    def test_bin_ms_int_coerced_to_float(self):
        config = {"correlograms": {"window_ms": 500.0, "bin_ms": 1, "method": "auto"}}
        _coerce_floats(config)
        self.assertIsInstance(config["correlograms"]["bin_ms"], float)
        self.assertEqual(config["correlograms"]["bin_ms"], 1.0)

    def test_ms_before_and_ms_after_coerced(self):
        config = {"waveforms": {"ms_before": 1, "ms_after": 2}}
        _coerce_floats(config)
        self.assertIsInstance(config["waveforms"]["ms_before"], float)
        self.assertIsInstance(config["waveforms"]["ms_after"], float)
        self.assertEqual(config["waveforms"]["ms_before"], 1.0)
        self.assertEqual(config["waveforms"]["ms_after"], 2.0)

    def test_isi_threshold_ms_coerced(self):
        config = {"isi_violation": {"isi_threshold_ms": 2}}
        _coerce_floats(config)
        self.assertIsInstance(config["isi_violation"]["isi_threshold_ms"], float)
        self.assertEqual(config["isi_violation"]["isi_threshold_ms"], 2.0)

    def test_radius_um_coerced(self):
        config = {"spike_retriver_kwargs": {"radius_um": 100}}
        _coerce_floats(config)
        self.assertIsInstance(config["spike_retriver_kwargs"]["radius_um"], float)
        self.assertEqual(config["spike_retriver_kwargs"]["radius_um"], 100.0)

    def test_band_list_elements_coerced_to_float(self):
        config = {"highpass or band filtering": {"btype": "bandpass", "band": [100, 10000]}}
        _coerce_floats(config)
        band = config["highpass or band filtering"]["band"]
        self.assertEqual(band, [100.0, 10000.0])
        self.assertIsInstance(band[0], float)
        self.assertIsInstance(band[1], float)

    # ── Already-correct values survive unchanged ───────────────────────────

    def test_already_float_values_are_unchanged(self):
        config = {"correlograms": {"window_ms": 500.0, "bin_ms": 1.0}}
        _coerce_floats(config)
        self.assertEqual(config["correlograms"]["window_ms"], 500.0)
        self.assertEqual(config["correlograms"]["bin_ms"], 1.0)

    # ── Non-float fields are not touched ──────────────────────────────────

    def test_integer_only_fields_keep_int_type(self):
        """Fields not in _FLOAT_FIELDS (e.g. array sizes, PC dims) stay as ints."""
        config = {"parameters": {"max_el_per_group": 6, "n_pc_dims": 2, "freq_min": 50}}
        _coerce_floats(config)
        self.assertIsInstance(config["parameters"]["max_el_per_group"], int)
        self.assertIsInstance(config["parameters"]["n_pc_dims"], int)
        self.assertIsInstance(config["parameters"]["freq_min"], int)

    def test_string_fields_are_unchanged(self):
        config = {"correlograms": {"window_ms": 500, "method": "auto"}}
        _coerce_floats(config)
        self.assertEqual(config["correlograms"]["method"], "auto")
        self.assertIsInstance(config["correlograms"]["method"], str)

    # ── Recursion and structure ────────────────────────────────────────────

    def test_deeply_nested_fields_are_reached(self):
        """isi_threshold_ms lives 4 levels deep in the analyzer config."""
        config = {
            "metrics": {
                "quality_metrics": {
                    "qm_params": {
                        "isi_violation": {"isi_threshold_ms": 2}
                    }
                }
            }
        }
        _coerce_floats(config)
        isi_ms = config["metrics"]["quality_metrics"]["qm_params"]["isi_violation"]["isi_threshold_ms"]
        self.assertIsInstance(isi_ms, float)
        self.assertEqual(isi_ms, 2.0)

    def test_empty_dict_is_unchanged(self):
        """Empty config (e.g. phy_export: {}) must not raise and must return {}."""
        config = {}
        result = _coerce_floats(config)
        self.assertEqual(result, {})

    def test_returns_same_dict_object(self):
        """Function must mutate and return the same dict, not a copy."""
        config = {"waveforms": {"ms_before": 1}}
        result = _coerce_floats(config)
        self.assertIs(result, config)

    # ── Realistic full-analyzer config ─────────────────────────────────────

    def test_full_analyzer_config_all_float_fields_coerced(self):
        """
        Mirrors the analyzer config from the sample pipeline JSONs, submitted with
        integer float fields as JS would produce. All timing/distance fields must
        become floats while int-only fields (n_components, etc.) stay as ints.
        """
        config = {
            "metrics": {
                "quality_metrics": {
                    "qm_params": {"isi_violation": {"isi_threshold_ms": 2}},
                },
                "waveforms": {"ms_before": 1, "ms_after": 2},
                "spike_locations": {
                    "method": "monopolar_triangulation",
                    "ms_before": 5,
                    "ms_after": 5,
                    "spike_retriver_kwargs": {
                        "channel_from_template": False,
                        "radius_um": 100,
                        "peak_sign": "both",
                    },
                },
                "correlograms": {"window_ms": 500, "bin_ms": 1, "method": "auto"},
                "isi_histograms": {"window_ms": 500, "bin_ms": 1, "method": "auto"},
                "principal_components": {"n_components": 5, "mode": "by_channel_local", "whiten": False},
            }
        }
        _coerce_floats(config)
        m = config["metrics"]

        # All timing fields must be float
        self.assertIsInstance(m["quality_metrics"]["qm_params"]["isi_violation"]["isi_threshold_ms"], float)
        self.assertIsInstance(m["waveforms"]["ms_before"], float)
        self.assertIsInstance(m["waveforms"]["ms_after"], float)
        self.assertIsInstance(m["spike_locations"]["ms_before"], float)
        self.assertIsInstance(m["spike_locations"]["ms_after"], float)
        self.assertIsInstance(m["spike_locations"]["spike_retriver_kwargs"]["radius_um"], float)
        self.assertIsInstance(m["correlograms"]["window_ms"], float)
        self.assertIsInstance(m["correlograms"]["bin_ms"], float)
        self.assertIsInstance(m["isi_histograms"]["window_ms"], float)
        self.assertIsInstance(m["isi_histograms"]["bin_ms"], float)

        # int-only fields must stay as int
        self.assertIsInstance(m["principal_components"]["n_components"], int)

        # Correct values
        self.assertEqual(m["correlograms"]["window_ms"], 500.0)
        self.assertEqual(m["correlograms"]["bin_ms"], 1.0)
        self.assertEqual(m["spike_locations"]["spike_retriver_kwargs"]["radius_um"], 100.0)

    def test_preprocessing_with_local_referencing_config(self):
        """
        Mirrors the 165.json preprocessing config that includes both bandpass filtering
        and local median referencing. local_radius contains ints that should stay ints.
        """
        config = {
            "methods": ["highpass or band filtering", "referensing"],
            "highpass or band filtering": {
                "btype": "bandpass",
                "band": [131, 7891],  # ints — simulating JS float→int on non-round floats
            },
            "referensing": {
                "reference": "local",
                "operator": "median",
                "groups": None,
                "ref_channel_ids": [],
                "local_radius": [385, 861],  # ints — these are not float fields
            },
        }
        _coerce_floats(config)
        self.assertIsInstance(config["highpass or band filtering"]["band"][0], float)
        self.assertIsInstance(config["highpass or band filtering"]["band"][1], float)
        # local_radius is not in _FLOAT_FIELDS — must stay as ints
        self.assertIsInstance(config["referensing"]["local_radius"][0], int)
