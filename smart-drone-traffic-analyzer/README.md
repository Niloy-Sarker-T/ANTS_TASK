# 🚁 Smart Drone Traffic Analyzer

A proof-of-concept application for analyzing drone traffic videos using **YOLOv11 + ByteTrack**.  
The system detects vehicles, tracks them across frames, counts **unique vehicles**, generates an annotated output video, and exports structured **CSV / Excel reports**.

---

## 🎥 Demo Videos Used

### Video 1
- Resolution: **1280 × 720**
- FPS: **29.97**
- Aspect Ratio: **1.78**

### Video 2
- Resolution: **1280 × 720**
- FPS: **25.0**
- Aspect Ratio: **1.78**

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

## ⚙️ Model Used

The final implementation uses:
model = YOLO("yolo11m.pt")
I tested multiple YOLOv11 variants and found that YOLOv11m provides the best balance of:
small-object recall
stable detection quality
class consistency


🧠 Architecture Overview

The system follows a modular 3-layer design:
1) UI Layer
Web: HTML, CSS, JavaScript
Desktop: PyQt-based GUI

Responsible for:

video upload / selection
progress display
output preview
report download
2) Application Layer
Web: FastAPI backend
Desktop: Worker thread (QThread) controller

Responsible for:

receiving user input
starting processing
tracking job state
returning output paths and results
3) Processing Layer

Implemented in processor.py.

Responsible for:

frame-by-frame processing
YOLO detection
ByteTrack tracking
unique vehicle counting logic
CSV / Excel generation
annotated video export

✔ The design is reusable: the same process_video() pipeline works for both web and GUI versions.






🏃 How to Run
🌐 Web Version
pip install -r requirements.txt
uvicorn app.main:app --reload

Then open:

http://127.0.0.1:8000

🖥 GUI Version
python -m gui_app.main





🚗 Tracking Methodology and Edge-Case Handling

The pipeline uses YOLOv11 for detection and ByteTrack for multi-object tracking.
ByteTrack assigns a persistent tracking ID to each vehicle across frames.
On top of that, I implemented custom counting logic to ensure each vehicle is counted only once.

🔢 Counting Strategy

A vehicle is counted only if:

it belongs to one of the target vehicle classes
it has a valid persistent tracking ID
it remains tracked for at least MIN_TRACK_FRAMES
it has not already been counted

To prevent duplicates, counted vehicle IDs are stored in a set:

counted_ids = set()

Once a track ID is counted, it cannot increase the count again, even if it remains visible for many frames.




🧩 Edge Cases Handled
Stopping / slowing:
Vehicle is still counted only once since counting is tied to the persistent track ID.
Temporary occlusion:
ByteTrack can preserve identity through short occlusions. If the same ID reappears, it is not counted again.
Short-lived false detections:
Suppressed using MIN_TRACK_FRAMES, so unstable detections do not instantly affect counts.
Double-counting across frames:
Prevented by combining ByteTrack IDs with custom count-once logic.
📝 Note on Earlier Counting Logic

During development, I tested a stricter line-crossing approach (vehicle counted only when bottom-center crosses a virtual line).
While effective for "passing-through" scenarios, the final solution uses the stable-track counting approach, which was more reliable across the provided videos.





🛠 Engineering Assumptions
Off-the-shelf pretrained detection is sufficient (no custom training).
Tracking-based counting is more reliable than raw per-frame counting.
A small amount of undercounting is preferable to unstable overcounting.
Generalizable logic is better than scene-specific hardcoding.
Extremely small / shadowed / partially occluded vehicles may still be missed due to detector limits.
🚙 Class Assumption

SUV-like large vehicles may sometimes be classified as truck, depending on YOLO's output.
This behavior is treated as acceptable and consistent with detector class mapping.

🔬 Experimentation Summary

I tested multiple configurations, including:

CONF_THRESHOLD
MIN_TRACK_FRAMES
imgsz
tiled inference
ROI enhancement
different YOLOv11 model sizes
Key Findings
MIN_TRACK_FRAMES had the highest impact on stability (3 was optimal).
Aggressive detection settings improved recall slightly but increased unstable/duplicate counts.
Tiled inference improved some tiny detections but introduced duplicates and false positives.
ROI enhancement helped recover some vehicles but sometimes destabilized class consistency.
YOLOv11m performed better overall than YOLOv11l on the provided videos.


🚀 Final Improvement (Two-Pass Strategy)
The final pipeline uses a two-pass strategy to balance small-object detection and train detection:
Pass 1 (Main Tracking Pass)
imgsz = 1280
ByteTrack enabled
Improves detection of small distant vehicles
Pass 2 (Large Object Recovery Pass)
imgsz = 640
Triggered on selected frames
Helps recover large train detections sometimes missed at higher input size

This improved the balance between:

small vehicle recall
train recovery
count stability


📦 Outputs

For each processed video, the system generates:

Annotated MP4 output video
CSV report
Excel report containing:
Summary sheet
Vehicle detection log
Time-series breakdown

The report includes:

total unique vehicle count
breakdown by vehicle type
processing duration
frame number and timestamp for detections
📁 Repository Structure
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
🏁 Final Notes

This project prioritizes:

stable tracking
duplicate prevention
structured reporting
practical generalization across multiple traffic scenes

The final system is not simply "detect every frame and count".
Instead, it combines detection + tracking + custom counting logic to produce a more reliable estimate of unique vehicles in the scene.