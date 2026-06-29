from pathlib import Path
from langchain.chat_models import BaseChatModel

from .evaluator_agent.evaluator import Evaluator
from .evaluator_agent.evaluation_runner import perform_agent_evaluation, perform_pipeline_evaluation
from .evaluator_agent.req_fidelity_review import ReqFidelityReview
from .codebase_reader.codebase import CodeBase
from .codebase_reader.codebase_reader import CodeBaseReader
from .codebase_reader.code_file import CodeFile
from .requirements_extractor.req_document import ReqDocument, Requirement
from .result_manager.result_manager import ResultManager
from .model_provider import ModelProvider
from .enums import EvaluationMode, RealEvaluation, LlmProvider


class RefiService:
    """
    Orchestration layer that encapsulates all application logic.
    The UI or any other client interacts exclusively through this interface.
    """

    def __init__(
        self,
        workdir: str,
        codebase_name: str,
        evaluator_llm: BaseChatModel,
        model_provider: ModelProvider,
        debug_mode: bool = False,
        evaluation_mode: EvaluationMode = EvaluationMode.AGENT_AI,
        real_evaluation: RealEvaluation = RealEvaluation.FULFILLED,
    ):
        self._workdir = workdir
        self._model_provider = model_provider
        self._debug_mode = debug_mode
        self._evaluation_mode = evaluation_mode
        self._real_evaluation = real_evaluation

        # Core modules
        self._evaluator = Evaluator(llm_ref=evaluator_llm)
        self._req_document = ReqDocument(workdir)
        self._codebase = CodeBase(path=workdir, name=codebase_name)
        self._codebase_reader = CodeBaseReader(codebase=self._codebase)
        self._result_manager = ResultManager()
        self._file_context: list[CodeFile] = []

        # Determine LLM provider from model name
        model_name = self._evaluator.get_model_name().lower().split()[0]
        match model_name:
            case "gemini":
                self._current_llm = LlmProvider.GEMINI
            case _:
                self._current_llm = LlmProvider.OLLAMA

    # ------------------------------------------------------------------ #
    #  Workspace (CODEBASE READER)
    # ------------------------------------------------------------------ #

    @property
    def codebase(self) -> CodeBase:
        return self._codebase

    @property
    def codebase_reader(self) -> CodeBaseReader:
        return self._codebase_reader

    def set_workdir(self, path: str, name: str | None = None) -> None:
        new_codebase = CodeBase(path=path, name=name or Path(path).name)
        self._codebase = new_codebase
        self._codebase_reader.codebase = new_codebase
        self._file_context.clear()

    # ------------------------------------------------------------------ #
    #  File context
    # ------------------------------------------------------------------ #

    @property
    def file_context(self) -> list[CodeFile]:
        return self._file_context

    def add_file_to_context(self, file_path: Path) -> bool:
        for f in self._codebase.files:
            if Path(f.path) == file_path:
                if f not in self._file_context:
                    self._file_context.append(f)
                    return True
                return False
        raise FileNotFoundError(
            f"El archivo '{file_path}' no se encuentra en el CodeBase "
            f"o su extensión no está permitida."
        )

    def add_directory_to_context(self, dir_path: Path) -> int:
        added = 0
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                try:
                    if self.add_file_to_context(file_path):
                        added += 1
                except FileNotFoundError:
                    pass
        return added

    def remove_file_from_context(self, file_path: Path) -> None:
        self._file_context = [
            f for f in self._file_context if Path(f.path) != file_path
        ]

    def clear_file_context(self) -> None:
        self._file_context.clear()

    # ------------------------------------------------------------------ #
    #  Requirements
    # ------------------------------------------------------------------ #

    @property
    def req_document(self) -> ReqDocument:
        return self._req_document

    def add_requirement(self, description: str, req_type: str) -> Requirement:
        import random
        import string

        req_id = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=3)
        )
        requirement = Requirement(id=req_id, description=description, type=req_type)
        self._req_document.add_requirement(requirement)
        return requirement

    def get_requirements(self) -> list[Requirement]:
        return list(self._req_document.requirements)

    def clear_requirements(self) -> None:
        self._req_document.requirements.clear()

    # ------------------------------------------------------------------ #
    #  Evaluation
    # ------------------------------------------------------------------ #

    def evaluate(self, log_callback=None) -> ReqFidelityReview:
        if not self._req_document.requirements:
            raise ValueError("No hay requerimientos cargados.")
        if not self._file_context:
            raise ValueError("No hay archivos cargados en el contexto.")

        if self._evaluation_mode == EvaluationMode.AGENT_AI:
            review = perform_agent_evaluation(
                evaluator=self._evaluator,
                req_document=self._req_document,
                codebase_reader=self._codebase_reader,
                file_context=self._file_context,
                model_provider=self._model_provider,
                current_llm=self._current_llm,
                debug_mode=self._debug_mode,
                real_batch_evaluation_type=self._real_evaluation,
                log_callback=log_callback,
            )
        else:
            review = perform_pipeline_evaluation(
                evaluator=self._evaluator,
                req_document=self._req_document,
                file_context=self._file_context,
                current_llm=self._current_llm,
                debug_mode=self._debug_mode,
                real_batch_evaluation_type=self._real_evaluation,
                log_callback=log_callback,
            )

        self._result_manager.add_review(review=review)
        review_index = len(self._result_manager.saved_reviews) - 1
        self._result_manager.save_review(review_index)

        return review

    # ------------------------------------------------------------------ #
    #  Results
    # ------------------------------------------------------------------ #

    @property
    def result_manager(self) -> ResultManager:
        return self._result_manager

    def get_saved_reviews(self) -> list[ReqFidelityReview]:
        return list(self._result_manager.saved_reviews)

    def get_formatted_review(self, index: int) -> str:
        return self._result_manager.format_review(index)

    # ------------------------------------------------------------------ #
    #  Configuration
    # ------------------------------------------------------------------ #

    @property
    def evaluation_mode(self) -> EvaluationMode:
        return self._evaluation_mode

    @evaluation_mode.setter
    def evaluation_mode(self, value: EvaluationMode) -> None:
        self._evaluation_mode = value

    @property
    def real_evaluation(self) -> RealEvaluation:
        return self._real_evaluation

    @real_evaluation.setter
    def real_evaluation(self, value: RealEvaluation) -> None:
        self._real_evaluation = value

    @property
    def current_llm(self) -> LlmProvider:
        return self._current_llm

    @current_llm.setter
    def current_llm(self, value: LlmProvider) -> None:
        self._current_llm = value

    @property
    def debug_mode(self) -> bool:
        return self._debug_mode

    @debug_mode.setter
    def debug_mode(self, value: bool) -> None:
        self._debug_mode = value
