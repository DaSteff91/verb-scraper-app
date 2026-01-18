"""
Main routes (Controller) for the Verb Scraper application.

This module handles the UI requests for scraping verbs and displaying
results from the database.
"""

import io
import logging
from typing import Any, List, Union, cast

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
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
    Handle the main dashboard and scraping form.
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
    Generate and serve a CSV file for the requested verb.
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
    """
    raw_data: Any = request.get_json()
    data = cast(dict[str, Any], raw_data)

    if not data or "tasks" not in data:
        return jsonify({"error": "No tasks provided"}), 400

    tasks = cast(list[dict[str, str]], data.get("tasks", []))
    filename = cast(str, data.get("filename", "batch_export"))

    # 1. Validate the whole batch
    from src.services.validator import InputValidator

    if not InputValidator.validate_batch(tasks):
        logger.warning("Batch validation failed for input: %s", data)
        return jsonify({"error": "One or more tasks contain invalid data"}), 400

    # 2. Trigger Parallel Execution via VerbManager
    from src.services.verb_manager import VerbManager

    manager: VerbManager = VerbManager()
    summary: dict[str, int] = manager.process_batch(tasks)

    # 3. Provide Feedback
    success_count = summary.get("success", 0)
    if success_count > 0:
        flash(f"Successfully processed {success_count} verbs.", "success")
    if summary.get("failed", 0) > 0:
        flash(f"Failed to process {summary.get('failed')} tasks.", "warning")

    # Redirect to index until the Unified Results Page (Phase 4) is built
    return jsonify(
        {
            "status": "success",
            "message": f"Processed {success_count} tasks",
            "redirect_url": url_for("main.index"),
        }
    )
