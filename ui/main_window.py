import threading
import traceback

from tkinter import messagebox
import ttkbootstrap as ttk

from core.refi_service import RefiService
from core.exceptions import ModelConfigurationError, ModelsNotConfiguredError, DomainError

# Local sub-modules
from .workingtree_tab import WorkingtreeTab
from .requirements_tab import RequirementsTab
from .evaluation_tab import EvaluationTab
from .config_tab import ConfigTab
from .log_console import LogConsole


class RefiApp:
    def __init__(
        self,
        root,
        title: str,
        geometry: str,
        service: RefiService,
    ):
        # 1. Window configuration
        self.root = root
        self.root.title(title)
        self.root.geometry(geometry)

        # 2. Service layer
        self.service = service

        # 3. Build visual components
        self._build_ui()
        self.log_message("Sistema listo e inicializado con la configuración externa.")

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Instantiate tabs (they receive self to access service via self.service)
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
        if not self.service.get_requirements():
            messagebox.showwarning("Advertencia", "No hay requerimientos cargados.")
            return
        if not self.service.file_context:
            messagebox.showwarning("Advertencia", "No hay archivos cargados en el contexto.")
            return

        confirm = messagebox.askyesno(
            "Confirmar Evaluación",
            "¿Deseas iniciar la evaluación con los datos actuales?",
        )
        if not confirm:
            return

        threading.Thread(target=self._run_evaluation_thread, daemon=True).start()

    def _run_evaluation_thread(self):
        try:
            self.service.evaluate(log_callback=self.log_message)
            save_path = (
                self.service.result_manager.default_save_path
                / self.service.result_manager.default_save_name
            )
            self.log_message(f"RESULTADOS GUARDADOS: {save_path}")
            self.root.after(
                0, lambda: messagebox.showinfo("Éxito", "Evaluación completada con éxito.")
            )
        except ModelsNotConfiguredError as e:
            self.log_message(f"Error de configuración: {e.message}")
            msg = (
                f"Para la operación '{e.operation}' se requieren modelos "
                f"que no están configurados: {', '.join(e.missing_models)}.\n"
                "Por favor, vaya a la pestaña de Configuración para configurarlos."
            )
            self.root.after(0, lambda msg=msg: messagebox.showerror("Configuración requerida", msg))
    
        except ModelConfigurationError as e:
            self.log_message(f"Error de configuración: {e.message}")
            msg = (
                f"Error con el modelo {e.model_type.upper()}: {e.message}\n"
                "Verifique la configuración en la pestaña correspondiente."
            )
            self.root.after(0, lambda msg=msg: messagebox.showerror("Error de configuración", msg))
        except DomainError as e:
            self.log_message(f"Error de REFI-ALPHA: {e}")
            msg = str(e)
            self.root.after(0, lambda msg=msg: messagebox.showerror("Error", msg))
        except Exception as e:
            tb = traceback.format_exc()
            self.log_message(f"Error crítico en el proceso de evaluación: {e}\n{tb}")
            msg = str(e)
            self.root.after(0, lambda msg=msg: messagebox.showerror("Error inesperado", msg))
        finally:
            self.root.after(0, self.tab_requirements.update_req_listbox)
            
