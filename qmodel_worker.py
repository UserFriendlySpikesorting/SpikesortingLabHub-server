import os
import time
import requests
import urllib3
from datetime import datetime
import json
import logging
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# -----------------------------------------------------------------------------
# 1. Worker Configuration
# -----------------------------------------------------------------------------
# Set BASE_URL to https://localhost:8443 when running Gunicorn with SSL.
# Defaults to plain HTTP for local development with manage.py runserver.
BASE_URL = os.environ.get("LABHUB_BASE_URL", "http://localhost:8000")

# Separate endpoints: one for fetching the next job, one for updating status
API_URL = f"{BASE_URL}/job-queue/next-job/"
UPDATE_STATUS_URL = f"{BASE_URL}/job-queue/update-status/"
POLLING_INTERVAL_SECONDS = 5

# SSL verification.
# - True  (default): verify the server certificate (use for real certs / Let's Encrypt)
# - False           : skip verification (safe for self-signed localhost certs only)
# - "/path/to/cert.pem": path to the CA bundle for a self-signed cert
_ssl_verify_env = os.environ.get("LABHUB_SSL_VERIFY", "true").lower()
if _ssl_verify_env == "false":
    SSL_VERIFY = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
elif _ssl_verify_env == "true":
    SSL_VERIFY = True
else:
    SSL_VERIFY = _ssl_verify_env  # treat as file path to CA bundle

# Security token from the user for API authentication
TOKEN = "7043591ad29f88607f2b109bfba5044eac892785"
HEADERS = {"Authorization": f"Token {TOKEN}"}

print(
    f"Worker started. Polling API at {API_URL} every {POLLING_INTERVAL_SECONDS} seconds..."
)


# -----------------------------------------------------------------------------
# 2. Status Update Function
# -----------------------------------------------------------------------------
def update_the_status(job_id, status, step_id=None):
    """
    Makes an API call to update the status of a job or a specific job step via a POST request.

    Args:
        job_id (str): The ID of the job
        status (str): The new status to set
        step_id (str, optional): The ID of the specific step to update. If None, updates the main job status.
    """
    payload = {"job_id": str(job_id), "status": status}

    # If step_id is provided, include it in the payload to update a specific step
    if step_id is not None:
        payload["step_id"] = str(step_id)

    try:
        # Use the same API_URL for POST requests
        response = requests.post(UPDATE_STATUS_URL, json=payload, headers=HEADERS, verify=SSL_VERIFY)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Log the appropriate success message based on whether we're updating a job or step
        if step_id is not None:
            logging.info(
                f"API call successful: Updated job {job_id}, step {step_id} to '{status}'."
            )
        else:
            logging.info(f"API call successful: Updated job {job_id} to '{status}'.")

    except requests.exceptions.RequestException as e:
        # Log the appropriate error message based on whether we're updating a job or step
        if step_id is not None:
            logging.error(
                f"Failed to update job {job_id}, step {step_id} status to '{status}': {e}"
            )
        else:
            logging.error(f"Failed to update job {job_id} status to '{status}': {e}")


# -----------------------------------------------------------------------------
# 3. Main Worker Loop
# -----------------------------------------------------------------------------
def run_worker():
    """Main function for the worker. It polls an API endpoint for new jobs."""
    while True:
        try:
            # Send a GET request to the API to fetch a pending job
            response = requests.get(API_URL, headers=HEADERS, verify=SSL_VERIFY)

            # Check if the response was successful
            if response.status_code == 200:
                job_data = response.json()
                logging.info(f"Received response: {job_data}")
                # Check if we got actual job data (has job_id) or empty response
                if job_data and "job_id" in job_data:
                    logging.info(f"Processing job: {job_data['job_id']}")
                    process_job(job_data)
                else:
                    logging.info("No pending jobs found. Waiting...")
            else:
                logging.error(f"API returned status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error connecting to the API: {e}")
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON from API response.")
        except Exception as e:
            logging.error(f"An unexpected error occurred in the worker loop: {e}")

        time.sleep(POLLING_INTERVAL_SECONDS)


def process_job(job_data):
    """
    Processes a single job by iterating through its steps.

    Actual API response format:
    {
        "version": "0.4.1",
        "si": "0.101.0",
        "job_id": "...",
        "job_evn": {...},
        "job_steps": [
            {"function": "...", "identifier": "...", "depends": [...]},
            ...
        ],
        "identifier_hash": {...config...}  # Config blocks by identifier
    }
    """
    job_id = job_data.get("job_id")
    job_steps = job_data.get("job_steps", [])

    if not job_id or not job_steps:
        logging.error("Invalid job data - missing job_id or job_steps")
        return

    logging.info(f"Starting to process new job: {job_id}")
    logging.info(f"Version: {job_data.get('version')}, SI: {job_data.get('si')}")
    logging.info(f"Total steps to process: {len(job_steps)}")

    update_the_status(job_id, "running")

    try:
        completed_steps = set()
        num_completed_steps = 0

        for step in job_steps:
            step_identifier = step.get("identifier")
            function_name = step.get("function")
            depends_on = step.get("depends", [])

            if not step_identifier:
                logging.warning(f"Step missing identifier: {step}")
                continue

            # Check dependencies before processing
            logging.info(f"\n{'='*80}")
            logging.info(
                f"Processing step: {function_name} ({step_identifier[:16]}...)"
            )
            logging.info(
                f"Dependencies: {[d[:16] + '...' if len(d) > 16 else d for d in depends_on]}"
            )

            # Wait for all dependencies to complete
            if depends_on:
                missing_deps = [d for d in depends_on if d not in completed_steps]
                if missing_deps:
                    logging.warning(
                        f"Waiting for dependencies: {[d[:16] + '...' for d in missing_deps]}"
                    )
                    # In a real scenario, you'd wait or skip this step
                    # For simulation, we'll just log it

            # Load configuration for this step
            step_config = job_data.get(step_identifier, {})
            logging.info(f"Step config: {str(step_config)[:100]}...")

            # Update step status to running
            update_the_status(job_id, "running", step_identifier)

            # --- Your processing logic would go here ---
            logging.info(f"Executing {function_name}...")
            time.sleep(random.uniform(1, 3))  # Simulate work
            # --- End of processing logic ---

            # Mark step as completed
            update_the_status(job_id, "completed", step_identifier)
            completed_steps.add(step_identifier)
            num_completed_steps += 1
            logging.info(f"✓ Completed step: {function_name}")

        # All steps completed
        if num_completed_steps == len(job_steps):
            update_the_status(job_id, "completed")
            logging.info(f"\n{'='*80}")
            logging.info(f"✓ Job {job_id} finished successfully!")
            logging.info(f"{'='*80}\n")
        else:
            logging.warning(
                f"Only {num_completed_steps}/{len(job_steps)} steps completed"
            )

    except Exception as e:
        update_the_status(job_id, "failed")
        logging.error(f"Job {job_id} failed with an error: {e}", exc_info=True)


if __name__ == "__main__":
    run_worker()
