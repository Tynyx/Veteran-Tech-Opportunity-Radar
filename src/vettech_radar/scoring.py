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
        "virtual"
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
        "customer support"
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
    remote, support-focused, junior-friendly, and connected to the user's tech background.
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
        "application support"
    ]

    if any(term in text for term in support_terms):
        score += 20

    junior_terms = [
        "junior",
        "entry level",
        "entry-level",
        "associate",
        "trainee",
        "apprentice"
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