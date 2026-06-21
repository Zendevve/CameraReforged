# CameraReforged

A tiny binary patcher for **WoW 3.3.5a** that raises the camera's target height, so the camera looks at a point closer to head height instead of the chest. Drag, drop, done.

## Usage

1. Download `CameraReforged.exe` from the [Releases](https://github.com/Zendevve/CameraReforged/releases) page.
2. Drag your `WoW.exe` onto `CameraReforged.exe`.
3. A console window runs the patch and pauses so you can read the result.

That's it — no Python, no command line, no installation. Just a single portable `.exe`.

## Requirements

- Windows (64-bit or 32-bit)

## What it does

It finds the spot in `Camera_Update` right after the camera reads its target position, and inserts a small code cave that adds a constant offset to the target's Z (height) value before the original code continues. Nothing else about the camera logic changes — distance, angle, and movement all behave the same, just looking at a higher point.

| Setting | Value |
|---|---|
| Height offset | `+0.5` yards |
| Patch site | `0x006070cb` |
| Target client | WoW 3.3.5a |

## Adjusting the height

If you've already patched your `WoW.exe`, you can change the baked-in offset without re-patching from scratch:

```
CameraReforged.exe WoW.exe --set-height 1.25
```

This rewrites the float constant inside the existing patch. Close WoW first.

## Safety

- A backup is saved automatically as `WoW.exe.bak` the first time you patch (it won't overwrite an existing backup).
- Running the patcher on an already-patched exe is detected and refused, so you can't double-patch.
- To revert: delete the patched `WoW.exe` and rename `WoW.exe.bak` back to `WoW.exe`.

## Building from source

If you want to modify the default height offset or tweak the patcher:

1. Edit `HEIGHT_ADD` in `patch_camera.py`.
2. Install [PyInstaller](https://pyinstaller.org/): `pip install pyinstaller`
3. Build: `pyinstaller --onefile --console --name CameraReforged patch_camera.py`
4. The built `.exe` will be in the `dist/` folder.

Alternatively, you can run the Python script directly if you have Python 3 installed:

```
python patch_camera.py WoW.exe --apply
```

Or use the included `Patch_WoW_Camera.bat` drag-and-drop launcher (it will auto-detect Python or offer to download a portable copy).

## Files

- `CameraReforged.exe` — standalone portable patcher (no dependencies)
- `patch_camera.py` — the source patcher script
- `Patch_WoW_Camera.bat` — fallback drag-and-drop launcher (for users with Python)
