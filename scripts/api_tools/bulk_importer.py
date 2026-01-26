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

    def fetch_chunk_csv(
        self, session: requests.Session, tasks: List[Dict[str, str]]
    ) -> None:
        """
        Download the CSV portion for a specific chunk and store it in memory.
        """
        endpoint = f"{self.base_url}/export-batch"
        params = {
            "tasks": json.dumps(tasks),
            "filename": "temp_chunk",
            "skip_tu_vos": "true",
        }
        try:
            # We call the GET route with a limited chunk size to avoid 414 errors
            response = session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()

            # Strip the UTF-8 BOM (\ufeff) if present to avoid multiple BOMs in merged file
            csv_content = response.text.lstrip("\ufeff")
            if csv_content.strip():
                self.csv_accumulator.append(csv_content)
                logger.debug("Chunk CSV added to accumulator.")
        except Exception as e:
            logger.error("Failed to download CSV chunk: %s", e)

    def process_chunk(
        self, session: requests.Session, tasks: List[Dict[str, str]]
    ) -> bool:
        """Submit a chunk as a background job and poll for completion."""
        endpoint = f"{self.base_url}/api/v1/batch"
        try:
            response = session.post(endpoint, json={"tasks": tasks}, timeout=10)
            response.raise_for_status()
            job_id = response.json()["job_id"]
            status_url = f"{self.base_url}/api/v1/batch/{job_id}"
            logger.info("Batch Job [%s] started. Polling...", job_id)
        except Exception as e:
            logger.error("Submission failed: %s", e)
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
                            "Job %s had %d failures.", job_id, progress["failed"]
                        )
                        self.failed_jobs.append(job_id)

                    # DOWNLOAD CHUNK IMMEDIATELY UPON COMPLETION
                    self.fetch_chunk_csv(session, tasks)
                    return True

                if status == "failed":
                    logger.error("Job %s failed completely.", job_id)
                    return False

                time.sleep(3)
            except Exception as e:
                logger.error("Polling error for job %s: %s", job_id, e)
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

    def execute_import(self, verbs: List[str], verbs_per_batch: int = 10) -> None:
        """Orchestrate the full loop: Chunk -> Scrape -> Fetch CSV -> Merge."""
        session = self._get_session()
        all_tasks = self.generate_task_matrix(verbs)

        # Calculate chunk size (verbs * grammar matrix entries)
        chunk_step = verbs_per_batch * len(self.GRAMMAR_MATRIX)
        total_tasks = len(all_tasks)

        logger.info("Starting execution for %d verbs...", len(verbs))

        for i in range(0, total_tasks, chunk_step):
            chunk = all_tasks[i : i + chunk_step]
            current_chunk_num = (i // chunk_step) + 1
            total_chunks = (total_tasks + chunk_step - 1) // chunk_step

            logger.info("Processing Chunk %d/%d...", current_chunk_num, total_chunks)
            self.process_chunk(session, chunk)

            # Cool-down to prevent rate-limiting on target websites
            time.sleep(2)

        # Merge and save
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        self.save_final_merged_csv(f"bulk_export_{ts}")

        # Final terminal summary
        print("\n" + "=" * 30)
        print("FINAL IMPORT REPORT")
        print("=" * 30)
        print(f"Verbs Processed:      {len(verbs)}")
        print(f"Total Tasks:          {total_tasks}")
        print(f"Jobs with Issues:     {len(self.failed_jobs)}")
        if self.failed_jobs:
            print(f"IDs: {', '.join(self.failed_jobs)}")
        print("=" * 30)


if __name__ == "__main__":
    # Path configuration
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent.parent
    DATA_FILE = SCRIPT_DIR / "295_irregular_portuguese_verbs.txt"

    try:
        importer = BulkImporter(env_path=ROOT_DIR / ".env")
        target_verbs = importer.load_verbs_from_file(DATA_FILE)

        if target_verbs:
            # Change to verbs_per_batch=20 when running on production
            importer.execute_import(target_verbs, verbs_per_batch=10)

    except Exception as exc:
        logger.error("Initialization error: %s", exc)
