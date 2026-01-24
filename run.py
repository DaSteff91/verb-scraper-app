"""
Main entry point for the Portuguese Conjugation Scraper application.

This script initializes the Flask app using the factory pattern
and starts the development server.
"""

from flask import Flask
from src import create_app

# Initialize the application instance
app: Flask = create_app()

if __name__ == "__main__":
    # Running with debug=True enables hot-reloading and better error messages
    app.run(debug=True)
