import os
import cv2
import time
import pandas as pd
from ultralytics import YOLO

MODEL_PATH = "yolo11m.pt"
CONF_THRESHOLD = 0.20
VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "train"}
LARGE_VEHICLE_CLASSES = {"train"}

RESIZE_WIDTH = None
FRAME_SKIP = 0
MIN_TRACK_FRAMES = 3
MAX_MISSING_FRAMES = 30

CLASS_COLORS = {
    "car":        (0, 255, 0),
    "motorcycle": (0, 165, 255),
    "bus":        (0, 255, 255),
    "truck":      (0, 0, 255),
    "train":      (255, 255, 0),
}

model = YOLO(MODEL_PATH)

def get_large_detections(model, frame, conf, large_classes):
    results = model.predict(
        frame,
        conf=conf,
        imgsz=640,
        verbose=False
    )[0]

    found = []
    if results.boxes is not None:
        for i in range(len(results.boxes)):
            cls_id = int(results.boxes.cls[i].item())
            cls_name = model.names[cls_id]
            if cls_name not in large_classes:
                continue
            conf_val = float(results.boxes.conf[i].item())
            bbox = results.boxes.xyxy[i].cpu().numpy().astype(int)
            found.append((cls_name, bbox[0], bbox[1], bbox[2], bbox[3], conf_val))
    return found

