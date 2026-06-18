from pathlib import Path
import logging

from dotenv import load_dotenv

from requirements_extractor.extractor import RequirementsExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()
def main():
    # Ruta al PDF a procesar
    pdf_path = Path("/home/chopancho/dev/pruebas_langchain/refi_demo/pdfs/epa.pdf")

    # Modelo LLM que utilizará LangChain
    llm_model = "google_genai:gemini-3.1-flash-lite"

    # Referencia del modelo de embeddings (si tu clase lo requiere)
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