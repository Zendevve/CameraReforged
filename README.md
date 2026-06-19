# CameraReforged

A tiny binary patcher for **WoW 3.3.5a** that raises the camera's target height, so the camera looks at a point closer to head height instead of the chest. Drag, drop, done.

## Usage

1. Put `Patch_WoW_Camera.bat` and `patch_camera.py` in the same folder.
2. Drag your `WoW.exe` onto `Patch_WoW_Camera.bat`.
3. A console window runs the patch and pauses so you can read the result.

That's it — no command line typing needed.

## Requirements

- Windows
- Python 3 installed, with `python` or `py` available on PATH ([python.org/downloads](https://www.python.org/downloads/))

## What it does

It finds the spot in `Camera_Update` right after the camera reads its target position, and inserts a small code cave that adds a constant offset to the target's Z (height) value before the original code continues. Nothing else about the camera logic changes — distance, angle, and movement all behave the same, just looking at a higher point.

| Setting | Value |
|---|---|
| Height offset | `+0.5` yards |
| Patch site | `0x006070cb` |
| Target client | WoW 3.3.5a |

## Adjusting the height

Open `patch_camera.py` and change:

```python
HEIGHT_ADD = 0.5
```

to whatever offset (in yards) you'd like, then drag `WoW.exe` onto the `.bat` again.

## Safety

- A backup is saved automatically as `WoW.exe.bak` the first time you patch (it won't overwrite an existing backup).
- Running the patcher on an already-patched exe is detected and refused, so you can't double-patch.
- To revert: delete the patched `WoW.exe` and rename `WoW.exe.bak` back to `WoW.exe`.

## Files

- `Patch_WoW_Camera.bat` — drag-and-drop launcher
- `patch_camera.py` — the actual patcher
