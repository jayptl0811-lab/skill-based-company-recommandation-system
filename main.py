from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
import sqlite3

from recommender import DEFAULT_WEIGHTS, score_job

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "skillmatch.db"))
SECRET_KEY = os.getenv("SECRET_KEY", "local-development-key-change-before-deployment")
ALGORITHM = "HS256"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
TOKEN = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="SkillMatch API", version="1.0.0", description="Explainable skill-based company and job recommendations.", lifespan=lifespan)
frontend_origins = {"http://127.0.0.1:5500", "http://localhost:5500"}
frontend_origins.update(
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGIN", "").split(",")
    if origin.strip()
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(frontend_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_DATA = [
    ("Northstar Labs", "Technology", "Bengaluru", "201-500", "Build thoughtful data products for teams changing how people work.", [
        ("Machine Learning Engineer", "Build and deploy production ML models for personalization.", 2, 6, "Bachelor's", 1200000, 2200000, "Hybrid", ["Python", "Machine Learning", "SQL", "TensorFlow", "Docker", "AWS"], "Machine Learning Engineer"),
        ("Data Analyst", "Turn product data into clear insights and experiments.", 0, 3, "Bachelor's", 700000, 1200000, "Remote", ["Python", "SQL", "Tableau", "Statistics", "Pandas"], "Data Analyst"),
    ]),
    ("Orbit Fintech", "Finance", "Mumbai", "501-1000", "Making everyday financial services simpler, safer, and more inclusive.", [
        ("Backend Engineer", "Design resilient APIs and payment services at scale.", 2, 5, "Bachelor's", 1400000, 2400000, "On-site", ["Java", "Spring Boot", "SQL", "Docker", "AWS", "REST APIs"], "Backend Engineer"),
        ("Product Data Analyst", "Partner with product teams to understand customer journeys.", 1, 4, "Bachelor's", 900000, 1600000, "Hybrid", ["SQL", "Python", "Excel", "Power BI", "Statistics"], "Data Analyst"),
    ]),
    ("Canopy Health", "Healthcare", "Hyderabad", "51-200", "A care technology company focused on making better health outcomes accessible.", [
        ("Data Scientist", "Use predictive analytics to help care teams make better decisions.", 1, 4, "Master's", 1100000, 1900000, "Remote", ["Python", "Machine Learning", "Pandas", "SQL", "Scikit-learn", "NLP"], "Data Scientist"),
    ]),
    ("Pixel & Pine", "E-commerce", "Pune", "201-500", "A growing commerce studio connecting independent brands with modern customers.", [
        ("Frontend Developer", "Create accessible, fast storefront experiences with a collaborative product team.", 1, 4, "Bachelor's", 850000, 1500000, "Hybrid", ["JavaScript", "React", "TypeScript", "HTML", "CSS", "Accessibility"], "Frontend Developer"),
    ]),
    ("GreenGrid Energy", "Energy", "Delhi", "51-200", "Modernizing energy infrastructure through smart, sustainable software.", [
        ("Cloud Engineer", "Operate secure cloud infrastructure for a new generation of clean-energy products.", 2, 5, "Bachelor's", 1300000, 2100000, "On-site", ["AWS", "Docker", "Kubernetes", "Terraform", "Python", "Linux"], "Cloud Engineer"),
    ]),
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}:{digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def init_db() -> None:
    with connect() as db:
        db.executescript((BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
        if db.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 0:
            for name, industry, location, size, description, jobs in SAMPLE_DATA:
                company_id = db.execute(
                    "INSERT INTO companies(name, industry, location, size, description) VALUES(?,?,?,?,?)",
                    (name, industry, location, size, description),
                ).lastrowid
                for title, desc, emin, emax, education, smin, smax, mode, skills, _role in jobs:
                    job_id = db.execute(
                        """INSERT INTO jobs(company_id,title,description,experience_min,experience_max,education,
                        salary_min,salary_max,work_mode) VALUES(?,?,?,?,?,?,?,?,?)""",
                        (company_id, title, desc, emin, emax, education, smin, smax, mode),
                    ).lastrowid
                    db.executemany("INSERT INTO job_skills(job_id,skill) VALUES(?,?)", [(job_id, s) for s in skills])
        if db.execute("SELECT COUNT(*) FROM recommendation_weights").fetchone()[0] == 0:
            db.executemany("INSERT INTO recommendation_weights(factor,weight) VALUES(?,?)", DEFAULT_WEIGHTS.items())
        admin_email = os.getenv("ADMIN_EMAIL", "")
        admin_password = os.getenv("ADMIN_PASSWORD", "")
        if admin_email and admin_password and not db.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone():
            user_id = db.execute(
                "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'admin')",
                ("Administrator", admin_email, hash_password(admin_password)),
            ).lastrowid
            db.execute("INSERT INTO user_profiles(user_id) VALUES(?)", (user_id,))


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class ProfileInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    experience_years: float = Field(ge=0, le=60)
    education: str = Field(default="", max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=80)
    education_history: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    preferred_roles: list[str] = Field(default_factory=list, max_length=20)
    preferred_industries: list[str] = Field(default_factory=list, max_length=20)
    preferred_locations: list[str] = Field(default_factory=list, max_length=20)
    certifications: list[str] = Field(default_factory=list, max_length=30)
    projects: list[dict[str, str]] = Field(default_factory=list, max_length=30)


class CompanyInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    industry: str = Field(min_length=2, max_length=80)
    location: str = Field(min_length=2, max_length=100)
    size: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=5, max_length=2000)


class JobInput(BaseModel):
    company_id: int
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=3000)
    skills: list[str] = Field(min_length=1, max_length=60)
    experience_min: float = Field(ge=0, le=60)
    experience_max: float = Field(ge=0, le=60)
    education: str = Field(default="", max_length=120)
    salary_min: int = Field(default=0, ge=0)
    salary_max: int = Field(default=0, ge=0)
    work_mode: str = Field(default="Hybrid", pattern="^(Remote|Hybrid|On-site)$")


def create_token(user: sqlite3.Row) -> str:
    from datetime import datetime, timedelta, timezone
    return jwt.encode({"sub": str(user["id"]), "role": user["role"], "exp": datetime.now(timezone.utc) + timedelta(hours=24)}, SECRET_KEY, algorithm=ALGORITHM)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(TOKEN)) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    with connect() as db:
        row = db.execute("SELECT id,name,email,role FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return dict(row)


def admin_user(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def profile_for(user_id: int, db: sqlite3.Connection) -> dict[str, Any]:
    row = db.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,)).fetchone()
    user = db.execute("SELECT name,email FROM users WHERE id=?", (user_id,)).fetchone()
    if not row or not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "name": user["name"], "email": user["email"],
        "experience_years": row["experience_years"], "education": row["education"],
        "preferred_roles": json.loads(row["preferred_roles"]),
        "preferred_industries": json.loads(row["preferred_industries"]),
        "preferred_locations": json.loads(row["preferred_locations"]),
        "skills": [dict(r) for r in db.execute("SELECT skill,level FROM user_skills WHERE user_id=? ORDER BY skill", (user_id,))],
        "education_history": [dict(r) for r in db.execute("""SELECT qualification,field_of_study,institution,graduation_year
            FROM user_education WHERE user_id=? ORDER BY id""", (user_id,))],
        "certifications": [r["name"] for r in db.execute("SELECT name FROM user_certifications WHERE user_id=?", (user_id,))],
        "projects": [dict(r) for r in db.execute("SELECT name,description FROM user_projects WHERE user_id=?", (user_id,))],
        "resume_filename": row["resume_filename"],
    }


def job_record(job_id: int, db: sqlite3.Connection) -> dict[str, Any]:
    row = db.execute("""SELECT j.*, c.name company_name,c.industry,c.location,c.size,c.description company_description
        FROM jobs j JOIN companies c ON c.id=j.company_id WHERE j.id=?""", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    result = dict(row)
    result["skills"] = [r["skill"] for r in db.execute("SELECT skill FROM job_skills WHERE job_id=? ORDER BY skill", (job_id,))]
    result["company"] = {"id": row["company_id"], "name": row["company_name"], "industry": row["industry"], "location": row["location"], "size": row["size"], "description": row["company_description"]}
    return result


def user_recommendations(user_id: int, db: sqlite3.Connection) -> list[dict[str, Any]]:
    raw = profile_for(user_id, db)
    profile = {**raw, "skills": [x["skill"] for x in raw["skills"]], "project_text": [p["name"] + " " + p["description"] for p in raw["projects"]]}
    weights = {r["factor"]: r["weight"] for r in db.execute("SELECT factor,weight FROM recommendation_weights")}
    applied_job_ids = {r["job_id"] for r in db.execute("SELECT job_id FROM job_applications WHERE user_id=?", (user_id,))}
    out = []
    for row in db.execute("SELECT id FROM jobs WHERE status='active'"):
        job = job_record(row["id"], db)
        match = score_job(profile, job, weights)
        job.update(match)
        job["applied"] = job["id"] in applied_job_ids
        out.append(job)
        db.execute("INSERT INTO recommendation_history(user_id,job_id,score) VALUES(?,?,?)", (user_id, job["id"], match["score"]))
    return sorted(out, key=lambda item: item["score"], reverse=True)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/register")
@app.get("/login")
def auth_page() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/assets/{filename}")
def assets(filename: str) -> FileResponse:
    if filename not in {"app.js", "styles.css"}:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(BASE_DIR / "static" / filename)


@app.post("/api/auth/register", status_code=201)
def register(body: RegisterInput) -> dict[str, Any]:
    try:
        with connect() as db:
            user_id = db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)", (body.name.strip(), body.email.lower(), hash_password(body.password))).lastrowid
            db.execute("INSERT INTO user_profiles(user_id) VALUES(?)", (user_id,))
            user = db.execute("SELECT id,name,email,role FROM users WHERE id=?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    return {"token": create_token(user), "user": dict(user)}


@app.post("/api/auth/login")
def login(body: LoginInput) -> dict[str, Any]:
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (body.email.lower(),)).fetchone()
    if not user or not check_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return {"token": create_token(user), "user": {k: user[k] for k in ("id", "name", "email", "role")}}


@app.get("/api/auth/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return user


@app.get("/api/profile")
def get_profile(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connect() as db:
        return profile_for(user["id"], db)


@app.put("/api/profile")
def update_profile(body: ProfileInput, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connect() as db:
        db.execute("UPDATE users SET name=? WHERE id=?", (body.name.strip(), user["id"]))
        db.execute("""UPDATE user_profiles SET experience_years=?,education=?,preferred_roles=?,
            preferred_industries=?,preferred_locations=? WHERE user_id=?""",
            (body.experience_years, body.education, json.dumps(body.preferred_roles), json.dumps(body.preferred_industries), json.dumps(body.preferred_locations), user["id"]))
        db.execute("DELETE FROM user_skills WHERE user_id=?", (user["id"],))
        db.executemany("INSERT INTO user_skills(user_id,skill) VALUES(?,?)", [(user["id"], s.strip()) for s in dict.fromkeys(body.skills) if s.strip()])
        db.execute("DELETE FROM user_education WHERE user_id=?", (user["id"],))
        db.executemany("""INSERT INTO user_education(user_id,qualification,field_of_study,institution,graduation_year)
            VALUES(?,?,?,?,?)""", [(user["id"], item.get("qualification", "").strip(), item.get("field_of_study", "").strip(),
            item.get("institution", "").strip(), item.get("graduation_year", "").strip())
            for item in body.education_history if item.get("qualification", "").strip()])
        db.execute("DELETE FROM user_certifications WHERE user_id=?", (user["id"],))
        db.executemany("INSERT INTO user_certifications(user_id,name) VALUES(?,?)", [(user["id"], s.strip()) for s in body.certifications if s.strip()])
        db.execute("DELETE FROM user_projects WHERE user_id=?", (user["id"],))
        db.executemany("INSERT INTO user_projects(user_id,name,description) VALUES(?,?,?)", [(user["id"], p.get("name", "").strip(), p.get("description", "").strip()) for p in body.projects if p.get("name", "").strip()])
        return profile_for(user["id"], db)


@app.post("/api/profile/resume")
async def upload_resume(file: UploadFile = File(...), user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx"}:
        raise HTTPException(status_code=400, detail="Resume must be a PDF or Word document")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Resume must be 5 MB or smaller")
    if suffix == ".pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF")
    if suffix == ".docx" and not content.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid DOCX document")
    if suffix == ".doc" and not content.startswith(bytes.fromhex("D0CF11E0")):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid DOC document")
    filename = f"{user['id']}_{secrets.token_hex(12)}{suffix}"
    (UPLOAD_DIR / filename).write_bytes(content)
    with connect() as db:
        db.execute("UPDATE user_profiles SET resume_filename=? WHERE user_id=?", (filename, user["id"]))
    return {"message": "Resume uploaded", "filename": Path(file.filename or "resume").name}


@app.get("/api/companies")
def companies(search: str = "", industry: str = "", location: str = "", size: str = "", user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("""SELECT c.*,COUNT(DISTINCT j.id) job_count FROM companies c LEFT JOIN jobs j ON j.company_id=c.id
            WHERE (?='' OR c.name LIKE '%'||?||'%' OR c.description LIKE '%'||?||'%')
            AND (?='' OR c.industry=?) AND (?='' OR c.location=?) AND (?='' OR c.size=?) GROUP BY c.id ORDER BY c.name""",
            (search, search, search, industry, industry, location, location, size, size)).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/jobs")
def jobs(search: str = "", skill: str = "", role: str = "", industry: str = "", location: str = "", company_size: str = "", work_mode: str = "", min_experience: float | None = None, max_salary: int | None = None, min_match: int = Query(default=0, ge=0, le=100), user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with connect() as db:
        records = user_recommendations(user["id"], db)
        results = [j for j in records if
            (not search or search.lower() in j["title"].lower() or search.lower() in j["description"].lower() or search.lower() in j["company"]["name"].lower()) and
            (not skill or any(skill.lower() in s.lower() for s in j["skills"])) and
            (not role or role.lower() in j["title"].lower()) and
            (not industry or industry.lower() == j["company"]["industry"].lower()) and
            (not location or location.lower() in j["company"]["location"].lower()) and
            (not company_size or company_size.lower() == j["company"]["size"].lower()) and
            (not work_mode or work_mode.lower() == j["work_mode"].lower()) and
            (min_experience is None or j["experience_min"] <= min_experience) and
            (max_salary is None or not j["salary_max"] or j["salary_min"] <= max_salary) and j["score"] >= min_match]
        return results


@app.post("/api/jobs/{job_id}/apply")
def apply_to_job(job_id: int, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connect() as db:
        job = db.execute("SELECT id FROM jobs WHERE id=? AND status='active'", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Active job not found")
        existing = db.execute(
            "SELECT 1 FROM job_applications WHERE user_id=? AND job_id=?",
            (user["id"], job_id),
        ).fetchone()
        if existing:
            return {"applied": True, "already_applied": True}
        db.execute("INSERT INTO job_applications(user_id,job_id) VALUES(?,?)", (user["id"], job_id))
        return {"applied": True, "already_applied": False}


@app.get("/api/recommendations")
def recommendations(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connect() as db:
        matches = user_recommendations(user["id"], db)
        companies_by_id: dict[int, dict[str, Any]] = {}
        for job in matches:
            company = companies_by_id.setdefault(job["company_id"], {**job["company"], "score": job["score"], "matching_skills": job["matching_skills"], "missing_skills": job["missing_skills"], "reasons": job["reasons"], "jobs": []})
            company["score"] = max(company["score"], job["score"])
            company["jobs"].append(job)
        return {"jobs": matches, "companies": sorted(companies_by_id.values(), key=lambda x: x["score"], reverse=True)}


@app.get("/api/dashboard")
def dashboard(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connect() as db:
        profile = profile_for(user["id"], db)
        recommendations_data = user_recommendations(user["id"], db)
        fields = [bool(profile["name"]), bool(profile["skills"]), bool(profile["education"]), bool(profile["preferred_roles"]), profile["experience_years"] > 0, bool(profile["certifications"] or profile["projects"])]
        demand = db.execute("""SELECT js.skill,COUNT(*) demand FROM job_skills js JOIN jobs j ON j.id=js.job_id
            WHERE j.status='active' GROUP BY js.skill ORDER BY demand DESC,js.skill LIMIT 8""").fetchall()
        skill_set = {s["skill"].lower() for s in profile["skills"]}
        gaps: dict[str, int] = {}
        for match in recommendations_data:
            if match["score"] >= 35:
                for skill in match["missing_skills"]:
                    gaps[skill] = gaps.get(skill, 0) + 1
        saved = [dict(r) for r in db.execute("SELECT item_type,item_id FROM saved_items WHERE user_id=?", (user["id"],))]
        return {"profile_completion": round(sum(fields) / len(fields) * 100), "top_jobs": recommendations_data[:3],
            "top_companies": recommendations_data[:3], "in_demand_skills": [dict(r, learned=r["skill"].lower() in skill_set) for r in demand],
            "skill_gaps": [{"skill": k, "count": v} for k, v in sorted(gaps.items(), key=lambda x: (-x[1], x[0]))[:6]],
            "saved_count": len(saved), "saved": saved, "total_jobs": len(recommendations_data)}


@app.get("/api/saved")
def get_saved(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connect() as db:
        rows = db.execute("SELECT item_type,item_id FROM saved_items WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
        jobs_out, companies_out = [], []
        for row in rows:
            if row["item_type"] == "job":
                try:
                    job = job_record(row["item_id"], db)
                    job["applied"] = bool(db.execute(
                        "SELECT 1 FROM job_applications WHERE user_id=? AND job_id=?",
                        (user["id"], row["item_id"]),
                    ).fetchone())
                    jobs_out.append(job)
                except HTTPException:
                    continue
            else:
                company = db.execute("SELECT * FROM companies WHERE id=?", (row["item_id"],)).fetchone()
                if company:
                    companies_out.append(dict(company))
        return {"jobs": jobs_out, "companies": companies_out}


@app.post("/api/saved/{item_type}/{item_id}")
def toggle_saved(item_type: str, item_id: int, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if item_type not in ("job", "company"):
        raise HTTPException(status_code=400, detail="Item type must be job or company")
    table = "jobs" if item_type == "job" else "companies"
    with connect() as db:
        if not db.execute(f"SELECT id FROM {table} WHERE id=?", (item_id,)).fetchone():
            raise HTTPException(status_code=404, detail=f"{item_type.title()} not found")
        exists = db.execute("SELECT 1 FROM saved_items WHERE user_id=? AND item_type=? AND item_id=?", (user["id"], item_type, item_id)).fetchone()
        if exists:
            db.execute("DELETE FROM saved_items WHERE user_id=? AND item_type=? AND item_id=?", (user["id"], item_type, item_id))
            return {"saved": False}
        db.execute("INSERT INTO saved_items(user_id,item_type,item_id) VALUES(?,?,?)", (user["id"], item_type, item_id))
        return {"saved": True}


@app.get("/api/admin/weights")
def get_weights(_: dict[str, Any] = Depends(admin_user)) -> dict[str, float]:
    with connect() as db:
        return {r["factor"]: r["weight"] for r in db.execute("SELECT factor,weight FROM recommendation_weights")}


@app.put("/api/admin/weights")
def set_weights(body: dict[str, float], _: dict[str, Any] = Depends(admin_user)) -> dict[str, float]:
    if set(body) != set(DEFAULT_WEIGHTS) or any(value < 0 or value > 1 for value in body.values()) or sum(body.values()) <= 0:
        raise HTTPException(status_code=422, detail="Provide all seven weights as values between 0 and 1, with a nonzero total")
    with connect() as db:
        db.executemany("UPDATE recommendation_weights SET weight=? WHERE factor=?", [(v, k) for k, v in body.items()])
    return body


@app.post("/api/admin/companies", status_code=201)
def create_company(body: CompanyInput, _: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    try:
        with connect() as db:
            company_id = db.execute("INSERT INTO companies(name,industry,location,size,description) VALUES(?,?,?,?,?)", (body.name, body.industry, body.location, body.size, body.description)).lastrowid
            return dict(db.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Company name already exists")


@app.put("/api/admin/companies/{company_id}")
def update_company(company_id: int, body: CompanyInput, _: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    try:
        with connect() as db:
            cur = db.execute("UPDATE companies SET name=?,industry=?,location=?,size=?,description=? WHERE id=?", (body.name, body.industry, body.location, body.size, body.description, company_id))
            if not cur.rowcount:
                raise HTTPException(status_code=404, detail="Company not found")
            return dict(db.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Company name already exists")


@app.delete("/api/admin/companies/{company_id}")
def delete_company(company_id: int, _: dict[str, Any] = Depends(admin_user)) -> dict[str, str]:
    with connect() as db:
        job_ids = [r["id"] for r in db.execute("SELECT id FROM jobs WHERE company_id=?", (company_id,))]
        if job_ids:
            db.executemany("DELETE FROM saved_items WHERE item_type='job' AND item_id=?", [(job_id,) for job_id in job_ids])
        db.execute("DELETE FROM saved_items WHERE item_type='company' AND item_id=?", (company_id,))
        cur = db.execute("DELETE FROM companies WHERE id=?", (company_id,))
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Company not found")
    return {"message": "Company and associated jobs deleted"}


@app.post("/api/admin/jobs", status_code=201)
def create_job(body: JobInput, _: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    if body.experience_max < body.experience_min or body.salary_max < body.salary_min:
        raise HTTPException(status_code=422, detail="Maximum values must be greater than or equal to minimum values")
    with connect() as db:
        if not db.execute("SELECT id FROM companies WHERE id=?", (body.company_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Company not found")
        job_id = db.execute("""INSERT INTO jobs(company_id,title,description,experience_min,experience_max,education,
            salary_min,salary_max,work_mode) VALUES(?,?,?,?,?,?,?,?,?)""",
            (body.company_id, body.title, body.description, body.experience_min, body.experience_max, body.education, body.salary_min, body.salary_max, body.work_mode)).lastrowid
        db.executemany("INSERT INTO job_skills(job_id,skill) VALUES(?,?)", [(job_id, s.strip()) for s in dict.fromkeys(body.skills) if s.strip()])
        return job_record(job_id, db)


@app.put("/api/admin/jobs/{job_id}")
def update_job(job_id: int, body: JobInput, _: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    if body.experience_max < body.experience_min or body.salary_max < body.salary_min:
        raise HTTPException(status_code=422, detail="Maximum values must be greater than or equal to minimum values")
    with connect() as db:
        if not db.execute("SELECT id FROM companies WHERE id=?", (body.company_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Company not found")
        cur = db.execute("""UPDATE jobs SET company_id=?,title=?,description=?,experience_min=?,experience_max=?,education=?,
            salary_min=?,salary_max=?,work_mode=? WHERE id=?""",
            (body.company_id, body.title, body.description, body.experience_min, body.experience_max, body.education, body.salary_min, body.salary_max, body.work_mode, job_id))
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Job not found")
        db.execute("DELETE FROM job_skills WHERE job_id=?", (job_id,))
        db.executemany("INSERT INTO job_skills(job_id,skill) VALUES(?,?)", [(job_id, s.strip()) for s in dict.fromkeys(body.skills) if s.strip()])
        return job_record(job_id, db)


@app.delete("/api/admin/jobs/{job_id}")
def delete_job(job_id: int, _: dict[str, Any] = Depends(admin_user)) -> dict[str, str]:
    with connect() as db:
        db.execute("DELETE FROM saved_items WHERE item_type='job' AND item_id=?", (job_id,))
        cur = db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted"}


@app.get("/api/admin/overview")
def admin_overview(_: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    with connect() as db:
        return {"users": db.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
            "companies": db.execute("SELECT COUNT(*) FROM companies").fetchone()[0],
            "jobs": db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
            "companies_list": [dict(r) for r in db.execute("SELECT * FROM companies ORDER BY name")],
            "jobs_list": [job_record(r["id"], db) for r in db.execute("SELECT id FROM jobs ORDER BY id")]}
