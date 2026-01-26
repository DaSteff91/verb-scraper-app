"""
Bulk API Importer Tool.

This script acts as a high-level client for the Verb Scraper API,
orchestrating the scraping of hundreds of verbs across all supported
grammatical modes and tenses.
"""

import os
import logging
import time
import requests
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

from dotenv import load_dotenv

# Initialize logging for the standalone script
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BulkImporter:
    """
    Handles file ingestion and task matrix generation for the API.
    """

    # Constants representing the "Gold Standard" coverage for every verb
    GRAMMAR_MATRIX: List[Dict[str, str]] = [
        # Indicativo
        {"mode": "Indicativo", "tense": "Presente"},
        {"mode": "Indicativo", "tense": "Pretérito Imperfeito"},
        {"mode": "Indicativo", "tense": "Pretérito Perfeito"},
        {"mode": "Indicativo", "tense": "Pretérito Mais-que-perfeito"},
        {"mode": "Indicativo", "tense": "Futuro do Presente"},
        {"mode": "Indicativo", "tense": "Futuro do Pretérito"},
        # Subjuntivo
        {"mode": "Subjuntivo", "tense": "Presente"},
        {"mode": "Subjuntivo", "tense": "Pretérito Imperfeito"},
        {"mode": "Subjuntivo", "tense": "Futuro"},
        # Imperativo
        {"mode": "Imperativo", "tense": "Afirmativo"},
        {"mode": "Imperativo", "tense": "Negativo"},
    ]

    def __init__(self, env_path: Path) -> None:
        """
        Initialize with environment variables for API communication.
        """
        load_dotenv(dotenv_path=env_path)
        self.api_key: str = os.getenv("API_KEY", "")
        self.base_url: str = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")
        self.failed_jobs: List[str] = []
        self.successful_tasks: List[Dict[str, str]] = []

        if not self.api_key:
            raise ValueError("API_KEY not found in environment.")

    def load_verbs_from_file(self, file_path: Path) -> List[str]:
        """
        Parse the comma-separated text file into a unique, sorted list.
        """
        if not file_path.exists():
            logger.error("Verb file not found: %s", file_path)
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # Split by comma, strip whitespace, remove empty strings, handle duplicates
        verb_set: Set[str] = {
            v.strip().lower() for v in raw_content.split(",") if v.strip()
        }

        sorted_verbs = sorted(list(verb_set))
        logger.info("Loaded %d unique verbs from file.", len(sorted_verbs))
        return sorted_verbs

    def generate_task_matrix(self, verbs: List[str]) -> List[Dict[str, str]]:
        """
        Combine every verb with every supported mode/tense.
        """
        all_tasks: List[Dict[str, str]] = []
        for verb in verbs:
            for combo in self.GRAMMAR_MATRIX:
                task = {"verb": verb, "mode": combo["mode"], "tense": combo["tense"]}
                all_tasks.append(task)

        logger.info("Generated task matrix: %d total tasks.", len(all_tasks))
        return all_tasks

    def _get_session(self) -> requests.Session:
        """Create a session with auth headers pre-configured."""
        session = requests.Session()
        session.headers.update({"X-API-KEY": self.api_key})
        return session

    def process_chunk(
        self, session: requests.Session, tasks: List[Dict[str, str]]
    ) -> bool:
        """
        Send a chunk of tasks to the API and wait for completion.
        """
        endpoint = f"{self.base_url}/api/v1/batch"
        try:
            response = session.post(endpoint, json={"tasks": tasks}, timeout=10)
            response.raise_for_status()
            job_data = response.json()
            job_id = job_data["job_id"]
            status_url = f"{self.base_url}{job_data['check_status_url']}"

            logger.info("Batch accepted. Job ID: %s. Polling...", job_id)
        except Exception as e:
            logger.error("Failed to submit batch: %s", e)
            return False

        while True:
            try:
                poll_resp = session.get(status_url, timeout=5)
                poll_resp.raise_for_status()
                info = poll_resp.json()

                status = info["status"]
                progress = info["progress"]

                if status == "completed":
                    if progress["failed"] > 0:
                        logger.warning(
                            "Job %s finished with %d failures.",
                            job_id,
                            progress["failed"],
                        )
                        self.failed_jobs.append(job_id)

                    self.successful_tasks.extend(tasks)
                    return True

                if status == "failed":
                    logger.error("Job %s reported a fatal system failure.", job_id)
                    return False

                time.sleep(3)
            except Exception as e:
                logger.error("Polling error: %s", e)
                time.sleep(5)

    def download_anki_export(self, filename: str) -> None:
        """
        Request the consolidated CSV from the server and save it locally.
        """
        if not self.successful_tasks:
            logger.warning("No successful tasks to export.")
            return

        logger.info(
            "Requesting consolidated Anki export for %d tasks...",
            len(self.successful_tasks),
        )

        # Build the query params for the UI export route
        # Note: We use the /export-batch route which takes a JSON string of tasks
        endpoint = f"{self.base_url}/export-batch"
        params = {
            "tasks": json.dumps(self.successful_tasks),
            "filename": filename,
            "skip_tu_vos": "true",  # Following your Brazilian dialect preference
        }

        try:
            session = self._get_session()
            response = session.get(endpoint, params=params, stream=True, timeout=30)
            response.raise_for_status()

            # Save file to a new 'exports' directory
            export_dir = Path(__file__).parent / "exports"
            export_dir.mkdir(exist_ok=True)

            file_path = export_dir / f"{filename}.csv"

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info("Success! Consolidated export saved to: %s", file_path)
        except Exception as e:
            logger.error("Export download failed: %s", e)

    def execute_import(
        self, all_tasks: List[Dict[str, str]], verbs_per_batch: int = 5
    ) -> None:
        """
        Divide all tasks into chunks, process them, and then trigger the export.
        """
        session = self._get_session()
        tasks_per_verb = len(self.GRAMMAR_MATRIX)
        chunk_size = verbs_per_batch * tasks_per_verb

        for i in range(0, len(all_tasks), chunk_size):
            chunk = all_tasks[i : i + chunk_size]
            self.process_chunk(session, chunk)
            time.sleep(2)

        # Trigger final export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.download_anki_export(f"bulk_export_{timestamp}")

        # Print Final Report
        print("\n" + "=" * 30)
        print("FINAL IMPORT REPORT")
        print("=" * 30)
        print(f"Total Verbs Processed: {len(all_tasks) // tasks_per_verb}")
        print(f"Total Tasks:          {len(all_tasks)}")
        print(f"Jobs with Issues:     {len(self.failed_jobs)}")
        if self.failed_jobs:
            print(f"Failed Job IDs:       {', '.join(self.failed_jobs)}")
        print("=" * 30)


if __name__ == "__main__":
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_FILE = Path(__file__).parent / "295_irregular_portuguese_verbs.txt"

    importer = BulkImporter(env_path=ROOT_DIR / ".env")
    verb_list = importer.load_verbs_from_file(DATA_FILE)

    # 2-verb test slice
    test_tasks = importer.generate_task_matrix(verb_list[:2])

    # Execute (Verbs per batch = 1, so we see the sequential logic twice)
    importer.execute_import(test_tasks, verbs_per_batch=1)
