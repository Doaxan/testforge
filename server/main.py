# EduForge · from @AlStack (https://t.me/AlStack) — AI freebies, abuse schemes, LLM keys & tools.
"""EduForge — verification combine server (FastAPI).

Run:  python -m server.main   (or uvicorn server.main:app --port 8890)
"""
import os
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, storage, gendocs
from .engine.client import SheerIDClient, parse_verification_id

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("eduforge")

app = FastAPI(title="EduForge", version="1.0.0")
storage.init()

POOL = ThreadPoolExecutor(max_workers=6)
SEM = asyncio.Semaphore(int(os.environ.get("EDUFORGE_CONCURRENCY", "3")))
ADMIN_TOKEN = os.environ.get("EDUFORGE_TOKEN", "")
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")


def _guard(req: Request):
    if ADMIN_TOKEN and req.headers.get("x-admin-token") != ADMIN_TOKEN:
        raise HTTPException(401, "invalid admin token")


class GenerateReq(BaseModel):
    doc_type: str = "student_id"
    first: Optional[str] = None
    last: Optional[str] = None
    school_id: str = config.DEFAULT_SCHOOL_ID
    dob: Optional[str] = None


class VerifyReq(BaseModel):
    url: Optional[str] = None
    vid: Optional[str] = None
    program: str = "student"
    school_id: str = config.DEFAULT_SCHOOL_ID
    doc_type: str = "student_id"
    first: Optional[str] = None
    last: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[str] = None
    proxy: Optional[str] = None
    skip_sso: bool = True


@app.get("/health")
def health():
    return {"ok": True, "service": "eduforge", "programs": len(config.PROGRAMS),
            "schools": len(config.SCHOOLS)}


@app.get("/api/programs")
def programs():
    return {"programs": config.PROGRAMS, "dead": config.PROGRAMS_DEAD}


@app.get("/api/schools")
def schools():
    return {"schools": config.SCHOOLS, "default": config.DEFAULT_SCHOOL_ID}


@app.get("/api/doc_types")
def doc_types():
    return {"doc_types": gendocs.DOC_TYPES}


@app.post("/api/generate")
def generate(req: GenerateReq, request: Request):
    _guard(request)
    school = config.SCHOOLS.get(req.school_id)
    if not school:
        raise HTTPException(400, "unknown school_id")
    ident = gendocs.make_identity(req.first, req.last, birth_date=req.dob)
    try:
        payload, filename, mime = gendocs.generate_doc(
            req.doc_type, ident["first_name"], ident["last_name"],
            school["name"], ident["birth_date"], req.school_id)
    except Exception as e:
        raise HTTPException(500, f"generation failed: {e}")
    return Response(content=payload, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"',
                             "X-Identity": f'{ident["first_name"]} {ident["last_name"]} <{ident["email"]}>'})


def _run_verify(tid: str, req: VerifyReq, vid: str):
    program = config.PROGRAMS[req.program]
    school = config.SCHOOLS.get(req.school_id, config.SCHOOLS[config.DEFAULT_SCHOOL_ID])
    ident = gendocs.make_identity(req.first, req.last, req.email, req.birth_date,
                                  school.get("domain", "psu.edu").lower())
    storage.update_task(tid, "generating", {"identity": {k: ident[k] for k in ("first_name", "last_name", "email", "birth_date")}})
    try:
        payload, filename, mime = gendocs.generate_doc(
            req.doc_type, ident["first_name"], ident["last_name"],
            school["name"], ident["birth_date"], req.school_id)
    except Exception as e:
        storage.update_task(tid, "failed", {"stage": "generate", "error": str(e)})
        return
    storage.update_task(tid, "submitting", {"doc_bytes": len(payload), "filename": filename})
    client = SheerIDClient(proxy=req.proxy)
    result = client.run(vid, program, ident, school, payload, filename, mime, req.skip_sso)
    storage.update_task(tid, "submitted" if result.get("success") else "failed", result)


@app.post("/api/verify")
async def verify(req: VerifyReq, request: Request):
    _guard(request)
    vid = req.vid or parse_verification_id(req.url or "")
    if not vid:
        raise HTTPException(400, "provide url with verificationId or a 24-hex vid")
    if req.program not in config.PROGRAMS:
        raise HTTPException(400, "unknown program")
    tid = uuid.uuid4().hex[:12]
    storage.add_task(tid, "verify", req.program, vid, req.model_dump())

    async def worker():
        async with SEM:
            storage.update_task(tid, "running", {})
            await asyncio.get_event_loop().run_in_executor(POOL, _run_verify, tid, req, vid)

    asyncio.create_task(worker())
    return {"task_id": tid, "vid": vid, "status": "queued"}


@app.get("/api/tasks")
def tasks(limit: int = 100):
    return {"tasks": storage.list_tasks(limit)}


@app.get("/api/task/{tid}")
def task(tid: str):
    t = storage.get_task(tid)
    if not t:
        raise HTTPException(404, "task not found")
    return t


@app.get("/api/status/{vid}")
def status(vid: str, proxy: Optional[str] = None):
    if not parse_verification_id(vid):
        raise HTTPException(400, "invalid verification id")
    client = SheerIDClient(proxy=proxy)
    return client.status(vid)


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


app.mount("/transcript", StaticFiles(directory=os.path.join(WEB_DIR, "transcript"), html=True), name="transcript")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("EDUFORGE_PORT", "8895")))