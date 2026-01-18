"""
Main routes (Controller) for the Verb Scraper application.

This module handles the UI requests for scraping verbs and displaying
results from the database.
"""

import logging
from typing import Union, List

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response as WerkzeugResponse

from src.models.verb import Conjugation, Tense, Verb, Mode
from src.services.verb_manager import VerbManager

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
        # Extract and sanitize form data
        verb_infinitive: str = request.form.get("verb", "").strip().lower()
        mode: str = request.form.get("mode", "Indicativo")
        tense: str = request.form.get("tense", "Presente")

        if verb_infinitive:
            manager = VerbManager()
            success: bool = manager.get_or_create_verb_data(
                verb_infinitive, mode, tense
            )

            if success:
                logger.info("Successfully processed verb: %s", verb_infinitive)
                return redirect(
                    url_for(
                        "main.results",
                        verb_infinitive=verb_infinitive,
                        mode=mode,
                        tense=tense,
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

    return render_template(
        "results.html",
        verb=verb,
        conjugations=display_conjugations,
        mode=mode_name,
        tense=tense_name,
    )
