from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

try:
    import boto3
except ImportError:
    boto3 = None


load_dotenv()

MASTER_FILE = Path("data/clean/jobs_master.csv")


st.set_page_config(
    page_title="VetTech Opportunity Radar",
    page_icon="🪖",
    layout="wide",
)


TACTICAL_CSS = """
<style>
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #0f1411 0%, #111827 45%, #1c2419 100%);
        color: #f5f5f0;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #10140f 0%, #1f2933 100%);
        border-right: 1px solid #3f4f2f;
    }

    section[data-testid="stSidebar"] * {
        color: #f5f5f0;
    }

    /* Headings */
    h1, h2, h3 {
        color: #f4e7c5;
        letter-spacing: 0.5px;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: rgba(35, 45, 32, 0.9);
        border: 1px solid #6b7f3f;
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 0 18px rgba(107, 127, 63, 0.12);
    }

    div[data-testid="stMetricLabel"] {
        color: #c7c9bd;
    }

    div[data-testid="stMetricValue"] {
        color: #f4e7c5;
        font-weight: 700;
    }

    /* Info blocks */
    .mission-card {
        background: rgba(22, 31, 25, 0.92);
        border-left: 5px solid #8a9a5b;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 20px;
        color: #e8e6dc;
    }

    .mission-card strong {
        color: #f4e7c5;
    }

    .status-pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: #2f3f22;
        color: #f4e7c5;
        border: 1px solid #8a9a5b;
        font-size: 0.85rem;
        margin-right: 8px;
        margin-bottom: 8px;
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        border: 1px solid #3f4f2f;
        border-radius: 12px;
    }

    /* Horizontal rules */
    hr {
        border-color: #3f4f2f;
    }

    /* Buttons */
    .stButton button {
        background-color: #2f3f22;
        color: #f4e7c5;
        border: 1px solid #8a9a5b;
        border-radius: 10px;
    }

    .stButton button:hover {
        background-color: #3f532e;
        color: #ffffff;
        border-color: #c2b280;
    }
</style>
"""


def decimal_to_float(value):
    """Convert DynamoDB Decimal values into normal Python numbers."""
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)

    if isinstance(value, dict):
        return {key: decimal_to_float(nested) for key, nested in value.items()}

    if isinstance(value, list):
        return [decimal_to_float(item) for item in value]

    return value


def load_from_dynamodb():
    """Load job records from DynamoDB if AWS is configured."""
    if boto3 is None:
        return pd.DataFrame(), "AWS unavailable: boto3 is not installed."

    try:
        import os

        table_name = os.getenv("DYNAMODB_TABLE_NAME")

        if not table_name:
            return pd.DataFrame(), "AWS skipped: DYNAMODB_TABLE_NAME is missing."

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        items = []
        response = table.scan()
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        clean_items = [decimal_to_float(item) for item in items]

        if not clean_items:
            return pd.DataFrame(), "AWS connected, but DynamoDB table has no records."

        return pd.DataFrame(clean_items), f"AWS DynamoDB: loaded {len(clean_items)} records."

    except Exception as error:
        return pd.DataFrame(), f"AWS fallback triggered: {error}"


def load_from_csv():
    """Load the local cleaned job dataset."""
    if not MASTER_FILE.exists():
        return pd.DataFrame(), f"Local CSV missing: {MASTER_FILE}"

    df = pd.read_csv(MASTER_FILE)
    return df, f"Local CSV: loaded {len(df)} records from {MASTER_FILE}"


def load_data():
    """
    Load data for the dashboard.

    Priority:
    1. Try AWS DynamoDB first.
    2. If AWS fails or has no records, fall back to local CSV.
    """
    aws_df, aws_message = load_from_dynamodb()

    if not aws_df.empty:
        return prepare_dataframe(aws_df), aws_message

    csv_df, csv_message = load_from_csv()

    if not csv_df.empty:
        return prepare_dataframe(csv_df), f"{csv_message} | {aws_message}"

    return pd.DataFrame(), f"No data loaded. {aws_message} | {csv_message}"


def prepare_dataframe(df):
    """Clean fields for dashboard display and filtering."""
    df = df.copy()

    text_columns = [
        "job_title",
        "company_name",
        "location",
        "job_category",
        "description",
        "search_term",
        "keywords_found",
        "redirect_url",
        "record_id",
        "job_id",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)

    for column in ["salary_min", "salary_max", "match_score"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "is_remote" in df.columns:
        df["is_remote"] = (
            df["is_remote"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "yes"])
        )

    if "date_collected" in df.columns:
        df["date_collected"] = pd.to_datetime(df["date_collected"], errors="coerce")

    if "job_title" in df.columns:
        df["role_family"] = df["job_title"].apply(classify_role_family)
    else:
        df["role_family"] = "Unknown"

    return df


