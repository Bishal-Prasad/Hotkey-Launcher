# app.py
# ⚡ Hotkey Launcher Pro+
# A modern, minimal hotkey launcher built with CustomTkinter + keyboard
# Dependencies:
#   pip install customtkinter keyboard
# Run:
#   python app.py

import os
import sys
import json
import time
import threading
import webbrowser
import platform
import subprocess
import traceback

import customtkinter as ctk
import keyboard

APP_TITLE = "⚡ Hotkey Launcher Pro+"
DATA_FILE = "hotkeys.json"

# ---------- Utility: cross-platform file opener ----------
def open_target(target: str, is_url: bool):
    """
    Open a URL or local file/app cross-platform.
    - URL uses webbrowser.open
    - File:
        * Windows: os.startfile
        * macOS: subprocess(["open", target])
        * Linux: subprocess(["xdg-open", target])
    """
    try:
        if is_url:
            webbrowser.open(target, new=2, autoraise=True)
        else:
            if platform.system() == "Windows":
                os.startfile(target)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        return True, "Opened successfully."
    except Exception as e:
        return False, f"Open failed: {e}"

# ---------- Model ----------
class HotkeyEntry:
    def __init__(self, combo: str, target: str, kind: str):
        self.combo = combo.strip()
        self.target = target.strip()
        # kind: "url" or "file"
        self.kind = kind

    def to_dict(self):
        return {"combo": self.combo, "target": self.target, "kind": self.kind}

    @staticmethod
    def from_dict(d):
        return HotkeyEntry(d["combo"], d["target"], d.get("kind", "file"))

# ---------- Hotkey Manager ----------
class HotkeyManager:
    def __init__(self, notify_callback):
        """
        notify_callback(level, message)
            level in {"info", "success", "error"}
        """
        self.notify = notify_callback
        self.entries: list[HotkeyEntry] = []
        self._registered_combos = set()
        self._listener_thread = None
        self._listening = threading.Event()

    # Persistence
    def load(self, path=DATA_FILE):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.entries = [HotkeyEntry.from_dict(x) for x in data]
                self.notify("success", f"Loaded {len(self.entries)} hotkey(s).")
            else:
                self.entries = []
                self.notify("info", "No saved hotkeys found. Start adding!")
        except Exception as e:
            self.notify("error", f"Load failed: {e}")

    def save(self, path=DATA_FILE):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in self.entries], f, indent=2)
            self.notify("success", "Hotkeys saved.")
        except Exception as e:
            self.notify("error", f"Save failed: {e}")

    # Registration with keyboard lib
    def register_all(self):
        # Clear prior registrations
        for combo in list(self._registered_combos):
            try:
                keyboard.remove_hotkey(combo)
            except Exception:
                pass
        self._registered_combos.clear()

        # Add new ones
        for e in self.entries:
            try:
                keyboard.add_hotkey(e.combo, lambda entry=e: self._on_hotkey(entry), suppress=False, trigger_on_release=False)
                self._registered_combos.add(e.combo)
            except Exception as ex:
                self.notify("error", f"Failed to register '{e.combo}': {ex}")

        self.notify("info", f"Registered {len(self._registered_combos)} hotkey(s).")

    def _on_hotkey(self, entry: HotkeyEntry):
        ok, msg = open_target(entry.target, entry.kind == "url")
        self.notify("success" if ok else "error", f"[{entry.combo}] {msg}")

    def start_listener(self):
        # keyboard hotkeys work without a dedicated wait loop, but
        # a background thread calling keyboard.wait ensures the hook stays alive.
        if self._listener_thread and self._listener_thread.is_alive():
            return
        self._listening.set()
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

    def stop_listener(self):
        self._listening.clear()

    def _listen_loop(self):
        try:
            while self._listening.is_set():
                # Block until any keyboard event happens; keeps thread alive.
                keyboard.wait()
        except Exception as e:
            self.notify("error", f"Listener stopped: {e}")

