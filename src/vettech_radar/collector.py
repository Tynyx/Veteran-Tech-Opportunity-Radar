import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.vettech_radar.adzuna_client import AdzunaClient
from src.vettech_radar.scoring import calculate_match_score, find_skills, is_remote_job


SEARCH_TERMS = [
    "IT support",
    "help desk",
    "technical support",
    "customer support engineer",
    "application support analyst",
    "junior developer",
    "remote support",
    "work from home IT",
]


RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/clean")


def get_timestamp():
    """Create a safe timestamp for file names."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_raw_json(data, search_term, timestamp):
    """Save the original API response before cleaning it."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    safe_search = search_term.replace(" ", "_").replace("/", "_").lower()
    file_path = RAW_DIR / f"{timestamp}_{safe_search}.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return file_path


def clean_job_record(job, search_term, collected_at):
    """Convert one Adzuna job record into a clean row for CSV analysis."""
    company = job.get("company", {})
    location = job.get("location", {})
    category = job.get("category", {})

    skills_found = find_skills(job)

    return {
        "job_id": job.get("id"),
        "job_title": job.get("title"),
        "company_name": company.get("display_name"),
        "location": location.get("display_name"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "job_category": category.get("label"),
        "date_posted": job.get("created"),
        "description": job.get("description"),
        "redirect_url": job.get("redirect_url"),
        "search_term": search_term,
        "date_collected": collected_at,
        "is_remote": is_remote_job(job),
        "keywords_found": ", ".join(skills_found),
        "match_score": calculate_match_score(job),
    }


def collect_jobs(results_per_page=10):
    """
    Collect jobs from Adzuna, save raw JSON, clean records,
    and save the cleaned data into CSV files.
    """
    client = AdzunaClient()
    timestamp = get_timestamp()
    collected_at = datetime.now().isoformat(timespec="seconds")

    all_clean_records = []
    raw_files = []

    for search_term in SEARCH_TERMS:
        print("=" * 60)
        print(f"Collecting search term: {search_term}")

        data = client.search_jobs(
            search_term=search_term,
            page=1,
            results_per_page=results_per_page,
            location=None,
        )

        raw_file = save_raw_json(data, search_term, timestamp)
        raw_files.append(str(raw_file))

        results = data.get("results", [])
        print(f"Total matches from API: {data.get('count', 0)}")
        print(f"Records downloaded this run: {len(results)}")
        print(f"Raw file saved: {raw_file}")

        for job in results:
            clean_record = clean_job_record(
                job=job,
                search_term=search_term,
                collected_at=collected_at,
            )
            all_clean_records.append(clean_record)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    run_file = CLEAN_DIR / f"jobs_run_{timestamp}.csv"
    master_file = CLEAN_DIR / "jobs_master.csv"

    df = pd.DataFrame(all_clean_records)

    if not df.empty:
        df.drop_duplicates(subset=["job_id"], inplace=True)
        df.to_csv(run_file, index=False)

        if master_file.exists():
            old_df = pd.read_csv(master_file)
            combined_df = pd.concat([old_df, df], ignore_index=True)
            combined_df.drop_duplicates(subset=["job_id"], inplace=True)
            combined_df.to_csv(master_file, index=False)
        else:
            df.to_csv(master_file, index=False)

    return {
        "records_collected": len(all_clean_records),
        "unique_records_saved": len(df) if not df.empty else 0,
        "raw_files": raw_files,
        "run_file": str(run_file),
        "master_file": str(master_file),
    }