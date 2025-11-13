import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from datetime import datetime
import requests

from database import db, create_document, get_documents
from schemas import Project as ProjectSchema, Message as MessageSchema

app = FastAPI(title="Adewale Portfolio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers
class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class ProjectOut(BaseModel):
    id: ObjectIdStr = Field(..., alias="_id")
    name: str
    description: str
    stack: List[str]
    github: Optional[str] = None
    live: Optional[str] = None
    featured: bool = False
    order: int = 0

    class Config:
        populate_by_name = True

class ContactIn(BaseModel):
    name: str
    email: EmailStr
    message: str

# Seed data on first run
SEED_PROJECTS = [
    {
        "name": "Sarepay",
        "description": "Multi-tenant payment processing system for merchants.",
        "stack": ["PHP", "Laravel", "MySQL", "Redis", "Docker", "AWS"],
        "github": "https://github.com/devwaleh/sarepay",
        "featured": True,
        "order": 1,
    },
    {
        "name": "Piper Backoffice",
        "description": "Admin dashboard for transaction monitoring and settlements.",
        "stack": ["Laravel", "MySQL", "Redis", "Tailwind"],
        "github": "https://github.com/devwaleh/piper-backoffice",
        "featured": True,
        "order": 2,
    },
    {
        "name": "Gridman",
        "description": "Distributed microservice for real-time wallet transactions.",
        "stack": ["Node.js", "Express", "MongoDB", "Docker", "Microservices"],
        "github": "https://github.com/devwaleh/gridman",
        "featured": False,
        "order": 3,
    },
    {
        "name": "Monitraka",
        "description": "AI-powered transaction anomaly detector.",
        "stack": ["Python", "FastAPI", "Scikit-learn", "Redis"],
        "github": "https://github.com/devwaleh/monitraka",
        "featured": False,
        "order": 4,
    },
]

def ensure_seed_projects():
    if db is None:
        return
    count = db["project"].count_documents({})
    if count == 0:
        for p in SEED_PROJECTS:
            create_document("project", ProjectSchema(**p))

# Auth dependency for admin endpoints
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def require_admin(authorization: Optional[str] = Header(None)):
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# Routes
@app.get("/")
def read_root():
    return {"message": "Adewale Portfolio Backend Running"}

@app.get("/api/projects", response_model=List[ProjectOut])
def list_projects():
    ensure_seed_projects()
    items = db["project"].find({}).sort("order", 1)
    return [ProjectOut(**i) for i in items]

@app.post("/api/projects", dependencies=[Depends(require_admin)])
def create_project(project: ProjectSchema):
    _id = create_document("project", project)
    return {"_id": _id}

@app.put("/api/projects/{project_id}", dependencies=[Depends(require_admin)])
def update_project(project_id: str, project: ProjectSchema):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid id")
    res = db["project"].update_one({"_id": ObjectId(project_id)}, {"$set": project.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"updated": True}

@app.delete("/api/projects/{project_id}", dependencies=[Depends(require_admin)])
def delete_project(project_id: str):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid id")
    res = db["project"].delete_one({"_id": ObjectId(project_id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"deleted": True}

@app.post("/api/contact")
def contact(data: ContactIn):
    create_document("message", MessageSchema(**data.model_dump()))
    return {"ok": True, "received_at": datetime.utcnow().isoformat() + "Z"}

# Spotify Now Playing
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

def get_spotify_access_token() -> Optional[str]:
    if not (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET and SPOTIFY_REFRESH_TOKEN):
        return None
    token_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": SPOTIFY_REFRESH_TOKEN,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }
    try:
        resp = requests.post(token_url, headers=headers, data=data, timeout=8)
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        return None
    return None

@app.get("/api/now-playing")
def now_playing():
    token = get_spotify_access_token()
    if not token:
        return {"isPlaying": False}
    try:
        r = requests.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if r.status_code == 204:
            return {"isPlaying": False}
        if r.status_code != 200:
            return {"isPlaying": False}
        data = r.json()
        is_playing = data.get("is_playing", False)
        item = data.get("item") or {}
        if not item:
            return {"isPlaying": False}
        artists = ", ".join([a.get("name") for a in item.get("artists", [])])
        album = item.get("album", {})
        image = None
        images = album.get("images", [])
        if images:
            image = images[0].get("url")
        return {
            "isPlaying": bool(is_playing),
            "title": item.get("name"),
            "artist": artists,
            "album": album.get("name"),
            "albumImageUrl": image,
            "songUrl": item.get("external_urls", {}).get("spotify"),
        }
    except Exception:
        return {"isPlaying": False}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = os.getenv("DATABASE_NAME") or "Unknown"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
