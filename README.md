# CameraReforged

A portable binary patcher for **WoW 3.3.5a** that raises the camera's target height, so the camera looks at a point closer to head height instead of the chest. No installation required — just a single `.exe`.

## Support the Project ☕

CameraReforged was built to solve a simple but frustrating problem: WoW's default camera focusing on your character's chest instead of their head, ruining the sense of immersion in Azeroth. I spent hours reverse-engineering assembly offsets, designing a safe byte-patching engine, and building this dark-themed GUI so you can fix it with a single click.

This tool is entirely free, open-source, and free of any ads or tracking. 

If this patcher has made your daily raids, dungeon runs, or leveling adventures more enjoyable, **consider buying me a coffee**. A small token of appreciation goes a long way in supporting the time spent maintaining and updating this project!

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow.svg?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/zendevve)

## Usage

1. Download `CameraReforged.exe` from the [Releases](https://github.com/Zendevve/CameraReforged/releases) page.
2. Place it in the same folder as your `WoW.exe`.
3. Double-click `CameraReforged.exe`.
4. The GUI will auto-detect your `WoW.exe`, show its patch status, and let you apply or adjust the patch with one click.

You can also use the **Browse** button to select a `WoW.exe` from any location.

## Requirements

- Windows (64-bit or 32-bit)

## Features

- **Auto-detect**: Finds `WoW.exe` in the same folder automatically
- **Status check**: Shows whether your exe is patched, unpatched, or an unsupported version
- **Height slider**: Adjust the camera height offset from 0.0 to 3.0 yards
- **Update height**: Change the offset on an already-patched exe without re-patching
- **Restore backup**: One-click revert to the original `WoW.exe` from the `.bak` file

## What it does

It finds the spot in `Camera_Update` right after the camera reads its target position, and inserts a small code cave that adds a constant offset to the target's Z (height) value before the original code continues. Nothing else about the camera logic changes — distance, angle, and movement all behave the same, just looking at a higher point.

| Setting | Value |
|---|---|
| Default height offset | `+0.50` yards |
| Patch site | `0x006070cb` |
| Target client | WoW 3.3.5a |

## Safety

- A backup is saved automatically as `WoW.exe.bak` the first time you patch (it won't overwrite an existing backup).
- Running the patcher on an already-patched exe is detected — use "Update Height" instead.
- To revert: click **Restore Backup** in the GUI, or manually delete `WoW.exe` and rename `WoW.exe.bak`.

## Building from source

1. Install [Python 3](https://www.python.org/downloads/) and [PyInstaller](https://pyinstaller.org/):
   ```
   pip install pyinstaller
   ```
2. Build:
   ```
   pyinstaller --onefile --windowed --name CameraReforged camerareforged.py
   ```
3. The built `.exe` will be in the `dist/` folder.

## Files

- `camerareforged.py` — GUI application (entry point)
- `patcher.py` — patching engine (no UI)

## Automated Releases

This project is configured with GitHub Actions to build and publish releases automatically.

To create a new release:
1. Tag your latest commit with a version number starting with `v` (e.g., `v1.0.0`):
   ```bash
   git tag v1.0.0
   ```
2. Push the tag to GitHub:
   ```bash
   git push origin v1.0.0
   ```

GitHub Actions will automatically trigger, build the standalone executable (`CameraReforged.exe`) using PyInstaller on a Windows runner, and attach it as a release asset under a new GitHub Release.



