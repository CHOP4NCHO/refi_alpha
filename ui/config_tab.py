import ttkbootstrap as ttk

from core.enums import LlmProvider, EvaluationMode, RealEvaluation


class ConfigTab(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        header = ttk.Label(self, text="Configuración de la Aplicación", font=("Helvetica", 14, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=10, pady=(15, 5))

        sep = ttk.Separator(self, orient="horizontal")
        sep.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        # --- debug_mode ---
        row = 2
        self.debug_var = ttk.BooleanVar(value=self.app.service.debug_mode)
        chk_debug = ttk.Checkbutton(
            self,
            text="Modo Debug",
            variable=self.debug_var,
            command=self._on_debug_toggle,
            bootstyle="info",
        )
        chk_debug.grid(row=row, column=0, sticky="w", padx=20, pady=5)

        lbl_debug_hint = ttk.Label(
            self,
            text="Activa o desactiva el modo de depuración.",
            font=("Helvetica", 9),
        )
        lbl_debug_hint.grid(row=row + 1, column=0, sticky="w", padx=40, pady=(0, 10))

        # --- current_llm ---
        row = 4
        ttk.Label(self, text="Proveedor LLM:", font=("Helvetica", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=20, pady=(10, 2)
        )
        self.llm_var = ttk.StringVar(value=self.app.service.current_llm.value)
        llm_values = [member.value for member in LlmProvider]
        combo_llm = ttk.Combobox(
            self,
            textvariable=self.llm_var,
            values=llm_values,
            state="readonly",
            width=30,
        )
        combo_llm.grid(row=row + 1, column=0, sticky="w", padx=20, pady=(0, 2))
        combo_llm.bind("<<ComboboxSelected>>", self._on_llm_change)

        # --- current_evaluation_mode ---
        row = 7
        ttk.Label(self, text="Modo de Evaluación:", font=("Helvetica", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=20, pady=(10, 2)
        )
        self.eval_mode_var = ttk.StringVar(value=self.app.service.evaluation_mode.value)
        eval_mode_values = [member.value for member in EvaluationMode]
        combo_eval = ttk.Combobox(
            self,
            textvariable=self.eval_mode_var,
            values=eval_mode_values,
            state="readonly",
            width=30,
        )
        combo_eval.grid(row=row + 1, column=0, sticky="w", padx=20, pady=(0, 2))
        combo_eval.bind("<<ComboboxSelected>>", self._on_eval_mode_change)

        # --- real_batch_evaluation_type ---
        row = 10
        ttk.Label(self, text="Tipo de Evaluación (Batch):", font=("Helvetica", 10, "bold")).grid(
            row=row, column=0, sticky="w", padx=20, pady=(10, 2)
        )
        self.real_eval_var = ttk.StringVar(value=self.app.service.real_evaluation.value)
        real_eval_values = [member.value for member in RealEvaluation]
        combo_real = ttk.Combobox(
            self,
            textvariable=self.real_eval_var,
            values=real_eval_values,
            state="readonly",
            width=30,
        )
        combo_real.grid(row=row + 1, column=0, sticky="w", padx=20, pady=(0, 2))
        combo_real.bind("<<ComboboxSelected>>", self._on_real_eval_change)

    # --- Callbacks ---

    def _on_debug_toggle(self):
        self.app.service.debug_mode = self.debug_var.get()
        self.app.log_message(f"debug_mode cambiado a {self.app.service.debug_mode}")

    def _on_llm_change(self, event=None):
        new_value = self.llm_var.get()
        self.app.service.current_llm = LlmProvider(new_value)
        self.app.log_message(f"current_llm cambiado a {self.app.service.current_llm.value}")

    def _on_eval_mode_change(self, event=None):
        new_value = self.eval_mode_var.get()
        self.app.service.evaluation_mode = EvaluationMode(new_value)
        self.app.log_message(f"current_evaluation_mode cambiado a {self.app.service.evaluation_mode.value}")

    def _on_real_eval_change(self, event=None):
        new_value = self.real_eval_var.get()
        self.app.service.real_evaluation = RealEvaluation(new_value)
        self.app.log_message(f"real_batch_evaluation_type cambiado a {self.app.service.real_evaluation.value}")
