import os
import requests
from dotenv import load_dotenv


load_dotenv()


class AdzunaClient:
    """Client for collecting job listing data from the Adzuna API."""

    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self):
        self.app_id = os.getenv("ADZUNA_APP_ID")
        self.app_key = os.getenv("ADZUNA_APP_KEY")
        self.country = os.getenv("ADZUNA_COUNTRY", "us")

        if not self.app_id or not self.app_key:
            raise ValueError(
                "Missing Adzuna API credentials. Check your .env file."
            )

    def search_jobs(self, search_term, page=1, results_per_page=20, location=None):
        """
        Search Adzuna job listings.

        Args:
            search_term: Job search keyword or phrase.
            page: Results page number.
            results_per_page: Number of results to request.
            location: Optional location filter. Leave as None for broader results.

        Returns:
            JSON response from Adzuna as a Python dictionary.
        """
        url = f"{self.BASE_URL}/{self.country}/search/{page}"

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": search_term,
            "results_per_page": results_per_page,
            "content-type": "application/json",
        }

        if location:
            params["where"] = location

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        return response.json()