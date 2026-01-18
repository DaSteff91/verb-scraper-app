"""
Main routes (Controller) for the Verb Scraper application.

This module handles the UI requests for scraping verbs and displaying
results from the database.
"""

import logging
import io
from typing import Union, List, cast, Any
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    send_file,
    jsonify,
)
from werkzeug.wrappers import Response as WerkzeugResponse

from src.models.verb import Conjugation, Tense, Verb, Mode
from src.services.validator import InputValidator

# Define the blueprint
main_bp: Blueprint = Blueprint("main", __name__)

# CORRECTED LINE: Use '=' for assignment, not ':'
logger = logging.getLogger(__name__)


@main_bp.route("/", methods=["GET", "POST"])
def index() -> Union[str, WerkzeugResponse]:
    """
    Handle the main dashboard and scraping form.

    This route displays the search form on GET requests and processes
    scraping requests on POST requests.

    Returns:
        Union[str, Response]: The rendered HTML template or a redirect response.
    """
    if request.method == "POST":
        # 1. Extract raw form data
        verb_raw: str = request.form.get("verb", "").strip()
        mode: str = request.form.get("mode", "Indicativo")
        tense: str = request.form.get("tense", "Presente")
        custom_filename: str = request.form.get("filename", "").strip()

        # 2. Validate Input
        if not InputValidator.is_valid_verb(verb_raw):
            flash("Invalid verb format. Please use only letters and hyphens.", "danger")
            return render_template("index.html")

        if not InputValidator.is_valid_grammar(mode, tense):
            flash("Invalid grammatical selection detected.", "danger")
            return render_template("index.html")

        # 3. Sanitize and prepare
        verb_infinitive: str = verb_raw.lower()

        # 4. Lazy Import and Scrape
        from src.services.verb_manager import VerbManager

        manager: VerbManager = VerbManager()
        success: bool = manager.get_or_create_verb_data(verb_infinitive, mode, tense)

        if success:
            logger.info("Successfully processed verb: %s", verb_infinitive)

            # 5. Determine filename for the redirect
            filename = (
                custom_filename if custom_filename else f"{verb_infinitive}_export"
            )

            return redirect(
                url_for(
                    "main.results",
                    verb_infinitive=verb_infinitive,
                    mode=mode,
                    tense=tense,
                    filename=filename,
                )
            )

        logger.warning("Failed to process verb: %s", verb_infinitive)
        flash(f"Could not find or scrape the verb '{verb_infinitive}'", "danger")

    return render_template("index.html")


@main_bp.route("/results/<verb_infinitive>")
def results(verb_infinitive: str) -> str:
    """
    Display the conjugations for a specific verb.

    Args:
        verb_infinitive: The infinitive form of the verb to look up.

    Returns:
        str: The rendered results HTML template.
    """
    mode_name: str = request.args.get("mode", "Indicativo")
    tense_name: str = request.args.get("tense", "Presente")

    verb: Verb = Verb.query.filter_by(infinitive=verb_infinitive).first_or_404()  # type: ignore
    # Extract context from the first result found for display
    display_conjugations: List[Conjugation] = (
        Conjugation.query.join(Tense)
        .join(Mode)
        .filter(
            Conjugation.verb_id == verb.id,
            Tense.name == tense_name,
            Mode.name == mode_name,  # type: ignore
        )
        .all()
    )  # type: ignore

    filename: str = request.args.get("filename", f"{verb_infinitive}_export")

    return render_template(
        "results.html",
        verb=verb,
        conjugations=display_conjugations,
        mode=mode_name,
        tense=tense_name,
        filename=filename,
    )


