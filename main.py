import logging
from dotenv import load_dotenv 
import ttkbootstrap as ttk

from ui import RefiApp
from core import RefiService
from core.enums import EvaluationMode, RealEvaluation
from core.model_provider import ModelProvider
from core.model_config import ModelConfig
from core.enums import LlmProvider

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
        "local_ip": "10.113.20.117",
        "cloud_ip": "generativelanguage.googleapis.com/v1beta/openai",
        "local_llm": "gemma4:12b",
        "cloud_llm": "google_genai:gemini-3.1-flash-lite",
        "cloud_vlm": "gemini-2.5-flash-lite",
        "local_embedding": "qwen3-embedding",
        "cloud_embedding": "google_genai:models/gemini-embedding-2",
        "temperature": 0.1,
        "debug_mode": True,
    }

    root = ttk.Window(themename=CONFIG["themename"])

    model_provider = ModelProvider(
        local_ip="localhost",
        cloud_ip="generativelanguage.googleapis.com/v1beta/openai",
        default_llm=ModelConfig(LlmProvider.GEMINI, "google_genai:gemini-3.1-flash-lite"),
        default_embedding=ModelConfig(LlmProvider.GEMINI, "gemini-embedding-001", "embedding"),
        default_vlm=ModelConfig(LlmProvider.GEMINI, "gemini-2.5-flash", "vlm"),
    )

    service = RefiService(
        workdir=CONFIG["workdir"],
        codebase_name=CONFIG["codebase_name"],
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
