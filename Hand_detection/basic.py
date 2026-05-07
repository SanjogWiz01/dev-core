"""Basic hand-motion drawing board.

Run:
    python Hand_detection/basic.py

How it works:
    - Raise only your index finger to draw.
    - Raise index + middle finger together to move without drawing.
    - Use index + middle finger on the top toolbar to select color or eraser.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import cv2
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions
except ModuleNotFoundError as exc:
    print(f"[ERROR] Missing Python package: {exc.name}", file=sys.stderr)
    print("Run: python -m pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1) from exc


WINDOW = "Hand Motion Drawing Board"
TOOLBAR_HEIGHT = 76
DRAW_THICKNESS = 9
ERASER_THICKNESS = 42
SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_NAME = "hand_landmarker.task"
MODEL_CANDIDATES = (
    SCRIPT_DIR / "models" / MODEL_NAME,
    SCRIPT_DIR.parent / "models" / MODEL_NAME,
)
CONNECTIONS = [
    (line.start, line.end) for line in vision.HandLandmarksConnections.HAND_CONNECTIONS
]


@dataclass(frozen=True)
class Tool:
    name: str
    color: tuple[int, int, int]
    key: int
    eraser: bool = False


TOOLS: dict[str, Tool] = {
    "blue": Tool("Blue", (255, 90, 0), ord("1")),
    "green": Tool("Green", (45, 210, 70), ord("2")),
    "red": Tool("Red", (30, 30, 255), ord("3")),
    "yellow": Tool("Yellow", (0, 220, 255), ord("4")),
    "eraser": Tool("Eraser", (0, 0, 0), ord("e"), eraser=True),
}
PALETTE = ["blue", "green", "red", "yellow", "eraser"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draw on screen with hand motion")
    parser.add_argument("--camera", type=int, default=0, help="camera index")
    parser.add_argument("--width", type=int, default=1280, help="camera width")
    parser.add_argument("--height", type=int, default=720, help="camera height")
    parser.add_argument("--model", type=Path, default=None, help="hand_landmarker.task path")
    parser.add_argument("--self-test", action="store_true", help="check the model and packages")
    return parser.parse_args()


def find_model(model_arg: Path | None) -> Path:
    candidates = (model_arg,) if model_arg else MODEL_CANDIDATES
    for candidate in candidates:
        if candidate is None:
            continue
        path = candidate.resolve()
        if path.exists() and path.stat().st_size > 1_000_000:
            return path

    searched = ", ".join(str(path) for path in candidates if path is not None)
    raise FileNotFoundError(
        f"Cannot find {MODEL_NAME}. Looked in: {searched}. "
        "Put the model in models/hand_landmarker.task or pass --model."
    )


def make_landmarker(model_path: Path) -> vision.HandLandmarker:
    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.65,
        min_hand_presence_confidence=0.65,
        min_tracking_confidence=0.65,
    )
    return vision.HandLandmarker.create_from_options(options)


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
        camera = cv2.VideoCapture(index, backend)
        if camera.isOpened():
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            return camera
        camera.release()
    raise RuntimeError("Cannot open camera. Try --camera 1 or close other camera apps.")


def landmark_point(landmarks, landmark_id: int, width: int, height: int) -> tuple[int, int]:
    landmark = landmarks[landmark_id]
    x = min(max(int(landmark.x * width), 0), width - 1)
    y = min(max(int(landmark.y * height), 0), height - 1)
    return x, y


def finger_is_up(landmarks, tip_id: int, pip_id: int) -> bool:
    return landmarks[tip_id].y < landmarks[pip_id].y


def draw_hand(frame, landmarks) -> None:
    height, width = frame.shape[:2]
    points = [landmark_point(landmarks, index, width, height) for index in range(21)]

    for start, end in CONNECTIONS:
        cv2.line(frame, points[start], points[end], (0, 190, 255), 2, cv2.LINE_AA)
    for point in points:
        cv2.circle(frame, point, 4, (30, 30, 30), -1, cv2.LINE_AA)
        cv2.circle(frame, point, 3, (255, 255, 255), -1, cv2.LINE_AA)


def toolbar_layout(width: int) -> list[tuple[str, tuple[int, int, int, int]]]:
    gap = 8
    left = 12
    usable_width = max(width - (left * 2) - gap * (len(PALETTE) - 1), 1)
    box_width = min(112, max(72, usable_width // len(PALETTE)))
    layout = []
    for index, name in enumerate(PALETTE):
        x1 = left + index * (box_width + gap)
        layout.append((name, (x1, 12, x1 + box_width, 60)))
    return layout


def tool_at(point: tuple[int, int], width: int) -> str | None:
    x, y = point
    if y > TOOLBAR_HEIGHT:
        return None
    for name, (x1, y1, x2, y2) in toolbar_layout(width):
        if x1 <= x <= x2 and y1 <= y <= y2:
            return name
    return None


def draw_toolbar(frame, active_tool: str, board_mode: bool) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, TOOLBAR_HEIGHT), (28, 28, 28), -1)
    cv2.addWeighted(overlay, 0.88, frame, 0.12, 0, frame)

    for index, (name, rect) in enumerate(toolbar_layout(width), start=1):
        x1, y1, x2, y2 = rect
        tool = TOOLS[name]
        border = (255, 255, 255) if name == active_tool else (95, 95, 95)
        cv2.rectangle(frame, (x1, y1), (x2, y2), tool.color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), border, 2)

        label = f"{index}" if not tool.eraser else "E"
        text_color = (20, 20, 20) if name == "yellow" else (255, 255, 255)
        cv2.putText(
            frame,
            label,
            (x1 + 12, y1 + 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            text_color,
            2,
            cv2.LINE_AA,
        )

    view_name = "Board" if board_mode else "Camera"
    help_text = f"{view_name} | 1-4 colors  E eraser  C clear  B view  S save  Q quit"
    cv2.putText(
        frame,
        help_text,
        (12, height - 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (45, 45, 45) if board_mode else (20, 255, 20),
        2,
        cv2.LINE_AA,
    )


def compose_display(frame, canvas, board_mode: bool):
    gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 8, 255, cv2.THRESH_BINARY)
    output = np.full_like(frame, 255) if board_mode else frame.copy()
    output[mask > 0] = canvas[mask > 0]
    return output


def save_canvas(canvas) -> Path:
    gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 8, 255, cv2.THRESH_BINARY)
    board = np.full_like(canvas, 255)
    board[mask > 0] = canvas[mask > 0]

    filename = f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    output_path = SCRIPT_DIR / filename
    cv2.imwrite(str(output_path), board)
    return output_path


def smooth_point(current: tuple[int, int], previous: tuple[int, int] | None) -> tuple[int, int]:
    if previous is None:
        return current
    return (
        int(previous[0] * 0.65 + current[0] * 0.35),
        int(previous[1] * 0.65 + current[1] * 0.35),
    )


def run() -> int:
    args = parse_args()
    model_path = find_model(args.model)

    if args.self_test:
        with make_landmarker(model_path):
            print(f"[OK] Ready. Using model: {model_path}")
        return 0

    camera = open_camera(args.camera, args.width, args.height)
    active_tool = "blue"
    board_mode = False
    last_draw_point: tuple[int, int] | None = None
    last_pointer: tuple[int, int] | None = None
    saved_message = ""
    saved_message_frames = 0
    last_ms = 0

    try:
        ok, frame = camera.read()
        if not ok:
            raise RuntimeError("Camera opened, but no frame was received.")

        frame = cv2.flip(frame, 1)
        canvas = np.zeros_like(frame)

        with make_landmarker(model_path) as landmarker:
            while True:
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("Camera frame could not be read.")

                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]
                if canvas.shape[:2] != frame.shape[:2]:
                    canvas = np.zeros_like(frame)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                now_ms = max(last_ms + 1, int(time.perf_counter() * 1000))
                last_ms = now_ms
                result = landmarker.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                    now_ms,
                )

                drawing_now = False
                if result.hand_landmarks:
                    hand_landmarks = result.hand_landmarks[0]
                    index_point = landmark_point(hand_landmarks, 8, width, height)
                    pointer = smooth_point(index_point, last_pointer)
                    last_pointer = pointer

                    index_up = finger_is_up(hand_landmarks, 8, 6)
                    middle_up = finger_is_up(hand_landmarks, 12, 10)
                    selecting = index_up and middle_up

                    selected_tool = tool_at(pointer, width) if selecting else None
                    if selected_tool:
                        active_tool = selected_tool
                        last_draw_point = None
                    elif index_up and not middle_up and pointer[1] > TOOLBAR_HEIGHT:
                        tool = TOOLS[active_tool]
                        thickness = ERASER_THICKNESS if tool.eraser else DRAW_THICKNESS
                        line_type = cv2.LINE_8 if tool.eraser else cv2.LINE_AA
                        if last_draw_point is not None:
                            cv2.line(
                                canvas,
                                last_draw_point,
                                pointer,
                                tool.color,
                                thickness,
                                line_type,
                            )
                        last_draw_point = pointer
                        drawing_now = True
                    else:
                        last_draw_point = None

                    display = compose_display(frame, canvas, board_mode)
                    draw_hand(display, hand_landmarks)

                    cursor_color = (
                        (255, 255, 255) if TOOLS[active_tool].eraser else TOOLS[active_tool].color
                    )
                    radius = ERASER_THICKNESS // 2 if TOOLS[active_tool].eraser else 10
                    cv2.circle(display, pointer, radius, cursor_color, 2, cv2.LINE_AA)
                    if drawing_now:
                        cv2.circle(display, pointer, 5, cursor_color, -1, cv2.LINE_AA)
                else:
                    last_draw_point = None
                    last_pointer = None
                    display = compose_display(frame, canvas, board_mode)

                draw_toolbar(display, active_tool, board_mode)

                if saved_message_frames > 0:
                    cv2.putText(
                        display,
                        saved_message,
                        (12, TOOLBAR_HEIGHT + 32),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (40, 255, 40),
                        2,
                        cv2.LINE_AA,
                    )
                    saved_message_frames -= 1

                cv2.imshow(WINDOW, display)
                key = cv2.waitKey(1) & 0xFF

                if key in (ord("q"), ord("Q"), 27):
                    break
                if key in (ord("c"), ord("C")):
                    canvas[:] = 0
                    last_draw_point = None
                elif key in (ord("b"), ord("B")):
                    board_mode = not board_mode
                elif key in (ord("s"), ord("S")):
                    output_path = save_canvas(canvas)
                    saved_message = f"Saved: {output_path.name}"
                    saved_message_frames = 80
                else:
                    for name, tool in TOOLS.items():
                        if key == tool.key or key == ord(chr(tool.key).upper()):
                            active_tool = name
                            last_draw_point = None
                            break
    finally:
        camera.release()
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
