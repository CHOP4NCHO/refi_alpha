from pathlib import Path

from dotenv import load_dotenv

from codebase_reader.codebase import CodeBase
from codebase_reader.codebase_reader import CodeBaseReader
from evaluator_agent.evaluator import Evaluator
from requirements_extractor.req_document import ReqDocument, Requirement

import random
import string

from datetime import datetime

import tkinter as tk
from tkinter import filedialog

from result_manager import req_fidelity_review
from result_manager.result_manager import ResultManager

load_dotenv()
CURRENT_WORKDIR="."
# ==========================================
# Inicialización
# ==========================================

print("\n==============================")
print("   INICIANDO EVALUADOR IA")
print("==============================")

evaluator = Evaluator(
    llm_ref="google_genai:gemini-3.1-flash-lite"
)

req_document = ReqDocument(".")

codebase = CodeBase(CURRENT_WORKDIR, "REFI_SOURCE_CODE")
codebase_reader = CodeBaseReader(codebase=codebase)

result_manager = ResultManager()

file_context = []

print("Sistema listo.\n")


# ==========================================
# Helpers UI
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


def generate_requirement_id(length: int = 3) -> str:
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))


def confirm(message: str) -> bool:
    while True:
        answer = input(f"{message} (y/n): ").strip().lower()

        if answer in ["y", "yes", "s", "si"]:
            return True

        if answer in ["n", "no"]:
            return False

        print("Respuesta inválida. Ingresa y/n.")


# ==========================================
# Menú principal
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

        option = safe_int_input(
            "Selecciona una opción (1-5): ",
            [1, 2, 3, 4, 5,6]
        )

        separator()

        match option:
            case 1:
                add_requirement(
                    evaluator=evaluator,
                    req_document=req_document
                )
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
# Requerimientos
# ==========================================

def add_requirement(
    evaluator: Evaluator,
    req_document: ReqDocument
):

    header("NUEVO REQUERIMIENTO")

    description = input(
        "Descripción del requerimiento:\n> "
    ).strip()

    req_type = safe_int_input(
        "\nTipo de requerimiento\n"
        "1) Funcional\n"
        "2) No Funcional\n"
        "> ",
        [1, 2]
    )

    requirement = Requirement(
        id=generate_requirement_id(),
        description=description,
        type="FUNCTIONAL" if req_type == 1 else "NON_FUNCTIONAL"
    )

    req_document.add_requirement(requirement)

    print("\nRequerimiento agregado correctamente.")
    print(f"ID: {requirement.id}")
    print(f"Tipo: {requirement.type}")
    print(f"Descripción: {requirement.description}")

    print("\nRequerimientos actuales:")

    for index, req in enumerate(req_document.requirements, start=1):
        print(f"{index}. [{req.id}] {req.description}")


# ==========================================
# Código fuente
# ==========================================

def set_worktree():
    header("CAMBIAR ESPACIO DE TRABAJO")
    print("Espacio de Trabajo Actual: " + codebase_reader.codebase.name)

    separator()

    root = tk.Tk()
    root.withdraw()

    root.attributes("-topmost", True)

    print("Selecciona la nueva carpeta en la ventana emergente...")
    selected_path = filedialog.askdirectory(
        title="Selecciona el nuevo espacio de trabajo"
    )

    if not selected_path:
        print("Operación cancelada por el usuario.")
        return

    name = input("Ingresa el nombre del espacio de trabajo (opcional): ")

    try:
        path = Path(selected_path)

        if not path.is_dir():
            raise ValueError(
                f"Failed to open given path: {selected_path} isn't a Directory."
            )

        name = path.name if path.exists() and len(name) == 0 else name

        codebase = CodeBase(path=selected_path, name=name)
        codebase_reader.codebase = codebase
        print(f"Espacio de trabajo cambiado con éxito a: {name}")

    except Exception as e:
        print(e)

def add_codefile():

    header("AÑADIR CÓDIGO FUENTE")

    print("Árbol del proyecto:\n")

    print(codebase_reader.codebase.name)
    codebase_reader.show_tree()

    separator()

    selected_path = input(
        "Ingresa la ruta del archivo:\n> "
    ).strip()

    try:
        complete_path = codebase_reader.codebase.path / selected_path

        if complete_path.is_dir():
            added = 0

            for file_path in complete_path.rglob("*"):
                if file_path.is_file():
                    try:
                        codefile = codebase_reader.get_file(file_path)
                        file_context.append(codefile)
                        added += 1
                    except Exception:
                        print(f"Error agregando {file_path}. Ignorando.")

            print(f"\nDirectorio agregado recursivamente: {selected_path}")
            print(f"{added} archivos agregados")

        else:
            codefile = codebase_reader.get_file(complete_path)
            file_context.append(codefile)

            print(f"\nArchivo agregado: {selected_path}")

    except FileNotFoundError:

        print(f"\nArchivo no encontrado: {selected_path}")

    except Exception as e:

        print("\nError agregando archivo:")
        print(e)

    print("\nArchivos cargados:")

    if not file_context:
        print("No hay archivos cargados.")
    else:
        for index, file in enumerate(file_context, start=1):
            print(f"{index}. {file}")


# ==========================================
# Evaluación
# ==========================================

def evaluate_reqs():

    header("EVALUACIÓN")

    if not req_document.requirements:
        print("No hay requerimientos cargados.")
        return

    if not file_context:
        print("No hay archivos cargados.")
        return

    print("Requerimientos:\n")

    for index, req in enumerate(
        req_document.requirements,
        start=1
    ):
        print(
            f"{index}. "
            f"[{req.id}] "
            f"{req.description} "
            f"({req.type})"
        )

    separator()

    print("Archivos utilizados:\n")

    for index, file in enumerate(file_context, start=1):
        print(f"{index}. {file}")

    separator()

    if not confirm("¿Iniciar evaluación?"):
        print("Evaluación cancelada.")
        return

    evaluator.set_requirements(req_document)

    print("\nIniciando evaluación...\n")

    for req in evaluator._requirement_list:

        print("=" * 50)
        print(f"Evaluando: {req.description}")
        print("=" * 50)

        try:

            evaluator.eval_requirement(
                model=None,
                req=req,
                files_content=file_context
            )

            print("Evaluación completada.")

        except Exception as e:

            print("Error durante evaluación:")
            print(e)

        print()

    separator()

    # creates review
    req_review = req_fidelity_review.ReqFidelityReview(
        review_date  = str(datetime.now()),
        reviewed_reqs= evaluator._req_evaluations,
        input_tokens = evaluator.total_input_tokens,
        output_tokens= evaluator.total_output_tokens
    )
    # delegates review to result_manager
    result_manager.add_review(req_review)
    review_index = len(result_manager.saved_reviews) - 1
    result_manager.save_review(review_index)
    print(
        f"Review saved correctly at "
        f"{result_manager.default_save_path / result_manager.default_save_name}"
    )
    # cleans previous requirements.
    evaluator._req_evaluations.clear()
    req_document.requirements.clear()
    evaluator.total_input_tokens = 0
    evaluator.total_output_tokens = 0


def get_results():
    print("="*20)
    print("Revisando evaluaciones registradas: ")
    for index, res in enumerate(result_manager.saved_reviews):
        print(res.review_date)
        result_manager.get_code_review_str(index)

# ==========================================
# Entry Point
# ==========================================

if __name__ == "__main__":
    menu()