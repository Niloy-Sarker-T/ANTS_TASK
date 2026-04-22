# 🚁 Smart Drone Traffic Analyzer

> A proof-of-concept application for analyzing drone traffic videos using **YOLOv11 + ByteTrack**.  
> The system detects vehicles, tracks them across frames, counts **unique vehicles**, generates an annotated output video, and exports structured **CSV / Excel reports**.

---

## 📋 Table of Contents

- [Demo Videos](#-demo-videos)
- [Features](#-features)
- [Architecture](#-architecture)
- [Setup & Usage](#-setup--usage)
- [How It Works](#-how-it-works)
- [Experiments](#-experiments)
- [Outputs](#-outputs)
- [Project Structure](#-project-structure)
- [Assumptions & Notes](#-assumptions--notes)

---

## 🎥 Demo Videos

| Property       | Video 1     | Video 2     |
|----------------|-------------|-------------|
| Resolution     | 1280 × 720  | 1280 × 720  |
| FPS            | 29.97       | 25.0        |
| Aspect Ratio   | 1.78        | 1.78        |

---

## ✅ Features

- Vehicle detection using **YOLOv11**
- Multi-object tracking using **ByteTrack**
- Unique vehicle counting with anti-duplication logic
- Output video with bounding boxes + IDs + class labels
- CSV report generation
- Excel report generation (summary + detailed logs + time-series breakdown)
- Processing progress tracking (percentage)

---

## 🧠 Architecture

The system follows a modular 3-layer design.

| Layer | Web | Desktop | Responsibilities |
|-------|-----|---------|-----------------|
| **UI** | HTML / CSS / JS | PyQt-based GUI | Video upload / selection, progress display, output preview, report download |
| **Application** | FastAPI backend | QThread controller | Receiving user input, starting processing, tracking job state, returning output paths and results |
| **Processing** | `processor.py` | `processor.py` | Frame-by-frame processing, YOLO detection, ByteTrack tracking, unique vehicle counting logic, CSV / Excel generation, annotated video export |

> ✔ The design is reusable: the same `process_video()` pipeline works for both web and GUI versions.

### Model

```python
model = YOLO("yolo11m.pt")
```

I tested multiple YOLOv11 variants and found that `yolo11m` provides the best balance of small-object recall, stable detection quality, and class consistency.

---

## 🚀 Setup & Usage

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Web Version

```bash
uvicorn app.main:app --reload
```

Then open: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Desktop Version

```bash
python -m gui_app.main
```

---

## ⚙️ How It Works

### Tracking & Counting

The pipeline uses **YOLOv11** for detection and **ByteTrack** for multi-object tracking. ByteTrack assigns a persistent tracking ID to each vehicle across frames. On top of that, I implemented custom counting logic to ensure each vehicle is counted only once.

A vehicle is counted only if:

- It belongs to one of the target vehicle classes
- It has a valid persistent tracking ID
- It remains tracked for at least `MIN_TRACK_FRAMES`
- It has not already been counted

To prevent duplicates, counted vehicle IDs are stored in a set:

```python
counted_ids = set()
```

Once a track ID is counted, it cannot increase the count again, even if it remains visible for many frames.

### Two-Pass Detection Strategy

The final pipeline uses a two-pass strategy to balance small-object detection and train detection:

| Pass | `imgsz` | Purpose |
|------|---------|---------|
| Pass 1 — Main Tracking Pass | `1280` | ByteTrack enabled — improves detection of small distant vehicles |
| Pass 2 — Large Object Recovery Pass | `640` | Triggered on selected frames — helps recover large train detections sometimes missed at higher input size |

This improved the balance between small vehicle recall, train recovery, and count stability.

### Edge Cases Handled

| Scenario | Handling |
|----------|----------|
| Stopping / slowing | Vehicle is still counted only once since counting is tied to the persistent track ID |
| Temporary occlusion | ByteTrack can preserve identity through short occlusions. If the same ID reappears, it is not counted again |
| Short-lived false detections | Suppressed using `MIN_TRACK_FRAMES`, so unstable detections do not instantly affect counts |
| Double-counting across frames | Prevented by combining ByteTrack IDs with custom count-once logic |

> **Note on Earlier Counting Logic:** During development, I tested a stricter line-crossing approach (vehicle counted only when bottom-center crosses a virtual line). While effective for "passing-through" scenarios, the final solution uses the stable-track counting approach, which was more reliable across the provided videos.

---

## 🔬 Experiments

I tested multiple configurations, including `CONF_THRESHOLD`, `MIN_TRACK_FRAMES`, `imgsz`, tiled inference, ROI enhancement, different YOLOv11 model sizes.

| Variable | Finding |
|----------|---------|
| `MIN_TRACK_FRAMES` | Highest impact on stability — **3 was optimal** |
| Aggressive detection settings | Improved recall slightly but increased unstable/duplicate counts |
| Tiled inference | Improved some tiny detections but introduced duplicates and false positives |
| ROI enhancement | Helped recover some vehicles but sometimes destabilized class consistency |
| Model size comparison | `yolo11m` performed better overall than `yolo11l` on the provided videos |

---

## 📦 Outputs

For each processed video, the system generates:

| Output | Description |
|--------|-------------|
| Annotated `.mp4` | Output video with bounding boxes, IDs, and class labels |
| `.csv` report | Flat structured detection log |
| `.xlsx` report | Three sheets: Summary, Vehicle Detection Log, Time-Series Breakdown |

The report includes total unique vehicle count, breakdown by vehicle type, processing duration, and frame number and timestamp for detections.

---

## 📁 Project Structure

```
smart-drone-traffic-analyzer/
│
├── app/
│   ├── main.py
│   ├── processor.py
│   ├── templates/
│   └── static/
│
├── gui_app/
│   ├── main.py
│   └── worker.py
│
├── uploads/
├── outputs/
├── requirements.txt
└── README.md
```

---

## 📝 Assumptions & Notes
- SUV-like large vehicles is classified as `truck`
