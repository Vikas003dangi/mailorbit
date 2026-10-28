import re
from typing import Any, Dict, List, Set


# Common high-value tech, engineering, and industry keywords
KNOWN_TECH_KEYWORDS = {
    # Languages
    "python", "javascript", "typescript", "golang", "go", "rust", "java", "c++", "c#", "ruby", "php", "swift", "kotlin",
    # Frontend
    "react", "react.js", "next.js", "vue", "vue.js", "angular", "svelte", "tailwind", "tailwindcss", "html", "css", "redux",
    # Backend & Frameworks
    "fastapi", "django", "flask", "node.js", "express", "nestjs", "spring", "spring boot", "ruby on rails", "asp.net",
    # Databases & Queues
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "cassandra", "kafka", "rabbitmq", "sqlite", "neon",
    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform", "ci/cd", "github actions", "linux", "serverless",
    # Architecture & APIs
    "rest", "restful", "rest api", "graphql", "grpc", "microservices", "distributed systems", "event-driven",
    # Data & AI
    "machine learning", "deep learning", "ai", "llm", "gemini", "openai", "pytorch", "tensorflow", "pandas", "numpy", "data engineering",
}


def normalize_text(text: str) -> str:
    """Normalizes whitespace and converts text to lowercase."""
    return re.sub(r"\s+", " ", text.lower().strip()) if text else ""


def extract_keywords(text: str, custom_keywords: Set[str] = None) -> Set[str]:
    """
    Extracts tech and domain keywords from text (e.g. job description, resume, notes).
    Matches both single words and multi-word phrases (e.g. 'next.js', 'machine learning').
    """
    if not text:
        return set()

    normalized = normalize_text(text)
    vocabulary = KNOWN_TECH_KEYWORDS | (custom_keywords or set())
    found: Set[str] = set()

    # Match multi-word terms and punctuation-containing terms first
    for kw in vocabulary:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, normalized):
            found.add(kw)

    return found


def match_profile_to_jd(
    profile_skills: List[str],
    jd_text: str,
    resume_text: str = "",
) -> Dict[str, Any]:
    """
    Calculates technical skill alignment between a user's profile/resume and a job description:
    - matched_skills: overlapping skills
    - missing_skills: required skills in JD missing from profile
    - match_score: percentage of JD skills matched (0 - 100)
    - pitch_angle: actionable cold outreach summary
    """
    profile_keywords = set()
    for s in profile_skills or []:
        profile_keywords.update(extract_keywords(s))

    if resume_text:
        profile_keywords.update(extract_keywords(resume_text))

    jd_keywords = extract_keywords(jd_text)

    if not jd_keywords:
        return {
            "match_score": 100 if profile_keywords else 0,
            "matched_skills": sorted(list(profile_keywords)),
            "missing_skills": [],
            "total_jd_skills_found": 0,
            "pitch_angle": "Focus on general problem-solving, impact, and strong technical foundation.",
        }

    matched = sorted(list(profile_keywords.intersection(jd_keywords)))
    missing = sorted(list(jd_keywords.difference(profile_keywords)))
    score = round((len(matched) / len(jd_keywords)) * 100)

    if score >= 70:
        angle = f"Strong technical match! Emphasize hands-on expertise in {', '.join(matched[:3])}."
    elif score >= 40:
        angle = f"Moderate match. Highlight {', '.join(matched[:2])} and express enthusiasm to quickly ramp up on {', '.join(missing[:2])}."
    else:
        angle = f"Adjacent skill profile. Pivot to foundational engineering skills, rapid learning, and architecture."

    return {
        "match_score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "total_jd_skills_found": len(jd_keywords),
        "pitch_angle": angle,
    }

