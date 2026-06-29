import time
from datetime import datetime

from codebase_reader.code_file import CodeFile
from codebase_reader.codebase_reader import CodeBaseReader
from evaluator_agent.evaluator import Evaluator
from evaluator_agent.req_fidelity_review import EvaluationMode, ReqFidelityReview, LlmProvider, RealEvaluation
from model_provider import ModelProvider
from requirements_extractor.req_document import ReqDocument

def perform_agent_evaluation(
    evaluator: Evaluator,
    req_document: ReqDocument,
    codebase_reader: CodeBaseReader,
    file_context: list[CodeFile],
    model_provider: ModelProvider,
    current_llm: LlmProvider,
    debug_mode: bool,
    real_batch_evaluation_type: RealEvaluation,
    log_callback=None
) -> ReqFidelityReview:
    """
    Orchestrates the entire evaluation lifecycle:
    1. Sets requirements and builds the semantic search (RAG) vector store if agent mode is up.
    2. Sequentially evaluates each requirement using Agent or Pipeline mode.
    3. Packages the outcomes, logs token metrics, and persists the review results.
    4. Automatically frees system resources (such as clearing vector stores).
    """
    def log(message):
        if log_callback:
            log_callback(message)

    log("INICIANDO EVALUACIÓN...")
    start_time = time.time()
    evaluator.set_requirements(req_document)

    if model_provider is not None:
        log("Preparando base de datos vectorial (RAG) para el repositorio...")
        try:
            embeddings = model_provider.get_embeddings()
            evaluator.build_vector_store(codebase_reader, embeddings, files_content=file_context)
            log("Base vectorial (RAG) construida con éxito.")
        except Exception as e:
            log(f"Advertencia: No se pudo construir la base vectorial (RAG): {str(e)}")
    else:
        log("Advertencia: No se detectó model_provider. Continuando sin RAG.")
        
    req_review = None

    try:
        for req in evaluator._requirement_list:
            log(f"Evaluando requerimiento: {req.description}")
            try:
                log("Performing evaluation in Agent mode...")
                evaluator.eval_requirement_agent(
                    codebase_reader=codebase_reader,
                    req=req,
                    files_content=file_context
                )
                log(f"Evaluación completada para: {req.id}")
            except Exception as e:
                log(f"Error evaluando {req.id}: {str(e)}")

        try:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Creates review object
            req_review = ReqFidelityReview(
                debug_mode=debug_mode,
                review_date=str(datetime.now()),
                reviewed_reqs=list(evaluator._req_evaluations),
                input_tokens=evaluator.total_input_tokens,
                output_tokens=evaluator.total_output_tokens,
                llm_provider=current_llm,
                evaluation_mode=EvaluationMode.AGENT_AI,
                real_evaluation=real_batch_evaluation_type,
                response_time=elapsed_time
            )

        except Exception as e:
            log(f"Error guardando resultados: {str(e)}")

    finally:
        # Clean up the vector store to free memory immediately after completion or on failure
        if hasattr(evaluator, "clear_vector_store"):
            try:
                evaluator.clear_vector_store()
                log("Memoria de la base vectorial (RAG) liberada.")
            except Exception as e:
                log(f"Error liberando base vectorial: {str(e)}")

        # Cleans given requirements from previous time
        evaluator._req_evaluations.clear()
        req_document.requirements.clear()
        evaluator.total_input_tokens = 0
        evaluator.total_output_tokens = 0

    # returns or raises exception
    if req_review is not None:
        return req_review
    else:
        raise ValueError("Error while saving ReqFidelityReview") 



def perform_pipeline_evaluation(
    evaluator: Evaluator,
    req_document: ReqDocument,
    file_context: list[CodeFile],
    current_llm,
    debug_mode,
    real_batch_evaluation_type,
    log_callback=None
) -> ReqFidelityReview:
    """
    Orchestrates the entire evaluation lifecycle:
    1. Sets requirements and builds the formatted prompt (using file_context).
    2. Sequentially evaluates each requirement using Agent or Pipeline mode.
    3. Packages the outcomes, logs token metrics, and persists the review results.
    """
    def log(message):
        if log_callback:
            log_callback(message)

    log("INICIANDO EVALUACIÓN...")
    start_time = time.time()
    evaluator.set_requirements(req_document)
        
    req_review = None

    try:
        for req in evaluator._requirement_list:
            log(f"Evaluando requerimiento: {req.description}")
            try:
                log("Performing evaluation in LLM Pipeline mode...")
                evaluator.eval_requirement_llm(
                    req=req,
                    files_content=file_context
                )
                log(f"Evaluación completada para: {req.id}")
            except Exception as e:
                log(f"Error evaluando {req.id}: {str(e)}")

        try:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Creates review object
            req_review = ReqFidelityReview(
                debug_mode=debug_mode,
                review_date=str(datetime.now()),
                reviewed_reqs=list(evaluator._req_evaluations),
                input_tokens=evaluator.total_input_tokens,
                output_tokens=evaluator.total_output_tokens,
                llm_provider=current_llm,
                evaluation_mode=EvaluationMode.AGENT_AI,
                real_evaluation=real_batch_evaluation_type,
                response_time=elapsed_time
            )
        except Exception as e:
            log(f"Error guardando resultados: {str(e)}")

    finally:
        # Cleans given requirements from previous time
        evaluator._req_evaluations.clear()
        req_document.requirements.clear()
        evaluator.total_input_tokens = 0
        evaluator.total_output_tokens = 0

    # returns or raises exception
    if req_review is not None:
        return req_review
    else:
        raise ValueError("Error while saving ReqFidelityReview") 