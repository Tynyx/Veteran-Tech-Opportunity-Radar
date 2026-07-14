from pathlib import Path

import matplotlib.pyplot as plt

from src.vettech_radar.analyze import (
    get_remote_counts,
    get_salary_summary_by_search_term,
    get_skill_counts,
    get_top_job_titles,
    get_top_matches,
    load_jobs,
)


REPORT_DIR = Path("reports/generated")


def save_bar_chart(data, x_column, y_column, title, xlabel, ylabel, file_name):
    """Create and save a horizontal bar chart."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if data.empty:
        print(f"Skipped {file_name}: no data available.")
        return None

    chart_data = data.copy()

    plt.figure(figsize=(11, 7))
    plt.barh(chart_data[y_column], chart_data[x_column])
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.gca().invert_yaxis()
    plt.tight_layout()

    file_path = REPORT_DIR / file_name
    plt.savefig(file_path)
    plt.close()

    return file_path


def create_top_titles_chart(df):
    """Create chart for most common job titles."""
    data = get_top_job_titles(df, limit=10)

    return save_bar_chart(
        data=data,
        x_column="posting_count",
        y_column="job_title",
        title="Most Common Job Titles Collected",
        xlabel="Number of Postings",
        ylabel="Job Title",
        file_name="top_job_titles.png",
    )


def create_top_skills_chart(df):
    """Create chart for most common skills/keywords."""
    data = get_skill_counts(df, limit=10)

    return save_bar_chart(
        data=data,
        x_column="mention_count",
        y_column="skill",
        title="Most Requested Skills and Keywords",
        xlabel="Number of Mentions",
        ylabel="Skill / Keyword",
        file_name="top_skills.png",
    )


def create_remote_counts_chart(df):
    """Create chart for remote vs non-remote jobs."""
    data = get_remote_counts(df)

    # Make the labels easier to read
    data["remote_label"] = data["is_remote"].map({
        True: "Remote detected",
        False: "Remote not detected",
    })

    return save_bar_chart(
        data=data,
        x_column="posting_count",
        y_column="remote_label",
        title="Remote Classification Count",
        xlabel="Number of Postings",
        ylabel="Remote Status",
        file_name="remote_counts.png",
    )


def create_top_match_scores_chart(df):
    """Create chart for highest match score jobs."""
    data = get_top_matches(df, limit=10).copy()

    if data.empty:
        print("Skipped top_match_scores.png: no data available.")
        return None

    data["job_label"] = data["job_title"] + " | " + data["company_name"]

    return save_bar_chart(
        data=data,
        x_column="match_score",
        y_column="job_label",
        title="Top Jobs by Custom Match Score",
        xlabel="Match Score",
        ylabel="Job",
        file_name="top_match_scores.png",
    )


def create_salary_chart(df):
    """Create chart for salary summary by search term."""
    data = get_salary_summary_by_search_term(df).copy()

    if data.empty:
        print("Skipped salary_by_search_term.png: no salary data available.")
        return None

    # Use average max salary when available, otherwise average min salary
    data["average_salary"] = data["average_salary_max"].fillna(data["average_salary_min"])
    data = data.dropna(subset=["average_salary"]).sort_values(
        by="average_salary",
        ascending=False,
    )

    return save_bar_chart(
        data=data,
        x_column="average_salary",
        y_column="search_term",
        title="Average Listed Salary by Search Term",
        xlabel="Average Salary",
        ylabel="Search Term",
        file_name="salary_by_search_term.png",
    )


def create_all_charts():
    """Create all project charts."""
    df = load_jobs()

    chart_files = [
        create_top_titles_chart(df),
        create_top_skills_chart(df),
        create_remote_counts_chart(df),
        create_top_match_scores_chart(df),
        create_salary_chart(df),
    ]

    return [file_path for file_path in chart_files if file_path is not None]