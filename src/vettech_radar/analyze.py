from pathlib import Path

import pandas as pd


MASTER_FILE = Path("data/clean/jobs_master.csv")
OUTPUT_DIR = Path("data/output")


def load_jobs(file_path=MASTER_FILE):
    """Load the cleaned jobs CSV and prepare fields for analysis."""
    if not file_path.exists():
        raise FileNotFoundError(
            f"Could not find {file_path}. Run run_collector.py first."
        )

    df = pd.read_csv(file_path)

    # Clean text fields
    text_columns = [
        "job_title",
        "company_name",
        "location",
        "job_category",
        "description",
        "search_term",
        "keywords_found",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = df[column].fillna("")

    # Convert numeric fields safely
    for column in ["salary_min", "salary_max", "match_score"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    # Convert date fields safely
    for column in ["date_posted", "date_collected"]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    # Normalize is_remote
    if "is_remote" in df.columns:
        df["is_remote"] = df["is_remote"].astype(str).str.lower().isin(["true", "1", "yes"])

    return df


def get_top_job_titles(df, limit=15):
    """Return the most common job titles."""
    return (
        df["job_title"]
        .value_counts()
        .head(limit)
        .reset_index()
        .rename(columns={"job_title": "job_title", "count": "posting_count"})
    )


def get_top_companies(df, limit=15):
    """Return companies that appeared most often."""
    return (
        df["company_name"]
        .value_counts()
        .head(limit)
        .reset_index()
        .rename(columns={"company_name": "company_name", "count": "posting_count"})
    )


def get_search_term_counts(df):
    """Return how many records were collected for each search term."""
    return (
        df["search_term"]
        .value_counts()
        .reset_index()
        .rename(columns={"search_term": "search_term", "count": "posting_count"})
    )


def get_remote_counts(df):
    """Return remote vs non-remote classification counts."""
    return (
        df["is_remote"]
        .value_counts()
        .reset_index()
        .rename(columns={"is_remote": "is_remote", "count": "posting_count"})
    )


def get_skill_counts(df, limit=20):
    """Return the most common skills/keywords found in job descriptions."""
    skill_rows = []

    for skills in df["keywords_found"].fillna(""):
        for skill in str(skills).split(","):
            cleaned_skill = skill.strip().lower()
            if cleaned_skill:
                skill_rows.append(cleaned_skill)

    if not skill_rows:
        return pd.DataFrame(columns=["skill", "mention_count"])

    skill_df = pd.DataFrame(skill_rows, columns=["skill"])

    return (
        skill_df["skill"]
        .value_counts()
        .head(limit)
        .reset_index()
        .rename(columns={"skill": "skill", "count": "mention_count"})
    )


def get_top_matches(df, limit=15):
    """Return jobs with the highest custom match scores."""
    columns = [
        "job_title",
        "company_name",
        "location",
        "search_term",
        "is_remote",
        "keywords_found",
        "match_score",
        "redirect_url",
    ]

    available_columns = [column for column in columns if column in df.columns]

    return (
        df[available_columns]
        .sort_values(by="match_score", ascending=False)
        .head(limit)
    )


def get_salary_summary_by_search_term(df):
    """Return average salary ranges grouped by search term."""
    salary_df = df.dropna(subset=["salary_min", "salary_max"], how="all")

    if salary_df.empty:
        return pd.DataFrame(
            columns=[
                "search_term",
                "average_salary_min",
                "average_salary_max",
                "salary_records_available",
            ]
        )

    return (
        salary_df
        .groupby("search_term")
        .agg(
            average_salary_min=("salary_min", "mean"),
            average_salary_max=("salary_max", "mean"),
            salary_records_available=("job_title", "count"),
        )
        .reset_index()
        .sort_values(by="salary_records_available", ascending=False)
    )


def save_summary_tables():
    """Create and save all summary tables."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_jobs()

    summaries = {
        "top_job_titles": get_top_job_titles(df),
        "top_companies": get_top_companies(df),
        "search_term_counts": get_search_term_counts(df),
        "remote_counts": get_remote_counts(df),
        "skill_counts": get_skill_counts(df),
        "top_matches": get_top_matches(df),
        "salary_summary_by_search_term": get_salary_summary_by_search_term(df),
    }

    saved_files = []

    for name, summary_df in summaries.items():
        file_path = OUTPUT_DIR / f"{name}.csv"
        summary_df.to_csv(file_path, index=False)
        saved_files.append(file_path)

    return saved_files