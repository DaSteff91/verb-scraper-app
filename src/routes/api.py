"""
API v1 Routes.

Provides JSON endpoints for searching and scraping verbs.
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Union, cast

from flask import Blueprint, current_app, jsonify, request, url_for
from werkzeug.exceptions import HTTPException
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
    Fetch scraped data for a specific verb, with optional filtering and dialect support.

    Supports query parameters:
    - mode: Filter by grammatical mode.
    - tense: Filter by grammatical tense.
    - dialect: 'br' (default, skips tu/vós) or 'pt' (includes all).
    - anki: 'true' to include a CSV-styled string in the response.
    """
    from src.services.auth import require_api_key

    @require_api_key
    def handle_request() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
        # 1. Capture parameters
        filter_mode: Optional[str] = request.args.get("mode")
        filter_tense: Optional[str] = request.args.get("tense")
        dialect: str = request.args.get("dialect", "br").lower()
        include_anki: bool = request.args.get("anki", "false").lower() == "true"

        # Determine skip logic (Brazilian by default)
        skip_tu_vos: bool = dialect == "br"

        logger.info(
            "API GET request: %s (Dialect: %s, Anki: %s)",
            infinitive,
            dialect,
            include_anki,
        )

        verb = cast(
            Optional[Verb], Verb.query.filter_by(infinitive=infinitive.lower()).first()
        )

        if not verb:
            logger.warning("API GET failed: Verb '%s' not found.", infinitive)
            return jsonify({"error": f"Verb '{infinitive}' not found."}), 404

        # 2. Prepare base result
        result: Dict[str, Any] = {
            "infinitive": str(verb.infinitive),
            "scraped_at": verb.created_at.isoformat(),
            "dialect": "Brazilian (no tu/vós)"
            if skip_tu_vos
            else "European (standard)",
            "filters_applied": {"mode": filter_mode, "tense": filter_tense},
            "conjugations": [],
        }

        # 3. Filter and gather conjugations
        filtered_conjs: List[Conjugation] = []
        for conj in cast(List[Conjugation], verb.conjugations):
            m_name: str = str(conj.tense.mode.name)
            t_name: str = str(conj.tense.name)
            p_name: str = str(conj.person.name)

            # Apply Mode/Tense filters
            if filter_mode and m_name.lower() != filter_mode.lower():
                continue
            if filter_tense and t_name.lower() != filter_tense.lower():
                continue

            # Apply Dialect filter
            if skip_tu_vos and p_name in ["tu", "vós"]:
                continue

            filtered_conjs.append(conj)
            result["conjugations"].append(
                {
                    "mode": m_name,
                    "tense": t_name,
                    "person": p_name,
                    "value": str(conj.value),
                }
            )

        # 4. Generate Anki Alternate Representation if requested
        if include_anki and filtered_conjs:
            from src.services.exporter import AnkiExporter

            m_ctx = filter_mode if filter_mode else "Mixed"
            t_ctx = filter_tense if filter_tense else "Selection"

            anki_str = AnkiExporter.generate_verb_csv(
                filtered_conjs,
                str(verb.infinitive),
                m_ctx,
                t_ctx,
                skip_tu_vos=False,
            )
            result["anki_string"] = anki_str.strip()
            logger.debug("Generated Anki string for verb: %s", infinitive)

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

        job_id = str(new_job.id)
        logger.info("Created Background Job [%s] for %d tasks.", job_id, len(tasks))

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


@api_bp.app_errorhandler(Exception)
def handle_api_exception(e: Exception) -> tuple[WerkzeugResponse, int]:
    """
    Global error handler for all exceptions occurring within the API blueprint.

    Ensures that even internal server errors return a valid JSON object
    instead of the default HTML error pages.
    """
    # 1. Handle standard Flask/HTTP errors (404, 405, etc.)
    if isinstance(e, HTTPException):
        response = jsonify(
            {"error": e.name, "message": e.description, "status_code": e.code}
        )
        return response, cast(int, e.code)

    # 2. Handle unexpected Python crashes (500 errors)
    logger.exception("Unexpected API error occurred: %s", str(e))

    response = jsonify(
        {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server.",
            "status_code": 500,
        }
    )
    return response, 500
