import logging
from dotenv import load_dotenv 
import ttkbootstrap as ttk

from ui import RefiApp
from core import RefiService
from core.enums import EvaluationMode, RealEvaluation
from core.model_provider import ModelProvider


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

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
        "ollama_ip": "10.113.20.117",
        "debug_mode": True,
    }

    root = ttk.Window(themename=CONFIG["themename"])

    model_provider = ModelProvider(
        ip=CONFIG["ollama_ip"],
        local_model=CONFIG["ollama_model"],
        fallback_model=CONFIG["evaluator_llm"]
    )

    service = RefiService(
        workdir=CONFIG["workdir"],
        codebase_name=CONFIG["codebase_name"],
        evaluator_llm=model_provider.get_multimodal_model(),
        model_provider=model_provider,
        debug_mode=CONFIG["debug_mode"],
        evaluation_mode=EvaluationMode.AGENT_AI,
        real_evaluation=RealEvaluation.FULFILLED,
    )

    app = RefiApp(
        root=root,
        title=CONFIG["title"],
        geometry=CONFIG["geometry"],
        service=service,
    )

    root.mainloop()
