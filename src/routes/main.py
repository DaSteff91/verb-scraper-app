"""
Main routes (Controller) for the Verb Scraper application.

This module handles the UI requests for scraping verbs and displaying
results from the database.
"""

import io
import os
import json
import logging
from typing import Any, Dict, List, Union, cast
from sqlalchemy import desc

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
    send_from_directory,
    make_response,
    current_app,
)
from werkzeug.wrappers import Response as WerkzeugResponse

from src.models.verb import Conjugation, Mode, Tense, Verb
from src.services.validator import InputValidator

# Define the blueprint
main_bp: Blueprint = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.route("/", methods=["GET", "POST"])
def index() -> Union[str, WerkzeugResponse]:
    """
    Handle the main dashboard and single-verb scraping form.

    Displays the search dashboard on GET requests. On POST requests, it
    sanitizes input, triggers the lazy-loaded scraping service for a
    single verb, and redirects to the individual results page.

    Returns:
        Union[str, WerkzeugResponse]: The rendered index HTML template
            or a redirect to the results view.
    """
    if request.method == "POST":
        # 1. Extract raw form data
        verb_raw: str = request.form.get("verb", "").strip()
        mode: str = request.form.get("mode", "Indicativo")
        tense: str = request.form.get("tense", "Presente")
        custom_filename: str = request.form.get("filename", "").strip()

        # 2. Validate Input
        if not InputValidator.is_valid_verb(verb_raw):
            flash("Invalid verb format. Use letters and hyphens.", "danger")
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
        flash(f"Could not find the verb '{verb_infinitive}'", "danger")

    return render_template("index.html")


@main_bp.route("/favicon.ico")
def favicon() -> WerkzeugResponse:
    """
    Handle the root favicon request made by browsers.
    Serves the icon directly from the static/image directory
    """
    image_dir = os.path.join(cast(str, current_app.static_folder), "image")

    return send_from_directory(
        image_dir, "favicon.ico", mimetype="image/vnd.microsoft.icon"
    )


