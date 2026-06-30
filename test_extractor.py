import sys
from pathlib import Path

# Add project root and core/ to Python path
_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "core"))

import logging

from dotenv import load_dotenv

from core.model_provider import ModelProvider
from core.requirements_extractor.extractor import RequirementsExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

OLLAMA_IP = "10.113.20.117"

def main():
    pdf_path = Path("/home/chopancho/dev/pruebas_langchain/refi_demo/pdfs/epa.pdf")

    try:
        model_provider = ModelProvider(
            ip=OLLAMA_IP,
            local_llm="gemma4:12b",
            fallback_llm="google_genai:gemini-3.1-flash-lite",
            local_vlm=None,
            cloud_vlm="gemini-2.5-flash-lite",
            local_embedding="qwen3-embedding",
            cloud_embedding="google_genai:models/gemini-embedding-2",
            temperature=0.1,
        )

        print("Inicializando extractor...")
        extractor = RequirementsExtractor(
            llm_ref=model_provider.get_llm(),
            embedding_ref=model_provider.current_embedding,
            vlm_options=model_provider.get_vlm_options(),
            is_local=model_provider.is_local,
        )

        print(f"Cargando documento: {pdf_path}")
        extractor.set_document(pdf_path)

        print("Extrayendo requisitos...")
        req_document = extractor.get_requirements()

        print("\n=== RESULTADOS ===")
        print(f"Documento: {req_document.name}")

        for idx, requirement in enumerate(req_document.requirements, start=1):
            print(f"\n[{idx}]")
            print(requirement)

    except FileNotFoundError as e:
        print(f"Error: {e}")

    except Exception as e:
        logging.exception("Error durante la ejecución")
        print(f"Error inesperado: {e}")


if __name__ == "__main__":
    main()
