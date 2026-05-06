"""Run the hand detection viewer from the project root."""

from pathlib import Path
import runpy


ROOT_SCRIPT = Path(__file__).resolve().parents[1] / "sys.py"
runpy.run_path(str(ROOT_SCRIPT), run_name="__main__")
