"""
Main routes (Controller) for the Verb Scraper application.

This module handles the UI requests for scraping verbs and displaying
results from the database.
"""

import logging
from typing import Union

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from src.models.verb import Verb
from src.services.verb_manager import VerbManager

# Define the blueprint
main_bp: Blueprint = Blueprint("main", __name__)

# CORRECTED LINE: Use '=' for assignment, not ':'
logger = logging.getLogger(__name__)


@main_bp.route("/", methods=["GET", "POST"])
def index() -> Union[str, Response]:
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
                    url_for("main.results", verb_infinitive=verb_infinitive)
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
    # Query the database for the verb and its relations (5NF)
    # first_or_404 returns a 404 page if the verb isn't in our DB
    verb: Verb = Verb.query.filter_by(infinitive=verb_infinitive).first_or_404()  # type: ignore

    return render_template("results.html", verb=verb)
