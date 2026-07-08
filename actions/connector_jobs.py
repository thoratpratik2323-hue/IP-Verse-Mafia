"""
actions/connector_jobs.py -- Hyper-local job connection registry.
"""
import json
from pathlib import Path

JOBS_DB = Path(__file__).resolve().parent.parent / "config" / "connector_jobs.json"

DEFAULT_JOBS = [
    {
        "id": "JOB_001",
        "title": "Barista / Café Assistant",
        "employer": "Blue Tokai Coffee",
        "location": "Pune, Maharashtra",
        "type": "Part-Time",
        "skills": ["communication", "coffee", "customer service"],
        "description": "Looking for a part-time barista to handle morning coffee service and customer checkout."
    },
    {
        "id": "JOB_002",
        "title": "Delivery Executive",
        "employer": "Zomato Local Delivery",
        "location": "Nashik, Maharashtra",
        "type": "Flexible",
        "skills": ["driving", "navigation"],
        "description": "Deliver food packages locally within a 5km radius. Flexible hours."
    },
    {
        "id": "JOB_003",
        "title": "Frontend React Intern",
        "employer": "XBLT Studio",
        "location": "Remote",
        "type": "Internship",
        "skills": ["react", "next.js", "tailwind css"],
        "description": "Help build next-gen generative IDE interfaces. Mentorship under Harsh."
    }
]

def load_jobs() -> list:
    if not JOBS_DB.exists():
        JOBS_DB.parent.mkdir(parents=True, exist_ok=True)
        JOBS_DB.write_text(json.dumps(DEFAULT_JOBS, indent=4), encoding="utf-8")
        return DEFAULT_JOBS
    try:
        return json.loads(JOBS_DB.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_JOBS

def save_jobs(jobs: list):
    try:
        JOBS_DB.write_text(json.dumps(jobs, indent=4), encoding="utf-8")
    except Exception:
        pass

def connector_jobs(
    action: str = "search",
    query: str | None = None,
    location: str | None = None,
    job_details: dict | None = None,
    player=None
) -> str:
    jobs = load_jobs()
    
    if action == "post" and job_details:
        title = job_details.get("title")
        employer = job_details.get("employer", "Anonymous Employer")
        loc = job_details.get("location", "Local")
        jtype = job_details.get("type", "Full-Time")
        skills = job_details.get("skills", [])
        desc = job_details.get("description", "")
        
        if not title:
            return "Bhai, job post karne ke liye 'title' parameters hona zaroori hai!"
            
        new_job = {
            "id": f"JOB_{len(jobs) + 1:03d}",
            "title": title,
            "employer": employer,
            "location": loc,
            "type": jtype,
            "skills": skills,
            "description": desc
        }
        jobs.append(new_job)
        save_jobs(jobs)
        msg = f"✅ [Connector] Job posted successfully: '{title}' at '{employer}' ({loc})!"
        if player:
            try:
                player.write_log(f"SYS: {msg}")
            except Exception:
                pass
        return msg
        
    # Default is search
    query_l = (query or "").lower()
    loc_l = (location or "").lower()
    
    results = []
    for j in jobs:
        match_q = not query_l or query_l in j["title"].lower() or query_l in j["employer"].lower() or any(query_l in s.lower() for s in j["skills"])
        match_l = not loc_l or loc_l in j["location"].lower()
        if match_q and match_l:
            results.append(j)
            
    if not results:
        return "Bhai, is query ke liye koi local jobs nahi mile. Naye job post karne ke liye bolo!"
        
    formatted = []
    for r in results:
        skills_str = ", ".join(r["skills"])
        formatted.append(
            f"📍 **[{r['id']}] {r['title']}**\n"
            f"   - **Employer:** {r['employer']} | **Location:** {r['location']}\n"
            f"   - **Type:** {r['type']} | **Skills:** {skills_str}\n"
            f"   - *Description:* {r['description']}"
        )
        
    return f"🔍 **Connector Local Job Listings ({len(results)} matches):**\n\n" + "\n\n".join(formatted)
