# Plan: Requerir Configuración de Modelos Obligatoria

## Objetivo
Eliminar todos los valores por defecto de los modelos para que el sistema no pueda utilizarse sin configurar previamente los modelos requeridos según la operación a realizar (Pipeline, Agente, o Importación de PDF).

## Análisis del Estado Actual

### Ubicaciones con valores por defecto:

1. **`main.py` (líneas 21-46)**: Valores hardcodeados en el diccionario `CONFIG` y en la creación de `ModelProvider`:
   - `local_llm`: "gemma4:12b"
   - `cloud_llm`: "google_genai:gemini-3.1-flash-lite"
   - `cloud_vlm`: "gemini-2.5-flash-lite"
   - `local_embedding`: "qwen3-embedding"
   - `cloud_embedding`: "google_genai:models/gemini-embedding-2"
   - `local_ip`: "localhost"
   - `cloud_ip`: "generativelanguage.googleapis.com/v1beta/openai"
   - Se crean `ModelConfig` con valores específicos en líneas 43-45

2. **`model_provider.py`**: El constructor acepta los 3 modelos como parámetros requeridos pero no valida que sean None o vacíos.

3. **`config_tab.py`**: No tiene validación para prevenir uso sin configuración.

---

## Reglas de Negocio: Modelos Requeridos por Operación

### Matriz de Requerimientos

| Operación | LLM | Embedding | VLM |
|-----------|-----|-----------|-----|
| Evaluar en modo **Pipeline** | ✅ Requerido | ❌ No requerido | ❌ No requerido |
| Evaluar en modo **Agente** | ✅ Requerido | ✅ Requerido | ❌ No requerido |
| **Importar PDF** | ❌ No requerido | ❌ No requerido | ✅ Requerido |
| **Exportar resultados** | ❌ No requerido | ❌ No requerido | ❌ No requerido |

### Validación Contextual

La validación de modelos depende de la operación que se vaya a realizar:
- **NO** se valida "todo o nada" al inicio
- Se valida **justo antes** de ejecutar la operación
- Cada operación sabe qué modelos necesita

---

## Arquitectura de Errores de Dominio

### Principio: Separación de Errores de Dominio y UI

Los errores de validación de modelos pertenecen al **dominio** (capa `core/`), no a la UI. La UI solo captura excepciones del dominio y muestra mensajes genéricos.

### 1. Crear excepciones de dominio
**Archivo nuevo:** `core/exceptions.py`

```python
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
```

### 2. Modificar `ModelConfig` para permitir valores None
**Archivo:** `core/model_config.py`

```python
@dataclass
class ModelConfig:
    provider: LlmProvider | None = None
    model_id: str | None = None
    category: str = "chat"  # chat | embedding | vlm

    def is_configured(self) -> bool:
        return self.provider is not None and self.model_id is not None
```

### 2. Modificar `ModelProvider` para validación contextual
**Archivo:** `core/model_provider.py`

- Cambiar los parámetros del constructor para que sean opcionales (None por defecto)
- Agregar métodos de validación **contextual** (según operación)
- Modificar `get_llm()`, `get_embeddings()`, `get_vlm_options()` para lanzar `ModelConfigurationError` con contexto de operación
- **NO** incluir lógica de UI en esta capa

