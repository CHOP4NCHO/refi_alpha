import json
from typing import Iterable
from pprint import pprint
from pydantic import BaseModel
from dataclasses import dataclass

from codebase_reader.code_file import CodeFile
from codebase_reader.codebase_reader import CodeBaseReader
from evaluator_agent.constants import EVALUATOR_SYSTEM_PROMPT
from codebase_reader.codebase import CodeBase
from evaluator_agent.token_tracker import TokenTrackerHandler

from evaluator_agent.tools import (
    create_evaluator_toolbelt
)

from requirements_extractor.req_document import ReqDocument, Requirement

from langchain.chat_models import BaseChatModel
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

import uuid

@dataclass
class CodeFileContext:
    code_content: list[str]

class SingleRequirementEval(BaseModel):
    initial_description: str
    reasoning: str       
    is_fulfilled: bool 

class Evaluator:
    _llm_ref: BaseChatModel
    _requirement_list: list[Requirement]
    _working_tree: dict | None
    _codebase: CodeBase | None
    _tools: list
    _req_evaluations: list[SingleRequirementEval]
    # token usage stats
    total_input_tokens: int
    total_output_tokens: int

    def __init__(self, llm_ref: BaseChatModel):
        """ Inits auxiliar variables """
        self._llm_ref = llm_ref
        self._requirement_list = []
        self._tools = []
        self._working_tree = None
        self._codebase = None
        self._req_evaluations = []

        self.total_input_tokens = 0
        self.total_output_tokens = 0

        
    def set_tools(self, tools: Iterable):
        """ Injects current toolset defined in ./tools.py """
        self._tools = list(tools)
    
    def set_requirements(self, req_document: ReqDocument):
        """ Sets new requirement list """
        self._requirement_list = list(req_document.requirements)
    
    def set_codebase(self, codebase: CodeBase):
        self._codebase = codebase

    def set_working_tree(self, tree):
        """ Sets the current working treee """
        self._target_codebase = tree

    def get_model_name(self) -> str:
        if hasattr(self._llm_ref, 'model'):
            return self._llm_ref.model # type: ignore
        else:
            return self._llm_ref.profile['name']  # type: ignore
    
    def eval_requirement_llm(self, req: Requirement, files_content: list[CodeFile]):
        """Performs one single evaluation with given model, req and files content."""
        llm = self._llm_ref
        

        files_index_map = "\n".join(
            [f"File Index {idx}: {f.path.name}\n{f.get_raw_content()}" for idx, f in enumerate(files_content)]
        )
        prompt = self._get_review_prompt_template(
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
        files_content: list[CodeFile]
    ) -> None:

        llm = self._llm_ref

        files_index_map = "\n".join(
            f"- {f.path}"
            for f in files_content
        )
        prompt = self._get_review_prompt_template_s(
            req_description=req.description,
            file_index_map=files_index_map
        )

        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4())
            },
            "callbacks": [
                TokenTrackerHandler(self)
            ],
            "recursion_limit": 15
        }

        used_tools = create_evaluator_toolbelt(
            codebase_reader
        )

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
                config=config # type: ignore
            )

            pprint(response)

            # ==================================================
            # 1) Structured response (preferido)
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
            # 2) Buscar JSON en mensajes
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

                # Eliminar markdown fences redundantes
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
            # 3) Diagnóstico útil
            # ==================================================
            last_ai = None
            for msg in reversed(messages):
                if msg.__class__.__name__ == "AIMessage":
                    last_ai = msg
                    break

            raise RuntimeError(
                f"No se encontró JSON válido.\n"
                f"Último AIMessage:\n{last_ai}"
            )

        except Exception as e:
            self._req_evaluations.append(
                SingleRequirementEval(
                    initial_description=req.description,
                    reasoning=f"Agent execution error: {str(e)}",
                    is_fulfilled=False
                )
            )

    def eval_requirement_agent_rag(
        self,
        codebase_reader: CodeBaseReader,
        req: Requirement,
        files_content: list[CodeFile],
        vector_store = None  # <-- Injected vector storage for RAG capabilities
    ) -> None:
        """
        Executes an agentic evaluation loop over a requirement using RAG and code inspection tools.
        Enforces a strict deterministic exit strategy if data cannot be retrieved.
        """
        llm = self._llm_ref

        # Baseline file map summary to feed initial context
        files_index_map = "\n".join(f"- {f.path}" for f in files_content)

        # Force the usage of the optimized semantic template
        prompt = self._get_rag_agent_prompt_template(
            req_description=req.description,
            file_index_map=files_index_map
        )

        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4())
            },
            "callbacks": [TokenTrackerHandler(self)],
            "recursion_limit": 10  # Reduced loop limit; RAG cuts down redundant trajectories
        }

        # Bind the vector store into the tool belt factory
        used_tools = create_evaluator_toolbelt(
            codebase_reader, 
            vector_store=vector_store
        )

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

            # Structured extraction layer (Preferred)
            structured = response.get("structured_response")
            if structured is not None:
                if isinstance(structured, SingleRequirementEval):
                    self._req_evaluations.append(structured)
                    return
                self._req_evaluations.append(SingleRequirementEval.model_validate(structured))
                return

            # Fallback JSON parsing layer over conversation history
            messages = response.get("messages", [])
            for msg in reversed(messages):
                if msg.__class__.__name__ != "AIMessage" or not getattr(msg, "content", ""):
                    continue
                
                content = msg.content.strip()
                if content.startswith("```"):
                    content = "\n".join(content.splitlines()[1:-1]).strip()
                
                try:
                    parsed = json.loads(content)
                    self._req_evaluations.append(SingleRequirementEval.model_validate(parsed))
                    return
                except Exception:
                    continue

            raise RuntimeError("Failed to isolate a valid SingleRequirementEval structure from agent state.")

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
    def _get_review_prompt_template(self, req_description: str, file_index_map: str) -> str:
        prompt = f"""
        Target Requirement to Evaluate:
        "{req_description}"

        Available Source Map Registry:
        {file_index_map}

        Instructions:
        0. Responde en español aunque las instrucciones vengan en inglés
        1. First, read the content of each available given codefile. You must evaluate if the target requirement is fulfilled or not. 
        2. Do NOT submit your final response until you have completely read and analyzed the relevant files.
        3. Once your review is complete, generate the final structured response:
           - 'initial_description': Repeat the target requirement text exactly.
           - 'reasoning': Provide a brief summary explaining EXACTLY how and where the codebase fulfills (or fails to fulfill) the requirement based on the files you read.
           - 'is_fulfilled': Set to True if the code successfully meets the requirement, otherwise False.
        4. Return ONLY a valid JSON object. considering the structured response:
        {{
            "initial_description": "",
            "reasoning": "",
            "is_fulfilled": true | false
        }}

        """
        return prompt

    def _get_review_prompt_template_s(
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
    def _get_rag_agent_prompt_template(self, req_description: str, file_index_map: str) -> str:
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