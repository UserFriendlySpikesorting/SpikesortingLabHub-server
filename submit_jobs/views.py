import os

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from job_queue.models import Job, get_or_create_step_configs, create_a_job
from .models import (
    build_job_steps_from_pipeline,
    resolve_placeholder_dependencies,
    build_job_env_config,
)
from .serializers import CreateSortingJobSerializer


def strip_nas_root(path: str) -> str:
    """
    Convert an absolute server path to a $NAS$-prefixed relative path.
    Paths under NAS_ROOT are stored as $NAS$/<relative> so the worker
    can substitute its own mount prefix at runtime.
    """
    nas_root = getattr(settings, "NAS_ROOT", "").rstrip("/")
    if nas_root and path and path.startswith(nas_root + "/"):
        return "$NAS$/" + path[len(nas_root) + 1:]
    return path


# ============================================================================
# Job Creation Endpoint
# ============================================================================


def create_sorting_job_logic(validated_data: dict) -> Response:
    """
    Orchestrates spike-sorting job creation from a validated wizard payload.
    """
    raw = dict(validated_data["recording"])
    recording = {
        "binfile":            strip_nas_root(raw["binfile"]),
        "sampling rate":      raw["sampling_rate"],
        "number of channels": raw["num_channels"],
        "gain_to_uV":         raw["gain_to_uV"],
        "offset_to_uV":       raw["offset_to_uV"],
        "probe":              strip_nas_root(raw.get("probe", "")),
        "remove":             raw.get("remove_channels", []),
        "bad_channels":       raw.get("bad_channels", []),
    }
    pipeline_id = validated_data["pipeline_id"]
    environment = validated_data["environment"]

    recording_identifier = get_or_create_step_configs("recording", recording)
    job_steps = build_job_steps_from_pipeline(pipeline_id, recording_identifier)
    job_steps = resolve_placeholder_dependencies(job_steps, recording_identifier)
    job_env_config = build_job_env_config(environment)

    try:
        job = create_a_job(job_env_config, job_steps)
    except RuntimeError as e:
        return Response(
            {"error": f"Failed to create job: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "message": "Job created successfully",
            "job_id": str(job.job_id),
            "recording_identifier": recording_identifier,
            "pipeline_steps_count": len(job_steps) - 1,
            "job_steps_count": len(job_steps),
            "status": "pending",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_sorting_job(request):
    """
    POST: Validate wizard payload and create a new sorting Job.
    """
    serializer = CreateSortingJobSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        return create_sorting_job_logic(serializer.validated_data)
    except Exception as e:
        return Response(
            {"error": f"Job creation failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================================
# Server File Browser Endpoint
# ============================================================================

DATA_FILE_EXTENSIONS = {".bin", ".dat", ".data", ".prb", ".json"}


def _is_safe_path(requested_path, allowed_roots):
    requested = os.path.realpath(requested_path)
    return any(
        requested.startswith(os.path.realpath(root.strip()) + os.sep)
        or requested == os.path.realpath(root.strip())
        for root in allowed_roots
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def browse_data_files(request):
    """
    GET: List the immediate contents of a server directory for file browsing.
    Query params: path (optional, defaults to DATA_DIRS roots)
    """
    data_dirs = [d.strip() for d in getattr(settings, "DATA_DIRS", []) if d.strip()]
    requested = request.query_params.get("path", "").strip()

    if not requested:
        roots = [{"name": os.path.basename(d) or d, "path": d} for d in data_dirs]
        return Response({"current_path": None, "parents": [], "dirs": roots, "files": []})

    if not _is_safe_path(requested, data_dirs):
        return Response({"error": "Path is outside the allowed data directories."}, status=status.HTTP_403_FORBIDDEN)

    if not os.path.isdir(requested):
        return Response({"error": f"Not a directory: {requested}"}, status=status.HTTP_400_BAD_REQUEST)

    dirs, files = [], []
    try:
        entries = sorted(os.scandir(requested), key=lambda e: (not e.is_dir(), e.name.lower()))
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                dirs.append({"name": entry.name, "path": entry.path})
            elif entry.is_file(follow_symlinks=False):
                filename_and_ext = os.path.splitext(entry.name)
                if len(filename_and_ext) == 2 and filename_and_ext[1].lower() in DATA_FILE_EXTENSIONS:
                    try:
                        size_mb = round(entry.stat().st_size / (1024 * 1024), 2)
                    except OSError:
                        size_mb = None
                    files.append({"name": entry.name, "path": entry.path, "ext": filename_and_ext[1].lower(), "size_mb": size_mb})
    except PermissionError:
        return Response({"error": f"Permission denied reading {requested}"}, status=status.HTTP_403_FORBIDDEN)

    parents = []
    cursor = os.path.dirname(requested)
    allowed_reals = {os.path.realpath(d) for d in data_dirs}
    while cursor and os.path.realpath(cursor) not in allowed_reals and cursor != os.path.dirname(cursor):
        parents.insert(0, {"name": os.path.basename(cursor) or cursor, "path": cursor})
        cursor = os.path.dirname(cursor)

    return Response({"current_path": requested, "parents": parents, "dirs": dirs, "files": files})
