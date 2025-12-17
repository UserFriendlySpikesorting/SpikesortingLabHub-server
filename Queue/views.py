import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpRequest
from django.contrib.auth import authenticate
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Job, JobStep, StepConfig, get_next_job_id
from .serializers import JobSerializer


class JobViewSet(viewsets.ModelViewSet):
    """
    REST API ViewSet for Job management.
    Provides CRUD operations for Job objects.
    """

    queryset = Job.objects.all().order_by("-created_at")
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]


def get_job() -> dict:
    """Fetch next job with all steps and configurations"""
    job_to_process = get_next_job_id()
    if job_to_process is None:
        return {}
    job_data = {
        "version": "0.4.1",
        "si": "0.101.0",
    }
    job_data["job_id"] = str(job_to_process.job_id)
    job_data["job_evn"] = job_to_process.job_env_config

    job_steps = job_to_process.jobstep_set.all()
    job_data["job_steps"] = [
        {
            "function": step.function,
            "identifier": step.identifier,
            "depends": step.depends_on,
        }
        for step in job_steps
    ]
    for step in job_steps:
        job_data[step.identifier] = step.config_block_hash.config_block
    return job_data


def update_job_status(data: dict) -> JsonResponse:
    """Updates job or job step status based on provided data."""
    job_id = data.get("job_id", None)
    step_id = data.get("step_id", None)
    status = data.get("status", None)

    if job_id is None or status is None:
        return JsonResponse({"error": "Job ID and status are required."}, status=400)

    if step_id:
        job_step = get_object_or_404(JobStep, identifier=step_id, job__job_id=job_id)
        job_step.status = status
        job_step.save()
        return JsonResponse(
            {"message": f"Job step {step_id} status updated to {status}."}
        )
    else:
        job = get_object_or_404(Job, job_id=job_id)
        job.status = status
        job.save()
        return JsonResponse({"message": f"Job {job_id} status updated to {status}."})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def get_next_job(request: HttpRequest):
    """
    Worker API Endpoint - Get next job and update job/step status.

    GET: Fetch the next pending job for the worker
    POST: Update job or job step status
    """
    if request.method == "GET":
        try:
            job_data = get_job()
            return JsonResponse(job_data, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            return update_job_status(data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


def job_list(request):
    """Renders a page listing all jobs, ordered by creation date (newest first)."""
    jobs = Job.objects.all().order_by("-created_at")
    job_steps = (
        JobStep.objects.all()
        .select_related("job", "config_block_hash")
        .order_by("job__created_at", "id")
    )
    context = {"jobs": jobs, "job_steps": job_steps}
    return render(request, "Queue/job_list.html", context)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """
    Authenticate user with username and password.
    Returns token and user info on success.
    """
    from rest_framework.authtoken.models import Token

    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return JsonResponse(
            {"detail": "Username and password are required."},
            status=400,
        )

    user = authenticate(username=username, password=password)
    if user is None:
        return JsonResponse(
            {"detail": "Invalid credentials."},
            status=401,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return JsonResponse(
        {
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
        },
        status=200,
    )
