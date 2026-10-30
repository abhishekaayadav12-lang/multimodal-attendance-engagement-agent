import cv2
import math


def analyze_video(path, threshold=8, window_seconds=30):
    """
    Analyze a classroom video without identity recognition.

    Returns:
      attendance_rows: anonymous track summaries
      visual_rows: activity score per time window
      meta: processing information
    """
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError("Could not open the video. Try MP4/AVI/MOV with a supported codec.")

    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    if detector.empty():
        cap.release()
        raise RuntimeError("OpenCV Haar face detector could not be loaded.")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if total_frames else 0.0

    # Track format: center, first, last, hits, missed
    tracks = {}
    next_id = 1
    frame_no = 0
    prev_small = None
    motion_by_window = {}

    # Process every second for speed and stable activity windows.
    step = max(1, int(round(fps)))

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_no += 1

        if frame_no % step != 0:
            continue

        t = frame_no / fps
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(35, 35)
        )
        centers = [
            (int(x + w / 2), int(y + h / 2))
            for x, y, w, h in faces
        ]

        # Greedy nearest-center tracking.
        available = set(tracks.keys())
        matched = set()

        for center in centers:
            best_id = None
            best_dist = float("inf")

            for tid in available:
                old = tracks[tid]["center"]
                dist = math.hypot(center[0] - old[0], center[1] - old[1])
                if dist < best_dist:
                    best_dist = dist
                    best_id = tid

            if best_id is not None and best_dist <= 100:
                tid = best_id
                available.discard(tid)
                matched.add(tid)
                tracks[tid]["center"] = center
                tracks[tid]["last"] = t
                tracks[tid]["hits"] += 1
            else:
                tid = f"Person-{next_id:02d}"
                next_id += 1
                tracks[tid] = {
                    "center": center,
                    "first": t,
                    "last": t,
                    "hits": 1,
                }

        # Motion/activity proxy.
        small = cv2.resize(gray, (320, 180))
        if prev_small is not None:
            diff = cv2.absdiff(small, prev_small)
            activity = float(diff.mean() / 255.0)
            window = int(t // window_seconds) * window_seconds
            motion_by_window.setdefault(window, []).append(activity)
        prev_small = small

    cap.release()

    attendance_rows = []
    for tid, tr in tracks.items():
        duration_seen = max(0.0, tr["last"] - tr["first"])
        if duration_seen >= float(threshold):
            attendance_rows.append(
                {
                    "track_id": tid,
                    "first_seen": round(tr["first"], 2),
                    "last_seen": round(tr["last"], 2),
                    "duration_seconds": round(duration_seen, 2),
                    "observations": tr["hits"],
                    "status": "Present",
                }
            )

    visual_rows = []
    for window, values in sorted(motion_by_window.items()):
        if values:
            visual_rows.append(
                {
                    "window_start": int(window),
                    "visual_activity": round(
                        min(1.0, max(0.0, sum(values) / len(values) * 4.0)), 4
                    ),
                }
            )

    meta = {
        "frames_processed": frame_no,
        "total_frames": total_frames,
        "fps": round(fps, 2),
        "duration_seconds": round(duration, 2),
        "tracks_detected": len(tracks),
        "present_tracks": len(attendance_rows),
        "threshold_seconds": float(threshold),
        "window_seconds": int(window_seconds),
        "note": "Anonymous face detection/tracking only; no identity recognition.",
    }
    return attendance_rows, visual_rows, meta
