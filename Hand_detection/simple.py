"""Compatibility launcher for the hand motion drawing board.

This file used to run an HSV skin-color contour demo. That approach is very
sensitive to lighting and often fails to detect hands, so keep the old command
working by launching the MediaPipe hand landmarker app instead.
"""

from pathlib import Path
import runpy


ROOT_SCRIPT = Path(__file__).resolve().parents[1] / "sys.py"
runpy.run_path(str(ROOT_SCRIPT), run_name="__main__")
