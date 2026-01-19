"""
API v1 Routes.

Provides JSON endpoints for searching and scraping verbs.
"""

import json
import logging
import threading
from typing import Any, Dict, List, Union, cast

from flask import Blueprint, current_app, jsonify, request, url_for
from werkzeug.wrappers import Response as WerkzeugResponse

from src.extensions import db
from src.models.verb import BatchJob, Conjugation, Mode, Tense, Verb

# Initialize logger
logger = logging.getLogger(__name__)

# Define the Blueprint for versioning
api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@api_bp.route("/verbs/<infinitive>", methods=["GET"])
def get_verb(infinitive: str) -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
    """
    Fetch all scraped data for a specific verb.
    """
    from src.services.auth import require_api_key

    @require_api_key
    def handle_request() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
        logger.info("API GET request for verb: %s", infinitive)
        verb = Verb.query.filter_by(infinitive=infinitive.lower()).first()

        if not verb:
            logger.warning("API GET failed: Verb '%s' not found.", infinitive)
            return jsonify({"error": f"Verb '{infinitive}' not found."}), 404

        result: Dict[str, Any] = {
            "infinitive": verb.infinitive,
            "scraped_at": verb.created_at.isoformat(),
            "conjugations": [],
        }

        for conj in verb.conjugations:
            result["conjugations"].append(
                {
                    "mode": conj.tense.mode.name,
                    "tense": conj.tense.name,
                    "person": conj.person.name,
                    "value": conj.value,
                }
            )

        logger.debug("Successfully serialized verb: %s", infinitive)
        return jsonify(result)

    return handle_request()


@api_bp.route("/scrape", methods=["POST"])
def scrape_verb() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
    """
    Trigger the scraper for a specific verb combination via JSON POST.
    """
    from src.services.auth import require_api_key
    from src.services.validator import InputValidator
    from src.services.verb_manager import VerbManager

    @require_api_key
    def handle_request() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
        data: Any = request.get_json()
        if not isinstance(data, dict):
            logger.error("API POST Scrape: Invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload"}), 400

        verb_raw = str(data.get("verb", "")).strip()
        mode = str(data.get("mode", "Indicativo"))
        tense = str(data.get("tense", "Presente"))

        logger.info("API POST Scrape request: %s (%s %s)", verb_raw, mode, tense)

        if not InputValidator.is_valid_verb(verb_raw):
            logger.warning("API POST Scrape: Invalid verb format '%s'", verb_raw)
            return jsonify({"error": f"Invalid verb format: {verb_raw}"}), 400

        if not InputValidator.is_valid_grammar(mode, tense):
            logger.warning("API POST Scrape: Invalid grammar %s/%s", mode, tense)
            return jsonify({"error": "Invalid grammatical selection"}), 400

        verb_infinitive = verb_raw.lower()
        manager = VerbManager()
        success = manager.get_or_create_verb_data(verb_infinitive, mode, tense)

        if success:
            logger.info("API POST Scrape: Successfully processed %s", verb_infinitive)
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Successfully scraped {verb_infinitive}",
                        "verb": verb_infinitive,
                    }
                ),
                201,
            )

        logger.error("API POST Scrape: Failed to process %s", verb_infinitive)
        return jsonify({"error": f"Failed to scrape verb '{verb_infinitive}'"}), 500

    return handle_request()


@api_bp.route("/batch", methods=["POST"])
def batch_scrape_api() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
    """
    Trigger parallel scraping for a list of verb combinations.

    Accepts JSON: {"tasks": [{"verb": "...", "mode": "...", "tense": "..."}, ...]}
    Returns a Job ID for asynchronous tracking (Status 202 Accepted).
    """
    from src.services.auth import require_api_key
    from src.services.validator import InputValidator
    from src.services.verb_manager import VerbManager

    @require_api_key
    def handle_request() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
        json_data: Any = request.get_json()
        if not isinstance(json_data, dict):
            logger.error("API Batch: Invalid JSON format.")
            return jsonify({"error": "Invalid JSON format"}), 400

        tasks_raw: Any = json_data.get("tasks")
        if not isinstance(tasks_raw, list):
            logger.error("API Batch: No tasks list provided.")
            return jsonify({"error": "No tasks list provided"}), 400

        tasks: List[Dict[str, str]] = cast(List[Dict[str, str]], tasks_raw)

        if not InputValidator.validate_batch(tasks):
            logger.warning("API Batch: Validation failed for task list.")
            return jsonify({"error": "Batch contains invalid data"}), 400

        # --- ASYNCHRONOUS ENGINE: Create Job Record ---
        new_job = BatchJob(total_tasks=len(tasks), status="pending")
        db.session.add(new_job)
        db.session.commit()

        job_id = new_job.id
        logger.info("Created Background Job [%s] for %d tasks.", job_id, len(tasks))

        # We grab the actual app object to pass to the background thread
        app_instance = current_app._get_current_object()  # type: ignore

        def run_background_scrape(
            app_obj: Any, task_list: List[Dict[str, str]], j_id: str
        ) -> None:
            """Wrapper to run the batch process inside an app context."""
            with app_obj.app_context():
                manager = VerbManager()
                manager.process_batch(task_list, job_id=j_id)

        # Launch the sidekick side-by-side
        thread = threading.Thread(
            target=run_background_scrape, args=(app_instance, tasks, job_id)
        )
        thread.start()

        # Return 202 Accepted immediately with the Pager (Job ID)
        return jsonify(
            {
                "status": "accepted",
                "job_id": job_id,
                "check_status_url": url_for("api_v1.get_batch_status", job_id=job_id),
                "message": f"Scraping {len(tasks)} verbs in the background.",
            }
        ), 202

    return handle_request()


@api_bp.route("/batch/<job_id>", methods=["GET"])
def get_batch_status(
    job_id: str,
) -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
    """
    Check the status of an asynchronous batch job.
    """
    from src.services.auth import require_api_key

    @require_api_key
    def handle_request() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
        logger.debug("Checking status for Job [%s]", job_id)
        job = BatchJob.query.get(job_id)

        if not job:
            logger.warning("Status check failed: Job [%s] not found.", job_id)
            return jsonify({"error": "Job not found"}), 404

        return jsonify(job.to_dict()), 200

    return handle_request()