# ---------- UI ----------
class HotkeyLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")  # default dark
        ctk.set_default_color_theme("blue")  # soft blue theme

        self.title(APP_TITLE)
        self.geometry("860x560")
        self.minsize(720, 460)

        # Soft shadow illusion: use a wrapper frame with padding and rounded corners
        self.root_container = ctk.CTkFrame(self, corner_radius=16)
        self.root_container.pack(fill="both", expand=True, padx=16, pady=16)

        # Header
        self.header = ctk.CTkFrame(self.root_container, corner_radius=16)
        self.header.pack(fill="x", padx=12, pady=(12, 8))

        self.title_label = ctk.CTkLabel(self.header, text=APP_TITLE, font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(side="left", padx=12, pady=12)

        # Search + Theme toggle
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(self.header, placeholder_text="🔎 Search hotkeys...", textvariable=self.search_var, corner_radius=12, width=260)
        self.search_entry.pack(side="right", padx=(6,12), pady=12)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        self.theme_btn = ctk.CTkButton(self.header, text="🌗 Toggle Theme", corner_radius=12, command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=6, pady=12)

        # Content area split: left form, right list
        self.content = ctk.CTkFrame(self.root_container, corner_radius=16)
        self.content.pack(fill="both", expand=True, padx=12, pady=8)

        self.left_panel = ctk.CTkFrame(self.content, corner_radius=16)
        self.left_panel.pack(side="left", fill="y", padx=12, pady=12)

        self.right_panel = ctk.CTkFrame(self.content, corner_radius=16)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=12, pady=12)

        # Form: Add Hotkey
        self.form_title = ctk.CTkLabel(self.left_panel, text="➕ Add Hotkey", font=ctk.CTkFont(size=16, weight="bold"))
        self.form_title.pack(anchor="w", padx=12, pady=(12, 6))

        self.combo_var = ctk.StringVar()
        self.target_var = ctk.StringVar()
        self.kind_var = ctk.StringVar(value="auto")

        self.combo_entry = ctk.CTkEntry(self.left_panel, placeholder_text="Hotkey (e.g., ctrl+alt+c)", textvariable=self.combo_var, corner_radius=12, width=280)
        self.combo_entry.pack(padx=12, pady=6)

        self.target_entry = ctk.CTkEntry(self.left_panel, placeholder_text="URL or file path", textvariable=self.target_var, corner_radius=12, width=280)
        self.target_entry.pack(padx=12, pady=6)

        self.kind_label = ctk.CTkLabel(self.left_panel, text="Type:")
        self.kind_label.pack(anchor="w", padx=12, pady=(8, 2))

        self.kind_row = ctk.CTkFrame(self.left_panel, corner_radius=12)
        self.kind_row.pack(fill="x", padx=12, pady=4)

        self.kind_auto = ctk.CTkRadioButton(self.kind_row, text="🧠 Auto", variable=self.kind_var, value="auto")
        self.kind_url = ctk.CTkRadioButton(self.kind_row, text="🌐 URL", variable=self.kind_var, value="url")
        self.kind_file = ctk.CTkRadioButton(self.kind_row, text="📁 File/App", variable=self.kind_var, value="file")
        self.kind_auto.pack(side="left", padx=6, pady=6)
        self.kind_url.pack(side="left", padx=6, pady=6)
        self.kind_file.pack(side="left", padx=6, pady=6)

        self.add_btn = ctk.CTkButton(self.left_panel, text="➕ Add Hotkey", corner_radius=12, command=self.on_add)
        self.add_btn.pack(padx=12, pady=(10, 6))

        self.remove_btn = ctk.CTkButton(self.left_panel, text="❌ Remove Selected", corner_radius=12, command=self.on_remove_selected)
        self.remove_btn.pack(padx=12, pady=6)

        self.clear_btn = ctk.CTkButton(self.left_panel, text="🗑️ Clear All", corner_radius=12, fg_color="#d9534f", hover_color="#c9302c", command=self.on_clear_all)
        self.clear_btn.pack(padx=12, pady=6)

        # Right: list with scrollable table-like layout
        self.list_title = ctk.CTkLabel(self.right_panel, text="🔗 Hotkeys", font=ctk.CTkFont(size=16, weight="bold"))
        self.list_title.pack(anchor="w", padx=12, pady=(12, 6))

        # Header row
        self.list_header = ctk.CTkFrame(self.right_panel, corner_radius=12)
        self.list_header.pack(fill="x", padx=12, pady=(4, 2))
        ctk.CTkLabel(self.list_header, text="Hotkey", width=200, anchor="w").pack(side="left", padx=(8,4))
        ctk.CTkLabel(self.list_header, text="Type", width=100, anchor="w").pack(side="left", padx=(4,4))
        ctk.CTkLabel(self.list_header, text="Target", anchor="w").pack(side="left", padx=(4,4))
        ctk.CTkLabel(self.list_header, text="Actions", width=120, anchor="center").pack(side="right", padx=(4,8))

        self.scroll = ctk.CTkScrollableFrame(self.right_panel, corner_radius=12)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=(2,12))

        # Selection tracking
        self.selected_index = None

        # Status bar
        self.status = ctk.CTkLabel(self.root_container, text="", anchor="w")
        self.status.pack(fill="x", padx=20, pady=(0, 8))
        self._status_clear_after = None

        # Hotkey manager
        self.manager = HotkeyManager(self.show_status)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Load and init
        self.manager.load(DATA_FILE)
        self.manager.register_all()
        self.manager.start_listener()
        self.refresh_list()

    # ---------- UI actions ----------
    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("light" if current == "Dark" else "dark")
        self.show_status("info", f"Theme set to {'Light' if current == 'Dark' else 'Dark'}.")

    def on_add(self):
        combo = self.combo_var.get().strip()
        target = self.target_var.get().strip()
        kind_sel = self.kind_var.get()

        if not combo:
            self.show_status("error", "Please enter a hotkey combination.")
            return
        if not target:
            self.show_status("error", "Please enter a URL or file path.")
            return

        # Kind auto-detection
        if kind_sel == "auto":
            is_url = target.lower().startswith(("http://", "https://"))
            kind = "url" if is_url else "file"
        else:
            kind = kind_sel

        # Validate combo by trying a temp registration (then remove)
        try:
            test_id = keyboard.add_hotkey(combo, lambda: None)
            keyboard.remove_hotkey(test_id)
        except Exception as ex:
            self.show_status("error", f"Invalid hotkey '{combo}': {ex}")
            return

        # For file, check existence (best-effort)
        if kind == "file":
            if not os.path.exists(target):
                # Still allow (could be an app on PATH), but warn.
                self.show_status("info", "File not found. Will attempt to open via system.")
        
        # Add entry and persist
        self.manager.entries.append(HotkeyEntry(combo, target, kind))
        self.manager.save(DATA_FILE)
        self.manager.register_all()
        self.refresh_list()
        self.combo_var.set("")
        self.target_var.set("")
        self.show_status("success", f"Added hotkey '{combo}'.")

    def on_remove_selected(self):
        idx = self.selected_index
        if idx is None:
            self.show_status("error", "No hotkey selected.")
            return
        try:
            entry = self.manager.entries[idx]
            del self.manager.entries[idx]
            self.manager.save(DATA_FILE)
            self.manager.register_all()
            self.refresh_list()
            self.selected_index = None
            self.show_status("success", f"Removed '{entry.combo}'.")
        except Exception as e:
            self.show_status("error", f"Remove failed: {e}")

    def on_delete_row(self, idx):
        try:
            entry = self.manager.entries[idx]
            del self.manager.entries[idx]
            self.manager.save(DATA_FILE)
            self.manager.register_all()
            self.refresh_list()
            self.show_status("success", f"Deleted '{entry.combo}'.")
        except Exception as e:
            self.show_status("error", f"Delete failed: {e}")

    def on_clear_all(self):
        if not self.manager.entries:
            self.show_status("info", "Nothing to clear.")
            return
        self.manager.entries.clear()
        self.manager.save(DATA_FILE)
        self.manager.register_all()
        self.refresh_list()
        self.selected_index = None
        self.show_status("success", "Cleared all hotkeys.")

    # ---------- List rendering ----------
    def refresh_list(self):
        # Clear scroll children
        for child in self.scroll.winfo_children():
            child.destroy()

        query = self.search_var.get().strip().lower()

        for idx, e in enumerate(self.manager.entries):
            # Filter
            text_blob = f"{e.combo} {e.kind} {e.target}".lower()
            if query and query not in text_blob:
                continue

            row = ctk.CTkFrame(self.scroll, corner_radius=12)
            row.pack(fill="x", padx=6, pady=4)

            # Selection highlight on click
            def make_select(i=idx, frame=row):
                def _select(event=None):
                    self.selected_index = i
                    # Visual feedback
                    for sib in self.scroll.winfo_children():
                        try:
                            sib.configure(fg_color=None)
                        except Exception:
                            pass
                    try:
                        frame.configure(fg_color=("#1f2937" if ctk.get_appearance_mode().lower()=="dark" else "#e5e7eb"))
                    except Exception:
                        pass
                return _select

            row.bind("<Button-1>", make_select())

            # Columns
            col_combo = ctk.CTkLabel(row, text=e.combo, width=200, anchor="w")
            col_combo.pack(side="left", padx=(8,4), pady=8)

            # Icon by type
            icon = "🌐" if e.kind == "url" else "📁"
            col_kind = ctk.CTkLabel(row, text=f"{icon} {e.kind}", width=100, anchor="w")
            col_kind.pack(side="left", padx=(4,4), pady=8)

            col_target = ctk.CTkLabel(row, text=e.target, anchor="w")
            col_target.pack(side="left", fill="x", expand=True, padx=(4,4), pady=8)

            # Actions
            actions = ctk.CTkFrame(row, corner_radius=8)
            actions.pack(side="right", padx=(4,8), pady=8)

            # Open button (test)
            open_btn = ctk.CTkButton(actions, text="🚀 Open", width=80, corner_radius=10,
                                     command=lambda entry=e: self._test_open(entry))
            open_btn.pack(side="left", padx=4)

            del_btn = ctk.CTkButton(actions, text="🗑️ Delete", width=80, corner_radius=10,
                                    fg_color="#d9534f", hover_color="#c9302c",
                                    command=lambda i=idx: self.on_delete_row(i))
            del_btn.pack(side="left", padx=4)

    def _test_open(self, entry: HotkeyEntry):
        ok, msg = open_target(entry.target, entry.kind == "url")
        self.show_status("success" if ok else "error", msg)

    # ---------- Status bar with subtle fade/auto-clear ----------
    def show_status(self, level: str, message: str):
        # Level styles
        colors = {
            "success": ("#16a34a", "#dcfce7"),
            "error": ("#dc2626", "#fee2e2"),
            "info": ("#2563eb", "#dbeafe"),
        }
        fg, bg = colors.get(level, ("#6b7280", "#e5e7eb"))
        dark_mode = ctk.get_appearance_mode().lower() == "dark"

        # Adapt for dark theme: use softer backgrounds
        if dark_mode:
            # darker variants
            bg = {
                "success": "#0f172a",
                "error": "#0f172a",
                "info": "#0f172a",
            }.get(level, "#0f172a")

        self.status.configure(text=f"{message}", text_color=fg)
        # Subtle animation: brief brightness pulse via repeated updates
        try:
            self.status.configure(font=ctk.CTkFont(size=12, weight="bold"))
            self.after(120, lambda: self.status.configure(font=ctk.CTkFont(size=12, weight="normal")))
        except Exception:
            pass

        # Auto-clear after 6 seconds
        if self._status_clear_after is not None:
            try:
                self.after_cancel(self._status_clear_after)
            except Exception:
                pass
        self._status_clear_after = self.after(6000, lambda: self.status.configure(text=""))

    # ---------- Lifecycle ----------
    def on_close(self):
        try:
            self.manager.stop_listener()
            self.manager.save(DATA_FILE)
        except Exception:
            traceback.print_exc()
        finally:
            self.destroy()

def main():
    app = HotkeyLauncherApp()
    app.mainloop()

if __name__ == "__main__":
    main()
