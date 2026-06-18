
from pathlib import Path
from typing import cast
import logging


from langchain.chat_models import init_chat_model
from langchain.messages import SystemMessage, HumanMessage
from docling.document_converter import DocumentConverter, PdfFormatOption
from pydantic import BaseModel

from requirements_extractor.constants import EXTRACTOR_PROMPT_TEMPLATE, HUMAN_PROMPT_TEMPLATE
from requirements_extractor.req_document import ReqDocument, Requirement

from pydantic import AnyUrl # Requerido para la URL del VLM

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    VlmPipelineOptions,
)
from docling.datamodel.pipeline_options_vlm_model import (
    ApiVlmOptions,
    ResponseFormat,
)
from docling.pipeline.vlm_pipeline import VlmPipeline


logger = logging.getLogger(__name__)

def create_vlm_options(model: str, prompt: str):
    return ApiVlmOptions(
        url=AnyUrl("http://10.113.20.117:11434/v1/chat/completions"),
        params=dict(
            model=model,
        ),
        prompt=prompt,
        timeout=90,
        scale=1.0,
        response_format=ResponseFormat.MARKDOWN
    )


class RequirementsResponse(BaseModel):
    items: list[Requirement]

class RequirementsExtractor:
    """ Uses a defined LLM pipeline to extract Requirements from file. 
    
    Built using the Docling library.
    """
    
    SYSTEM_PROMPT_TEMPLATE = EXTRACTOR_PROMPT_TEMPLATE
    HUMAN_PROMPT_TEMPLATE = HUMAN_PROMPT_TEMPLATE
    _current_document = None

    def __init__(self, llm_ref: str, embedding_ref: str):
        """Starts the models and objects."""

        logger.info("Initializing Requirements Extractor.")

        self.extractor = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=VlmPipeline,
                    pipeline_options=VlmPipelineOptions(
                        enable_remote_services=True,
                        vlm_options=create_vlm_options(
                            model="gemma4:12b",
                            prompt="OCR the full page to markdown",
                        ),
                    ),
                )
            }
        )

        self.llm = llm_ref
        self.embedding_ref = embedding_ref

    def set_document(self, pdf_path: Path):
        """ Sets current pdf document. """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        content = self.extractor.convert(pdf_path).document
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

        print("0. Generating markdown version...")
        markdown_content = self._to_markdown()

        print("1. Initializing LLM...")
        model = init_chat_model(
            model=self.llm,
            temperature=0,
        )

        conversation = [
            SystemMessage(content=self.SYSTEM_PROMPT_TEMPLATE),
            HumanMessage(
                content=f"{self.HUMAN_PROMPT_TEMPLATE}\n\n{markdown_content}"
            ),
        ]

        print("2. Indicating structured output...")
        structured_model = model.with_structured_output(
            RequirementsResponse
        )

        print("3. Generating structured response...")
        response = cast(
            RequirementsResponse,
            structured_model.invoke(conversation)
        )

        print("4. Returning ReqDocument...")
        name: str = self._get_content().name

        output = ReqDocument(name)

        for requirement in response.items:
            output.add_requirement(requirement)

        return output
            

