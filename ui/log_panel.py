import customtkinter as ctk
from datetime import datetime

class LogPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._expanded = False

        self._toggle_btn = ctk.CTkButton(
            self, text="▶ 日志", anchor="w", fg_color="transparent",
            text_color=("gray10", "gray90"), hover_color=("gray80", "gray30"),
            command=self._toggle
        )
        self._toggle_btn.pack(fill="x", padx=4, pady=(4, 0))

        self._textbox = ctk.CTkTextbox(self, height=120, state="disabled", wrap="word")
        # not packed initially — hidden by default

    def _toggle(self):
        if self._expanded:
            self._textbox.pack_forget()
            self._toggle_btn.configure(text="▶ 日志")
        else:
            self._textbox.pack(fill="both", expand=True, padx=4, pady=(0, 4))
            self._toggle_btn.configure(text="▼ 日志")
        self._expanded = not self._expanded

    def add_message(self, message: str, level: str = "info") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        colors = {"info": "", "error": "[ERROR] ", "warn": "[WARN] "}
        prefix = colors.get(level, "")
        line = f"{ts} {prefix}{message}\n"
        self._textbox.configure(state="normal")
        self._textbox.insert("end", line)
        self._textbox.see("end")
        self._textbox.configure(state="disabled")

    def clear(self) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
