import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as ttk


class EvaluationTab(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ctrl_frame = ttk.Frame(self)
        ctrl_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        btn_eval = ttk.Button(ctrl_frame, text="\u25b6 Iniciar Evaluación", command=self.app.evaluate_reqs)
        btn_eval.pack(side="left", padx=5)

        btn_results = ttk.Button(ctrl_frame, text="Ver Resultados Guardados", command=self.get_results)
        btn_results.pack(side="left", padx=5)

        self.btn_export = ttk.Button(
            ctrl_frame,
            text="\U0001F4BE Exportar Evaluación",
            command=self.export_selected_review,
        )
        self.btn_export.pack(side="left", padx=5)

        self.text_results = ScrolledText(self, state='disabled')
        self.text_results.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def _ask_export_format(self) -> str | None:
        dialog = _ExportFormatDialog(self)
        self.wait_window(dialog)
        return dialog.choice

    def export_selected_review(self):
        reviews = self.app.service.get_saved_reviews()
        if not reviews:
            messagebox.showwarning(
                "Sin evaluaciones",
                "No hay evaluaciones registradas para exportar.",
            )
            return

        index = simpledialog.askinteger(
            "Seleccionar evaluación",
            f"¿Qué evaluación deseas exportar? (0 - {len(reviews) - 1}):",
            parent=self,
            minvalue=0,
            maxvalue=len(reviews) - 1,
        )
        if index is None:
            return

        fmt = self._ask_export_format()
        if fmt is None:
            return

        file_types = (
            [("JSON", "*.json")] if fmt == "json"
            else [("Texto", "*.txt"), ("Markdown", "*.md")]
        )
        default_ext = "json" if fmt == "json" else "txt"
        review = reviews[index]
        default_name = f"review_{review.review_date.replace(' ', '_').replace(':', '-')}.{default_ext}"

        path = filedialog.asksaveasfilename(
            title="Guardar informe de fidelidad",
            defaultextension=f".{default_ext}",
            initialfile=default_name,
            filetypes=file_types,
        )
        if not path:
            return

        try:
            from pathlib import Path
            output_path = self.app.service.export_review(
                index=index,
                format=fmt,
                path=Path(path),
            )
        except ValueError as e:
            messagebox.showerror("Formato no soportado", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
            return

        self.app.log_message(f"Reporte exportado a: {output_path}")
        messagebox.showinfo(
            "Exportación exitosa",
            f"El informe se guardó correctamente en:\n{output_path}",
        )

    def get_results(self):
        self.text_results.config(state='normal')
        self.text_results.delete(1.0, tk.END)

        reviews = self.app.service.get_saved_reviews()
        result_manager = self.app.service.result_manager

        if not reviews:
            self.text_results.insert(tk.END, "No hay evaluaciones registradas.\n")
            self.text_results.config(state='disabled')
            return

        self.text_results.insert(tk.END, "=== EVALUACIONES REGISTRADAS ===\n\n")

        for index, res in enumerate(reviews):
            self.text_results.insert(tk.END, f"[{index}] Fecha: {res.review_date}\n")

            try:
                review_str = result_manager.format_review(index)
                if review_str:
                    self.text_results.insert(tk.END, review_str + "\n")
            except Exception:
                pass

            self.text_results.insert(tk.END, "-" * 40 + "\n")

        self.text_results.config(state='disabled')
        self.app.log_message("Resultados cargados en la pestaña 'Evaluación y Resultados'.")


class _ExportFormatDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Formato de exportación")
        self.transient(parent)
        self.resizable(False, False)
        self.choice: str | None = None

        ttk.Label(
            self,
            text="¿En qué formato deseas exportar la evaluación?",
            padding=(20, 15, 20, 10),
        ).pack()

        btn_frame = ttk.Frame(self, padding=(20, 10, 20, 15))
        btn_frame.pack()
        ttk.Button(
            btn_frame,
            text="Texto / Markdown (.txt)",
            command=self._choose_string,
            width=24,
        ).pack(side="left", padx=5)
        ttk.Button(
            btn_frame,
            text="JSON (.json)",
            command=self._choose_json,
            width=24,
        ).pack(side="left", padx=5)
        ttk.Button(
            btn_frame,
            text="Cancelar",
            command=self.destroy,
            width=12,
        ).pack(side="left", padx=5)

        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()
        self._center_on(parent)

    def _choose_string(self):
        self.choice = "string"
        self.destroy()

    def _choose_json(self):
        self.choice = "json"
        self.destroy()

    def _center_on(self, parent):
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")
        except Exception:
            pass
