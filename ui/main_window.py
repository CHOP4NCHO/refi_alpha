
from datetime import datetime
import threading

from tkinter import messagebox
import ttkbootstrap as ttk
from dotenv import load_dotenv

from codebase_reader.codebase import CodeBase
from codebase_reader.codebase_reader import CodeBaseReader
from evaluator_agent.evaluator import Evaluator
from requirements_extractor.req_document import ReqDocument
from result_manager import req_fidelity_review
from result_manager.result_manager import ResultManager
from result_manager.req_fidelity_review import (
    LlmProvider,
    EvaluationMode,
    RealEvaluation,
) 
#from langchain_ollama import ChatOllama

# Importación de submódulos locales
from .workingtree_tab import WorkingtreeTab
from .requirements_tab import RequirementsTab
from .evaluation_tab import EvaluationTab
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
        model_provider=None
    ):
        # 1. Main Frame Configuration
        self.root = root
        self.root.title(title)
        self.root.geometry(geometry)

        load_dotenv()
        
        # 2. Internal Use Variables
        self.CURRENT_WORKDIR = workdir
        self.model_provider = model_provider
        
        # 3. Core Modules Initialization
        self.evaluator          = Evaluator(llm_ref=evaluator_llm)
        self.req_document       = ReqDocument(self.CURRENT_WORKDIR)
        self.codebase           = CodeBase(path=self.CURRENT_WORKDIR, name=codebase_name)
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

        self.notebook.add(self.tab_workspace, text="1. Espacio de Trabajo")
        self.notebook.add(self.tab_requirements, text="2. Requerimientos")
        self.notebook.add(self.tab_evaluation, text="3. Evaluación y Resultados")

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
        self.log_message("INICIANDO EVALUACIÓN...")
        self.evaluator.set_requirements(self.req_document)

        # Prepare RAG vector store once at the beginning of the evaluation run
        if self.current_evaluation_mode == EvaluationMode.AGENT_AI:
            if self.model_provider is not None:
                self.log_message("Preparando base de datos vectorial (RAG) para el repositorio...")
                try:
                    embeddings = self.model_provider.get_embeddings()
                    self.evaluator.build_vector_store(self.codebase_reader, embeddings)
                    self.log_message("Base vectorial (RAG) construida con éxito.")
                except Exception as e:
                    self.log_message(f"Advertencia: No se pudo construir la base vectorial (RAG): {str(e)}")
            else:
                self.log_message("Advertencia: No se detectó model_provider. Continuando sin RAG.")

        try:
            for req in self.evaluator._requirement_list:
                self.log_message(f"Evaluando requerimiento: {req.description}")
                try:
                    #performs evaluation depending on current evaluation mode
                    self.log_message(f"Performing evaluation in current mode:  {self.current_evaluation_mode.value}")
                    # AGENT MODE
                    if self.current_evaluation_mode == EvaluationMode.AGENT_AI:
                        self.evaluator.eval_requirement_agent(
                            codebase_reader= self.codebase_reader,
                            req=req, 
                            files_content=self.file_context
                        )
                    # LLM PIPELINE MODE
                    elif self.current_evaluation_mode == EvaluationMode.LLM_PIPELINE:
                        self.evaluator.eval_requirement_llm( 
                            req=req, 
                            files_content=self.file_context
                        )
                    self.log_message(f"Evaluación completada para: {req.id}")
                except Exception as e:
                    self.log_message(f"Error evaluando {req.id}: {str(e)}")

            try:
                #creates review object
                req_review = req_fidelity_review.ReqFidelityReview(
                    debug_mode=self.debug_mode,
                    review_date=str(datetime.now()),
                    reviewed_reqs=list(self.evaluator._req_evaluations), 
                    input_tokens=self.evaluator.total_input_tokens,
                    output_tokens=self.evaluator.total_output_tokens,
                    llm_provider=self.current_llm,
                    evaluation_mode=self.current_evaluation_mode,
                    real_evaluation=self.real_batch_evaluation_type
                )
                #saves review
                self.result_manager.add_review(req_review)
                review_index = len(self.result_manager.saved_reviews) - 1
                self.result_manager.save_review(review_index)
                #logs results
                save_path = self.result_manager.default_save_path / self.result_manager.default_save_name
                self.log_message(f"RESULTADOS GUARDADOS: {save_path}")

            except Exception as e:
                self.log_message(f"Error guardando resultados: {str(e)}")

        finally:
            # Clean up the vector store to free memory immediately after completion or on failure
            if hasattr(self.evaluator, "clear_vector_store"):
                try:
                    self.evaluator.clear_vector_store()
                    self.log_message("Memoria de la base vectorial (RAG) liberada.")
                except Exception as e:
                    self.log_message(f"Error liberando base vectorial: {str(e)}")

            #cleans given requirements from previous time
            self.evaluator._req_evaluations.clear()
            self.req_document.requirements.clear()
            self.evaluator.total_input_tokens = 0
            self.evaluator.total_output_tokens = 0
            
            self.root.after(0, self.tab_requirements.update_req_listbox)
            self.root.after(0, lambda: messagebox.showinfo("Éxito", "Evaluación completada con éxito."))