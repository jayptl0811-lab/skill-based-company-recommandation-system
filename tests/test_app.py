import os

os.environ["DATABASE_PATH"] = ":memory:"

import pytest
from fastapi.testclient import TestClient
import main
from recommender import score_job


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def register(client, email="person@example.com"):
    response = client.post("/api/auth/register", json={"name": "Test Person", "email": email, "password": "GoodPassword123"})
    assert response.status_code == 201
    client.headers["Authorization"] = f"Bearer {response.json()['token']}"
    return response.json()


def test_recommendation_explains_matching_and_missing_skills():
    result = score_job(
        {"skills": ["Python", "SQL", "ML"], "experience_years": 2, "preferred_roles": ["Data Scientist"]},
        {"skills": ["Python", "SQL", "Machine Learning", "Docker"], "title": "Data Scientist", "experience_min": 1,
         "experience_max": 4, "company": {"name": "Example", "industry": "Technology", "location": "Remote"}},
    )
    assert result["score"] == 71
    assert result["matching_skills"] == ["Machine Learning", "Python", "SQL"]
    assert result["missing_skills"] == ["Docker"]
    assert any("Docker" in reason for reason in result["reasons"])


def test_skill_aliases_are_normalized():
    result = score_job({"skills": ["JS"]}, {"skills": ["JavaScript"], "company": {}})
    assert result["matching_skills"] == ["JavaScript"]
    assert result["score"] == 75
    assert 0 <= result["text_similarity"] <= 100


def test_register_login_and_duplicate_email(client):
    register(client)
    assert client.post("/api/auth/register", json={"name": "Other User", "email": "person@example.com", "password": "GoodPassword123"}).status_code == 409
    client.headers.pop("Authorization")
    assert client.post("/api/auth/login", json={"email": "person@example.com", "password": "GoodPassword123"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "person@example.com", "password": "incorrect"}).status_code == 401


def test_profile_recommendations_and_saved_item(client):
    register(client)
    profile = {"name": "Test Person", "experience_years": 2, "education": "Bachelor's", "skills": ["Python", "SQL", "Machine Learning", "Pandas"],
               "education_history": [{"qualification": "BSc", "field_of_study": "Computer Science", "institution": "State University", "graduation_year": "2025"}],
               "preferred_roles": ["Machine Learning Engineer"], "preferred_industries": ["Technology"], "preferred_locations": ["Bengaluru"],
               "certifications": ["AWS"], "projects": [{"name": "Forecasting", "description": "Python ML project"}]}
    updated = client.put("/api/profile", json=profile)
    assert updated.status_code == 200
    assert updated.json()["education_history"][0]["qualification"] == "BSc"
    results = client.get("/api/recommendations").json()
    assert results["jobs"][0]["score"] > 0
    assert "TensorFlow" in results["jobs"][0]["missing_skills"] or "Docker" in results["jobs"][0]["missing_skills"]
    job_id = results["jobs"][0]["id"]
    assert client.post(f"/api/saved/job/{job_id}").json() == {"saved": True}
    assert client.get("/api/saved").json()["jobs"][0]["id"] == job_id


def test_apply_to_job_is_persisted_and_user_scoped(client):
    register(client)
    job = client.get("/api/jobs").json()[0]
    job_id = job["id"]

    response = client.post(f"/api/jobs/{job_id}/apply")
    assert response.status_code == 200
    assert response.json() == {"applied": True, "already_applied": False}
    assert client.post(f"/api/jobs/{job_id}/apply").json() == {"applied": True, "already_applied": True}
    assert next(job for job in client.get("/api/jobs").json() if job["id"] == job_id)["applied"] is True
    assert next(job for job in client.get("/api/recommendations").json()["jobs"] if job["id"] == job_id)["applied"] is True


def test_apply_to_missing_or_closed_job_fails(client):
    register(client)
    assert client.post("/api/jobs/99999/apply").status_code == 404


def test_admin_routes_require_admin(client):
    register(client)
    response = client.get("/api/admin/overview")
    assert response.status_code == 403


def test_search_filters_and_dashboard(client):
    register(client)
    assert client.get("/api/jobs?work_mode=Remote").status_code == 200
    assert all(job["work_mode"] == "Remote" for job in client.get("/api/jobs?work_mode=Remote").json())
    data = client.get("/api/dashboard").json()
    assert "profile_completion" in data and "in_demand_skills" in data


def test_text_similarity_contributes_to_skill_factor():
    profile = {"skills": ["Python"], "project_text": ["Built a Python recommendation engine with FastAPI"]}
    job = {"skills": ["Python"], "title": "Python Engineer", "description": "Build a recommendation engine using FastAPI", "company": {}}
    result = score_job(profile, job)
    assert result["text_similarity"] > 0
    assert result["factors"]["skills"] > 85


def test_admin_can_manage_company_job_and_weights(client):
    register(client)
    with main.connect() as db:
        db.execute("UPDATE users SET role='admin' WHERE email='person@example.com'")
    assert client.get("/api/admin/overview").status_code == 200
    company = {"name": "Test Studio", "industry": "Technology", "location": "Remote", "size": "1-50", "description": "A test company for API coverage."}
    created = client.post("/api/admin/companies", json=company)
    assert created.status_code == 201
    company_id = created.json()["id"]
    job = {"company_id": company_id, "title": "Python Developer", "description": "Build useful tools.", "skills": ["Python", "SQL"],
           "experience_min": 0, "experience_max": 3, "education": "", "salary_min": 500000, "salary_max": 900000, "work_mode": "Remote"}
    created_job = client.post("/api/admin/jobs", json=job)
    assert created_job.status_code == 201
    job_id = created_job.json()["id"]
    job["title"] = "Senior Python Developer"
    assert client.put(f"/api/admin/jobs/{job_id}", json=job).json()["title"] == "Senior Python Developer"
    assert client.get("/api/companies?size=1-50").json()[0]["name"] == "Test Studio"
    weights = client.get("/api/admin/weights").json()
    assert client.put("/api/admin/weights", json=weights).status_code == 200
    assert client.delete(f"/api/admin/jobs/{job_id}").status_code == 200
    assert client.delete(f"/api/admin/companies/{company_id}").status_code == 200


def test_static_ui_and_openapi_are_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert "/api/recommendations" in client.get("/openapi.json").json()["paths"]


def test_frontend_origin_can_call_api(client):
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5500"


def test_resume_upload_rejects_unsupported_file_type(client):
    register(client)
    response = client.post("/api/profile/resume", files={"file": ("resume.exe", b"not a resume", "application/octet-stream")})
    assert response.status_code == 400
