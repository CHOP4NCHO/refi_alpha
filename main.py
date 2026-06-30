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
    # === CONFIGURACIÓN DE LA APLICACIÓN ===
    # Modelos se configuran desde la UI (Pestaña 4: Configuración)
    CONFIG = {
        "title": "REFI ALPHA - UI Prototype",
        "geometry": "1024x720",
        "themename": "cosmo",
        "workdir": ".",
        "codebase_name": "REFI_SOURCE_CODE",
        "local_ip": "localhost",
        "cloud_ip": "generativelanguage.googleapis.com/v1beta/openai",
        "temperature": 0.1,
        "debug_mode": True,
    }

    root = ttk.Window(themename=CONFIG["themename"])

    model_provider = ModelProvider(
        local_ip=CONFIG["local_ip"],
        cloud_ip=CONFIG["cloud_ip"],
        temperature=CONFIG["temperature"],
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
