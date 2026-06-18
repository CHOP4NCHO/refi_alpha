import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as ttk

class LogConsole(ttk.Labelframe):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="Consola / Logs", **kwargs)
        self._build_ui()

    def _build_ui(self):
        self.log_text = ScrolledText(self, height=8, state='disabled', bg="black", fg="lightgreen")
        self.log_text.pack(fill="x", padx=5, pady=5)

    def log_message(self, message):
        def update_ui():
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
            
        self.after(0, update_ui)