from dotenv import load_dotenv
import ttkbootstrap as ttk
from model_provider import ModelProvider
from result_manager.req_fidelity_review import EvaluationMode, RealEvaluation
from ui import RefiApp



load_dotenv()

if __name__ == "__main__":
    # === CENTRALIZACIÓN DE VARIABLES DE CONFIGURACIÓN ===
    CONFIG = {
        "title": "REFI ALPHA - UI Prototype",
        "geometry": "1024x720",
        "themename": "cosmo",
        "workdir": ".",
        "codebase_name": "REFI_SOURCE_CODE",
        "evaluator_llm": "google_genai:gemini-3.1-flash-lite",
        "ollama_model": "gemma4:12b",
        "ollama_temperature": 0.1,
        "debug_mode": True,
    }
    
    root = ttk.Window(themename=CONFIG["themename"])

    model_provider = ModelProvider(
        ip="10.113.20.117",
        local_model="gemma4:12b",
        fallback_model="google_genai:gemini-3.1-flash-lite"
    )
  
    app = RefiApp(
        root=root,
        title=CONFIG["title"],
        geometry=CONFIG["geometry"],
        workdir=CONFIG["workdir"],
        codebase_name=CONFIG["codebase_name"],
        evaluator_llm=model_provider.get_default_model(),
        #############################################
        debug_mode=True,
        current_evaluation_mode=EvaluationMode.AGENT_AI,
        real_batch_evaluation_type=RealEvaluation.FULFILLED,
        model_provider=model_provider
    )
    
    root.mainloop()
