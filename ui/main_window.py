import threading


from tkinter import messagebox
import ttkbootstrap as ttk
from dotenv import load_dotenv

from codebase_reader.codebase import CodeBase
from codebase_reader.constants import DEFAULT_IGNORES
from codebase_reader.codebase_reader import CodeBaseReader
from evaluator_agent import Evaluator, perform_pipeline_evaluation, perform_agent_evaluation
from requirements_extractor.req_document import ReqDocument
from evaluator_agent import ReqFidelityReview
from result_manager.result_manager import ResultManager
from evaluator_agent.req_fidelity_review import (
    LlmProvider,
    EvaluationMode,
    RealEvaluation,
) 
# Importación de submódulos locales
from .workingtree_tab import WorkingtreeTab
from .requirements_tab import RequirementsTab
from .evaluation_tab import EvaluationTab
from .config_tab import ConfigTab
from .log_console import LogConsole

class RefiApp:
    debug_mode: bool
    current_llm: LlmProvider
    current_evaluation_mode: EvaluationMode
    real_batch_evaluation_type: RealEvaluation

    def __init__(
        self, 
        root, 
        title, 
        geometry, 
        workdir, 
        codebase_name, 
        evaluator_llm, 
        debug_mode, 
        current_evaluation_mode,
        real_batch_evaluation_type,
        model_provider
    ):
        # 1. Main Frame Configuration
        self.root = root
        self.root.title(title)
        self.root.geometry(geometry)

        load_dotenv()
        
        # 2. Internal Use Variables
        self.workdir = workdir
        self.model_provider = model_provider
        
        # 3. Core Modules Initialization
        self.evaluator          = Evaluator(llm_ref=evaluator_llm)
        self.req_document       = ReqDocument(self.workdir)
        self.codebase           = CodeBase(path=self.workdir, name=codebase_name)
        self.codebase_reader    = CodeBaseReader(codebase=self.codebase)
        self.result_manager     = ResultManager()
        self.file_context       = []

        # DEBUGGING variables
        self.debug_mode                 = debug_mode
        self.current_evaluation_mode    = current_evaluation_mode
        self.real_batch_evaluation_type = real_batch_evaluation_type

        model_name = self.evaluator.get_model_name().lower().split()[0]
        match model_name:
            case 'gemini': 
                self.current_llm = LlmProvider.GEMINI
            case _:
                self.current_llm = LlmProvider.OLLAMA
        
        # 4. Build Visual components
        self._build_ui()
        self.log_message("Sistema listo e inicializado con la configuración externa.")

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Instanciar las pestañas (Siguen funcionando igual apuntando a self.app)
        self.tab_workspace = WorkingtreeTab(self.notebook, app=self)
        self.tab_requirements = RequirementsTab(self.notebook, app=self)
        self.tab_evaluation = EvaluationTab(self.notebook, app=self)
        self.tab_config = ConfigTab(self.notebook, app=self)

        self.notebook.add(self.tab_workspace, text="1. Espacio de Trabajo")
        self.notebook.add(self.tab_requirements, text="2. Requerimientos")
        self.notebook.add(self.tab_evaluation, text="3. Evaluación y Resultados")
        self.notebook.add(self.tab_config, text="4. Configuración")

        self.log_console = LogConsole(self.root)
        self.log_console.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    def log_message(self, message):
        self.log_console.log_message(message)

    def evaluate_reqs(self):
        if not self.req_document.requirements:
            messagebox.showwarning("Advertencia", "No hay requerimientos cargados.")
            return
        if not self.file_context:
            messagebox.showwarning("Advertencia", "No hay archivos cargados en el contexto.")
            return

        confirm = messagebox.askyesno("Confirmar Evaluación", "¿Deseas iniciar la evaluación con los datos actuales?")
        if not confirm:
            return

        threading.Thread(target=self._run_evaluation_thread, daemon=True).start()

    def _run_evaluation_thread(self):
        try:
            if self.current_evaluation_mode == EvaluationMode.AGENT_AI:
                review: ReqFidelityReview = perform_agent_evaluation(
                    evaluator=self.evaluator,
                    req_document=self.req_document,
                    codebase_reader=self.codebase_reader,
                    file_context=self.file_context,
                    model_provider=self.model_provider,
                    current_llm=self.current_llm,
                    debug_mode=self.debug_mode,
                    real_batch_evaluation_type=self.real_batch_evaluation_type,
                    log_callback=self.log_message
                )
            else:
                review: ReqFidelityReview = perform_pipeline_evaluation(
                    evaluator=self.evaluator,
                    req_document=self.req_document,
                    file_context=self.file_context,
                    current_llm=self.current_llm,
                    debug_mode=self.debug_mode,
                    real_batch_evaluation_type=self.real_batch_evaluation_type,
                    log_callback=self.log_message
                )
            # saves result
            self.result_manager.add_review(review=review)
            review_index = len(self.result_manager.saved_reviews) - 1
            self.result_manager.save_review(review_index)
            # Logs results
            save_path = self.result_manager.default_save_path / self.result_manager.default_save_name
            self.log_message(f"RESULTADOS GUARDADOS: {save_path}")
        except Exception as e:
            self.log_message(f"Error crítico en el proceso de evaluación: {str(e)}")
        finally:
            self.root.after(0, self.tab_requirements.update_req_listbox)
            self.root.after(0, lambda: messagebox.showinfo("Éxito", "Evaluación completada con éxito."))