@main_bp.route("/results/<verb_infinitive>")
def results(verb_infinitive: str) -> str:
    """
    Display the conjugations for a specific verb.

    Fetches the requested verb and its related conjugations from the
    database based on the infinitive and query parameters.

    Args:
        verb_infinitive: The infinitive form of the verb to look up.

    Returns:
        str: The rendered results HTML template.
    """
    mode_name: str = request.args.get("mode", "Indicativo")
    tense_name: str = request.args.get("tense", "Presente")
    filename: str = request.args.get("filename", f"{verb_infinitive}_export")

    verb: Verb = Verb.query.filter_by(infinitive=verb_infinitive).first_or_404()  # type: ignore

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
    Generate and serve a CSV file for a single requested verb.

    Utilizes the lazy-loaded AnkiExporter to transform database records
    into an in-memory CSV string for download.

    Args:
        verb_infinitive: The infinitive of the verb to be exported.

    Returns:
        Union[str, WerkzeugResponse]: A downloadable CSV file response
            or a redirect to results if data is missing.
    """
    mode_name: str = request.args.get("mode", "Indicativo")
    tense_name: str = request.args.get("tense", "Presente")
    skip_tu_vos: bool = request.args.get("skip_tu_vos") == "true"
    custom_filename: str = request.args.get("filename", "")

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
        flash("No data available to export.", "warning")
        return redirect(
            url_for(
                "main.results",
                verb_infinitive=verb_infinitive,
                mode=mode_name,
                tense=tense_name,
            )
        )

    from src.services.exporter import AnkiExporter

    csv_content: str = AnkiExporter.generate_verb_csv(
        conjugations, verb_infinitive, mode_name, tense_name, skip_tu_vos
    )

    mem_file: io.BytesIO = io.BytesIO()
    mem_file.write(csv_content.encode("utf-8-sig"))
    mem_file.seek(0)

    filename = (
        f"{custom_filename}.csv"
        if custom_filename
        else f"{verb_infinitive}_{mode_name}_{tense_name}.csv"
    )
    filename = filename.lower().replace(" ", "_")

    return send_file(
        mem_file,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@main_bp.route("/batch-scrape", methods=["POST"])
def batch_scrape() -> Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]:
    """
    Handle the JSON payload for multi-scraping tasks.

    Receives a list of tasks from the frontend basket, validates the
    entire set, and triggers the threaded parallel orchestrator.

    Returns:
        Union[WerkzeugResponse, tuple[WerkzeugResponse, int]]: A JSON
            response containing the success status and redirect URL.
    """
    json_data: Any = request.get_json()
    if not isinstance(json_data, dict):
        return jsonify({"error": "Invalid JSON format"}), 400

    tasks_raw: Any = json_data.get("tasks")
    if not isinstance(tasks_raw, list):
        return jsonify({"error": "No tasks list provided"}), 400

    tasks: List[Dict[str, str]] = cast(List[Dict[str, str]], tasks_raw)
    filename: str = str(json_data.get("filename", "batch_export"))

    # Validate batch data integrity
    from src.services.validator import InputValidator

    if not InputValidator.validate_batch(tasks):
        logger.warning("Batch validation failed for: %s", tasks)
        return jsonify({"error": "Batch contains invalid data"}), 400

    logger.info("Batch accepted: %d tasks. Orchestrating...", len(tasks))

    # Trigger Parallel Execution
    from src.services.verb_manager import VerbManager

    manager: VerbManager = VerbManager()
    summary: Dict[str, int] = manager.process_batch(tasks)

    success_count = summary.get("success", 0)
    failed_count = summary.get("failed", 0)

    if success_count > 0:
        flash(f"Successfully scraped {success_count} combinations.", "success")
    if failed_count > 0:
        flash(f"Failed to scrape {failed_count} tasks.", "warning")

    return jsonify(
        {
            "status": "success",
            "redirect_url": url_for(
                "main.results_batch", tasks=json.dumps(tasks), filename=filename
            ),
        }
    )


@main_bp.route("/results-batch")
def results_batch() -> str:
    """
    Display a grouped summary of multiple scraped verbs.

    Iterates through the batch tasks to prepare a structured dataset
    for the accordion-style results dashboard.

    Returns:
        str: The rendered batch results HTML template.
    """
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
        tasks_json=tasks_raw,
    )


@main_bp.route("/export-batch")
def export_batch_csv() -> Union[WerkzeugResponse, Any]:
    """
    Generate and serve a single unified CSV containing multiple verbs.

    Aggregates database records for all verbs in the requested batch
    and provides a single, Anki-optimized CSV download.

    Returns:
        Union[WerkzeugResponse, Any]: A downloadable CSV file response
            containing the aggregated batch data.
    """
    tasks_raw = request.args.get("tasks", "[]")
    custom_filename = request.args.get("filename", "batch_export")
    skip_tu_vos = request.args.get("skip_tu_vos") == "true"

    tasks = json.loads(tasks_raw)
    batch_data = []

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

        batch_data.append(
            {
                "verb": verb.infinitive,
                "mode": t["mode"],
                "tense": t["tense"],
                "conjugations": conjs,
            }
        )

    from src.services.exporter import AnkiExporter

    csv_content = AnkiExporter.generate_batch_csv(batch_data, skip_tu_vos)

    mem_file = io.BytesIO()
    mem_file.write(csv_content.encode("utf-8-sig"))
    mem_file.seek(0)

    filename = f"{custom_filename}.csv".lower().replace(" ", "_")
    return send_file(
        mem_file,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@main_bp.route("/robots.txt")
def serve_robots() -> WerkzeugResponse:
    """
    Serve the robots.txt file from the static directory.

    Returns:
        WerkzeugResponse: The plain text robots.txt file.
    """
    return send_from_directory(
        cast(str, current_app.static_folder), "robots.txt", mimetype="text/plain"
    )


@main_bp.route("/sitemap.xml")
def sitemap() -> WerkzeugResponse:
    """
    Generate a capped dynamic sitemap for search engines.
    Limits the query to the 500 most recent verbs to optimize resources.
    """
    # 1. Fetch only the most recent 500 verbs
    verbs = Verb.query.order_by(desc(Verb.created_at)).limit(500).all()

    url_root = request.url_root.rstrip("/")  # Ensure no trailing slash issues

    # 2. Render the XML template
    sitemap_xml = render_template("sitemap.xml", verbs=verbs, url_root=url_root)

    # 3. Explicitly set the application/xml mimetype
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"

    return response
