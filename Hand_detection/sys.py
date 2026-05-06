"""Short MediaPipe hand detection viewer."""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions
except ModuleNotFoundError as exc:
    print(f"[ERROR] Missing Python package: {exc.name}", file=sys.stderr)
    print("Run: python -m pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1) from exc


ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models" / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
WINDOW = "Hand Detection"
CONNECTIONS = [
    (line.start, line.end) for line in vision.HandLandmarksConnections.HAND_CONNECTIONS
]


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MediaPipe hand detection viewer")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def ensure_model(path: Path, download: bool) -> Path:
    path = path.resolve()
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    if not download:
        raise FileNotFoundError(f"Missing model: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".download")
    print(f"[INFO] Downloading model to {path}")
    try:
        urllib.request.urlretrieve(MODEL_URL, temp)
        temp.replace(path)
    except (OSError, urllib.error.URLError) as exc:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download model from {MODEL_URL}") from exc
    return path


def make_landmarker(model: Path) -> vision.HandLandmarker:
    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.55,
        min_hand_presence_confidence=0.55,
        min_tracking_confidence=0.55,
    )
    return vision.HandLandmarker.create_from_options(options)


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            return cap
        cap.release()
    raise RuntimeError("Cannot open camera. Try --camera 1 or close other camera apps.")


def point(landmark, width: int, height: int) -> tuple[int, int]:
    x = min(max(int(landmark.x * width), 0), width - 1)
    y = min(max(int(landmark.y * height), 0), height - 1)
    return x, y


def draw_hand(frame, landmarks, label: str = "") -> None:
    height, width = frame.shape[:2]
    points = [point(landmark, width, height) for landmark in landmarks]

    for start, end in CONNECTIONS:
        cv2.line(frame, points[start], points[end], (0, 220, 255), 2, cv2.LINE_AA)
    for p in points:
        cv2.circle(frame, p, 4, (30, 30, 30), -1, cv2.LINE_AA)
        cv2.circle(frame, p, 3, (255, 255, 255), -1, cv2.LINE_AA)
    if label:
        cv2.putText(frame, label, points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)


def run() -> int:
    config = args()
    model = ensure_model(config.model, download=not config.no_download)

    if config.self_test:
        with make_landmarker(model):
            print("[OK] Self-test passed. MediaPipe hand model loaded.")
        return 0

    cap = open_camera(config.camera, config.width, config.height)
    last_ms = 0

    try:
        with make_landmarker(model) as landmarker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Camera frame could not be read.")

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                now_ms = max(last_ms + 1, int(time.perf_counter() * 1000))
                last_ms = now_ms
                result = landmarker.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                    now_ms,
                )

                hands = result.hand_landmarks or []
                for index, landmarks in enumerate(hands):
                    label = ""
                    if result.handedness and index < len(result.handedness):
                        label = result.handedness[index][0].category_name
                    draw_hand(frame, landmarks, label)

                cv2.putText(
                    frame,
                    f"Hands: {len(hands)}   Q/Esc: quit",
                    (20, 38),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (30, 255, 30),
                    2,
                )
                cv2.imshow(WINDOW, frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        raise SystemExit(1)
