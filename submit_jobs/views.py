import os
import json
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
from .serializers import CreateSortingJobSerializer, CombineDownsampleSerializer


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


# ============================================================================
# Bit-Volts Lookup Endpoint
# ============================================================================
#
# Reads an Open Ephys `structure.oebin` and reports its bit_volts values so
# the frontend can show them to the user for explicit confirmation. Neither
# the CLI nor the worker ever reads this file themselves — by the time a
# combine/downsample job is submitted, the value has already been reviewed
# and is passed through as an explicit number.


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def read_bit_volts(request):
    """
    GET: Read per-channel bit_volts from a structure.oebin file.
    Query params: path (required, absolute path to a structure.oebin file)
    """
    data_dirs = [d.strip() for d in getattr(settings, "DATA_DIRS", []) if d.strip()]
    requested = request.query_params.get("path", "").strip()

    if not requested:
        return Response({"error": "`path` is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not _is_safe_path(requested, data_dirs):
        return Response({"error": "Path is outside the allowed data directories."}, status=status.HTTP_403_FORBIDDEN)
    if not os.path.isfile(requested):
        return Response({"error": f"Not a file: {requested}"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with open(requested) as fd:
            meta = json.load(fd)
        bit_volts = [ch["bit_volts"] for ch in meta["continuous"][0]["channels"]]
    except (OSError, ValueError, KeyError, IndexError) as e:
        return Response({"error": f"Cannot read bit_volts from {requested}: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"path": requested, "bit_volts": bit_volts})


# ============================================================================
# Combine & Downsample Job Endpoint
# ============================================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def combine_downsample_job(request):
    """
    POST: Create a standalone combine and/or downsample job.

    The caller must say explicitly which step(s) to run and exactly where
    the resulting file(s) should go — nothing here is inferred from the
    input file paths.

    Expected JSON body:
        {
          "input_files":       ["/abs/path/to/recording1/continuous.dat", ...],
          "num_channels":      64,
          "combine":           true,
          "downsample":        true,
          "downsample_factor": 30,                 // required if downsample == true
          "output_folder":     "/mnt/nas/out",
          "output_name":       "session01",
          "bit_volts":         [0.195]                       // optional; caller-confirmed
        }
    """
    serializer = CombineDownsampleSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    vd = serializer.validated_data

    # Paths on the NAS are stored with the $NAS$ prefix so the worker can
    # substitute its own mount point at runtime.
    input_files = [strip_nas_root(p) for p in vd["input_files"]]
    out_dir     = strip_nas_root(vd["output_folder"])

    job_steps    = []
    output_files = []

    if vd["combine"]:
        fname    = f"combined_raw_{vd['output_name']}.dat"
        raw_file = os.path.join(out_dir, fname)
        step_config = {
            "input files":        input_files,
            "number of channels": vd["num_channels"],
            "output file":        raw_file,
        }
        try:
            identifier = get_or_create_step_configs("combine_raw_dat", step_config)
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        job_steps.append({"function": "combine_raw_dat", "identifier": identifier, "depends": []})
        output_files.append({
            "name": fname,
            "path": os.path.join(vd["output_folder"], fname),
            "description": "full-rate int16 binary",
        })

    if vd["downsample"]:
        fname   = f"combined_ds{vd['downsample_factor']}_{vd['output_name']}.h5"
        ds_file = os.path.join(out_dir, fname)
        step_config = {
            "input files":        input_files,
            "number of channels": vd["num_channels"],
            "downsample factor":  vd["downsample_factor"],
            "output file":        ds_file,
        }
        if vd.get("bit_volts"):
            step_config["bit volts"] = vd["bit_volts"]
        try:
            identifier = get_or_create_step_configs("downsample_to_lfp", step_config)
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        job_steps.append({"function": "downsample_to_lfp", "identifier": identifier, "depends": []})
        output_files.append({
            "name": fname,
            "path": os.path.join(vd["output_folder"], fname),
            "description": f"downsampled LFP at {30000 // vd['downsample_factor']} Hz",
        })

    job_env = {
        "base directory": "$LOCAL$/$JOB_ID$",
        "log_level": "DEBUG",
        "REDIRECT": {
            "log": "$NAS$/SORTING_LOGS/$JOB_ID$/run.log",
            "out": "$NAS$/SORTING_LOGS/$JOB_ID$/run.out",
            "err": "$NAS$/SORTING_LOGS/$JOB_ID$/run.err",
        },
    }

    try:
        job = create_a_job(job_env, job_steps)
    except RuntimeError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    operation = " + ".join(
        label for flag, label in [(vd["combine"], "Combine"), (vd["downsample"], "Downsample")] if flag
    )

    return Response(
        {
            "operation":      operation,
            "input_files":    vd["input_files"],
            "output_folder":  vd["output_folder"],
            "output_files":   output_files,
        },
        status=status.HTTP_201_CREATED,
    )
