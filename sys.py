"""
Hand Motion Detection Drawing Board
===================================

Use your index finger like a marker and write on the screen.

Gesture controls:
  Index finger only       -> draw
  Index + middle fingers  -> move without drawing
  Open palm / four fingers -> erase

Keyboard controls:
  C       clear board
  S       save drawing to Desktop
  B       toggle camera/whiteboard background
  1-9     change color
  + / -   change brush size
  Q / Esc quit
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = ROOT_DIR / "models" / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)

WINDOW_NAME = "Hand Motion Drawing Board"
TOP_BAR_HEIGHT = 82
BOTTOM_BAR_HEIGHT = 36

COLORS = {
    "1": ("Red", (0, 0, 255)),
    "2": ("Green", (0, 210, 80)),
    "3": ("Blue", (255, 90, 0)),
    "4": ("Yellow", (0, 230, 230)),
    "5": ("Purple", (190, 0, 200)),
    "6": ("Orange", (0, 150, 255)),
    "7": ("Cyan", (255, 220, 0)),
    "8": ("White", (255, 255, 255)),
    "9": ("Pink", (180, 100, 255)),
}

MODE_COLORS = {
    "DRAW": (0, 190, 80),
    "MOVE": (0, 170, 255),
    "ERASE": (0, 70, 230),
}

HAND_CONNECTIONS = [
    (connection.start, connection.end)
    for connection in vision.HandLandmarksConnections.HAND_CONNECTIONS
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hand motion drawing board")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--width", type=int, default=1280, help="Camera width")
    parser.add_argument("--height", type=int, default=720, help="Camera height")
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Path to hand_landmarker.task",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Do not download the MediaPipe model if it is missing",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Verify imports and model loading without opening the camera",
    )
    return parser.parse_args()


def ensure_model(model_path: Path, allow_download: bool = True) -> Path:
    model_path = model_path.resolve()
    if model_path.exists() and model_path.stat().st_size > 1_000_000:
        return model_path

    if not allow_download:
        raise FileNotFoundError(
            f"Model file not found: {model_path}\n"
            f"Download it from {MODEL_URL} and save it at that path."
        )

    model_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = model_path.with_suffix(".task.download")
    print(f"[INFO] Downloading MediaPipe hand model to {model_path}")
    print(f"[INFO] Source: {MODEL_URL}")

    try:
        urllib.request.urlretrieve(MODEL_URL, temp_path)
        temp_path.replace(model_path)
    except (OSError, urllib.error.URLError) as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(
            "Could not download the hand model. Check your internet connection "
            f"or manually download it from:\n{MODEL_URL}"
        ) from exc

    return model_path


def create_landmarker(model_path: Path) -> vision.HandLandmarker:
    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.65,
        min_hand_presence_confidence=0.65,
        min_tracking_confidence=0.65,
    )
    return vision.HandLandmarker.create_from_options(options)


def open_camera(camera_index: int, width: int, height: int) -> cv2.VideoCapture:
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    for backend in backends:
        cap = cv2.VideoCapture(camera_index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, 30)
            return cap
        cap.release()
    raise RuntimeError(
        "Cannot open webcam. Close other camera apps, allow camera permission, "
        "or try another camera index with --camera 1."
    )


def fingers_up(landmarks: list, handedness: str = "Right") -> list[bool]:
    tips = [4, 8, 12, 16, 20]
    dips = [3, 6, 10, 14, 18]

    if handedness == "Right":
        thumb = landmarks[tips[0]].x < landmarks[dips[0]].x
    else:
        thumb = landmarks[tips[0]].x > landmarks[dips[0]].x

    fingers = [thumb]
    for index in range(1, 5):
        fingers.append(landmarks[tips[index]].y < landmarks[dips[index]].y)
    return fingers


def get_mode(up_flags: list[bool]) -> str:
    index_up = up_flags[1]
    middle_up = up_flags[2]
    ring_up = up_flags[3]
    pinky_up = up_flags[4]

    if index_up and middle_up and ring_up and pinky_up:
        return "ERASE"
    if index_up and middle_up and not ring_up and not pinky_up:
        return "MOVE"
    if index_up and not middle_up:
        return "DRAW"
    return "MOVE"


def landmark_point(landmark, width: int, height: int) -> tuple[int, int]:
    x = int(np.clip(landmark.x, 0.0, 1.0) * (width - 1))
    y = int(np.clip(landmark.y, 0.0, 1.0) * (height - 1))
    return x, y


def draw_hand_landmarks(frame: np.ndarray, landmarks: list) -> None:
    height, width = frame.shape[:2]
    points = [landmark_point(landmark, width, height) for landmark in landmarks]

    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, points[start], points[end], (80, 210, 255), 2, cv2.LINE_AA)

    for point in points:
        cv2.circle(frame, point, 4, (20, 35, 45), -1, cv2.LINE_AA)
        cv2.circle(frame, point, 3, (255, 255, 255), -1, cv2.LINE_AA)


def blend_canvas(background: np.ndarray, canvas: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 8, 255, cv2.THRESH_BINARY)
    mask_inv = cv2.bitwise_not(mask)
    bg = cv2.bitwise_and(background, background, mask=mask_inv)
    fg = cv2.bitwise_and(canvas, canvas, mask=mask)
    return cv2.add(bg, fg)


def draw_ui(
    frame: np.ndarray,
    mode: str,
    color_key: str,
    brush_size: int,
    fps: int,
    board_mode: bool,
) -> None:
    height, width = frame.shape[:2]
    color_name, color_bgr = COLORS[color_key]

    cv2.rectangle(frame, (0, 0), (width, TOP_BAR_HEIGHT), (22, 24, 32), -1)
    cv2.rectangle(frame, (0, TOP_BAR_HEIGHT), (width, TOP_BAR_HEIGHT + 2), (70, 76, 96), -1)

    mode_color = MODE_COLORS.get(mode, (170, 170, 170))
    cv2.rectangle(frame, (14, 14), (160, 62), mode_color, -1)
    cv2.putText(frame, mode, (30, 47), cv2.FONT_HERSHEY_SIMPLEX, 0.92, (10, 12, 14), 2)

    cv2.rectangle(frame, (180, 18), (245, 58), color_bgr, -1)
    cv2.rectangle(frame, (180, 18), (245, 58), (220, 220, 220), 1)
    cv2.putText(frame, color_name, (258, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (225, 225, 225), 1)

    cv2.putText(frame, f"Brush {brush_size}px", (390, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (215, 215, 215), 1)
    cv2.circle(frame, (520, 38), min(brush_size, 22), color_bgr, -1, cv2.LINE_AA)

    view_text = "Whiteboard" if board_mode else "Camera"
    cv2.putText(frame, f"View {view_text}", (570, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (215, 215, 215), 1)
    cv2.putText(frame, f"FPS {fps}", (width - 105, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (165, 165, 165), 1)

    palette_start = max(width - 320, 760)
    for offset, (key, (_, bgr)) in enumerate(COLORS.items()):
        cx = palette_start + offset * 30
        if cx + 14 > width - 120:
            break
        cv2.circle(frame, (cx, 64), 11, bgr, -1, cv2.LINE_AA)
        border = (255, 255, 255) if key == color_key else (85, 85, 85)
        cv2.circle(frame, (cx, 64), 13, border, 2 if key == color_key else 1, cv2.LINE_AA)
        cv2.putText(frame, key, (cx - 4, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (15, 15, 15), 1)

    cv2.rectangle(frame, (0, height - BOTTOM_BAR_HEIGHT), (width, height), (22, 24, 32), -1)
    hint = "Index=Draw  Two fingers=Move  Open palm=Erase   C Clear  S Save  B Board  Q Quit"
    cv2.putText(frame, hint, (14, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (165, 170, 185), 1)


def show_toast(frame: np.ndarray, message: str, started_at: float, duration: float = 2.3) -> None:
    elapsed = time.time() - started_at
    if elapsed >= duration:
        return

    alpha = max(0.0, min(1.0, duration - elapsed))
    height, width = frame.shape[:2]
    box_width = min(max(300, len(message) * 13 + 34), width - 40)
    x1 = (width - box_width) // 2
    y1 = max(TOP_BAR_HEIGHT + 20, height // 2 - 34)

    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x1 + box_width, y1 + 62), (24, 28, 42), -1)
    cv2.rectangle(overlay, (x1, y1), (x1 + box_width, y1 + 62), (95, 110, 145), 1)
    cv2.putText(overlay, message, (x1 + 18, y1 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (90, 235, 145), 2)
    cv2.addWeighted(overlay, 0.82 * alpha, frame, 1 - 0.82 * alpha, 0, frame)


def save_canvas(canvas: np.ndarray, save_dir: Path) -> Path:
    save_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = save_dir / f"hand_drawing_{timestamp}.png"
    cv2.imwrite(str(path), canvas)
    return path


def run_app(args: argparse.Namespace) -> None:
    model_path = ensure_model(args.model, allow_download=not args.no_download)
    save_dir = Path.home() / "Desktop"
    if not save_dir.exists():
        save_dir = Path.home()

    print(__doc__)
    print(f"[INFO] Python {sys.version.split()[0]}")
    print(f"[INFO] OpenCV {cv2.__version__}")
    print(f"[INFO] MediaPipe {mp.__version__}")
    print(f"[INFO] Model {model_path}")

    if args.self_test:
        with create_landmarker(model_path):
            print("[OK] Self-test passed. Imports and hand model loaded.")
        return

    cap = open_camera(args.camera, args.width, args.height)
    canvas = None
    prev_point: tuple[int, int] | None = None
    mode = "MOVE"
    color_key = "1"
    brush_size = 8
    board_mode = False
    toast_message = "Show your hand, then use index finger to draw"
    toast_started_at = time.time()
    previous_time = time.time()
    fps = 0

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    try:
        with create_landmarker(model_path) as landmarker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Camera frame could not be read.")

                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]

                if canvas is None or canvas.shape[:2] != frame.shape[:2]:
                    canvas = np.zeros((height, width, 3), dtype=np.uint8)

                now = time.time()
                fps = int(1.0 / max(now - previous_time, 1e-6))
                previous_time = now

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(mp_image, int(now * 1000))

                draw_layer = frame.copy()
                if board_mode:
                    draw_layer[:] = (244, 244, 238)

                color_name, color_bgr = COLORS[color_key]

                if result.hand_landmarks:
                    landmarks = result.hand_landmarks[0]
                    handedness = "Right"
                    if result.handedness and result.handedness[0]:
                        handedness = result.handedness[0][0].category_name

                    up_flags = fingers_up(landmarks, handedness)
                    mode = get_mode(up_flags)
                    fingertip = landmark_point(landmarks[8], width, height)
                    cursor_color = MODE_COLORS.get(mode, color_bgr)

                    draw_hand_landmarks(draw_layer, landmarks)
                    cv2.circle(draw_layer, fingertip, brush_size + 7, cursor_color, 2, cv2.LINE_AA)
                    cv2.circle(draw_layer, fingertip, 4, cursor_color, -1, cv2.LINE_AA)

                    can_write_here = TOP_BAR_HEIGHT + 4 < fingertip[1] < height - BOTTOM_BAR_HEIGHT - 4
                    if mode == "DRAW" and can_write_here:
                        if prev_point is None:
                            prev_point = fingertip
                        cv2.line(canvas, prev_point, fingertip, color_bgr, brush_size * 2, cv2.LINE_AA)
                        cv2.circle(canvas, fingertip, brush_size, color_bgr, -1, cv2.LINE_AA)
                        prev_point = fingertip
                    elif mode == "ERASE" and can_write_here:
                        eraser_radius = brush_size * 5
                        cv2.circle(canvas, fingertip, eraser_radius, (0, 0, 0), -1, cv2.LINE_AA)
                        cv2.circle(draw_layer, fingertip, eraser_radius, MODE_COLORS["ERASE"], 2, cv2.LINE_AA)
                        prev_point = None
                    else:
                        prev_point = None
                else:
                    mode = "MOVE"
                    prev_point = None

                frame_out = blend_canvas(draw_layer, canvas)
                draw_ui(frame_out, mode, color_key, brush_size, fps, board_mode)
                show_toast(frame_out, toast_message, toast_started_at)

                cv2.imshow(WINDOW_NAME, frame_out)
                key = cv2.waitKey(1) & 0xFF

                if key in (ord("q"), ord("Q"), 27):
                    break
                if key in (ord("c"), ord("C")):
                    canvas[:] = 0
                    toast_message = "Board cleared"
                    toast_started_at = time.time()
                elif key in (ord("s"), ord("S")):
                    path = save_canvas(canvas, save_dir)
                    toast_message = f"Saved {path.name}"
                    toast_started_at = time.time()
                    print(f"[INFO] Saved drawing to {path}")
                elif key in (ord("b"), ord("B")):
                    board_mode = not board_mode
                    toast_message = "Whiteboard view" if board_mode else "Camera view"
                    toast_started_at = time.time()
                elif key in (ord("+"), ord("=")):
                    brush_size = min(brush_size + 2, 50)
                elif key == ord("-"):
                    brush_size = max(brush_size - 2, 2)
                elif chr(key) in COLORS:
                    color_key = chr(key)
                    color_name = COLORS[color_key][0]
                    toast_message = f"Color: {color_name}"
                    toast_started_at = time.time()
    finally:
        cap.release()
        cv2.destroyAllWindows()


def main() -> int:
    args = parse_args()
    try:
        run_app(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
