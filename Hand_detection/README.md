# Hand Detection

This project opens your webcam, detects hands with MediaPipe, and draws hand
landmarks on the video.

## Run

From the repository root:

```powershell
python sys.py
```

Or from this folder:

```powershell
python hand.py
```

The old simple command also runs the same detector now:

```powershell
python simple.py
```

## Controls

- `Q` or `Esc`: quit

If the camera does not open, try:

```powershell
python sys.py --camera 1
```
