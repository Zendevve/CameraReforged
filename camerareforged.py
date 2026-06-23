"""
CameraReforged — WoW 3.3.5a Camera Height Offset Patcher (GUI)

Dark-themed tkinter application.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os
import sys
import webbrowser

import patcher


# ── Colour palette ──────────────────────────────────────────────────────────
BG_DARK      = "#0f0f1a"
BG_PANEL     = "#1a1a2e"
BG_INPUT     = "#16213e"
BG_LOG       = "#0d1117"
FG_PRIMARY   = "#e0e0e0"
FG_DIM       = "#8b8fa3"
FG_BRIGHT    = "#ffffff"
ACCENT       = "#4361ee"
ACCENT_HOVER = "#5a7cff"
GREEN        = "#2ecc71"
AMBER        = "#f39c12"
RED          = "#e74c3c"
BORDER       = "#2a2a4a"


class CameraReforgedApp:
    """Main application window."""

    def __init__(self, root):
        self.root = root
        self.root.title("CameraReforged")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, False)

        # Centre on screen
        w, h = 560, 650
        x = (self.root.winfo_screenwidth()  - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.exe_path = None
        self.status   = None  # "unpatched" | "patched" | "unknown" | None
        self.cur_height = None

        self._build_ui()
        self._auto_detect()

    # ── UI Construction ─────────────────────────────────────────────────

    def _build_ui(self):
        # Main container
        main = tk.Frame(self.root, bg=BG_DARK, padx=20, pady=16)
        main.pack(fill="both", expand=True)

        # ── Header ──
        hdr = tk.Frame(main, bg=BG_DARK)
        hdr.pack(fill="x", pady=(0, 16))

        tk.Label(
            hdr, text="⚔  CameraReforged", font=("Segoe UI", 20, "bold"),
            fg=FG_BRIGHT, bg=BG_DARK
        ).pack(side="left")

        tk.Label(
            hdr, text="WoW 3.3.5a Camera Patcher",
            font=("Segoe UI", 10), fg=FG_DIM, bg=BG_DARK
        ).pack(side="left", padx=(12, 0), pady=(6, 0))

        # ── Support section ──
        support_frame = tk.Frame(main, bg=BG_PANEL, highlightbackground=BORDER,
                                 highlightthickness=1, padx=14, pady=12)
        support_frame.pack(fill="x", pady=(0, 12))

        support_label = tk.Label(
            support_frame, text="Crafted for the community. If CameraReforged made Azeroth feel more immersive, support is always appreciated! ☕",
            font=("Segoe UI", 8, "italic"), fg=FG_DIM, bg=BG_PANEL, justify="left", anchor="w",
            wraplength=380
        )
        support_label.pack(side="left", anchor="w")

        support_btn = tk.Button(
            support_frame, text="☕ Support", font=("Segoe UI", 9, "bold"),
            fg="#000000", bg="#FFDD00", activebackground="#ffea5c",
            activeforeground="#000000", bd=0, padx=12, pady=5,
            cursor="hand2", command=self._open_donation
        )
        support_btn.pack(side="right", anchor="e")

        # ── File section ──
        file_frame = tk.Frame(main, bg=BG_PANEL, highlightbackground=BORDER,
                              highlightthickness=1, padx=14, pady=12)
        file_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            file_frame, text="WOW EXECUTABLE", font=("Segoe UI", 8, "bold"),
            fg=FG_DIM, bg=BG_PANEL
        ).pack(anchor="w")

        path_row = tk.Frame(file_frame, bg=BG_PANEL)
        path_row.pack(fill="x", pady=(6, 0))

        self.path_var = tk.StringVar(value="No file selected")
        self.path_label = tk.Label(
            path_row, textvariable=self.path_var, font=("Consolas", 10),
            fg=FG_PRIMARY, bg=BG_INPUT, anchor="w", padx=10, pady=6
        )
        self.path_label.pack(side="left", fill="x", expand=True)

        self.browse_btn = tk.Button(
            path_row, text="Browse", font=("Segoe UI", 9, "bold"),
            fg=FG_BRIGHT, bg=ACCENT, activebackground=ACCENT_HOVER,
            activeforeground=FG_BRIGHT, bd=0, padx=16, pady=6,
            cursor="hand2", command=self._browse
        )
        self.browse_btn.pack(side="right", padx=(8, 0))

        # ── Status section ──
        status_frame = tk.Frame(main, bg=BG_PANEL, highlightbackground=BORDER,
                                highlightthickness=1, padx=14, pady=12)
        status_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            status_frame, text="PATCH STATUS", font=("Segoe UI", 8, "bold"),
            fg=FG_DIM, bg=BG_PANEL
        ).pack(anchor="w")

        self.status_var = tk.StringVar(value="—  No file loaded")
        self.status_label = tk.Label(
            status_frame, textvariable=self.status_var,
            font=("Segoe UI", 13, "bold"), fg=FG_DIM, bg=BG_PANEL, anchor="w"
        )
        self.status_label.pack(anchor="w", pady=(6, 0))

        # ── Height control ──
        height_frame = tk.Frame(main, bg=BG_PANEL, highlightbackground=BORDER,
                                highlightthickness=1, padx=14, pady=12)
        height_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            height_frame, text="HEIGHT OFFSET (YARDS)",
            font=("Segoe UI", 8, "bold"), fg=FG_DIM, bg=BG_PANEL
        ).pack(anchor="w")

        slider_row = tk.Frame(height_frame, bg=BG_PANEL)
        slider_row.pack(fill="x", pady=(8, 0))

        self.height_var = tk.DoubleVar(value=patcher.DEFAULT_HEIGHT)

        self.height_scale = tk.Scale(
            slider_row, from_=0.0, to=3.0, resolution=0.05, orient="horizontal",
            variable=self.height_var, bg=BG_PANEL, fg=FG_PRIMARY,
            troughcolor=BG_INPUT, highlightbackground=BG_PANEL,
            activebackground=ACCENT, sliderrelief="flat",
            font=("Consolas", 10), bd=0, length=380,
            command=self._on_slider_change
        )
        self.height_scale.pack(side="left", fill="x", expand=True)

        self.height_entry = tk.Entry(
            slider_row, textvariable=self.height_var, width=6,
            font=("Consolas", 12, "bold"), fg=ACCENT, bg=BG_INPUT,
            insertbackground=FG_PRIMARY, bd=0, justify="center"
        )
        self.height_entry.pack(side="right", padx=(10, 0), ipady=4)
        self.height_entry.bind("<Return>", self._on_entry_change)
        self.height_entry.bind("<FocusOut>", self._on_entry_change)

        # ── Action buttons ──
        btn_frame = tk.Frame(main, bg=BG_DARK)
        btn_frame.pack(fill="x", pady=(0, 12))

        self.patch_btn = tk.Button(
            btn_frame, text="⚡  Apply Patch", font=("Segoe UI", 11, "bold"),
            fg=FG_BRIGHT, bg=ACCENT, activebackground=ACCENT_HOVER,
            activeforeground=FG_BRIGHT, bd=0, padx=20, pady=10,
            cursor="hand2", command=self._apply_patch
        )
        self.patch_btn.pack(side="left", fill="x", expand=True)

        self.height_btn = tk.Button(
            btn_frame, text="📐  Update Height", font=("Segoe UI", 11, "bold"),
            fg=FG_BRIGHT, bg="#2a6041", activebackground=GREEN,
            activeforeground=FG_BRIGHT, bd=0, padx=20, pady=10,
            cursor="hand2", command=self._update_height
        )
        self.height_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.restore_btn = tk.Button(
            btn_frame, text="↩  Restore Backup", font=("Segoe UI", 11, "bold"),
            fg=FG_BRIGHT, bg="#6b2130", activebackground=RED,
            activeforeground=FG_BRIGHT, bd=0, padx=20, pady=10,
            cursor="hand2", command=self._restore_backup
        )
        self.restore_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # ── Log area ──
        log_frame = tk.Frame(main, bg=BG_PANEL, highlightbackground=BORDER,
                             highlightthickness=1)
        log_frame.pack(fill="both", expand=True)

        tk.Label(
            log_frame, text="LOG", font=("Segoe UI", 8, "bold"),
            fg=FG_DIM, bg=BG_PANEL
        ).pack(anchor="w", padx=14, pady=(8, 0))

        self.log_text = tk.Text(
            log_frame, height=7, font=("Consolas", 9), fg=FG_DIM, bg=BG_LOG,
            bd=0, padx=14, pady=8, wrap="word", state="disabled",
            insertbackground=FG_PRIMARY
        )
        self.log_text.pack(fill="both", expand=True, padx=2, pady=(4, 2))

        # Configure log tag colours
        self.log_text.tag_configure("info",    foreground=FG_PRIMARY)
        self.log_text.tag_configure("success", foreground=GREEN)
        self.log_text.tag_configure("warning", foreground=AMBER)
        self.log_text.tag_configure("error",   foreground=RED)

        self._update_buttons()

    # ── Logging ─────────────────────────────────────────────────────────

    def _log(self, msg, tag="info"):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ── Auto-detect ─────────────────────────────────────────────────────

    def _auto_detect(self):
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        auto_path = os.path.join(script_dir, 'WoW.exe')

        if os.path.isfile(auto_path):
            self._load_exe(auto_path)
            self._log(f"Auto-detected WoW.exe in patcher directory.", "info")
        else:
            self._log("Place CameraReforged.exe next to WoW.exe for auto-detect,", "warning")
            self._log("or click Browse to select your WoW.exe manually.", "warning")

    # ── File loading ────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select WoW.exe",
            filetypes=[("WoW Executable", "WoW.exe"), ("Executables", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self._load_exe(path)

    def _load_exe(self, path):
        self.exe_path = path
        # Show just filename + parent folder for readability
        display = os.path.join("...", os.path.basename(os.path.dirname(path)), os.path.basename(path))
        self.path_var.set(display)

        try:
            status, height = patcher.check_status(path)
            self.status = status
            self.cur_height = height
            self._update_status_display()

            if status == "patched" and height is not None:
                self.height_var.set(round(height, 2))

        except Exception as e:
            self.status = "error"
            self.cur_height = None
            self._set_status(f"✗  Error: {e}", RED)
            self._log(f"Error loading: {e}", "error")

        self._update_buttons()

    def _update_status_display(self):
        if self.status == "unpatched":
            self._set_status("○  Not Patched — Ready to apply", AMBER)
            self._log("WoW.exe is unpatched and ready.", "info")
        elif self.status == "patched":
            h = f" ({self.cur_height:+.2f} yards)" if self.cur_height else ""
            self._set_status(f"●  Patched{h}", GREEN)
            self._log(f"WoW.exe is already patched{h}.", "success")
        elif self.status == "unknown":
            self._set_status("✗  Unknown — Wrong version?", RED)
            self._log("Unexpected bytes at patch site. Needs WoW 3.3.5a.", "error")

    def _set_status(self, text, colour):
        self.status_var.set(text)
        self.status_label.configure(fg=colour)

    # ── Button state ────────────────────────────────────────────────────

    def _update_buttons(self):
        has_file = self.exe_path is not None

        # Apply Patch — only when unpatched
        if has_file and self.status == "unpatched":
            self.patch_btn.configure(state="normal", bg=ACCENT)
        else:
            self.patch_btn.configure(state="disabled", bg=BG_INPUT)

        # Update Height — only when already patched
        if has_file and self.status == "patched":
            self.height_btn.configure(state="normal", bg="#2a6041")
        else:
            self.height_btn.configure(state="disabled", bg=BG_INPUT)

        # Restore Backup — only when .bak exists
        if has_file and os.path.exists(self.exe_path + '.bak'):
            self.restore_btn.configure(state="normal", bg="#6b2130")
        else:
            self.restore_btn.configure(state="disabled", bg=BG_INPUT)

    # ── Slider/Entry sync ───────────────────────────────────────────────

    def _on_slider_change(self, val):
        pass  # DoubleVar already syncs

    def _on_entry_change(self, event=None):
        try:
            v = float(self.height_entry.get())
            v = max(0.0, min(3.0, v))
            self.height_var.set(v)
        except ValueError:
            self.height_var.set(patcher.DEFAULT_HEIGHT)

    # ── Actions ─────────────────────────────────────────────────────────

    def _apply_patch(self):
        if not self.exe_path:
            return
        try:
            height = self.height_var.get()
            result = patcher.apply_patch(self.exe_path, height)
            self._log(result, "success")
            self._load_exe(self.exe_path)  # Refresh status
        except Exception as e:
            self._log(f"Patch failed: {e}", "error")

    def _update_height(self):
        if not self.exe_path:
            return
        try:
            new_h = self.height_var.get()
            result = patcher.set_height(self.exe_path, new_h)
            self._log(result, "success")
            self._load_exe(self.exe_path)  # Refresh status
        except Exception as e:
            self._log(f"Height update failed: {e}", "error")

    def _restore_backup(self):
        if not self.exe_path:
            return
        try:
            result = patcher.restore_backup(self.exe_path)
            self._log(result, "success")
            self._load_exe(self.exe_path)  # Refresh status
        except Exception as e:
            self._log(f"Restore failed: {e}", "error")

    def _open_donation(self):
        webbrowser.open("https://buymeacoffee.com/zendevve")
        self._log("Opening support link in browser. Thank you for your support! ❤️", "success")


def main():
    root = tk.Tk()
    CameraReforgedApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
