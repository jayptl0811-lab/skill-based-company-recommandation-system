"""Explainable, configurable recommendation scoring."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

DEFAULT_WEIGHTS = {
    "skills": 0.50,
    "experience": 0.15,
    "education": 0.10,
    "role": 0.10,
    "industry": 0.05,
    "location": 0.05,
    "extras": 0.05,
}

ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "scikit learn": "scikit-learn",
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "structured query language": "sql",
    "node": "node.js",
}
STOP_WORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into", "is", "it", "of", "on", "or", "our", "the", "this", "to", "with", "you"}


def normalize(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9+#.\s-]", " ", value.lower()).strip()
    return ALIASES.get(re.sub(r"\s+", " ", cleaned), re.sub(r"\s+", " ", cleaned))


def tfidf_cosine(left: str, right: str) -> float:
    """Return TF-IDF cosine similarity for two short profile/job documents."""
    token_pattern = re.compile(r"[a-z0-9+#.]+")
    documents = [
        [expanded for token in token_pattern.findall(left.lower()) for expanded in token_pattern.findall(normalize(token)) if expanded not in STOP_WORDS],
        [expanded for token in token_pattern.findall(right.lower()) for expanded in token_pattern.findall(normalize(token)) if expanded not in STOP_WORDS],
    ]
    if not documents[0] or not documents[1]:
        return 0.0
    frequencies = [Counter(document) for document in documents]
    terms = set(frequencies[0]) | set(frequencies[1])
    vectors = []
    for counts in frequencies:
        vector = {
            term: (1 + math.log(counts[term])) * (1 + math.log(2 / (1 + sum(term in doc for doc in frequencies))))
            for term in terms if counts[term]
        }
        vectors.append(vector)
    dot = sum(vectors[0].get(term, 0) * vectors[1].get(term, 0) for term in terms)
    norms = [math.sqrt(sum(value * value for value in vector.values())) for vector in vectors]
    return dot / (norms[0] * norms[1]) if norms[0] and norms[1] else 0.0


def score_job(profile: dict[str, Any], job: dict[str, Any], weights: dict[str, float] | None = None) -> dict[str, Any]:
    """Score a job against a user profile and explain the result."""
    weights = weights or DEFAULT_WEIGHTS
    supplied_total = sum(max(0.0, float(weights.get(key, 0))) for key in DEFAULT_WEIGHTS)
    if supplied_total <= 0:
        weights = DEFAULT_WEIGHTS
        supplied_total = 1.0

    user_skills = {normalize(skill) for skill in profile.get("skills", [])}
    required_skills = list(dict.fromkeys(job.get("skills", [])))
    required = {normalize(skill) for skill in required_skills}
    matching = sorted((skill for skill in required_skills if normalize(skill) in user_skills), key=str.lower)
    missing = sorted((skill for skill in required_skills if normalize(skill) not in user_skills), key=str.lower)
    skill_coverage = len(matching) / len(required) if required else 0.0
    profile_text = " ".join(profile.get("skills", []) + profile.get("certifications", []) + profile.get("project_text", []))
    job_text = " ".join([job.get("title", ""), job.get("description", ""), *job.get("skills", [])])
    text_similarity = tfidf_cosine(profile_text, job_text)
    skill_score = skill_coverage * 0.85 + text_similarity * 0.15

    years = max(0.0, float(profile.get("experience_years", 0) or 0))
    min_years = float(job.get("experience_min", 0) or 0)
    max_years = float(job.get("experience_max", 50) or 50)
    experience_score = 1.0 if years >= min_years else (years / min_years if min_years else 1.0)
    if years > max_years:
        experience_score = max(0.5, 1.0 - (years - max_years) * 0.05)

    def includes_any(values: list[str], target: str) -> bool:
        return bool(values) and any(normalize(value) in normalize(target) or normalize(target) in normalize(value) for value in values)

    role_score = float(includes_any(profile.get("preferred_roles", []), job.get("title", "")))
    company = job.get("company", {})
    industry_score = float(includes_any(profile.get("preferred_industries", []), company.get("industry", "")))
    location_score = float(includes_any(profile.get("preferred_locations", []), company.get("location", "")))
    user_education = normalize(profile.get("education", ""))
    job_education = normalize(job.get("education", ""))
    education_score = float(not job_education or bool(user_education and job_education in user_education))
    extras = {normalize(item) for item in profile.get("certifications", []) + profile.get("project_text", [])}
    extras_score = min(1.0, len(extras & required) / max(1, min(2, len(required))))

    factors = {
        "skills": skill_score,
        "experience": experience_score,
        "education": education_score,
        "role": role_score,
        "industry": industry_score,
        "location": location_score,
        "extras": extras_score,
    }
    weighted = sum(factors[key] * max(0.0, float(weights.get(key, 0))) for key in factors)
    score = round(weighted / supplied_total * 100)
    company_name = company.get("name", "this team")
    reasons = []
    if matching:
        reasons.append(f"You bring {', '.join(matching[:4])}, which this role needs.")
    if experience_score >= 0.8:
        reasons.append(f"Your {years:g} year(s) of experience fit the role's experience expectations.")
    if role_score:
        reasons.append(f"{job.get('title', 'This role')} aligns with your preferred roles.")
    if industry_score:
        reasons.append(f"{company_name} is in an industry you selected.")
    if location_score:
        reasons.append(f"{company.get('location', 'The location')} matches your location preferences.")
    if not reasons:
        reasons.append(f"{company_name} has an active opening that could help you grow.")
    if missing:
        reasons.append(f"Consider building {', '.join(missing[:4])} to strengthen your application.")
    return {
        "score": score,
        "matching_skills": matching,
        "missing_skills": missing,
        "text_similarity": round(text_similarity * 100),
        "reasons": reasons,
        "factors": {key: round(value * 100) for key, value in factors.items()},
    }