```python
from .exceptions import ModelConfigurationError, ModelsNotConfiguredError

class ModelProvider:
    # Constantes para identificar operaciones
    OP_EVALUATE_PIPELINE = "evaluar_pipeline"
    OP_EVALUATE_AGENT = "evaluar_agente"
    OP_IMPORT_PDF = "importar_pdf"

    def __init__(
        self,
        local_ip: str = "localhost",
        cloud_ip: str = "",
        default_llm: ModelConfig | None = None,
        default_embedding: ModelConfig | None = None,
        default_vlm: ModelConfig | None = None,
        temperature: float = 0.1,
    ):
        # ... código existente ...
        self._llm_config = default_llm or ModelConfig(None, None)
        self._embedding_config = default_embedding or ModelConfig(None, None)
        self._vlm_config = default_vlm or ModelConfig(None, None)

    # Métodos de consulta (retornan bool, no lanzan excepciones)
    def is_llm_configured(self) -> bool:
        return self._llm_config.is_configured()

    def is_embedding_configured(self) -> bool:
        return self._embedding_config.is_configured()

    def is_vlm_configured(self) -> bool:
        return self._vlm_config.is_configured()

    # --------------------------------------------------
    # Validación contextual por operación
    # --------------------------------------------------

    def validate_for_pipeline(self) -> None:
        """Valida modelos requeridos para evaluación en modo Pipeline."""
        missing = []
        if not self.is_llm_configured():
            missing.append("LLM")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_EVALUATE_PIPELINE)

    def validate_for_agent(self) -> None:
        """Valida modelos requeridos para evaluación en modo Agente."""
        missing = []
        if not self.is_llm_configured():
            missing.append("LLM")
        if not self.is_embedding_configured():
            missing.append("Embedding")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_EVALUATE_AGENT)

    def validate_for_pdf_import(self) -> None:
        """Valida modelos requeridos para importar PDF."""
        missing = []
        if not self.is_vlm_configured():
            missing.append("VLM")
        if missing:
            raise ModelsNotConfiguredError(missing, self.OP_IMPORT_PDF)

    def validate_for_operation(self, operation: str) -> None:
        """Valida modelos para una operación específica."""
        validators = {
            self.OP_EVALUATE_PIPELINE: self.validate_for_pipeline,
            self.OP_EVALUATE_AGENT: self.validate_for_agent,
            self.OP_IMPORT_PDF: self.validate_for_pdf_import,
        }
        
        validator = validators.get(operation)
        if validator:
            validator()
        else:
            raise ValueError(f"Operación desconocida: {operation}")

    # --------------------------------------------------
    # Métodos que lanzan excepciones de dominio
    # --------------------------------------------------

    def get_llm(self, operation: str | None = None) -> BaseChatModel:
        if not self.is_llm_configured():
            raise ModelConfigurationError("llm", operation or "general")
        # ... código existente ...

    def get_embeddings(self, operation: str | None = None):
        if not self.is_embedding_configured():
            raise ModelConfigurationError("embedding", operation or "general")
        # ... código existente ...

    def get_vlm_options(self, prompt: str = "OCR the full page to markdown", operation: str | None = None) -> ApiVlmOptions:
        if not self.is_vlm_configured():
            raise ModelConfigurationError("vlm", operation or "general")
        # ... código existente ...
```

### 3. Modificar `RefiService` para validar según operación
**Archivo:** `core/refi_service.py`

- Validar modelos **justo antes** de ejecutar cada operación
- Usar los métodos de validación contextual de `ModelProvider`
- Las excepciones se propagan naturalmente hacia la UI

```python
from .exceptions import ModelsNotConfiguredError, ModelConfigurationError

class RefiService:
    def evaluate(self, log_callback=None) -> None:
        if not self._req_document.requirements:
            raise ValueError("No hay requerimientos cargados.")

        if not self._file_context:
            raise ValueError("No hay archivos cargados en el contexto.")

        # Validar según el modo de evaluación
        if self._evaluation_mode == EvaluationMode.AGENT_AI:
            self._model_provider.validate_for_agent()
        else:
            self._model_provider.validate_for_pipeline()

        current_llm = self._model_provider.get_llm(
            operation=self._evaluation_mode.value
        )

        # ... resto del código de evaluación ...

    def extract_requirements_from_pdf(self, pdf_path: str | Path) -> ReqDocument:
        path = Path(pdf_path).expanduser()

        if not path.is_file():
            raise FileNotFoundError(f"No se encontró el archivo PDF: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("El archivo seleccionado debe tener extensión .pdf.")

        # Validar VLM para importar PDF
        self._model_provider.validate_for_pdf_import()

        extractor = self._get_requirements_extractor()
        extractor.set_document(path)

        extracted_document = extractor.get_requirements()
        self._req_document = extracted_document

        return extracted_document
```

### 4. Modificar `main.py` para no usar valores por defecto
**Archivo:** `main.py`

- Eliminar el diccionario `CONFIG` completo con valores hardcodeados
- Crear `ModelProvider` sin valores por defecto
- Cargar configuración desde archivo si existe, o dejar vacío

