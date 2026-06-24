# CameraReforged — Definitive Edition

A portable, standalone binary patcher for **WoW 3.3.5a** that extends the game client's camera system natively. It offers over-the-shoulder views, custom defaults, and registers new console variables (CVars) directly in the executable on disk—with **no DLL injection, no background processes, and zero Warden detection risk**.

---

## Support the Project ☕

CameraReforged was built to solve the immersion-breaking default WoW camera (focusing on the character's chest instead of their head) and replace risky DLL injection engines. I spent hours reverse-engineering binary offsets, designing an x86 assembly code cave compiler, and building this GUI.

If this patcher has made your leveling or raiding adventures more immersive, **consider buying me a coffee**. A small token of appreciation goes a long way!

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow.svg?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/zendevve)

---

## Features

- **Vertical Height Offset**: Raise the camera focus point (0.0 to 3.0 yards) so it centers at head height instead of the chest.
- **Horizontal Shoulder Offset**: Shift the camera horizontally (-2.0 to 2.0 yards) for a modern, over-the-shoulder action perspective.
- **Max Camera Distance**: Override the client's stock maximum zoom factor limit (1.0 to 5.0 factor, default `2.60`).
- **Camera Zoom Speed**: Customize how quickly the camera zooms in/out (1.0 to 100.0, default `20.00`).
- **Native CVar Registration**: Registers `test_cameraHeight` and `test_cameraOverShoulder` console variables directly inside `WoW.exe` upon startup.
- **Dynamic In-Game Tweaks**: Once patched, variables can be updated in-game instantly via `/console` commands, custom macros, or addons (like DynamicCam)—no need to re-run the patcher.
- **Addon Compatibility**: Fully compatible with WotLK backports of camera addons.
- **Warden Safe**: Zero runtime injection or DLL loading. All modifications are on-disk, localized entirely within safe padding bytes in the `.rdata` section.
- **Automatic Backup**: Saves a `WoW.exe.bak` backup automatically before patching.

---

## CVar Reference

Once patched, the client registers and responds to these console variables natively:

| CVar | Default | Range | What It Does |
|---|---|---|---|
| `/console test_cameraHeight <val>` | `0.50` | `0.00` to `3.00` | Vertical camera focus offset (yards) |
| `/console test_cameraOverShoulder <val>` | `0.00` | `-2.00` to `2.00` | Horizontal camera shoulder offset (yards) |
| `/console cameraDistanceMaxFactor <val>` | `2.60` | `1.00` to `5.00` | Native max camera zoom distance multiplier |
| `/console cameraDistanceMoveSpeed <val>` | `20.00` | `1.00` to `100.00` | Native camera zoom speed |

---

## ConsoleXP Migration Guide

DynamicCam and similar layouts previously required running `ConsoleXP.dll` via hook injectors (e.g. `ConsoleXPPatcher.exe`) to register camera variables. Since CameraReforged now registers these exact same CVars natively, you can completely uninstall ConsoleXP:

1. Restore your original, unpatched `WoW.exe` (or rename your backup).
2. Delete `ConsoleXP.dll`, `ConsoleXPPatcher.exe`, and any related DLL injection launchers.
3. Open `CameraReforged.exe` and click **Browse** to select your `WoW.exe`.
4. Configure your desired defaults and click **Apply Patch**.
5. Launch the game. Your existing camera addons will automatically detect the CVars and function perfectly out-of-the-box!

---

## Usage

1. Download the latest `CameraReforged.exe` from the [Releases](https://github.com/Zendevve/CameraReforged/releases) page.
2. Place the executable next to your `WoW.exe`.
3. Double-click to launch the dark-themed GUI.
4. Set your default settings, and click **Apply Patch**.
5. To change settings without patching again:
   - Either adjust the sliders and click **Update Settings** in the GUI.
   - Or change them inside the game using the `/console` commands listed above.
6. To restore the original executable, click **Restore Backup** in the GUI.

---

## Technical Details

CameraReforged modifies the PE header to mark the `.rdata` section as executable and writeable. It utilizes 384 bytes of dead alignment padding at the end of the `.rdata` section to build a code cave containing:
- Float variables and CVar string definitions.
- Custom FPU assembly callback routines that intercept CVar updates and store the parsed float value at offset `0x2C` inside the CVar structure.
- Detour hooks placed at the entry point of `CVars_Initialize` (`0x0051D9B0`) and the camera update routine (`0x006070cb`).

---

## Building from Source

1. Install [Python 3](https://www.python.org/downloads/) and [PyInstaller](https://pyinstaller.org/):
   ```
   pip install pyinstaller
   ```
2. Build the standalone executable:
   ```
   pyinstaller --onefile --windowed --name CameraReforged camerareforged.py
   ```
3. The packaged `.exe` will be generated in the `dist/` folder.

---

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](file:///d:/COMPROG/camerawow/LICENSE) file for details.

