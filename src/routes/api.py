"""
API v1 Routes.

Provides JSON endpoints for searching and scraping verbs.
"""

import json
from typing import Any, Dict, List, Union, cast

from flask import Blueprint, jsonify, request, url_for
from werkzeug.wrappers import Response as WerkzeugResponse

from src.models.verb import Conjugation, Mode, Tense, Verb

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
        verb = Verb.query.filter_by(infinitive=infinitive.lower()).first()

        if not verb:
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
            return jsonify({"error": "Invalid JSON payload"}), 400

        verb_raw = str(data.get("verb", "")).strip()
        mode = str(data.get("mode", "Indicativo"))
        tense = str(data.get("tense", "Presente"))

        if not InputValidator.is_valid_verb(verb_raw):
            return jsonify({"error": f"Invalid verb format: {verb_raw}"}), 400

        if not InputValidator.is_valid_grammar(mode, tense):
            return jsonify({"error": "Invalid grammatical selection"}), 400

        verb_infinitive = verb_raw.lower()
        manager = VerbManager()
        success = manager.get_or_create_verb_data(verb_infinitive, mode, tense)

        if success:
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

        return jsonify({"error": f"Failed to scrape verb '{verb_infinitive}'"}), 500

    return handle_request()


@api_bp.route("/batch", methods=["POST"])
def batch_scrape_api() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
    """
    Trigger parallel scraping for a list of verb combinations.

    Accepts JSON: {"tasks": [{"verb": "...", "mode": "...", "tense": "..."}, ...]}
    """
    from src.services.auth import require_api_key
    from src.services.validator import InputValidator
    from src.services.verb_manager import VerbManager

    @require_api_key
    def handle_request() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
        # 1. Capture and verify the JSON object exists
        json_data: Any = request.get_json()
        if not isinstance(json_data, dict):
            return jsonify({"error": "Invalid JSON format"}), 400

        # 2. Extract and type-check 'tasks'
        tasks_raw: Any = json_data.get("tasks")
        if not isinstance(tasks_raw, list):
            return jsonify({"error": "No tasks list provided"}), 400

        # Cast to satisfying strict type checkers
        tasks: List[Dict[str, str]] = cast(List[Dict[str, str]], tasks_raw)

        # 3. Validate batch integrity
        if not InputValidator.validate_batch(tasks):
            return jsonify({"error": "Batch contains invalid data"}), 400

        # 4. Trigger Parallel Execution via the existing VerbManager
        manager = VerbManager()
        summary = manager.process_batch(tasks)

        # 5. Return JSON Summary (Success/Fail counts)
        return jsonify(
            {
                "status": "success",
                "results": summary,
                "message": f"Finished processing {len(tasks)} tasks.",
            }
        ), 200

    return handle_request()
