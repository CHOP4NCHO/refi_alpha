class RequirementsExtractionError(RuntimeError):
    """Base error for failures while extracting requirements from a PDF."""

class ExtractorConnectionError(RequirementsExtractionError):
    """Raised when the OCR service cannot be reached."""

class DocumentConversionError(RequirementsExtractionError):
    """Raised when Docling cannot convert the selected document."""

class RequirementsModelError(RequirementsExtractionError):
    """Raised when the LLM cannot produce the structured requirements."""