```python
if __name__ == "__main__":
    # Cargar configuración desde archivo o usar vacío
    config = load_app_config()  # Nueva función que busca config.json
    
    model_provider = ModelProvider(
        local_ip=config.get("local_ip", "localhost"),
        cloud_ip=config.get("cloud_ip", ""),
        default_llm=None,  # Se configura desde UI
        default_embedding=None,
        default_vlm=None,
    )
    # ... resto del código ...
```

### 5. Modificar la UI para capturar excepciones de dominio
**Archivo:** `ui/main_window.py`

- **NO** incluir lógica de validación en la UI
- Capturar excepciones del dominio y mostrar mensajes genéricos
- La UI es solo una capa de presentación

```python
from core.exceptions import ModelConfigurationError, ModelsNotConfiguredError, DomainError

class RefiApp:
    def evaluate_reqs(self):
        try:
            # El dominio lanza excepciones si hay problemas de configuración
            self.service.evaluate(log_callback=self.log_message)
            
        except ModelsNotConfiguredError as e:
            # Captura errores de configuración y muestra mensaje genérico
            messagebox.showerror(
                "Configuración requerida",
                f"Para la operación '{e.operation}' se requieren modelos "
                f"que no están configurados: {', '.join(e.missing_models)}.\n"
                "Por favor, vaya a la pestaña de Configuración para configurarlos."
            )
            self.log_message(f"Error: {e.message}")
            
        except ModelConfigurationError as e:
            # Captura errores de un modelo específico
            messagebox.showerror(
                "Error de configuración",
                f"Error con el modelo {e.model_type.upper()}: {e.message}\n"
                "Verifique la configuración en la pestaña correspondiente."
            )
            self.log_message(f"Error: {e.message}")
            
        except DomainError as e:
            # Captura otros errores de dominio
            messagebox.showerror("Error", str(e))
            self.log_message(f"Error: {e}")
            
        except Exception as e:
            # Errores inesperados
            messagebox.showerror("Error inesperado", str(e))
            self.log_message(f"Error inesperado: {e}")

    def _import_pdf(self):
        try:
            # La validación de VLM ocurre dentro de extract_requirements_from_pdf
            self.service.extract_requirements_from_pdf(pdf_path)
            
        except ModelsNotConfiguredError as e:
            messagebox.showerror(
                "Configuración requerida",
                f"Para importar PDF se requiere el modelo VLM configurado.\n"
                "Por favor, vaya a la pestaña de Configuración para configurarlo."
            )
            self.log_message(f"Error: {e.message}")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log_message(f"Error: {e}")
```

**Archivo:** `ui/config_tab.py`

```python
from core.exceptions import ModelConfigurationError, DomainError

class ConfigTab:
    def _on_llm_change(self, event=None):
        try:
            model = self._find_model(self.llm_var.get(), "chat")
            self.app.service.model_provider.set_llm(model)
        except ValueError as e:
            messagebox.showwarning("Modelo no encontrado", str(e))
        except DomainError as e:
            messagebox.showerror("Error", str(e))

    def _on_embedding_change(self, event=None):
        try:
            model = self._find_model(self.embedding_var.get(), "embedding")
            self.app.service.model_provider.set_embedding(model)
        except ValueError as e:
            messagebox.showwarning("Modelo no encontrado", str(e))
        except DomainError as e:
            messagebox.showerror("Error", str(e))
```

### 5. Agregar persistencia de configuración (Opcional)
**Archivo nuevo:** `config.json` o `config.yaml`

Crear un archivo de configuración que guarde los modelos seleccionados para que no tengan que reconfigurarse en cada inicio:

```json
{
  "local_ip": "localhost",
  "cloud_ip": "generativelanguage.googleapis.com/v1beta/openai",
  "llm": {
    "provider": "gemini",
    "model_id": "google_genai:gemini-2.5-flash"
  },
  "embedding": {
    "provider": "gemini",
    "model_id": "google_genai:models/gemini-embedding-2"
  },
  "vlm": {
    "provider": "gemini",
    "model_id": "gemini-2.5-flash"
  }
}
```

### 6. Modificar `ConfigTab` para mostrar estado
**Archivo:** `ui/config_tab.py`

- Agregar indicadores visuales de qué modelos están configurados
- Agregar botón "Validar Configuración" que muestre si el sistema está listo
- Bloquear otras pestañas hasta que la configuración sea válida

---

## Patrón de Manejo de Errores

