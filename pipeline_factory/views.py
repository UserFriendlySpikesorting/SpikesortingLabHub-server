from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from .models import Pipeline, PipelineStep
from .serializers import (
    PipelineSerializer,
    PipelineStepSerializer,
    PipelineCreateSerializer,
)
from job_queue.models import StepConfig


# Shared base viewset for authentication/permission
class AuthenticatedModelViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class PipelineViewSet(AuthenticatedModelViewSet):
    """ViewSet for listing and creating Pipelines."""

    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def create(self, request, *args, **kwargs):
        # Support uploaded JSON that uses the 'job_steps' convention.
        data = request.data

        # Simply pass the data through to the serializer
        # The serializer now handles both 'steps' and 'job_steps' formats
        create_serializer = PipelineCreateSerializer(data=data)
        create_serializer.is_valid(raise_exception=True)
        pipeline = create_serializer.save()
        out_serializer = PipelineSerializer(pipeline)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class PipelineStepViewSet(AuthenticatedModelViewSet):
    """ViewSet for managing pipeline steps"""

    queryset = PipelineStep.objects.all()
    serializer_class = PipelineStepSerializer
