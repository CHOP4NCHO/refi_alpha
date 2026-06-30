class DomainError(Exception):
    """Excepción base para errores de dominio."""
    pass


class ModelConfigurationError(DomainError):
    """Se lanza cuando un modelo requerido no está configurado."""
    
    def __init__(self, model_type: str, operation: str, message: str | None = None):
        self.model_type = model_type  # "llm", "embedding", "vlm"
        self.operation = operation  # "evaluar_pipeline", "evaluar_agente", "importar_pdf"
        self.message = message or (
            f"El modelo {model_type.upper()} es requerido para la operación '{operation}'. "
            f"Configure el modelo antes de continuar."
        )
        super().__init__(self.message)


class ModelsNotConfiguredError(DomainError):
    """Se lanza cuando faltan múltiples modelos para una operación."""
    
    def __init__(self, missing_models: list[str], operation: str):
        self.missing_models = missing_models
        self.operation = operation
        self.message = (
            f"Para la operación '{operation}' se requieren los siguientes modelos "
            f"que no están configurados: {', '.join(missing_models)}. "
            "Configure los modelos antes de continuar."
        )
        super().__init__(self.message)


class ProviderConnectionError(DomainError):
    """Se lanza cuando no se puede conectar al proveedor."""
    
    def __init__(self, provider: str, details: str | None = None):
        self.provider = provider
        self.message = f"No se pudo conectar al proveedor {provider}."
        if details:
            self.message += f" Detalles: {details}"
        super().__init__(self.message)
