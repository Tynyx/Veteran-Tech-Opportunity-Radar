import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

import boto3


SEARCH_TERMS = [
    "IT support",
    "help desk",
    "technical support",
    "customer support engineer",
    "application support analyst",
    "junior developer",
    "junior software developer",
    "software developer",
    "software engineer",
    "junior software engineer",
    "full stack developer",
    "backend developer",
    "remote support",
    "work from home IT",
]


def get_timestamp():
    """Create a safe timestamp for file names."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def get_collected_at():
    """Create an ISO timestamp for database records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def combine_job_text(job):
    """Combine important job fields into one lowercase text block."""
    title = job.get("title", "")
    description = job.get("description", "")
    location = job.get("location", {}).get("display_name", "")

    return f"{title} {description} {location}".lower()


def is_remote_job(job):
    """Detect whether a job appears to be remote based on keywords."""
    remote_keywords = [
        "remote",
        "work from home",
        "work-from-home",
        "wfh",
        "telecommute",
        "anywhere",
        "virtual",
    ]

    text = combine_job_text(job)
    return any(keyword in text for keyword in remote_keywords)


def find_skills(job):
    """Find career-relevant skills mentioned in the job listing."""
    skill_keywords = [
        "python",
        "java",
        "sql",
        "api",
        "apis",
        "aws",
        "cloud",
        "zendesk",
        "salesforce",
        "servicenow",
        "linux",
        "windows",
        "troubleshooting",
        "help desk",
        "technical support",
        "customer support",
    ]

    text = combine_job_text(job)
    found = []

    for skill in skill_keywords:
        if skill in text:
            found.append(skill)

    return found


def calculate_match_score(job):
    """
    Score jobs based on how well they match the project goal:
    remote, support-focused, junior-friendly, and connected to tech skills.
    """
    text = combine_job_text(job)
    score = 0

    if is_remote_job(job):
        score += 20

    support_terms = [
        "support",
        "help desk",
        "technical support",
        "customer support",
        "service desk",
        "application support",
    ]

    if any(term in text for term in support_terms):
        score += 20

    junior_terms = [
        "junior",
        "entry level",
        "entry-level",
        "associate",
        "trainee",
        "apprentice",
    ]

    if any(term in text for term in junior_terms):
        score += 15

    skill_points = {
        "python": 10,
        "java": 10,
        "sql": 10,
        "api": 10,
        "apis": 10,
        "aws": 10,
        "cloud": 10,
        "zendesk": 8,
        "salesforce": 8,
        "servicenow": 8,
    }

    found_skills = find_skills(job)

    for skill, points in skill_points.items():
        if skill in found_skills:
            score += points

    if job.get("salary_min") or job.get("salary_max"):
        score += 5

    if job.get("company", {}).get("display_name"):
        score += 5

    return min(score, 100)


def search_adzuna(search_term, page=1, results_per_page=5):
    """Call the Adzuna API and return JSON job data."""
    app_id = os.environ["ADZUNA_APP_ID"]
    app_key = os.environ["ADZUNA_APP_KEY"]
    country = os.environ.get("ADZUNA_COUNTRY", "us")

    base_url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": search_term,
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }

    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_job_record(job, search_term, collected_at):
    """Convert one Adzuna job record into a clean DynamoDB-ready record."""
    company = job.get("company", {})
    location = job.get("location", {})
    category = job.get("category", {})

    skills_found = find_skills(job)

    return {
        "job_id": str(job.get("id", "")),
        "job_title": job.get("title", ""),
        "company_name": company.get("display_name", ""),
        "location": location.get("display_name", ""),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "job_category": category.get("label", ""),
        "date_posted": job.get("created", ""),
        "description": job.get("description", ""),
        "redirect_url": job.get("redirect_url", ""),
        "search_term": search_term,
        "date_collected": collected_at,
        "is_remote": is_remote_job(job),
        "keywords_found": ", ".join(skills_found),
        "match_score": calculate_match_score(job),
    }


def convert_floats_to_decimal(value):
    """
    Convert floats to Decimal because DynamoDB does not accept Python float values.
    """
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {
            key: convert_floats_to_decimal(nested_value)
            for key, nested_value in value.items()
        }

    if isinstance(value, list):
        return [convert_floats_to_decimal(item) for item in value]

    return value


def create_record_id(clean_record):
    """Create a unique record ID for DynamoDB."""
    collected_date = str(clean_record.get("date_collected", ""))[:10]
    search_term = str(clean_record.get("search_term", "unknown")).replace(" ", "_").lower()
    job_id = str(clean_record.get("job_id", "no_job_id"))

    return f"{collected_date}#{search_term}#{job_id}"


def save_raw_json_to_s3(data, search_term, timestamp):
    """Save the original API response to S3."""
    bucket_name = os.environ["S3_BUCKET_NAME"]

    safe_search = search_term.replace(" ", "_").replace("/", "_").lower()
    today = datetime.now(timezone.utc)

    key = (
        f"raw_data/{today.year}/{today.month:02d}/{today.day:02d}/"
        f"{safe_search}_{timestamp}.json"
    )

    s3 = boto3.client("s3")

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType="application/json",
    )

    return f"s3://{bucket_name}/{key}"


def save_clean_records_to_dynamodb(clean_records):
    """Save cleaned job records to DynamoDB."""
    table_name = os.environ["DYNAMODB_TABLE_NAME"]
    table = boto3.resource("dynamodb").Table(table_name)

    saved_count = 0

    for record in clean_records:
        record["record_id"] = create_record_id(record)
        safe_record = convert_floats_to_decimal(record)
        table.put_item(Item=safe_record)
        saved_count += 1

    return saved_count


def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    Collects Adzuna job data, saves raw JSON to S3,
    and saves cleaned records to DynamoDB.
    """
    timestamp = get_timestamp()
    collected_at = get_collected_at()

    total_downloaded = 0
    total_saved = 0
    s3_files = []

    for search_term in SEARCH_TERMS:
        print("=" * 60)
        print(f"Collecting search term: {search_term}")

        data = search_adzuna(
            search_term=search_term,
            page=1,
            results_per_page=5,
        )

        s3_path = save_raw_json_to_s3(
            data=data,
            search_term=search_term,
            timestamp=timestamp,
        )

        results = data.get("results", [])

        clean_records = [
            clean_job_record(
                job=job,
                search_term=search_term,
                collected_at=collected_at,
            )
            for job in results
        ]

        saved_count = save_clean_records_to_dynamodb(clean_records)

        total_downloaded += len(results)
        total_saved += saved_count
        s3_files.append(s3_path)

        print(f"Total matches from API: {data.get('count', 0)}")
        print(f"Records downloaded this run: {len(results)}")
        print(f"Raw backup saved: {s3_path}")
        print(f"Records saved to DynamoDB: {saved_count}")

    return {
        "statusCode": 200,
        "body": {
            "message": "VetTech Opportunity Radar Lambda run complete.",
            "records_downloaded": total_downloaded,
            "records_saved_to_dynamodb": total_saved,
            "s3_files": s3_files,
        },
    }