@main_bp.route("/export/<verb_infinitive>")
def export_csv(verb_infinitive: str) -> Union[str, WerkzeugResponse]:
    """
    Generate and serve a CSV file for the requested verb.

    Args:
        verb_infinitive: The infinitive of the verb to be exported.

    Returns:
        Union[str, WerkzeugResponse]: A downloadable CSV file response
                                      or a redirect on error.
    """
    # 1. Extract and type query parameters
    mode_name: str = request.args.get("mode", "Indicativo")
    tense_name: str = request.args.get("tense", "Presente")
    skip_tu_vos: bool = request.args.get("skip_tu_vos") == "true"

    # 2. Fetch Verb and specific Conjugations
    verb: Verb = Verb.query.filter_by(infinitive=verb_infinitive).first_or_404()  # type: ignore

    conjugations: List[Conjugation] = (
        Conjugation.query.join(Tense)
        .join(Mode)
        .filter(
            Conjugation.verb_id == verb.id,
            Tense.name == tense_name,
            Mode.name == mode_name,
        )
        .all()
    )  # type: ignore

    if not conjugations:
        logger.warning("Export requested for %s with no DB data.", verb_infinitive)
        flash("No data available to export. Please scrape first.", "warning")
        return redirect(
            url_for(
                "main.results",
                verb_infinitive=verb_infinitive,
                mode=mode_name,
                tense=tense_name,
            )
        )

    custom_filename: str = request.args.get("filename", "")

    # Lazy Import of Exporter logic
    from src.services.exporter import AnkiExporter

    # 3. Generate CSV content via Service
    csv_content: str = AnkiExporter.generate_verb_csv(
        conjugations, verb_infinitive, mode_name, tense_name, skip_tu_vos
    )

    # 4. Prepare in-memory binary stream for Flask
    mem_file: io.BytesIO = io.BytesIO()
    mem_file.write(csv_content.encode("utf-8-sig"))
    mem_file.seek(0)

    # Generate sanitized filename
    if custom_filename:
        filename = f"{custom_filename}.csv"
    else:
        filename = f"{verb_infinitive}_{mode_name}_{tense_name}.csv"

    filename = filename.lower().replace(" ", "_")

    return send_file(
        mem_file, mimetype="text/csv", as_attachment=True, download_name=filename
    )


@main_bp.route("/batch-scrape", methods=["POST"])
def batch_scrape() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
    """
    Handle the JSON payload for multi-scraping tasks.

    This endpoint receives a list of verbs and grammatical combinations from
    the frontend "basket". It validates the integrity of the entire batch
    before triggering the background scraping process.

    Returns:
        WerkzeugResponse: A JSON response containing a success status and
            redirect URL, or a 400 error if validation fails.
    """
    # Cast the JSON payload to a dictionary so Pylance understands 'get'
    raw_data: Any = request.get_json()
    data = cast(dict[str, Any], raw_data)

    if not data or "tasks" not in data:
        return jsonify({"error": "No tasks provided"}), 400

    # Explicitly type the extracted variables
    tasks = cast(list[dict[str, str]], data.get("tasks", []))
    filename = cast(str, data.get("filename", "batch_export"))

    # Lazy import remains inside for memory optimization
    from src.services.validator import InputValidator

    if not InputValidator.validate_batch(tasks):
        logger.warning("Batch validation failed for input: %s", data)
        return jsonify({"error": "One or more tasks contain invalid data"}), 400

    logger.info(
        "Batch request accepted: %d tasks for filename: %s", len(tasks), filename
    )

    # Note: Phase 3 will implement the Scraper Service orchestration here.

    # Redirect to index temporarily until the unified results page is ready
    return jsonify(
        {
            "status": "success",
            "redirect_url": url_for(
                "main.results_batch", tasks=json.dumps(tasks), filename=filename
            ),
        }
    )


# 2. Add the New Route
@main_bp.route("/results-batch")
def results_batch() -> str:
    """Displays a summary of multiple scraped verbs."""
    import json

    tasks_raw = request.args.get("tasks", "[]")
    filename = request.args.get("filename", "batch_export")
    tasks = json.loads(tasks_raw)

    batch_display = []
    for t in tasks:
        verb = Verb.query.filter_by(infinitive=t["verb"]).first()
        if not verb:
            continue

        conjs = (
            Conjugation.query.join(Tense)
            .join(Mode)
            .filter(
                Conjugation.verb_id == verb.id,
                Tense.name == t["tense"],
                Mode.name == t["mode"],
            )
            .all()
        )

        batch_display.append(
            {
                "verb": verb.infinitive,
                "mode": t["mode"],
                "tense": t["tense"],
                "conjugations": conjs,
            }
        )

    return render_template(
        "results_batch.html",
        batch=batch_display,
        filename=filename,
        # We pass tasks back so the "Download" button knows what to include
        tasks_json=tasks_raw,
    )
