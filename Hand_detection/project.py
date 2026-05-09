"""Advanced hand-motion writing board.

Run:
    python Hand_detection/project.py

Controls:
    - Keep only the index finger extended to write.
    - Keep index + middle extended to move/select without writing.
    - Touch the top toolbar with index + middle to select color or eraser.
    - Press 1-4 for colors, E for eraser, [/] for marker size, C clear,
      B board/camera view, S save, Q or Esc quit.

This version keeps MediaPipe for robust landmark detection, then uses a
geometry-based gesture classifier instead of the simple "tip above joint"
check. That makes index tracking and draw/select gestures work when the hand is
up, down, or sideways.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

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


WINDOW = "Advanced Hand Writing Board"
TOOLBAR_HEIGHT = 84
DEFAULT_MARKER_THICKNESS = 10
ERASER_THICKNESS = 46
MAX_DRAW_JUMP = 135
INK_ANCHOR_MAX_OFFSET = 24
WRITE_GRACE_FRAMES = 7
GESTURE_SMOOTHING_FRAMES = 5
PEN_TIP_EXTENSION_RATIO = 0.35
MAX_PEN_TIP_EXTENSION = 22.0
MIN_HAND_DETECTION_CONFIDENCE = 0.45
MIN_HAND_PRESENCE_CONFIDENCE = 0.45
MIN_TRACKING_CONFIDENCE = 0.50
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


@dataclass(frozen=True)
class GestureState:
    thumb: bool
    index: bool
    middle: bool
    ring: bool
    pinky: bool
    pose: str
    motion: str

    @property
    def writing(self) -> bool:
        return self.index and not self.middle

    @property
    def selecting(self) -> bool:
        return self.index and self.middle and not self.ring and not self.pinky

    @property
    def raised_count(self) -> int:
        return sum((self.thumb, self.index, self.middle, self.ring, self.pinky))


TOOLS: dict[str, Tool] = {
    "blue": Tool("Blue", (255, 95, 0), ord("1")),
    "green": Tool("Green", (45, 210, 70), ord("2")),
    "red": Tool("Red", (35, 35, 255), ord("3")),
    "yellow": Tool("Yellow", (0, 220, 255), ord("4")),
    "eraser": Tool("Eraser", (0, 0, 0), ord("e"), eraser=True),
}
PALETTE = ["blue", "green", "red", "yellow", "eraser"]


class OneEuro1D:
    """Responsive smoothing: steady when slow, quick when the finger moves fast."""

    def __init__(
        self,
        min_cutoff: float = 1.7,
        beta: float = 0.015,
        derivative_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.derivative_cutoff = derivative_cutoff
        self.last_time: float | None = None
        self.last_raw: float | None = None
        self.last_value: float | None = None
        self.last_derivative: float = 0.0

    def reset(self) -> None:
        self.last_time = None
        self.last_raw = None
        self.last_value = None
        self.last_derivative = 0.0

    @staticmethod
    def alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    @staticmethod
    def low_pass(value: float, previous: float, alpha: float) -> float:
        return alpha * value + (1.0 - alpha) * previous

    def __call__(self, value: float, now: float) -> float:
        if self.last_time is None or self.last_raw is None or self.last_value is None:
            self.last_time = now
            self.last_raw = value
            self.last_value = value
            return value

        dt = max(now - self.last_time, 1e-6)
        derivative = (value - self.last_raw) / dt
        derivative_alpha = self.alpha(self.derivative_cutoff, dt)
        derivative_hat = self.low_pass(
            derivative,
            self.last_derivative,
            derivative_alpha,
        )
        cutoff = self.min_cutoff + self.beta * abs(derivative_hat)
        value_alpha = self.alpha(cutoff, dt)
        smoothed = self.low_pass(value, self.last_value, value_alpha)

        self.last_time = now
        self.last_raw = value
        self.last_value = smoothed
        self.last_derivative = derivative_hat
        return smoothed


class PointerFilter:
    def __init__(
        self,
        min_cutoff: float = 1.7,
        beta: float = 0.015,
        derivative_cutoff: float = 1.0,
    ) -> None:
        self.x = OneEuro1D(min_cutoff, beta, derivative_cutoff)
        self.y = OneEuro1D(min_cutoff, beta, derivative_cutoff)

    def reset(self) -> None:
        self.x.reset()
        self.y.reset()

    def __call__(self, point: tuple[int, int], now: float) -> tuple[int, int]:
        return (
            int(round(self.x(float(point[0]), now))),
            int(round(self.y(float(point[1]), now))),
        )


class GestureSmoother:
    """Debounce landmark noise while keeping index-finger writing responsive."""

    def __init__(self, window: int = GESTURE_SMOOTHING_FRAMES) -> None:
        self.samples: deque[GestureState] = deque(maxlen=window)

    def reset(self) -> None:
        self.samples.clear()

    @staticmethod
    def voted(values: Iterable[bool], required: int) -> bool:
        return sum(values) >= required

    def update(self, gesture: GestureState) -> GestureState:
        self.samples.append(gesture)
        sample_count = len(self.samples)
        if sample_count < 3:
            return gesture

        # Writing starts quickly, while middle/ring/pinky need stronger
        # agreement so one noisy frame does not lift the pen.
        index_required = max(2, sample_count // 2)
        blocker_required = max(3, (sample_count + 1) // 2)
        latest = self.samples[-1]

        return GestureState(
            thumb=self.voted((sample.thumb for sample in self.samples), blocker_required),
            index=self.voted((sample.index for sample in self.samples), index_required),
            middle=self.voted((sample.middle for sample in self.samples), blocker_required),
            ring=self.voted((sample.ring for sample in self.samples), blocker_required),
            pinky=self.voted((sample.pinky for sample in self.samples), blocker_required),
            pose=latest.pose,
            motion=latest.motion,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write smoothly with hand motion")
    parser.add_argument("--camera", type=int, default=0, help="camera index")
    parser.add_argument("--width", type=int, default=1280, help="camera width")
    parser.add_argument("--height", type=int, default=720, help="camera height")
    parser.add_argument("--model", type=Path, default=None, help="hand_landmarker.task path")
    parser.add_argument("--hands", type=int, default=1, choices=(1, 2), help="maximum hands to track")
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


def make_landmarker(model_path: Path, max_hands: int = 1) -> vision.HandLandmarker:
    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=max_hands,
        min_hand_detection_confidence=MIN_HAND_DETECTION_CONFIDENCE,
        min_hand_presence_confidence=MIN_HAND_PRESENCE_CONFIDENCE,
        min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
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


def as_vector(landmark) -> np.ndarray:
    return np.array((landmark.x, landmark.y, landmark.z), dtype=np.float32)


def distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    denom = float(np.linalg.norm(ba) * np.linalg.norm(bc))
    if denom <= 1e-7:
        return 0.0
    cosine = float(np.clip(np.dot(ba, bc) / denom, -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def landmark_point(landmarks, landmark_id: int, width: int, height: int) -> tuple[int, int]:
    landmark = landmarks[landmark_id]
    x = min(max(int(landmark.x * width), 0), width - 1)
    y = min(max(int(landmark.y * height), 0), height - 1)
    return x, y


def index_pen_point(landmarks, width: int, height: int) -> tuple[int, int]:
    tip = np.array(landmark_point(landmarks, 8, width, height), dtype=np.float32)
    dip = np.array(landmark_point(landmarks, 7, width, height), dtype=np.float32)
    direction = tip - dip
    length = float(np.linalg.norm(direction))
    if length <= 1e-6:
        x, y = tip
    else:
        extension = min(MAX_PEN_TIP_EXTENSION, length * PEN_TIP_EXTENSION_RATIO)
        x, y = tip + (direction / length) * extension

    return (
        min(max(int(round(x)), 0), width - 1),
        min(max(int(round(y)), 0), height - 1),
    )


def anchor_point_to_raw(
    point: tuple[int, int],
    raw_point: tuple[int, int],
    max_offset: int,
) -> tuple[int, int]:
    dx = point[0] - raw_point[0]
    dy = point[1] - raw_point[1]
    distance_px = math.hypot(dx, dy)
    if distance_px <= max_offset or distance_px <= 1e-6:
        return point

    scale = max_offset / distance_px
    return (
        int(round(raw_point[0] + dx * scale)),
        int(round(raw_point[1] + dy * scale)),
    )


def finger_extended(
    landmarks,
    ids: tuple[int, int, int, int],
    *,
    relaxed: bool = False,
) -> bool:
    mcp_id, pip_id, dip_id, tip_id = ids
    mcp = as_vector(landmarks[mcp_id])
    pip = as_vector(landmarks[pip_id])
    dip = as_vector(landmarks[dip_id])
    tip = as_vector(landmarks[tip_id])
    wrist = as_vector(landmarks[0])
    palm = (as_vector(landmarks[0]) + as_vector(landmarks[5]) + as_vector(landmarks[9]) + as_vector(landmarks[17])) / 4.0

    finger_length = distance(mcp, pip) + distance(pip, dip) + distance(dip, tip)
    if finger_length <= 1e-6:
        return False

    pip_angle = joint_angle(mcp, pip, dip)
    dip_angle = joint_angle(pip, dip, tip)
    reach = distance(mcp, tip) / finger_length
    tip_from_palm = distance(tip, palm)
    pip_from_palm = distance(pip, palm)
    tip_from_wrist = distance(tip, wrist)
    pip_from_wrist = distance(pip, wrist)

    if relaxed:
        min_pip_angle = 118.0
        min_dip_angle = 108.0
        min_reach = 0.50
        palm_ratio = 0.98
        wrist_ratio = 0.98
    else:
        min_pip_angle = 132.0
        min_dip_angle = 118.0
        min_reach = 0.58
        palm_ratio = 1.04
        wrist_ratio = 1.02

    straight_enough = (
        pip_angle >= min_pip_angle
        and dip_angle >= min_dip_angle
        and reach >= min_reach
    )
    points_away = (
        tip_from_palm >= pip_from_palm * palm_ratio
        and tip_from_wrist >= pip_from_wrist * wrist_ratio
    )

    # Upright hands are common while drawing. This fallback keeps writing usable
    # when the 3D angle estimate is noisy, but still requires the fingertip to
    # reach away from the palm.
    upright_fallback = (
        tip[1] < pip[1] - 0.012
        and tip[1] < mcp[1] - 0.018
        and reach >= min_reach * 0.9
        and tip_from_palm >= pip_from_palm * 0.96
    )

    folded = (
        pip_angle < min_pip_angle - 18.0
        and reach < min_reach
        and tip_from_palm < pip_from_palm * 0.92
    )
    if folded:
        return False

    return (straight_enough and points_away) or upright_fallback


def thumb_extended(landmarks) -> bool:
    cmc = as_vector(landmarks[1])
    mcp = as_vector(landmarks[2])
    ip = as_vector(landmarks[3])
    tip = as_vector(landmarks[4])
    wrist = as_vector(landmarks[0])
    palm = (as_vector(landmarks[5]) + as_vector(landmarks[9]) + as_vector(landmarks[17])) / 3.0

    thumb_length = distance(cmc, mcp) + distance(mcp, ip) + distance(ip, tip)
    if thumb_length <= 1e-6:
        return False

    open_angle = joint_angle(cmc, mcp, tip)
    reach = distance(mcp, tip) / thumb_length
    away_from_palm = distance(tip, palm) > distance(ip, palm)
    away_from_wrist = distance(tip, wrist) > distance(mcp, wrist)
    return open_angle > 135.0 and reach > 0.58 and away_from_palm and away_from_wrist


def classify_pose(landmarks) -> str:
    wrist = as_vector(landmarks[0])
    middle_mcp = as_vector(landmarks[9])
    axis = middle_mcp - wrist
    dx = float(axis[0])
    dy = float(axis[1])

    if abs(dx) > abs(dy) * 1.15:
        return "SIDE"
    if dy < 0:
        return "UP"
    return "DOWN"


def classify_motion(history: deque[tuple[float, tuple[int, int]]]) -> str:
    if len(history) < 4:
        return "STEADY"

    old_time, old_point = history[0]
    new_time, new_point = history[-1]
    dt = max(new_time - old_time, 1e-6)
    dx = new_point[0] - old_point[0]
    dy = new_point[1] - old_point[1]
    speed = math.hypot(dx, dy) / dt

    if speed < 720:
        return "STEADY"
    if abs(dx) > abs(dy) * 1.35:
        return "SLIDE RIGHT" if dx > 0 else "SLIDE LEFT"
    if abs(dy) > abs(dx) * 1.35:
        return "SLIDE DOWN" if dy > 0 else "SLIDE UP"
    return "FAST MOVE"


def classify_gesture(landmarks, motion: str) -> GestureState:
    return GestureState(
        thumb=thumb_extended(landmarks),
        index=finger_extended(landmarks, (5, 6, 7, 8), relaxed=True),
        middle=finger_extended(landmarks, (9, 10, 11, 12)),
        ring=finger_extended(landmarks, (13, 14, 15, 16)),
        pinky=finger_extended(landmarks, (17, 18, 19, 20)),
        pose=classify_pose(landmarks),
        motion=motion,
    )


def palm_size_pixels(landmarks, width: int, height: int) -> float:
    wrist = np.array(landmark_point(landmarks, 0, width, height), dtype=np.float32)
    middle = np.array(landmark_point(landmarks, 9, width, height), dtype=np.float32)
    index = np.array(landmark_point(landmarks, 5, width, height), dtype=np.float32)
    pinky = np.array(landmark_point(landmarks, 17, width, height), dtype=np.float32)
    return float(np.linalg.norm(wrist - middle) + np.linalg.norm(index - pinky))


def draw_jump_limit(landmarks, width: int, height: int) -> float:
    scaled_limit = palm_size_pixels(landmarks, width, height) * 0.55
    return min(220.0, max(float(MAX_DRAW_JUMP), scaled_limit))


def select_primary_hand(
    hands: Iterable,
    width: int,
    height: int,
    last_pointer: tuple[int, int] | None,
):
    hands = list(hands)
    if not hands:
        return None
    if last_pointer is not None:
        lx, ly = last_pointer
        return min(
            hands,
            key=lambda hand: math.hypot(
                landmark_point(hand, 8, width, height)[0] - lx,
                landmark_point(hand, 8, width, height)[1] - ly,
            ),
        )
    return max(hands, key=lambda hand: palm_size_pixels(hand, width, height))


def draw_hand(frame, landmarks, active: bool = True) -> None:
    height, width = frame.shape[:2]
    points = [landmark_point(landmarks, index, width, height) for index in range(21)]
    line_color = (0, 205, 255) if active else (140, 140, 140)
    dot_color = (255, 255, 255) if active else (200, 200, 200)

    for start, end in CONNECTIONS:
        cv2.line(frame, points[start], points[end], line_color, 2, cv2.LINE_AA)
    for point in points:
        cv2.circle(frame, point, 4, (25, 25, 25), -1, cv2.LINE_AA)
        cv2.circle(frame, point, 3, dot_color, -1, cv2.LINE_AA)


def toolbar_layout(width: int) -> list[tuple[str, tuple[int, int, int, int]]]:
    gap = 8
    left = 12
    usable_width = max(width - (left * 2) - gap * (len(PALETTE) - 1), 1)
    box_width = min(116, max(74, usable_width // len(PALETTE)))
    layout = []
    for index, name in enumerate(PALETTE):
        x1 = left + index * (box_width + gap)
        layout.append((name, (x1, 12, x1 + box_width, 64)))
    return layout


def tool_at(point: tuple[int, int], width: int) -> str | None:
    x, y = point
    if y > TOOLBAR_HEIGHT:
        return None
    for name, (x1, y1, x2, y2) in toolbar_layout(width):
        if x1 <= x <= x2 and y1 <= y <= y2:
            return name
    return None


def draw_toolbar(
    frame,
    active_tool: str,
    board_mode: bool,
    marker_thickness: int,
    gesture: GestureState | None,
) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, TOOLBAR_HEIGHT), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.88, frame, 0.12, 0, frame)

    for index, (name, rect) in enumerate(toolbar_layout(width), start=1):
        x1, y1, x2, y2 = rect
        tool = TOOLS[name]
        border = (255, 255, 255) if name == active_tool else (100, 100, 100)
        cv2.rectangle(frame, (x1, y1), (x2, y2), tool.color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), border, 2)

        label = f"{index}" if not tool.eraser else "E"
        text_color = (25, 25, 25) if name == "yellow" else (255, 255, 255)
        cv2.putText(
            frame,
            label,
            (x1 + 13, y1 + 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            text_color,
            2,
            cv2.LINE_AA,
        )

    mode = "Board" if board_mode else "Camera"
    pose = "NO HAND" if gesture is None else f"{gesture.pose} | {gesture.motion}"
    state = "WRITE" if gesture and gesture.writing else "MOVE"
    if gesture and gesture.selecting:
        state = "SELECT"
    help_text = (
        f"{mode} | {state} | {pose} | size {marker_thickness} | "
        "1-4 colors E eraser [] size C clear B view S save Q quit"
    )
    text_color = (45, 45, 45) if board_mode else (20, 255, 20)
    cv2.putText(
        frame,
        help_text,
        (12, height - 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        text_color,
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

    filename = f"writing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    output_path = SCRIPT_DIR / filename
    cv2.imwrite(str(output_path), board)
    return output_path


def draw_marker_stroke(
    canvas,
    start: tuple[int, int] | None,
    end: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int,
    eraser: bool,
) -> None:
    line_type = cv2.LINE_8 if eraser else cv2.LINE_AA
    radius = max(2, thickness // 2)
    if start is None:
        cv2.circle(canvas, end, radius, color, -1, line_type)
        return

    distance_px = math.hypot(end[0] - start[0], end[1] - start[1])
    steps = max(1, int(distance_px / max(2, radius * 0.45)))
    for step in range(1, steps + 1):
        t = step / steps
        x = int(round(start[0] + (end[0] - start[0]) * t))
        y = int(round(start[1] + (end[1] - start[1]) * t))
        cv2.circle(canvas, (x, y), radius, color, -1, line_type)


def clamp_marker_size(value: int) -> int:
    return min(max(value, 3), 30)


def run() -> int:
    args = parse_args()
    model_path = find_model(args.model)

    if args.self_test:
        with make_landmarker(model_path, args.hands):
            print(f"[OK] Ready. Using model: {model_path}")
        return 0

    camera = open_camera(args.camera, args.width, args.height)
    active_tool = "blue"
    board_mode = False
    marker_thickness = DEFAULT_MARKER_THICKNESS
    pointer_filter = PointerFilter()
    ink_filter = PointerFilter(min_cutoff=4.8, beta=0.055, derivative_cutoff=1.4)
    gesture_smoother = GestureSmoother()
    pointer_history: deque[tuple[float, tuple[int, int]]] = deque(maxlen=7)
    last_draw_point: tuple[int, int] | None = None
    last_pointer: tuple[int, int] | None = None
    last_ink_point: tuple[int, int] | None = None
    missing_frames = 0
    write_grace_frames = 0
    saved_message = ""
    saved_message_frames = 0
    last_ms = 0

    try:
        ok, frame = camera.read()
        if not ok:
            raise RuntimeError("Camera opened, but no frame was received.")

        frame = cv2.flip(frame, 1)
        canvas = np.zeros_like(frame)

        with make_landmarker(model_path, args.hands) as landmarker:
            while True:
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("Camera frame could not be read.")

                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]
                if canvas.shape[:2] != frame.shape[:2]:
                    canvas = np.zeros_like(frame)
                    last_draw_point = None
                    last_ink_point = None

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                now_seconds = time.perf_counter()
                now_ms = max(last_ms + 1, int(now_seconds * 1000))
                last_ms = now_ms
                result = landmarker.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                    now_ms,
                )

                gesture: GestureState | None = None
                hands = result.hand_landmarks or []
                selected_hand = select_primary_hand(hands, width, height, last_pointer)

                if selected_hand is not None:
                    missing_frames = 0
                    raw_pointer = index_pen_point(selected_hand, width, height)
                    pointer = pointer_filter(raw_pointer, now_seconds)
                    ink_point = anchor_point_to_raw(
                        ink_filter(raw_pointer, now_seconds),
                        raw_pointer,
                        INK_ANCHOR_MAX_OFFSET,
                    )
                    pointer_history.append((now_seconds, pointer))
                    last_pointer = pointer
                    last_ink_point = ink_point
                    motion = classify_motion(pointer_history)
                    gesture = gesture_smoother.update(classify_gesture(selected_hand, motion))

                    selected_tool = tool_at(pointer, width) if gesture.selecting else None
                    if selected_tool:
                        active_tool = selected_tool
                        last_draw_point = None
                        write_grace_frames = 0
                    else:
                        in_writing_area = ink_point[1] > TOOLBAR_HEIGHT
                        keep_writing = (
                            write_grace_frames > 0
                            and last_draw_point is not None
                            and in_writing_area
                            and not gesture.selecting
                            and not gesture.middle
                            and not gesture.ring
                            and not gesture.pinky
                        )
                        should_write = gesture.writing and in_writing_area

                        if should_write:
                            write_grace_frames = WRITE_GRACE_FRAMES
                        elif keep_writing:
                            write_grace_frames -= 1
                        else:
                            write_grace_frames = 0

                    if write_grace_frames > 0:
                        tool = TOOLS[active_tool]
                        thickness = ERASER_THICKNESS if tool.eraser else marker_thickness
                        if last_draw_point is not None:
                            jump = math.hypot(
                                ink_point[0] - last_draw_point[0],
                                ink_point[1] - last_draw_point[1],
                            )
                            if jump > draw_jump_limit(selected_hand, width, height):
                                last_draw_point = None
                        draw_marker_stroke(
                            canvas,
                            last_draw_point,
                            ink_point,
                            tool.color,
                            thickness,
                            tool.eraser,
                        )
                        last_draw_point = ink_point
                    else:
                        last_draw_point = None
                else:
                    missing_frames += 1
                    last_draw_point = None
                    last_ink_point = None
                    write_grace_frames = 0
                    if missing_frames > 5:
                        pointer_filter.reset()
                        ink_filter.reset()
                        gesture_smoother.reset()
                        pointer_history.clear()
                        last_pointer = None

                display = compose_display(frame, canvas, board_mode)
                for hand in hands:
                    draw_hand(display, hand, active=(hand is selected_hand))

                if selected_hand is not None and last_pointer is not None:
                    tool = TOOLS[active_tool]
                    radius = ERASER_THICKNESS // 2 if tool.eraser else max(7, marker_thickness)
                    cursor_color = (255, 255, 255) if tool.eraser else tool.color
                    cursor_point = last_ink_point if write_grace_frames > 0 else last_pointer
                    cv2.circle(display, cursor_point, radius, cursor_color, 2, cv2.LINE_AA)
                    cv2.circle(display, cursor_point, 4, cursor_color, -1, cv2.LINE_AA)

                draw_toolbar(display, active_tool, board_mode, marker_thickness, gesture)

                if saved_message_frames > 0:
                    cv2.putText(
                        display,
                        saved_message,
                        (12, TOOLBAR_HEIGHT + 34),
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
                elif key in (ord("["), ord("{")):
                    marker_thickness = clamp_marker_size(marker_thickness - 1)
                elif key in (ord("]"), ord("}")):
                    marker_thickness = clamp_marker_size(marker_thickness + 1)
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
