import sys
from pathlib import Path


from dotenv import load_dotenv

from core.refi_service import RefiService
from core.model_provider import ModelProvider

import tkinter as tk
from tkinter import filedialog

# Add project root and core/ to Python path
_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "core"))
load_dotenv()

CURRENT_WORKDIR = "."
OLLAMA_IP = "10.113.20.117"
LOCAL_LLM = "gemma4:12b"
FALLBACK_LLM = "google_genai:gemini-3.1-flash-lite"

# ==========================================
# Initialization
# ==========================================

print("\n==============================")
print("   INICIANDO EVALUADOR IA")
print("==============================")

model_provider = ModelProvider(
    ip=OLLAMA_IP,
    local_llm=LOCAL_LLM,
    fallback_llm=FALLBACK_LLM,
    local_vlm=None,
    cloud_vlm="paligemma-3b",
    local_embedding="qwen3-embedding",
    cloud_embedding="google_genai:models/gemini-embedding-2",
    temperature=0.1,
)

service = RefiService(
    workdir=CURRENT_WORKDIR,
    codebase_name="REFI_SOURCE_CODE",
    model_provider=model_provider,
    debug_mode=False,
)

print("Sistema listo.\n")


# ==========================================
# Helpers
# ==========================================

def separator():
    print("\n" + "-" * 50)


def header(title: str):
    print("\n" + "=" * 50)
    print(f"{title.center(50)}")
    print("=" * 50)


def pause():
    input("\nPresiona ENTER para continuar...")


def safe_int_input(message: str, valid_options: list[int] | None = None) -> int:
    while True:
        try:
            value = int(input(message))
            if valid_options and value not in valid_options:
                print(f"Opción inválida. Opciones válidas: {valid_options}")
                continue
            return value
        except ValueError:
            print("Debes ingresar un número válido.")


def confirm(message: str) -> bool:
    while True:
        answer = input(f"{message} (y/n): ").strip().lower()
        if answer in ["y", "yes", "s", "si"]:
            return True
        if answer in ["n", "no"]:
            return False
        print("Respuesta inválida. Ingresa y/n.")


# ==========================================
# Menu
# ==========================================

def menu():
    while True:
        header("REFI ALPHA")

        print("1) Añadir requerimiento")
        print("2) Añadir código fuente")
        print("3) Cambiar espacio de trabajo")
        print("4) Evaluar")
        print("5) Obtener resultados")
        print("6) Salir")

        separator()

        option = safe_int_input("Selecciona una opción (1-6): ", [1, 2, 3, 4, 5, 6])

        separator()

        match option:
            case 1:
                add_requirement()
            case 2:
                add_codefile()
            case 3:
                set_worktree()
            case 4:
                evaluate_reqs()
            case 5:
                get_results()
            case 6:
                print("Cerrando aplicación...")
                break

        pause()


# ==========================================
# Requirements
# ==========================================

def add_requirement():
    header("NUEVO REQUERIMIENTO")

    description = input("Descripción del requerimiento:\n> ").strip()

    req_type = safe_int_input(
        "\nTipo de requerimiento\n"
        "1) Funcional\n"
        "2) No Funcional\n"
        "> ",
        [1, 2],
    )

    type_str = "FUNCTIONAL" if req_type == 1 else "NON_FUNCTIONAL"
    requirement = service.add_requirement(description=description, req_type=type_str)

    print("\nRequerimiento agregado correctamente.")
    print(f"ID: {requirement.id}")
    print(f"Tipo: {requirement.type}")
    print(f"Descripción: {requirement.description}")

    print("\nRequerimientos actuales:")
    for index, req in enumerate(service.get_requirements(), start=1):
        print(f"{index}. [{req.id}] {req.description}")


# ==========================================
# Code source
# ==========================================

def set_worktree():
    header("CAMBIAR ESPACIO DE TRABAJO")
    print("Espacio de Trabajo Actual: " + service.codebase.name)

    separator()

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    print("Selecciona la nueva carpeta en la ventana emergente...")
    selected_path = filedialog.askdirectory(title="Selecciona el nuevo espacio de trabajo")

    if not selected_path:
        print("Operación cancelada por el usuario.")
        return

    name = input("Ingresa el nombre del espacio de trabajo (opcional): ")

    try:
        service.set_workdir(selected_path, name if name else None)
        print(f"Espacio de trabajo cambiado con éxito a: {service.codebase.name}")
    except Exception as e:
        print(e)


def add_codefile():
    header("AÑADIR CÓDIGO FUENTE")

    print("Árbol del proyecto:\n")
    print(service.codebase.name)
    service.codebase_reader.show_tree()

    separator()

    selected_path = input("Ingresa la ruta del archivo:\n> ").strip()

    try:
        base_path = Path(service.codebase.path)
        complete_path = base_path / selected_path

        if complete_path.is_dir():
            added = service.add_directory_to_context(complete_path)
            print(f"\nDirectorio agregado recursivamente: {selected_path}")
            print(f"{added} archivos agregados")
        else:
            service.add_file_to_context(complete_path)
            print(f"\nArchivo agregado: {selected_path}")

    except FileNotFoundError as e:
        print(f"\n{e}")
    except Exception as e:
        print("\nError agregando archivo:")
        print(e)

    print("\nArchivos cargados:")
    if not service.file_context:
        print("No hay archivos cargados.")
    else:
        for index, file in enumerate(service.file_context, start=1):
            print(f"{index}. {file}")


# ==========================================
# Evaluation
# ==========================================

def evaluate_reqs():
    header("EVALUACIÓN")

    requirements = service.get_requirements()
    if not requirements:
        print("No hay requerimientos cargados.")
        return

    if not service.file_context:
        print("No hay archivos cargados.")
        return

    print("Requerimientos:\n")
    for index, req in enumerate(requirements, start=1):
        print(f"{index}. [{req.id}] {req.description} ({req.type})")

    separator()

    print("Archivos utilizados:\n")
    for index, file in enumerate(service.file_context, start=1):
        print(f"{index}. {file}")

    separator()

    if not confirm("¿Iniciar evaluación?"):
        print("Evaluación cancelada.")
        return

    print("\nIniciando evaluación...\n")

    try:
        review = service.evaluate(log_callback=lambda msg: print(msg))
        print(f"\nReview saved correctly at "
              f"{service.result_manager.default_save_path / service.result_manager.default_save_name}")
    except Exception as e:
        print(f"\nError durante evaluación: {e}")


def get_results():
    print("=" * 20)
    print("Revisando evaluaciones registradas: ")
    for index, res in enumerate(service.get_saved_reviews()):
        print(res.review_date)
        print(service.get_formatted_review(index))


# ==========================================
# Entry Point
# ==========================================

if __name__ == "__main__":
    menu()
