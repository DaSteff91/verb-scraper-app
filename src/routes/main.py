"""
Main routes (Controller) for the Verb Scraper application.
"""

import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for
from src.services.verb_manager import VerbManager

# Define the blueprint
main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.route("/", methods=["GET", "POST"])
def index() -> str:
    """
    Handle the main dashboard and scraping form.

    Returns:
        str: The rendered HTML or a redirect.
    """
    manager = VerbManager()

    if request.method == "POST":
        # Extract form data
        verb = request.form.get("verb", "").strip()
        mode = request.form.get("mode", "Indicativo")
        tense = request.form.get("tense", "Presente")

        if verb:
            logger.info("UI request to scrape: %s (%s %s)", verb, mode, tense)
            success = manager.get_or_create_verb_data(verb, mode, tense)

            if success:
                # Placeholder until we have a results view
                return f"<h1>Success!</h1><p>Scraped {verb}. Check the database.</p>"

            return f"<h1>Error</h1><p>Failed to scrape {verb}.</p>", 400

    # GET request: return the placeholder UI
    return "<h1>Verb Scraper Form</h1><p>Next: Implement HTML templates.</p>"
