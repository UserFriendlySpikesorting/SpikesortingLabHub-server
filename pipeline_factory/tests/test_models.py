from django.test import TestCase

from pipeline_factory.models import Pipeline, PipelineStep
from job_queue.models import get_or_create_step_configs


# ============================================================================
# Pipeline model
# ============================================================================


class PipelineModelTests(TestCase):
    """Tests for the Pipeline model — str, ordering, and field behaviour."""

    def test_str_contains_pipeline_id_and_description(self):
        pipeline = Pipeline.objects.create(description="Test pipeline")
        result = str(pipeline)
        self.assertIn(str(pipeline.pipeline_id), result)
        self.assertIn("Test pipeline", result)

    def test_str_truncates_long_description_to_50_chars(self):
        pipeline = Pipeline.objects.create(description="x" * 100)
        # __str__ format: "Pipeline <id>: <desc[:50]>" — description part must be ≤ 50 chars
        description_part = str(pipeline).split(": ", 1)[1]
        self.assertLessEqual(len(description_part), 50)

    def test_default_ordering_returns_newest_first(self):
        p1 = Pipeline.objects.create(description="First")
        p2 = Pipeline.objects.create(description="Second")
        pipelines = list(Pipeline.objects.all())
        self.assertEqual(pipelines[0].pipeline_id, p2.pipeline_id)

    def test_created_at_is_set_automatically(self):
        pipeline = Pipeline.objects.create(description="Test")
        self.assertIsNotNone(pipeline.created_at)


# ============================================================================
# PipelineStep model
# ============================================================================


class PipelineStepModelTests(TestCase):
    """Tests for the PipelineStep model — str, defaults, cascade delete."""

    def setUp(self):
        self.pipeline = Pipeline.objects.create(description="Test pipeline")
        self.config_hash = get_or_create_step_configs("sorting", {"name": "hdsort"})

    def _create_step(self, depends_on=None):
        return PipelineStep.objects.create(
            pipeline=self.pipeline,
            config_block_hash_id=self.config_hash,
            depends_on=depends_on or [],
        )

    def test_str_contains_step_id_and_hash(self):
        step = self._create_step()
        result = str(step)
        self.assertIn(str(step.pipeline_step_id), result)
        self.assertIn(self.config_hash, result)

    def test_depends_on_defaults_to_empty_list(self):
        step = PipelineStep.objects.create(
            pipeline=self.pipeline,
            config_block_hash_id=self.config_hash,
        )
        self.assertEqual(step.depends_on, [])

    def test_depends_on_stores_and_retrieves_list(self):
        deps = ["hash_a", "hash_b"]
        step = self._create_step(depends_on=deps)
        step.refresh_from_db()
        self.assertEqual(step.depends_on, deps)

    def test_cascade_delete_removes_steps_when_pipeline_deleted(self):
        self._create_step()
        pipeline_id = self.pipeline.pipeline_id
        self.pipeline.delete()
        self.assertEqual(PipelineStep.objects.filter(pipeline_id=pipeline_id).count(), 0)

    def test_multiple_steps_can_belong_to_one_pipeline(self):
        hash2 = get_or_create_step_configs("preprocessing", {"methods": ["bandpass"]})
        self._create_step()
        PipelineStep.objects.create(
            pipeline=self.pipeline,
            config_block_hash_id=hash2,
            depends_on=[self.config_hash],
        )
        self.assertEqual(PipelineStep.objects.filter(pipeline=self.pipeline).count(), 2)
