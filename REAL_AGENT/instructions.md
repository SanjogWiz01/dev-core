# REAL_AGENT Instructions

This folder contains a Python CLI agent that accepts any topic and returns **exactly 5 valid points**.

## Requirements
- Python **3.8+** (your Python **3.13.4** is fully supported).

## How to Run
Open terminal in the project root (`/workspace/dev-core`) and run one of these:

```bash
python3 REAL_AGENT/agent.py
```

If `python3` is not available on your system (common on Windows), run:

```bash
python REAL_AGENT/agent.py
```

Then enter any topic when prompted. Type `exit` or `quit` to stop.

## One-line (non-interactive) usage
You can pass a topic directly:

```bash
python3 REAL_AGENT/agent.py "Artificial Intelligence in Healthcare"
```

(or use `python` instead of `python3` on Windows)

## Output format
The script always prints exactly five numbered points:
1. Definition
2. Key Components
3. Practical Importance
4. Common Challenges
5. Actionable Next Step

## Notes
- Works offline (no API keys needed).
- Interactive mode starts when no topic argument is provided.
