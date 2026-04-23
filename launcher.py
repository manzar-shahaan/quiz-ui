#!/usr/bin/env python3
"""
Quiz Launcher — graphical front-end for quiz-ui.
Pick a .md file and launch it in the browser without touching the terminal.
"""
import socket
import subprocess
import sys
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

HERE = Path(__file__).resolve().parent
SERVER = HERE / "run_quiz_server.py"
ICON = HERE / "assets" / "icon.png"
POLL_MS = 1000


def _free_port(start: int = 8000) -> int:
    for port in range(start, 9000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free port found in 8000–9000")


class QuizRow(ctk.CTkFrame):
    """One row representing a single running (or stopped) quiz session."""

    def __init__(self, parent, path: Path, port: int, on_remove):
        super().__init__(parent, corner_radius=8)
        self._path = path
        self._port = port
        self._proc: subprocess.Popen | None = None
        self._on_remove = on_remove
        self._build()
        self._launch()
        self._poll()

    # ── layout ───────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(1, weight=1)

        self._dot = ctk.CTkLabel(
            self, text="●", font=ctk.CTkFont(size=18), text_color="gray", width=28
        )
        self._dot.grid(row=0, column=0, padx=(12, 4), pady=10)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, sticky="w", padx=4, pady=10)

        ctk.CTkLabel(
            info,
            text=self._path.name,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(anchor="w")

        self._status_lbl = ctk.CTkLabel(
            info,
            text="Starting…",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self._status_lbl.pack(anchor="w")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=0, column=2, padx=12, pady=8)

        self._open_btn = ctk.CTkButton(
            btns, text="Open in browser", width=130, command=self._open
        )
        self._open_btn.pack(side="left", padx=(0, 6))

        self._action_btn = ctk.CTkButton(
            btns,
            text="Stop",
            width=80,
            fg_color="#c0392b",
            hover_color="#922b21",
            command=self._action,
        )
        self._action_btn.pack(side="left")

    # ── subprocess ───────────────────────────────────────────────────────

    def _launch(self):
        if getattr(sys, "frozen", False):
            # Frozen executable re-launches itself in server mode
            cmd = [sys.executable, "--server", str(self._path),
                   "--port", str(self._port), "--launcher"]
        else:
            cmd = [sys.executable, str(SERVER), str(self._path),
                   "--port", str(self._port), "--launcher"]
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    # ── status polling ───────────────────────────────────────────────────

    def _poll(self):
        if self._proc is None:
            return
        if self._proc.poll() is None:
            self._dot.configure(text_color="#27ae60")
            self._status_lbl.configure(
                text=f"Running  ·  http://127.0.0.1:{self._port}",
                text_color="#27ae60",
            )
            self._action_btn.configure(
                text="Stop",
                fg_color="#c0392b",
                hover_color="#922b21",
            )
            self._open_btn.configure(state="normal")
        else:
            self._dot.configure(text_color="#888888")
            self._status_lbl.configure(text="Stopped", text_color="#888888")
            self._action_btn.configure(
                text="Remove",
                fg_color=("#555555", "#444444"),
                hover_color=("#444444", "#333333"),
            )
        self.after(POLL_MS, self._poll)

    # ── button actions ────────────────────────────────────────────────────

    def _open(self):
        url = f"http://127.0.0.1:{self._port}"
        if sys.platform == "darwin":
            subprocess.Popen(["open", url])
        elif sys.platform == "win32":
            subprocess.Popen(["start", "", url], shell=True)
        else:
            subprocess.Popen(["xdg-open", url])

    def _action(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        else:
            self._on_remove(self)

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def destroy(self):
        self.stop()
        super().destroy()


class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Quiz Launcher")
        self.geometry("620x440")
        self.minsize(500, 300)
        self._rows: list[QuizRow] = []
        self._next_port = 8000
        self._empty_lbl: ctk.CTkLabel | None = None
        self._build()
        self._set_icon()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_icon(self):
        if not ICON.exists():
            return
        try:
            from PIL import Image, ImageTk  # type: ignore
            img = ImageTk.PhotoImage(Image.open(ICON).resize((32, 32)))
            self.iconphoto(True, img)
            self._icon_ref = img  # prevent GC
        except Exception:
            pass

    # ── layout ───────────────────────────────────────────────────────────

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(
            top, text="Quiz Launcher", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")
        ctk.CTkButton(
            top, text="+ Add Quiz", width=120, command=self._add_quiz
        ).pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=20, pady=(0, 8)
        )

        self._scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent"
        )
        self._scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._show_empty()

    def _show_empty(self):
        self._empty_lbl = ctk.CTkLabel(
            self._scroll,
            text="No quizzes loaded yet.\nClick  + Add Quiz  to pick a .md file.",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        self._empty_lbl.pack(pady=40)

    def _hide_empty(self):
        if self._empty_lbl:
            self._empty_lbl.pack_forget()
            self._empty_lbl = None

    # ── quiz management ───────────────────────────────────────────────────

    def _add_quiz(self):
        path = filedialog.askopenfilename(
            title="Select a quiz file",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if not path:
            return

        port = _free_port(self._next_port)
        self._next_port = port + 1
        self._hide_empty()

        row = QuizRow(self._scroll, Path(path), port, on_remove=self._remove_row)
        row.pack(fill="x", pady=4)
        self._rows.append(row)

    def _remove_row(self, row: QuizRow):
        row.destroy()
        self._rows.remove(row)
        if not self._rows:
            self._show_empty()

    def _on_close(self):
        for row in self._rows:
            row.stop()
        self.destroy()


def _run_as_server() -> None:
    """Used when the frozen executable is called as a Flask server subprocess."""
    args = sys.argv[1:]          # ['--server', path, '--port', N, '--launcher']
    args.remove("--server")
    sys.argv = ["quiz-launcher"] + args
    from run_quiz_server import main  # noqa: PLC0415
    main()


if __name__ == "__main__":
    if getattr(sys, "frozen", False) and "--server" in sys.argv:
        _run_as_server()
    else:
        LauncherApp().mainloop()
