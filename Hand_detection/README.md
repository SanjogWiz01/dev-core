# Hand Motion Drawing Board

This project turns your webcam into a hand-controlled drawing board.

## Run

From the repository root:

```powershell
python sys.py
```

Or from this folder:

```powershell
python hand.py
```

## Controls

- Index finger only: draw
- Index + middle fingers: move without drawing
- Open palm / four fingers: erase
- `C`: clear board
- `S`: save drawing to Desktop
- `B`: switch between camera view and whiteboard view
- `1` to `9`: change marker color
- `+` / `-`: change brush size
- `Q` or `Esc`: quit

If the camera does not open, try:

```powershell
python sys.py --camera 1
```
