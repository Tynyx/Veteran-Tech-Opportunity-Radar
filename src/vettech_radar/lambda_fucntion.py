from datetime import datetime

from src.vettech_radar.adzuna_client import AdzunaClient
from src.vettech_radar.collector import SEARCH_TERMS, clean_job_record, get_timestamp
from src.vettech_radar.aws_storage import (
    save_clean_records_to_dynamodb,
    save_raw_json_to_s3,
)


def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    Collects job data from Adzuna, stores raw JSON in S3,
    and stores cleaned records in DynamoDB.
    """
    client = AdzunaClient()

    timestamp = get_timestamp()
    collected_at = datetime.now().isoformat(timespec="seconds")
    results_per_page = 10

    total_downloaded = 0
    total_saved_to_dynamodb = 0
    s3_files = []

    for search_term in SEARCH_TERMS:
        print("=" * 60)
        print(f"Collecting search term: {search_term}")

        data = client.search_jobs(
            search_term=search_term,
            page=1,
            results_per_page=results_per_page,
            location=None,
        )

        s3_file = save_raw_json_to_s3(
            data=data,
            search_term=search_term,
            timestamp=timestamp,
        )
        s3_files.append(s3_file)

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
        total_saved_to_dynamodb += saved_count

        print(f"Total matches from API: {data.get('count', 0)}")
        print(f"Records downloaded this run: {len(results)}")
        print(f"Raw file saved to S3: {s3_file}")
        print(f"Records saved to DynamoDB: {saved_count}")

    return {
        "statusCode": 200,
        "message": "VetTech Opportunity Radar collection complete.",
        "records_downloaded": total_downloaded,
        "records_saved_to_dynamodb": total_saved_to_dynamodb,
        "s3_files": s3_files,
    }


if __name__ == "__main__":
    print(lambda_handler({}, None))