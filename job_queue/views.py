import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpRequest
from django.contrib.auth import authenticate
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Job, JobStep, StepConfig, get_next_job_id
from .serializers import JobSerializer, JobListSerializer


# ============================================================================
# API ViewSet for Jobs
# ============================================================================


class JobViewSet(viewsets.ModelViewSet):
    """
    REST API ViewSet for Job management.
    Provides CRUD operations for Job objects.
    """

    queryset = Job.objects.all().order_by("-created_at")
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]


# ============================================================================
# Cancel / Resume Endpoints
# ============================================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_job(request: HttpRequest):
    """
    POST: Cancel a pending job.
    Body: { "job_id": "..." }
    Only jobs with status='pending' can be canceled.
    """
    job_id = request.data.get("job_id")
    if not job_id:
        return JsonResponse({"error": "job_id is required."}, status=400)
    job = get_object_or_404(Job, job_id=job_id)
    if job.status != "pending":
        return JsonResponse(
            {"error": f"Only pending jobs can be canceled. Current status: {job.status}."},
            status=400,
        )
    job.status = "canceled"
    job.save()
    return JsonResponse({"message": f"Job {job_id} has been canceled."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resume_job(request: HttpRequest):
    """
    POST: Resume a canceled job by resetting it to pending.
    Body: { "job_id": "..." }
    Only jobs with status='canceled' can be resumed.
    """
    job_id = request.data.get("job_id")
    if not job_id:
        return JsonResponse({"error": "job_id is required."}, status=400)
    job = get_object_or_404(Job, job_id=job_id)
    if job.status != "canceled":
        return JsonResponse(
            {"error": f"Only canceled jobs can be resumed. Current status: {job.status}."},
            status=400,
        )
    job.status = "pending"
    job.save()
    return JsonResponse({"message": f"Job {job_id} has been resumed."})


# ============================================================================
# Worker API Endpoints
# ============================================================================


# Endpoint: update_status (POST only)
# Dedicated endpoint for the worker to report job/step status changes
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_status(request: HttpRequest):
    """
    Worker API Endpoint - Update job or job step status.

    POST: { "job_id": "...", "status": "...", "step_id": "..." (optional) }
    """
    return next_job_post_logic(request)


def get_job() -> dict:
    job_to_process = get_next_job_id()
    if job_to_process is None:
        return {}
    job_data = {
        "version": "0.4.1",  # Added version aug27
        "si": "0.101.0",  # Added si aug27
    }
    job_data["job_id"] = str(job_to_process.job_id)
    job_data["job_evn"] = job_to_process.job_env_config  # Use "job_evn" to match spec

    job_steps = job_to_process.jobstep_set.all()
    job_data["job_steps"] = [
        {
            "function": step.function,
            "identifier": step.identifier,
            "depends": step.depends_on,  # Use "depends" to match spec
        }
        for step in job_steps
    ]
    for step in job_steps:
        job_data[step.identifier] = step.config_block_hash.config_block
    return job_data


def update_job_status(data: dict) -> JsonResponse:
    """
    Updates job or job step status based on provided data.

    Args:
        data: Dictionary containing job_id, optional step_id, and status

    Returns:
        JsonResponse: Success or error message
    """
    job_id = data.get("job_id", None)
    step_id = data.get("step_id", None)
    status = data.get("status", None)

    if job_id is None or status is None:
        return JsonResponse({"error": "Job ID and status are required."}, status=400)

    if step_id:
        # Update a specific job step - use identifier field, not id field
        job_step = get_object_or_404(JobStep, identifier=step_id, job__job_id=job_id)
        job_step.status = status
        job_step.save()

        # Cascade step failure to the parent job
        if status == "failed":
            job = get_object_or_404(Job, job_id=job_id)
            job.status = "failed"
            job.save()

        return JsonResponse(
            {"message": f"Job step {step_id} status updated to {status}."}
        )
    else:
        # Update the main job
        job = get_object_or_404(Job, job_id=job_id)
        job.status = status
        job.save()
        return JsonResponse({"message": f"Job {job_id} status updated to {status}."})


# ============================================================================
# Worker API Endpoints - Helper Functions
# ============================================================================


def next_job_get_logic() -> JsonResponse:
    """
    GET handler for worker job assignment.
    Fetches the next pending job and returns its details.

    Returns:
        JsonResponse: Job data with all steps and configurations, or empty dict if none available
    """
    # try:
    #     job_data = get_job()
    #     return JsonResponse(job_data, status=200)
    # except Exception as e:
    #     return JsonResponse({"error": str(e)}, status=500)
    try:
        job_data = get_job()
        if not job_data:
            return JsonResponse({}, status=204)
        return JsonResponse(job_data, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def next_job_post_logic(request: HttpRequest) -> JsonResponse:
    """
    POST handler for worker job/step status updates.
    Updates job or individual step status based on the request data.

    Args:
        request: HTTP request containing job_id, optional step_id, and status

    Returns:
        JsonResponse: Success or error message
    """
    try:
        data = json.loads(request.body)
        return update_job_status(data)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Endpoint: get_next_job (GET/POST)
# Handles worker requests for job assignments and status updates
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def get_next_job(request: HttpRequest):
    """
    Worker API Endpoint - Get next job and update job/step status.

    GET: Fetch the next pending job for the worker
    POST: Update job or job step status
    """
    if request.method == "GET":
        return next_job_get_logic()
    elif request.method == "POST":
        return next_job_post_logic(request)


# ------------------------------
# View: job_list
# ------------------------------
def job_list(request):
    """
    Renders a page listing all jobs, ordered by creation date (newest first).
    """
    jobs = Job.objects.all().order_by("-created_at")
    job_steps = (
        JobStep.objects.all()
        .select_related("job", "config_block_hash")
        .order_by("job__created_at", "id")
    )
    context = {"jobs": jobs, "job_steps": job_steps}
    return render(request, "job_queue/job_list.html", context)


# ============================================================================
# Authentication Endpoint
# ============================================================================


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


# ============================================================================
# Job List, Detail, Statistics
# ============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_jobs(request):
    """GET: List jobs with optional status filter and limit/offset pagination."""
    status_filter = request.query_params.get("status", None)
    limit = int(request.query_params.get("limit", 100))
    offset = int(request.query_params.get("offset", 0))
    try:
        jobs_query = Job.objects.all().order_by("-created_at")
        if status_filter:
            jobs_query = jobs_query.filter(status=status_filter)
        total_count = jobs_query.count()
        jobs = jobs_query[offset: offset + limit]
        serializer = JobListSerializer(jobs, many=True)
        return Response(
            {"total_count": total_count, "count": len(jobs), "limit": limit, "offset": offset, "jobs": serializer.data},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response({"error": f"Failed to fetch jobs: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def job_detail(request, job_id):
    """GET: Retrieve full details for a specific job."""
    try:
        job = Job.objects.get(job_id=job_id)
        serializer = JobListSerializer(job)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Job.DoesNotExist:
        return Response({"error": f"Job {job_id} not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": f"Failed to fetch job: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def job_statistics(request):
    """GET: Total job count broken down by status."""
    try:
        total_jobs = Job.objects.count()
        status_breakdown = {
            s: Job.objects.filter(status=s).count()
            for s in ["pending", "fetched", "running", "completed", "failed", "canceled"]
        }
        return Response({"total_jobs": total_jobs, "status_breakdown": status_breakdown}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Failed to fetch statistics: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_jobs(request):
    """GET: All jobs as a flat list with optional status filter."""
    try:
        jobs = Job.objects.all().order_by("-created_at")
        status_filter = request.query_params.get("status", None)
        if status_filter:
            jobs = jobs.filter(status=status_filter)
        serializer = JobListSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Failed to retrieve jobs: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# Worker API Endpoints
# ============================================================================
