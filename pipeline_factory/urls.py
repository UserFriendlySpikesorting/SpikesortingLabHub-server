from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PipelineViewSet, PipelineStepViewSet

router = DefaultRouter()
router.register(r"pipelines", PipelineViewSet, basename="pipeline")
router.register(r"pipeline-steps", PipelineStepViewSet, basename="pipelinestep")

urlpatterns = [
    path("", include(router.urls)),
]