### Reglas de Separación de Responsabilidades

1. **Dominio (`core/`)**: Define y lanza excepciones de dominio
   - `ModelConfigurationError`: Cuando un modelo específico no está configurado
   - `ModelsNotConfiguredError`: Cuando faltan múltiples modelos
   - `ProviderConnectionError`: Cuando no se puede conectar al proveedor

2. **UI (`ui/`)**: Solo captura excepciones y muestra mensajes genéricos
   - Nunca contiene lógica de validación de dominio
   - Usa `try/except` para capturar excepciones del dominio
   - Muestra mensajes amigables sin exponer detalles internos

3. **Servicio (`core/refi_service.py`)**: Propaga excepciones del dominio
   - No valida en exceso, delega a ModelProvider
   - Permite que las excepciones propaguen hacia la UI

### Flujo de Excepción

```
Usuario acciona UI (ej: botón Evaluar)
    ↓
UI llama a service.evaluate()
    ↓
service valida según modo de evaluación:
    - Si es Pipeline → model_provider.validate_for_pipeline()
    - Si es Agente → model_provider.validate_for_agent()
    ↓
model_provider valida configuración requerida
    ↓
Si faltan modelos → lanza ModelsNotConfiguredError
    ↓
Excepción se propaga hasta UI
    ↓
UI captura y muestra mensaje genérico con detalles
```

### Ejemplo: Importar PDF

```
Usuario selecciona archivo PDF
    ↓
UI llama a service.extract_requirements_from_pdf()
    ↓
service llama a model_provider.validate_for_pdf_import()
    ↓
model_provider valida que VLM esté configurado
    ↓
Si falta VLM → lanza ModelsNotConfiguredError
    ↓
Excepción se propaga hasta UI
    ↓
UI muestra: "Para importar PDF se requiere el modelo VLM configurado"
```

### Beneficios

- **Mantenibilidad**: La lógica de validación está centralizada en el dominio
- **Reutilización**: Las excepciones pueden usarse desde cualquier capa
- **Testing**: Fácil de testear el dominio sin UI
- **Acoplamiento**: La UI no conoce las reglas de validación, solo muestra errores

---

## Flujo de Uso Propuesto

1. **Primer inicio**: El usuario abre la aplicación
2. **Pestaña Configuración**: Solo la pestaña de configuración está habilitada
3. **Configurar modelos**: El usuario selecciona proveedor y modelos
4. **Validar**: El sistema verifica que los 3 modelos estén configurados
5. **Habilitar**: Solo cuando todo está configurado se habilitan las demás pestañas
6. **Operar**: El sistema puede usarse normalmente

---

## Archivos a Modificar

| Archivo | Cambios |
|---------|---------|
| `core/exceptions.py` | **NUEVO**: Excepciones de dominio (ModelConfigurationError, ModelsNotConfiguredError, ProviderConnectionError) |
| `core/model_config.py` | Agregar método `is_configured()`, hacer provider/model_id opcionales |
| `core/model_provider.py` | Agregar métodos de validación contextual (validate_for_pipeline, validate_for_agent, validate_for_pdf_import), lanzar excepciones de dominio |
| `core/refi_service.py` | Agregar validación antes de cada operación (evaluate, extract_requirements_from_pdf) |
| `main.py` | Eliminar valores hardcodeados, crear ModelProvider vacío |
| `ui/main_window.py` | Capturar excepciones del dominio, mostrar mensajes genéricos |
| `ui/config_tab.py` | Capturar excepciones del dominio al cambiar modelos |

---

## Prioridad de Implementación

1. **Alta**: Crear `core/exceptions.py` con excepciones de dominio
2. **Alta**: Modificar `ModelConfig` para agregar `is_configured()`
3. **Alta**: Modificar `ModelProvider` con validación contextual
4. **Alta**: Modificar `RefiService` para validar antes de cada operación
5. **Alta**: Modificar `main.py` para eliminar defaults
6. **Media**: Modificar UI para capturar excepciones
7. **Baja**: Agregar persistencia con `config.json`

---

## Notas

- Se debe mantener compatibilidad con el archivo `.env` para API keys
- Los modelos de Gemini en `list_models()` son estáticos pero aún requieren configuración del usuario
- Considerar agregar un wizard de primera configuración en futuras iteraciones
