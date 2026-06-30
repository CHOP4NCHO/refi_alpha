import json
import logging
from typing import Iterable
from pydantic import BaseModel
from dataclasses import dataclass

from ..codebase_reader.code_file import CodeFile
from ..codebase_reader.codebase_reader import CodeBaseReader
from .constants import EVALUATOR_SYSTEM_PROMPT
from ..codebase_reader.codebase import CodeBase
from .token_tracker import TokenTrackerHandler

from .tools import (
    create_evaluator_toolbelt
)

from ..requirements_extractor.req_document import ReqDocument, Requirement

from langchain.chat_models import BaseChatModel
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

import uuid
from pathlib import Path
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore

logger = logging.getLogger(__name__)

@dataclass
class CodeFileContext:
    code_content: list[str]

class SingleRequirementEval(BaseModel):
    initial_description: str
    reasoning: str       
    is_fulfilled: bool 

class Evaluator:
    _requirement_list: list[Requirement]
    _working_tree: dict | None
    _codebase: CodeBase | None
    _tools: list
    _req_evaluations: list[SingleRequirementEval]
    _vector_store: InMemoryVectorStore | None
    # token usage stats
    total_input_tokens: int
    total_output_tokens: int

    def __init__(self):
        """Initializes auxiliary variables."""
        self._requirement_list = []
        self._tools = []
        self._working_tree = None
        self._codebase = None
        self._req_evaluations = []
        self._vector_store = None

        self.total_input_tokens = 0
        self.total_output_tokens = 0

        
    def set_tools(self, tools: Iterable):
        """Injects the current toolset defined in ./tools.py."""
        self._tools = list(tools)
    
    def set_requirements(self, req_document: ReqDocument):
        """Sets a new requirement list."""
        self._requirement_list = list(req_document.requirements)
    
    def set_codebase(self, codebase: CodeBase):
        """Sets the current codebase."""
        self._codebase = codebase

    def set_working_tree(self, tree):
        """Sets the current working tree."""
        self._working_tree = tree

    def build_vector_store(self, codebase_reader: CodeBaseReader, embeddings_model, files_content: list[CodeFile] | None = None) -> None:
        """
        Creates an in-memory vector store populated with chunked code snippets
        from the provided codebase reader. Splits files into overlapping chunks of lines.
        If files_content is provided, only those files are processed (subset mode).
        """
        logger.info("Building in-memory RAG vector store...")
        documents = []
        files_to_process = files_content if files_content else codebase_reader.codebase.files
        for code_file in files_to_process:
            try:
                content = code_file.get_raw_content()
                if not content.strip():
                    continue
                
                # Split content into line-based chunks for precise code windows
                lines = content.splitlines()
                chunk_size = 300  # Number of lines per chunk
                chunk_overlap = 30  # Number of overlapping lines between consecutive chunks
                
                for i in range(0, len(lines), chunk_size - chunk_overlap):
                    chunk_lines = lines[i : i + chunk_size]
                    chunk_content = "\n".join(chunk_lines)
                    
                    if chunk_content.strip():
                        # Store relative path in source metadata for easy retrieval by agent tools
                        rel_path = Path(code_file.path).relative_to(codebase_reader.codebase.path)
                        documents.append(
                            Document(
                                page_content=chunk_content,
                                metadata={
                                    "source": str(rel_path),
                                    "start_line": i + 1,
                                    "end_line": i + len(chunk_lines)
                                }
                            )
                        )
            except Exception as e:
                logger.error(f"Error processing file {code_file.path} for RAG: {e}")

        if documents:
            logger.info(f"Generated {len(documents)} document chunks. Embedding via model...")
            self._vector_store = InMemoryVectorStore.from_documents(documents, embeddings_model)
            logger.info("In-memory RAG vector store built successfully.")
        else:
            logger.warning("No readable documents found to populate the RAG vector store.")
            self._vector_store = None

    def clear_vector_store(self) -> None:
        """
        Clears the in-memory vector store to release associated RAM resources immediately.
        """
        if self._vector_store is not None:
            self._vector_store = None
            logger.info("In-memory RAG vector store cleared and memory released.")

    def get_model_name(self, llm_ref) -> str:
        if hasattr(llm_ref, 'model'):
            return llm_ref.model # type: ignore
        else:
            return llm_ref.profile['name']  # type: ignore
    
    def eval_requirement_llm(
            self, 
            req: Requirement, 
            files_content: list[CodeFile],
            llm_ref: BaseChatModel
        ):
        """Performs one single evaluation with given model, req and files content."""
        llm = llm_ref

        files_index_map = "\n".join(
            [f"File Index {idx}: {f.path.name}\n{f.get_raw_content()}" for idx, f in enumerate(files_content)]
        )
        prompt = self._build_pipeline_prompt(
            req_description=req.description,
            file_index_map=files_index_map
        )

        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4())
            },
            "callbacks": [TokenTrackerHandler(self)]
        }

        eval_agent = create_agent(
            model=llm,
            tools=[], 
            context_schema=CodeFileContext,
            response_format=ToolStrategy(SingleRequirementEval),
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
        )

        response = eval_agent.invoke({
            "messages": [{
                "role": "user",
                "content": prompt
            }],},
            config=config, # type: ignore
        )

        formatted_value = response["structured_response"]
        self._req_evaluations.append(formatted_value)



    def eval_requirement_agent(
        self,
        codebase_reader: CodeBaseReader,
        req: Requirement,
        files_content: list[CodeFile],
        llm_ref: BaseChatModel
    ) -> None:
        """
        Executes an agentic evaluation loop over a requirement.
        Integrates RAG if an active vector store is present.
        """
        llm = llm_ref

        # Baseline file map summary to feed initial context
        files_index_map = "\n".join(f"- {f.path}" for f in files_content)

        # Decide prompts and tools based on vector store presence (RAG vs Standard)
        if self._vector_store is not None:
            logger.info("Active RAG vector store detected. Running with RAG capabilities.")
            prompt = self._build_rag_agent_prompt(
                req_description=req.description,
                file_index_map=files_index_map
            )
            used_tools = create_evaluator_toolbelt(
                codebase_reader,
                vector_store=self._vector_store,
                allowed_files=files_content
            )
        else:
            logger.info("No vector store detected. Running standard agent evaluation.")
            prompt = self._build_agent_prompt(
                req_description=req.description,
                file_index_map=files_index_map
            )
            used_tools = create_evaluator_toolbelt(
                codebase_reader,
                vector_store=None,
                allowed_files=files_content
            )

        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4())
            },
            "callbacks": [
                TokenTrackerHandler(self)
            ],
            "recursion_limit": 25  # High limit to prevent "Recursion limit reached" errors
        }

        eval_agent = create_agent(
            model=llm,
            tools=used_tools,
            context_schema=CodeFileContext,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            response_format=SingleRequirementEval
        )

        try:
            response = eval_agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                config=config  # type: ignore
            )

            # ==================================================
            # 1) Structured response (Preferred)
            # ==================================================
            structured = response.get("structured_response")

            if structured is not None:
                if isinstance(structured, SingleRequirementEval):
                    self._req_evaluations.append(structured)
                    return

                self._req_evaluations.append(
                    SingleRequirementEval.model_validate(structured)
                )
                return

            # ==================================================
            # 2) Fallback JSON parsing layer over conversation history
            # ==================================================
            messages = response.get("messages", [])

            for msg in reversed(messages):
                if msg.__class__.__name__ != "AIMessage":
                    continue

                content = getattr(msg, "content", "")
                if not isinstance(content, str):
                    continue

                content = content.strip()
                if not content:
                    continue

                # Remove redundant markdown fences
                if content.startswith("```"):
                    lines = content.splitlines()
                    if len(lines) >= 2:
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()

                try:
                    parsed = json.loads(content)
                    evaluation = SingleRequirementEval.model_validate(parsed)
                    self._req_evaluations.append(evaluation)
                    return
                except Exception:
                    continue

            # ==================================================
            # 3) Useful diagnosis
            # ==================================================
            last_ai = None
            for msg in reversed(messages):
                if msg.__class__.__name__ == "AIMessage":
                    last_ai = msg
                    break

            raise RuntimeError(
                f"Failed to isolate a valid SingleRequirementEval structure from agent state.\n"
                f"Last AIMessage:\n{last_ai}"
            )

        except Exception as e:
            # Resilient safety net fallback
            self._req_evaluations.append(
                SingleRequirementEval(
                    initial_description=req.description,
                    reasoning=f"Agent execution error during structural evaluation: {str(e)}",
                    is_fulfilled=False
                )
            )

    
    # ----------------------
    #   TEMPLATES
    #
    def _build_pipeline_prompt(self, req_description: str, file_index_map: str) -> str:
        prompt = f"""
        Requerimiento Objetivo a Evaluar:
        "{req_description}"

        Registro de Archivos de Código Fuente Disponibles:
        {file_index_map}

        Instrucciones:
        1. Responde SIEMPRE en español.
        2. Primero, lee el contenido de cada archivo de código provisto. Debes evaluar si el requerimiento objetivo se cumple o no en la base de código.
        3. NO envíes tu respuesta final hasta haber analizado por completo los archivos relevantes.
        4. Una vez completado tu análisis, genera la respuesta final estructurada en formato JSON:
           - 'initial_description': Copia exactamente el texto del requerimiento objetivo.
           - 'reasoning': Proporciona una explicación técnica concisa de cómo/dónde se implementa en el código, o indica que no se encontró evidencia suficiente. Todo el texto de este campo debe estar en español técnico detallado.
           - 'is_fulfilled': Establécelo en true si el código cumple con éxito el requerimiento, de lo contrario false.
        5. Devuelve ÚNICAMENTE un objeto JSON válido que cumpla con este formato exacto:
        {{
            "initial_description": "",
            "reasoning": "",
            "is_fulfilled": true | false
        }}
        """
        return prompt

    def _build_agent_prompt(
        self,
        req_description: str,
        file_index_map: str
    ) -> str:
        return f"""
    Responde SIEMPRE en español.

    REQUERIMIENTO OBJETIVO A EVALUAR:
    "{req_description}"

    REGISTRO DE ARCHIVOS DISPONIBLES EN EL WORKSPACE:
    {file_index_map}

    TAREA:
    Inspecciona los archivos relevantes usando tus herramientas. 

    REGLA DE PARADA CRÍTICA: 
    Si utilizas tus herramientas de búsqueda y obtienes "No matches found" 3 o 5 o si no encuentras evidencia clara después de 2 o 3 intentos, DEBES detenerte. 
    No te quedes en un bucle. Asume inmediatamente que el requerimiento NO ESTÁ IMPLEMENTADO y genera la respuesta.

    Cuando tengas tu conclusión (ya sea exitosa o por falta de evidencia), genera la respuesta final estructurada completando estrictamente este formato JSON (sin incluir texto adicional):

    {{
        "initial_description": "{req_description}",
        "reasoning": "Inserta aquí una explicación técnica concisa de cómo/dónde se implementa en el código, o indica que no se encontró evidencia en el workspace tras buscar las palabras clave.",
        "is_fulfilled": true o false
    }}
    """
    def _build_rag_agent_prompt(self, req_description: str, file_index_map: str) -> str:
            """
            Returns a prompt tailored for semantic discovery (RAG) transition into analytical thinking.
            Explicitly requests the final answer to be formulated in Spanish.
            """
            return f"""
        Responde SIEMPRE en ESPAÑOL.
    
        REQUERIMIENTO OBJETIVO A EVALUAR:
        "{req_description}"
    
        REGISTRO DE ARCHIVOS INICIALES (Sugeridos):
        {file_index_map}
    
        INSTRUCCIONES DE RAZONAMIENTO AGÉNTICO:
        1. **Búsqueda Semántica (RAG):** Comienza llamando a la herramienta `query_codebase_rag`. Pasa palabras clave del requerimiento para rastrear qué archivos contienen la lógica del negocio.
        2. **Mapeo Estructural:** Una vez identifiques los archivos sospechosos o candidatos, usa `get_file_structure_summary` para ver la arquitectura interna de clases/métodos sin leer líneas innecesarias.
        3. **Lectura y Verificación:** Usa `read_specific_file_lines` en las zonas críticas descubiertas para asegurar el cumplimiento real del código. No asumas que una característica está completada solo porque una función tiene un nombre similar.
        4. **Proximidad de Pruebas:** Ejecuta `check_test_coverage_proximity` si requieres comprobar si existen tests unitarios/integración dándole soporte.
    
        REGLA DE PARADA DETERMINISTA:
        Si la consulta a `query_codebase_rag` indica repetidamente que los conceptos clave no existen o si las búsquedas fallan, asume inmediatamente que el requerimiento NO ESTÁ IMPLEMENTADO (`is_fulfilled`: false). No iteres a ciegas.
    
        FORMATO DE SALIDA COMPULSORIO:
        Genera tu respuesta completando el esquema estructurado `SingleRequirementEval`. Todo el texto redactado en el campo 'reasoning' debe ser en español técnico detallado (indicando archivos y lógica analizada).
        """
