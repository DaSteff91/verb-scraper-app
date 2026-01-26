"""
Bulk API Importer Tool.

Orchestrates the scraping of hundreds of verbs via the REST API and
consolidates the results into a single Anki-ready CSV file. Handles
chunking and local merging to avoid URL length limitations.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests
from dotenv import load_dotenv

# Initialize logging for the standalone script
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BulkImporter:
    """
    Handles file ingestion, task matrix generation, and incremental
    CSV merging from the Verb Scraper API.
    """

    # The "Gold Standard" coverage for every verb
    GRAMMAR_MATRIX: List[Dict[str, str]] = [
        {"mode": "Indicativo", "tense": "Presente"},
        {"mode": "Indicativo", "tense": "Pretérito Imperfeito"},
        {"mode": "Indicativo", "tense": "Pretérito Perfeito"},
        {"mode": "Indicativo", "tense": "Pretérito Mais-que-perfeito"},
        {"mode": "Indicativo", "tense": "Futuro do Presente"},
        {"mode": "Indicativo", "tense": "Futuro do Pretérito"},
        {"mode": "Subjuntivo", "tense": "Presente"},
        {"mode": "Subjuntivo", "tense": "Pretérito Imperfeito"},
        {"mode": "Subjuntivo", "tense": "Futuro"},
    ]

    def __init__(self, env_path: Path) -> None:
        """
        Initialize the importer with API credentials and state tracking.

        Args:
            env_path: Path to the .env file containing API_KEY and BASE_URL.
        """
        load_dotenv(dotenv_path=env_path)
        self.api_key: str = os.getenv("API_KEY", "")
        self.base_url: str = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")

        if not self.api_key:
            raise ValueError("API_KEY not found in environment.")

        self.failed_jobs: List[str] = []
        # Stores CSV text chunks to avoid 414 URI Too Large errors
        self.csv_accumulator: List[str] = []

    def _get_session(self) -> requests.Session:
        """Create a session with auth headers pre-configured."""
        session = requests.Session()
        session.headers.update({"X-API-KEY": self.api_key})
        return session

    def load_verbs_from_file(self, file_path: Path) -> List[str]:
        """Parse the comma-separated text file into a unique, sorted list."""
        if not file_path.exists():
            logger.error("Verb file not found: %s", file_path)
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        verb_set: Set[str] = {
            v.strip().lower() for v in raw_content.split(",") if v.strip()
        }
        sorted_verbs = sorted(list(verb_set))
        logger.info("Loaded %d unique verbs from file.", len(sorted_verbs))
        return sorted_verbs

    def generate_task_matrix(self, verbs: List[str]) -> List[Dict[str, str]]:
        """Combine every verb with every supported mode/tense."""
        all_tasks: List[Dict[str, str]] = []
        for verb in verbs:
            for combo in self.GRAMMAR_MATRIX:
                all_tasks.append(
                    {"verb": verb, "mode": combo["mode"], "tense": combo["tense"]}
                )
        logger.info("Generated task matrix: %d total tasks.", len(all_tasks))
        return all_tasks

    def fetch_chunk_csv_safely(
        self, session: requests.Session, tasks: List[Dict[str, str]]
    ) -> None:
        """
        Downloads CSV data in 'Safe Sub-Chunks' (one verb at a time).

        This prevents the '400 Bad Request / URL Too Large' error on
        production servers by ensuring each GET request has a short URI.
        """
        # A single verb has len(GRAMMAR_MATRIX) tasks
        sub_step = len(self.GRAMMAR_MATRIX)

        for i in range(0, len(tasks), sub_step):
            # sub_tasks contains exactly 11 tasks for 1 verb
            sub_tasks = tasks[i : i + sub_step]
            current_verb = sub_tasks[0]["verb"]

            endpoint = f"{self.base_url}/export-batch"
            params = {
                "tasks": json.dumps(sub_tasks),
                "filename": f"export_{current_verb}",
                "skip_tu_vos": "true",
            }

            try:
                response = session.get(endpoint, params=params, timeout=20)
                response.raise_for_status()

                # Strip the BOM (\ufeff) to ensure clean merging
                clean_csv = response.text.lstrip("\ufeff")
                if clean_csv.strip():
                    self.csv_accumulator.append(clean_csv)
            except Exception as e:
                logger.error(
                    "Failed to download CSV for verb '%s': %s", current_verb, e
                )

    def process_chunk(
        self, session: requests.Session, tasks: List[Dict[str, str]]
    ) -> bool:
        """Submit a background job and poll for completion."""
        endpoint = f"{self.base_url}/api/v1/batch"
        try:
            response = session.post(endpoint, json={"tasks": tasks}, timeout=10)
            response.raise_for_status()
            job_id = response.json()["job_id"]
            status_url = f"{self.base_url}/api/v1/batch/{job_id}"
            logger.info("Polling Job [%s] for %d tasks...", job_id, len(tasks))
        except Exception as e:
            logger.error("Submission failed: %s", e)
            return False

        while True:
            try:
                poll_resp = session.get(status_url, timeout=5)
                poll_resp.raise_for_status()
                info = poll_resp.json()

                if info["status"] == "completed":
                    if info["progress"]["failed"] > 0:
                        self.failed_jobs.append(job_id)

                    self.fetch_chunk_csv_safely(session, tasks)
                    return True

                if info["status"] == "failed":
                    return False
                time.sleep(3)
            except Exception as e:
                logger.error("Polling error: %s", e)
                time.sleep(5)

    def save_final_merged_csv(self, filename: str) -> None:
        """Merge all accumulated CSV chunks into one file with a single BOM."""
        if not self.csv_accumulator:
            logger.warning("No CSV data to save.")
            return

        export_dir = Path(__file__).parent / "exports"
        export_dir.mkdir(exist_ok=True)
        file_path = export_dir / f"{filename}.csv"

        # Write using UTF-8-SIG to ensure Anki recognizes special characters
        with open(file_path, "w", encoding="utf-8-sig") as f:
            for content in self.csv_accumulator:
                f.write(content)

        logger.info("SUCCESS: Consolidated CSV saved to: %s", file_path)

    def execute_import(self, verbs: List[str], verbs_per_batch: int = 20) -> None:
        """Orchestrate the full loop: Chunk -> Scrape -> Download -> Save."""
        session = self._get_session()
        all_tasks = self.generate_task_matrix(verbs)
        chunk_step = verbs_per_batch * len(self.GRAMMAR_MATRIX)

        logger.info("Starting execution for %d verbs at %s", len(verbs), self.base_url)

        for i in range(0, len(all_tasks), chunk_step):
            chunk = all_tasks[i : i + chunk_step]
            curr_epoch = (i // chunk_step) + 1
            total_epochs = (len(all_tasks) + chunk_step - 1) // chunk_step

            logger.info(">>> Processing Epoch %d/%d...", curr_epoch, total_epochs)
            self.process_chunk(session, chunk)
            time.sleep(2)

        # Merge and save
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        self.save_final_merged_csv(f"bulk_export_{ts}")

        print("\n" + "=" * 30 + "\nFINAL IMPORT REPORT\n" + "=" * 30)
        print(f"Total Verbs:      {len(verbs)}")
        print(f"Jobs with Issues: {len(self.failed_jobs)}")
        print("=" * 30)


if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent.parent
    DATA_FILE = SCRIPT_DIR / "295_irregular_portuguese_verbs.txt"

    try:
        importer = BulkImporter(env_path=ROOT_DIR / ".env")
        target_verbs = importer.load_verbs_from_file(DATA_FILE)

        if target_verbs:
            # Change to verbs_per_batch=20 when running on production
            importer.execute_import(target_verbs, verbs_per_batch=20)

    except Exception as exc:
        logger.error("Initialization error: %s", exc)
