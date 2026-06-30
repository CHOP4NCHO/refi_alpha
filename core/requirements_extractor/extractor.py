
from pathlib import Path
from typing import cast
import logging

import requests
from langchain.chat_models import BaseChatModel
from langchain.messages import SystemMessage, HumanMessage
from docling.document_converter import DocumentConverter, PdfFormatOption
from pydantic import BaseModel

from .ocr_errors import (
    ExtractorConnectionError,
    DocumentConversionError,
    RequirementsModelError
)
from .constants import EXTRACTOR_PROMPT_TEMPLATE, HUMAN_PROMPT_TEMPLATE
from .req_document import ReqDocument, Requirement
from .vlm_retry import VlmRetryWrapper
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import VlmPipelineOptions
from docling.pipeline.vlm_pipeline import VlmPipeline
from langchain.embeddings.base import Embeddings

logger = logging.getLogger(__name__)

class RequirementsResponse(BaseModel):
    items: list[Requirement]


class RequirementsExtractor:
    """ Uses a defined LLM pipeline to extract Requirements from file. 
    
    Built using the Docling library.
    """
    
    SYSTEM_PROMPT_TEMPLATE = EXTRACTOR_PROMPT_TEMPLATE
    HUMAN_PROMPT_TEMPLATE = HUMAN_PROMPT_TEMPLATE
    _current_document = None

    def __init__(
        self,
        llm_ref: BaseChatModel,
        embedding_ref: Embeddings,
        vlm_options,
        is_local: bool = True,
    ):
        """Starts the models and objects."""

        logger.info("Initializing Requirements Extractor.")

        raw_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=VlmPipeline,
                    pipeline_options=VlmPipelineOptions(
                        enable_remote_services=True,
                        vlm_options=vlm_options,
                    ),
                )
            }
        )
        self.extractor = VlmRetryWrapper(raw_converter)

        self.llm = llm_ref
        self.embedding_ref = embedding_ref
        self.vlm_options = vlm_options
        self.is_local = is_local
        self.ollama_ip = self.vlm_options.url.host or "localhost"

    def _check_ocr_service(self) -> None:
        """Fail fast with an actionable error when Ollama is unavailable."""
        url = f"http://{self.ollama_ip}:11434/api/tags"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except requests.RequestException as error:
            raise ExtractorConnectionError(
                "No hay conexión con Ollama, necesario para leer el PDF. "
                f"Verifica que el servicio esté activo en {self.ollama_ip}:11434 "
                "e inténtalo nuevamente."
            ) from error

    def set_document(self, pdf_path: Path):
        """ Sets current pdf document. """
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError("The selected document must be a PDF file.")

        self._current_document = None
        if self.is_local:
            self._check_ocr_service()
        try:
            content = self.extractor.convert(pdf_path).document
        except Exception as error:
            logger.exception("Docling failed to convert PDF '%s'.", pdf_path)
            model_label = self.vlm_options.params.get("model", "desconocido")
            if self.is_local:
                model_message = f"y que el modelo OCR de Ollama '{model_label}' esté instalado."
            else:
                model_message = f"y que el modelo VLM '{model_label}' esté disponible."
            raise DocumentConversionError(
                "No fue posible leer el PDF. Comprueba que el archivo no esté "
                f"dañado {model_message}"
            ) from error
        self._current_document = content

    def _get_content(self):
        """_summary_
        Generates the DoclingDocument

        Raises:
            FileNotFoundError _description_ :
            Must define the current target document using set_document()

        Returns:
            _type_: _description_ DoclingDocument object.
        """
        if not self._current_document:
            raise FileNotFoundError("Current Document is not defined. ")
        
        return self._current_document
    
    def _to_markdown(self) -> str:
        """_summary_
        Transforms the defined current DoclingDocument object into a string 

        Raises:
            FileNotFoundError _description_ :
            Must define the current target document using set_document()

        Returns:
            _type_: _description_ complete text in .md format
        """
        if not self._current_document:
            raise FileNotFoundError("Current Document is not defined. ")
        
        return self._get_content().export_to_markdown()


    def get_requirements(self) -> ReqDocument:
        """
        get_requirements():

        0) get markdown version
        1) init LLM using both markdown content and SYSTEM_PROMPT_TEMPLATE
        2) prepare LLM indicating structured output
        3) save answer in indicated format
        4) generate and return ReqDocument object
        """

        logger.info("Generating markdown version of the requirements document.")
        try:
            markdown_content = self._to_markdown()
        except Exception as error:
            logger.exception("Failed to export the converted PDF to markdown.")
            raise DocumentConversionError(
                "El PDF fue procesado, pero no fue posible interpretar su contenido."
            ) from error

        logger.info("Initializing requirements extraction LLM.")
        conversation = [
            SystemMessage(content=self.SYSTEM_PROMPT_TEMPLATE),
            HumanMessage(
                content=f"{self.HUMAN_PROMPT_TEMPLATE}\n\n{markdown_content}"
            ),
        ]

        try:
            model = self.llm
            logger.info("Configuring structured requirements output.")
            structured_model = model.with_structured_output(RequirementsResponse)

            logger.info("Generating structured requirements response.")
            response = cast(
                RequirementsResponse,
                structured_model.invoke(conversation)
            )
        except Exception as error:
            logger.exception("The LLM failed to extract structured requirements.")
            raise RequirementsModelError(
                "El documento fue leído, pero el modelo no pudo extraer los "
                "requerimientos. Verifica la conexión y configuración del LLM."
            ) from error

        logger.info("Building extracted requirements document.")
        name: str = self._get_content().name

        output = ReqDocument(name)

        for requirement in response.items:
            output.add_requirement(requirement)

        return output
