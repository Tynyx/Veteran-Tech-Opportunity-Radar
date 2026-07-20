import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv


# Add the project root folder to Python's import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.vettech_radar.aws_storage import (
    save_clean_records_to_dynamodb,
    save_raw_json_to_s3,
)

def main():
    load_dotenv()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    fake_raw_data = {
        "source": "local AWS test",
        "message": "Testing s3 raw JSON upload",
        "timestamp": timestamp,
        "results": [
            {
                "id": "test-job-1",
                "title": "Remote IT Support Specialist",
                "company": {"display_name": "Tech Solutions Inc."},
            }
        ]
    }

    print("Testing S3 upload...")
    s3_path = save_raw_json_to_s3(
        data=fake_raw_data,
        search_term="aws testp",
        timestamp=timestamp,
    )
    print(f"S3 upload successful: {s3_path} ")

    fake_clean_record = {
        "job_id": f"test-job-{timestamp}",
        "job_title": "Remote IT Support Specialist",
        "company_name": "Tech Solutions Inc.",
        "location": "Remote",
        "salary_min": 50000.0,
        "salary_max": 70000.0,
        "job_category": "IT Support",
        "date_posted": "2026-01-01:00:00:00",
        "description": "Test record for DynamoDB",
        "search_term": "aws test",
        "date_collected": datetime.now().isoformat(timespec="seconds"),
        "is_remote": True,
        "keywords": "remote, technicial support, cloud",
        "match_score": 75,
    }

    print("Testing DynamoDB write...")
    saved_count = save_clean_records_to_dynamodb([fake_clean_record])
    print(f"DynamoDB write successful. Records saved: {saved_count}")

    print("\nAWS write test complete.")

if __name__ == "__main__":
    main()