def classify_role_family(title):
    """Classify job titles into broader career paths."""
    title = str(title).lower()

    if any(term in title for term in ["software engineer", "software developer", "developer", "full stack", "backend", "frontend"]):
        return "Software / Developer"

    if any(term in title for term in ["help desk", "service desk", "it support", "support technician", "desktop support"]):
        return "IT Support"

    if any(term in title for term in ["technical support", "customer support engineer", "support engineer"]):
        return "Technical Support"

    if any(term in title for term in ["application support", "systems analyst", "support analyst"]):
        return "Application / Systems Support"

    if any(term in title for term in ["cloud", "aws", "azure", "devops"]):
        return "Cloud / DevOps"

    if any(term in title for term in ["security", "cyber", "soc"]):
        return "Cybersecurity"

    return "Other"


def get_skill_counts(df):
    """Count skills found in the keywords_found column."""
    skills = []

    if "keywords_found" not in df.columns:
        return pd.DataFrame(columns=["skill", "count"])

    for item in df["keywords_found"].fillna(""):
        for skill in str(item).split(","):
            cleaned = skill.strip().lower()
            if cleaned:
                skills.append(cleaned)

    if not skills:
        return pd.DataFrame(columns=["skill", "count"])

    return (
        pd.Series(skills)
        .value_counts()
        .reset_index()
        .rename(columns={"index": "skill", "count": "count"})
    )


def filter_data(df):
    """Apply sidebar filters."""
    filtered = df.copy()

    st.sidebar.header("Mission Filters")

    if "search_term" in filtered.columns:
        search_terms = sorted(filtered["search_term"].dropna().unique())
        selected_terms = st.sidebar.multiselect(
            "Search terms",
            options=search_terms,
            default=search_terms,
        )

        if selected_terms:
            filtered = filtered[filtered["search_term"].isin(selected_terms)]

    if "role_family" in filtered.columns:
        role_families = sorted(filtered["role_family"].dropna().unique())
        selected_roles = st.sidebar.multiselect(
            "Career path",
            options=role_families,
            default=role_families,
        )

        if selected_roles:
            filtered = filtered[filtered["role_family"].isin(selected_roles)]

    if "is_remote" in filtered.columns:
        remote_option = st.sidebar.selectbox(
            "Remote status",
            options=["All", "Remote detected", "Remote not detected"],
        )

        if remote_option == "Remote detected":
            filtered = filtered[filtered["is_remote"] == True]
        elif remote_option == "Remote not detected":
            filtered = filtered[filtered["is_remote"] == False]

    if "match_score" in filtered.columns:
        selected_score = st.sidebar.slider(
            "Minimum match score",
            min_value=0,
            max_value=100,
            value=0,
        )

        filtered = filtered[filtered["match_score"].fillna(0) >= selected_score]

    if "keywords_found" in filtered.columns:
        skill_search = st.sidebar.text_input(
            "Skill keyword search",
            placeholder="python, sql, aws, servicenow",
        )

        if skill_search:
            filtered = filtered[
                filtered["keywords_found"]
                .str.lower()
                .str.contains(skill_search.lower(), na=False)
            ]

    if "job_title" in filtered.columns:
        title_search = st.sidebar.text_input(
            "Job title search",
            placeholder="software, developer, support",
        )

        if title_search:
            filtered = filtered[
                filtered["job_title"]
                .str.lower()
                .str.contains(title_search.lower(), na=False)
            ]

    return filtered


