import sys
from pathlib import Path

# Add project root and core/ to Python path
_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "core"))

import logging

from dotenv import load_dotenv

from core.requirements_extractor.extractor import RequirementsExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

def main():
    pdf_path = Path("/home/chopancho/dev/pruebas_langchain/refi_demo/pdfs/epa.pdf")

    llm_model = "google_genai:gemini-3.1-flash-lite"
    embedding_model = "text-embedding-3-small"

    try:
        print("Inicializando extractor...")
        extractor = RequirementsExtractor(
            llm_ref=llm_model,
            embedding_ref=""
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
