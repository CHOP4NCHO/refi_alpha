import tkinter as tk
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

        btn_eval = ttk.Button(ctrl_frame, text="▶ Iniciar Evaluación", command=self.app.evaluate_reqs)
        btn_eval.pack(side="left", padx=5)

        btn_results = ttk.Button(ctrl_frame, text="Ver Resultados Guardados", command=self.get_results)
        btn_results.pack(side="left", padx=5)

        self.text_results = ScrolledText(self, state='disabled')
        self.text_results.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def get_results(self):
        self.text_results.config(state='normal')
        self.text_results.delete(1.0, tk.END)
        
        if not self.app.result_manager.saved_reviews:
            self.text_results.insert(tk.END, "No hay evaluaciones registradas.\n")
            self.text_results.config(state='disabled')
            return

        self.text_results.insert(tk.END, "=== EVALUACIONES REGISTRADAS ===\n\n")
        
        for index, res in enumerate(self.app.result_manager.saved_reviews):
            self.text_results.insert(tk.END, f"[{index}] Fecha: {res.review_date}\n")
            
            try:
                review_str = self.app.result_manager.format_review(index)
                if review_str:
                    self.text_results.insert(tk.END, review_str + "\n")
            except Exception:
                pass
                
            self.text_results.insert(tk.END, "-" * 40 + "\n")
            
        self.text_results.config(state='disabled')
        self.app.log_message("Resultados cargados en la pestaña 'Evaluación y Resultados'.")