def process_video(input_video, output_dir, progress_callback=None):
    os.makedirs(output_dir, exist_ok=True)

    output_video = os.path.join(output_dir, "processed_video.mp4")
    output_csv = os.path.join(output_dir, "vehicle_report.csv")
    output_xlsx = os.path.join(output_dir, "vehicle_report.xlsx")

    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_video}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if RESIZE_WIDTH is not None:
        scale = RESIZE_WIDTH / orig_width
        width = RESIZE_WIDTH
        height = int(orig_height * scale)
    else:
        width = orig_width
        height = orig_height

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

    counted_ids = set()
    track_memory = {}
    vehicle_counts = {cls_name: 0 for cls_name in VEHICLE_CLASSES}
    detection_log = []

    frame_idx = 0
    processed_frames = 0
    start_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if RESIZE_WIDTH is not None:
            frame = cv2.resize(frame, (width, height))

        if FRAME_SKIP > 0 and (frame_idx % (FRAME_SKIP + 1) != 0):
            out.write(frame)
            frame_idx += 1
            continue

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=CONF_THRESHOLD,
            imgsz=1280,
            verbose=False
        )

        large_dets = []
        if frame_idx >= 240:
            large_dets = get_large_detections(model, frame, CONF_THRESHOLD, LARGE_VEHICLE_CLASSES)

        annotated = frame.copy()

        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is not None and boxes.id is not None:
                xyxy = boxes.xyxy.cpu().numpy()
                ids = boxes.id.cpu().numpy().astype(int)
                clss = boxes.cls.cpu().numpy().astype(int)
                confs = boxes.conf.cpu().numpy()

                for box, track_id, cls_id, conf in zip(xyxy, ids, clss, confs):
                    class_name = model.names[cls_id]
                    if class_name not in VEHICLE_CLASSES:
                        continue

                    x1, y1, x2, y2 = map(int, box)
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)

                    if track_id not in track_memory:
                        track_memory[track_id] = {
                            "class_name": class_name,
                            "frames_seen": 1,
                            "first_seen_frame": frame_idx,
                            "last_seen_frame": frame_idx,
                            "counted": False
                        }
                    else:
                        track_memory[track_id]["frames_seen"] += 1
                        track_memory[track_id]["last_seen_frame"] = frame_idx

                    mem = track_memory[track_id]

                    if (track_id not in counted_ids) and (mem["frames_seen"] >= MIN_TRACK_FRAMES):
                        counted_ids.add(track_id)
                        mem["counted"] = True
                        vehicle_counts[class_name] += 1

                        timestamp_sec = frame_idx / fps
                        detection_log.append({
                            "track_id": track_id,
                            "vehicle_type": class_name,
                            "frame_number": frame_idx,
                            "timestamp_sec": round(timestamp_sec, 2),
                            "confidence": round(float(conf), 3),
                            "bbox_x1": x1, "bbox_y1": y1,
                            "bbox_x2": x2, "bbox_y2": y2,
                            "centroid_x": cx, "centroid_y": cy,
                            "event": "unique_vehicle_counted"
                        })

                    base_color = CLASS_COLORS.get(class_name, (200, 200, 200))
                    color = base_color if track_id in counted_ids else (130, 130, 130)

                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    cv2.circle(annotated, (cx, cy), 4, (0, 0, 255), -1)

                    status = "COUNTED" if track_id in counted_ids else "TRACKING"
                    label = f"{class_name} ID:{track_id} {status} {conf:.2f}"
                    cv2.putText(annotated, label, (x1, max(20, y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        for (cls_name, x1, y1, x2, y2, conf_val) in large_dets:
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            grid_x = cx // 300
            grid_y = cy // 300
            synth_id = abs(hash(f"large_{cls_name}_{grid_x}_{grid_y}")) % 99999 + 100000

            if synth_id not in track_memory:
                track_memory[synth_id] = {
                    "class_name": cls_name,
                    "frames_seen": 1,
                    "first_seen_frame": frame_idx,
                    "last_seen_frame": frame_idx,
                    "counted": False
                }
            else:
                track_memory[synth_id]["frames_seen"] += 1
                track_memory[synth_id]["last_seen_frame"] = frame_idx

            mem = track_memory[synth_id]

            if (synth_id not in counted_ids) and (mem["frames_seen"] >= MIN_TRACK_FRAMES):
                counted_ids.add(synth_id)
                mem["counted"] = True
                vehicle_counts[cls_name] += 1

                detection_log.append({
                    "track_id": synth_id,
                    "vehicle_type": cls_name,
                    "frame_number": frame_idx,
                    "timestamp_sec": round(frame_idx / fps, 2),
                    "confidence": round(conf_val, 3),
                    "bbox_x1": x1, "bbox_y1": y1,
                    "bbox_x2": x2, "bbox_y2": y2,
                    "centroid_x": cx, "centroid_y": cy,
                    "event": "unique_vehicle_counted"
                })

            train_color = CLASS_COLORS.get(cls_name, (255, 255, 0))
            status = "COUNTED" if synth_id in counted_ids else "TRACKING"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), train_color, 3)
            cv2.putText(annotated, f"{cls_name} [{status}] {conf_val:.2f}",
                        (x1, max(20, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, train_color, 2)

        stale_ids = []
        for tid, mem in track_memory.items():
            if frame_idx - mem["last_seen_frame"] > MAX_MISSING_FRAMES:
                stale_ids.append(tid)
        for tid in stale_ids:
            del track_memory[tid]

        total_count = sum(vehicle_counts.values())

        y_text = 30
        cv2.putText(annotated, f"Total Unique Vehicle Count: {total_count}",
                    (20, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        y_text += 30

        for cls_name in sorted(vehicle_counts.keys()):
            cv2.putText(annotated, f"{cls_name}: {vehicle_counts[cls_name]}",
                        (20, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_text += 25

        cv2.putText(annotated, f"Frame: {frame_idx}/{total_frames}",
                    (20, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 255, 200), 2)

        out.write(annotated)
        processed_frames += 1
        frame_idx += 1

        if progress_callback:
            progress_callback(frame_idx, total_frames)

    cap.release()
    out.release()

    processing_duration = round(time.time() - start_time, 2)

    df = pd.DataFrame(detection_log)
    df.to_csv(output_csv, index=False)

    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        summary_rows = [
            ("Video File", os.path.basename(input_video)),
            ("Resolution", f"{orig_width}x{orig_height}"),
            ("FPS", round(fps, 2)),
            ("Total Frames", total_frames),
            ("Frames Processed", processed_frames),
            ("Processing Duration(s)", processing_duration),
            ("Model", MODEL_PATH),
            ("Confidence Threshold", CONF_THRESHOLD),
            ("imgsz Pass1 (small)", 1280),
            ("imgsz Pass2 (train)", 640),
            ("Min Track Frames", MIN_TRACK_FRAMES),
            ("", ""),
            ("TOTAL UNIQUE VEHICLES", sum(vehicle_counts.values())),
        ]
        for cls, cnt in sorted(vehicle_counts.items()):
            if cnt > 0:
                summary_rows.append((f"  {cls}", cnt))

        pd.DataFrame(summary_rows, columns=["Metric", "Value"]).to_excel(
            writer, sheet_name="Summary", index=False
        )

        if len(df) > 0:
            df.to_excel(writer, sheet_name="Vehicle Details", index=False)

        if len(df) > 0:
            df["minute"] = (df["timestamp_sec"] / 60).astype(int)
            ts = df.groupby("minute").agg(total=("track_id", "count")).reset_index()
            pivot = df.groupby(["minute", "vehicle_type"]).size().unstack(fill_value=0)
            ts = ts.merge(pivot, left_on="minute", right_index=True, how="left").fillna(0)
            ts.to_excel(writer, sheet_name="Time Series", index=False)

    return {
        "output_video": output_video,
        "output_csv": output_csv,
        "output_xlsx": output_xlsx,
        "processing_duration": processing_duration,
        "vehicle_counts": vehicle_counts,
        "total_unique": sum(vehicle_counts.values())
    }