def show_header(data_source_message):
    """Display dashboard header and mission statement."""
    st.title("VetTech Opportunity Radar")
    st.caption("Veterans transitioning into technology | Remote tech job market tracker")

    st.markdown(
        """
        <div class="mission-card">
            <strong>Mission:</strong> Track remote and support-focused technology roles,
            identify common skills, compare career paths, and rank job postings using a
            custom match score for veterans moving into tech.
            <br><br>
            <span class="status-pill">Adzuna API</span>
            <span class="status-pill">Python</span>
            <span class="status-pill">Pandas</span>
            <span class="status-pill">Streamlit Frontend</span>
            <span class="status-pill">AWS S3</span>
            <span class="status-pill">AWS DynamoDB</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(data_source_message)


def show_metric_cards(df):
    """Display metric cards."""
    total_jobs = len(df)

    remote_jobs = 0
    if "is_remote" in df.columns:
        remote_jobs = int(df["is_remote"].sum())

    developer_jobs = 0
    if "role_family" in df.columns:
        developer_jobs = int((df["role_family"] == "Software / Developer").sum())

    avg_score = 0
    max_score = 0

    if "match_score" in df.columns and not df["match_score"].dropna().empty:
        avg_score = round(df["match_score"].mean(), 1)
        max_score = int(df["match_score"].max())

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Jobs", total_jobs)
    col2.metric("Remote Jobs", remote_jobs)
    col3.metric("Developer Roles", developer_jobs)
    col4.metric("Avg Match Score", avg_score)
    col5.metric("Highest Score", max_score)


def show_charts(df):
    """Display Streamlit charts."""
    st.subheader("Job Market Charts")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Career Path Breakdown")
        if "role_family" in df.columns and not df.empty:
            role_counts = df["role_family"].value_counts()
            st.bar_chart(role_counts, horizontal=True)
        else:
            st.info("No career path data available.")

    with col2:
        st.markdown("### Most Requested Skills")
        skill_counts = get_skill_counts(df).head(12)
        if not skill_counts.empty:
            st.bar_chart(skill_counts.set_index("skill")["count"], horizontal=True)
        else:
            st.info("No skill keyword data available.")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("### Most Common Job Titles")
        if "job_title" in df.columns and not df.empty:
            title_counts = df["job_title"].value_counts().head(12)
            st.bar_chart(title_counts, horizontal=True)
        else:
            st.info("No job title data available.")

    with col4:
        st.markdown("### Jobs by Search Term")
        if "search_term" in df.columns and not df.empty:
            search_counts = df["search_term"].value_counts()
            st.bar_chart(search_counts, horizontal=True)
        else:
            st.info("No search term data available.")

    col5, col6 = st.columns(2)

    with col5:
        st.markdown("### Remote Classification")
        if "is_remote" in df.columns and not df.empty:
            remote_counts = (
                df["is_remote"]
                .map({True: "Remote detected", False: "Remote not detected"})
                .value_counts()
            )
            st.bar_chart(remote_counts, horizontal=True)
        else:
            st.info("No remote classification data available.")

    with col6:
        st.markdown("### Match Score Distribution")
        if "match_score" in df.columns and not df.empty:
            score_bins = pd.cut(
                df["match_score"].fillna(0),
                bins=[0, 25, 50, 75, 100],
                labels=["0-25", "26-50", "51-75", "76-100"],
                include_lowest=True,
            )
            st.bar_chart(score_bins.value_counts().sort_index())
        else:
            st.info("No match score data available.")


def show_top_matches(df):
    """Display top matching jobs."""
    st.subheader("Top Jobs by Custom Match Score")

    if "match_score" not in df.columns or df.empty:
        st.info("No match score data available.")
        return

    display_columns = [
        "job_title",
        "role_family",
        "company_name",
        "location",
        "search_term",
        "is_remote",
        "keywords_found",
        "match_score",
        "redirect_url",
    ]

    available_columns = [column for column in display_columns if column in df.columns]

    top_matches = (
        df[available_columns]
        .sort_values(by="match_score", ascending=False)
        .head(15)
    )

    st.dataframe(
        top_matches,
        use_container_width=True,
        hide_index=True,
    )


def show_full_table(df):
    """Display full filtered job table."""
    st.subheader("Filtered Job Records")

    display_columns = [
        "job_title",
        "role_family",
        "company_name",
        "location",
        "salary_min",
        "salary_max",
        "job_category",
        "search_term",
        "date_collected",
        "is_remote",
        "keywords_found",
        "match_score",
        "redirect_url",
    ]

    available_columns = [column for column in display_columns if column in df.columns]

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True,
    )


def show_streamlit_explanation():
    """Display frontend explanation for presentation practice."""
    with st.expander("How this frontend works"):
        st.markdown(
            """
            This dashboard is built with Streamlit, a Python framework for creating
            interactive data apps. Instead of writing a separate HTML, CSS, and JavaScript
            frontend, this app uses Python commands to create the page layout, sidebar filters,
            metric cards, charts, and data tables.

            The dashboard first tries to load cleaned job records from AWS DynamoDB. If AWS is
            unavailable, it falls back to the local `jobs_master.csv` file. Pandas is used to
            clean and filter the dataset, count job titles and skills, classify role families,
            and calculate the values shown in the charts.

            The charts are generated from the dataset instead of being hardcoded. For example,
            the skills chart counts values from the `keywords_found` column, and the career
            path chart classifies job titles into groups like Software / Developer, IT Support,
            Technical Support, Cloud / DevOps, and Cybersecurity.
            """
        )


def main():
    st.markdown(TACTICAL_CSS, unsafe_allow_html=True)

    df, data_source_message = load_data()

    show_header(data_source_message)

    if df.empty:
        st.warning(
            "No job data found. Run `python run_collector.py` first or confirm DynamoDB contains records."
        )
        return

    filtered_df = filter_data(df)

    show_metric_cards(filtered_df)

    st.divider()

    show_charts(filtered_df)

    st.divider()

    show_top_matches(filtered_df)

    st.divider()

    show_full_table(filtered_df)

    st.divider()

    show_streamlit_explanation()


if __name__ == "__main__":
    main()