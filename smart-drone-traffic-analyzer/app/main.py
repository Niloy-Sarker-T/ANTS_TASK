import os
import uuid
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.processor import process_video

# ---------------- APP ----------------
app = FastAPI(title="Smart Drone Traffic Analyzer")

# ---------------- PATHS ----------------
BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------- STATIC FILES ----------------
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "app" / "static")),
    name="static"
)

app.mount(
    "/outputs",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="outputs"
)

# ---------------- JOB STORAGE ----------------
jobs = {}

# ---------------- HOME (NO JINJA) ----------------
@app.get("/")
def home():
    return FileResponse(str(BASE_DIR / "app" / "templates" / "index.html"))

# ---------------- BACKGROUND PROCESS ----------------
def run_processing(job_id, input_path, output_dir):

    def progress_callback(current, total):
        jobs[job_id]["progress"] = int((current / total) * 100)

    try:
        jobs[job_id]["status"] = "processing"

        result = process_video(input_path, output_dir, progress_callback)

        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = result
        jobs[job_id]["progress"] = 100

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

# ---------------- UPLOAD ----------------
@app.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):

    if not file.filename.endswith(".mp4"):
        return JSONResponse({"error": "Only .mp4 files allowed"}, status_code=400)

    job_id = str(uuid.uuid4())

    input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    output_dir = OUTPUT_DIR / job_id
    output_dir.mkdir(exist_ok=True)

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "result": None
    }

    background_tasks.add_task(run_processing, job_id, str(input_path), str(output_dir))

    return {"job_id": job_id}

# ---------------- STATUS ----------------
@app.get("/status/{job_id}")
def status(job_id: str):
    return jobs.get(job_id, {"error": "Job not found"})

# ---------------- RESULT ----------------
@app.get("/result/{job_id}")
def result(job_id: str):

    if job_id not in jobs:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    job = jobs[job_id]

    if job["status"] != "done":
        return JSONResponse({"error": "Not completed yet"}, status_code=400)

    result = job["result"]

    base_url = f"/outputs/{job_id}"

    return {
        "video_url": f"{base_url}/processed_video.mp4",
        "csv_url": f"{base_url}/vehicle_report.csv",
        "xlsx_url": f"{base_url}/vehicle_report.xlsx",
        "processing_duration": result["processing_duration"],
        "vehicle_counts": result["vehicle_counts"],
        "total_unique": result["total_unique"]
    }