import ttkbootstrap as ttk

from core.enums import EvaluationMode, RealEvaluation, LlmProvider
from core.model_config import ModelConfig


class ConfigTab(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self._models_cache = []
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        header = ttk.Label(self, text="Configuración de la Aplicación", font=("Helvetica", 14, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=10, pady=(15, 5))

        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        # --- DEBUG ---
        self.debug_var = ttk.BooleanVar(value=self.app.service.debug_mode)
        ttk.Checkbutton(
            self,
            text="Modo Debug",
            variable=self.debug_var,
            command=self._on_debug_toggle,
            bootstyle="info",
        ).grid(row=2, column=0, sticky="w", padx=20, pady=5)

        # --- PROVIDER ---
        ttk.Label(self, text="Proveedor:", font=("Helvetica", 10, "bold")).grid(
            row=4, column=0, sticky="w", padx=20, pady=(10, 2)
        )

        self.provider_var = ttk.StringVar(value=self.app.service.model_provider.current_provider.value)

        combo_provider = ttk.Combobox(
            self,
            textvariable=self.provider_var,
            values=[p.value for p in LlmProvider],
            state="readonly",
            width=30,
        )
        combo_provider.grid(row=5, column=0, sticky="w", padx=20)
        combo_provider.bind("<<ComboboxSelected>>", self._on_provider_change)

        # --- LLM MODEL ---
        ttk.Label(self, text="Modelo LLM:", font=("Helvetica", 10, "bold")).grid(
            row=6, column=0, sticky="w", padx=20, pady=(10, 2)
        )

        self.llm_var = ttk.StringVar()
        self.combo_llm = ttk.Combobox(self, textvariable=self.llm_var, width=30)
        self.combo_llm.grid(row=7, column=0, sticky="w", padx=20)
        self.combo_llm.bind("<<ComboboxSelected>>", self._on_llm_change)

        # --- VLM MODEL ---
        ttk.Label(self, text="Modelo VLM:", font=("Helvetica", 10, "bold")).grid(
            row=8, column=0, sticky="w", padx=20, pady=(10, 2)
        )

        self.vlm_var = ttk.StringVar()
        self.combo_vlm = ttk.Combobox(self, textvariable=self.vlm_var, width=30)
        self.combo_vlm.grid(row=9, column=0, sticky="w", padx=20)
        self.combo_vlm.bind("<<ComboboxSelected>>", self._on_vlm_change)

        # --- EMBEDDING MODEL ---
        ttk.Label(self, text="Modelo Embedding:", font=("Helvetica", 10, "bold")).grid(
            row=10, column=0, sticky="w", padx=20, pady=(10, 2)
        )

        self.embedding_var = ttk.StringVar()
        self.combo_embedding = ttk.Combobox(self, textvariable=self.embedding_var, width=30)
        self.combo_embedding.grid(row=11, column=0, sticky="w", padx=20)
        self.combo_embedding.bind("<<ComboboxSelected>>", self._on_embedding_change)

        # --- EVAL MODE ---
        ttk.Label(self, text="Modo de Evaluación:", font=("Helvetica", 10, "bold")).grid(
            row=12, column=0, sticky="w", padx=20, pady=(10, 2)
        )

        self.eval_mode_var = ttk.StringVar(value=self.app.service.evaluation_mode.value)
        combo_eval = ttk.Combobox(
            self,
            textvariable=self.eval_mode_var,
            values=[e.value for e in EvaluationMode],
            state="readonly",
            width=30,
        )
        combo_eval.grid(row=13, column=0, sticky="w", padx=20)
        combo_eval.bind("<<ComboboxSelected>>", self._on_eval_mode_change)

        # --- REAL EVAL ---
        ttk.Label(self, text="Tipo de Evaluación:", font=("Helvetica", 10, "bold")).grid(
            row=14, column=0, sticky="w", padx=20, pady=(10, 2)
        )

        self.real_eval_var = ttk.StringVar(value=self.app.service.real_evaluation.value)
        combo_real = ttk.Combobox(
            self,
            textvariable=self.real_eval_var,
            values=[r.value for r in RealEvaluation],
            state="readonly",
            width=30,
        )
        combo_real.grid(row=15, column=0, sticky="w", padx=20)
        combo_real.bind("<<ComboboxSelected>>", self._on_real_eval_change)

        # INIT MODELS
        self._refresh_models()

    # --------------------------------------------------
    # Model handling
    # --------------------------------------------------

    def _refresh_models(self):
        provider = LlmProvider(self.provider_var.get())
        all_models = self.app.service.model_provider.list_models()

        self._models_cache = [m for m in all_models if m.provider == provider]

        llm_models = [m.model_id for m in self._models_cache if m.category == "chat"]
        vlm_models = [m.model_id for m in self._models_cache if m.category == "vlm"]
        emb_models = [m.model_id for m in self._models_cache if m.category == "embedding"]

        self.combo_llm["values"] = llm_models
        self.combo_vlm["values"] = vlm_models
        self.combo_embedding["values"] = emb_models

    def _find_model(self, model_id: str, category: str) -> ModelConfig:
        for m in self._models_cache:
            if m.model_id == model_id and m.category == category:
                return m
        raise ValueError(f"Modelo no encontrado: {model_id}")

    # --------------------------------------------------
    # Callbacks
    # --------------------------------------------------

    def _on_debug_toggle(self):
        self.app.service.debug_mode = self.debug_var.get()

    def _on_provider_change(self, event=None):
        self._refresh_models()

    def _on_llm_change(self, event=None):
        model = self._find_model(self.llm_var.get(), "chat")
        self.app.service.model_provider.set_llm(model)

    def _on_vlm_change(self, event=None):
        model = self._find_model(self.vlm_var.get(), "vlm")
        self.app.service.model_provider.set_vlm(model)

    def _on_embedding_change(self, event=None):
        model = self._find_model(self.embedding_var.get(), "embedding")
        self.app.service.model_provider.set_embedding(model)

    def _on_eval_mode_change(self, event=None):
        self.app.service.evaluation_mode = EvaluationMode(self.eval_mode_var.get())

    def _on_real_eval_change(self, event=None):
        self.app.service.real_evaluation = RealEvaluation(self.real_eval_var.get())