# Arquitectura de Componentes

El sistema se implementa como un **Monolito Modular (Modular
Monolith)**, donde toda la aplicación se ejecuta como un único proceso,
pero su lógica de negocio se encuentra organizada en módulos con
responsabilidades bien definidas y bajo acoplamiento. Cada componente
encapsula una capacidad específica del dominio y se comunica mediante
interfaces internas, evitando dependencias directas con los proveedores
de IA.

## Visión General

``` text
Entradas
├── Working Directory
└── Requirements Document
         │
         ▼
+---------------------------------------------+
| Requirement Fidelity Evaluator Application  |
|                                             |
|  Codebase Reader ─────┐                     |
|                       ├──► AI Evaluator ───► Results Manager
|  Requirements Extractor┘                     |
|          │                ▲                  |
|          ▼                │                  |
|       RefiService ◄───────┘                  |
|                                             |
+---------------------------------------------+
         │
         ▼
ModelProvider (Ollama / Gemini)
```

# Componentes del Dominio

## Codebase Reader

**Responsabilidad**

Realiza la lectura y análisis estructural del directorio de trabajo que
contiene el código fuente.

**Funciones principales**

-   Recorrido recursivo del proyecto.
-   Filtrado de archivos relevantes (14 extensiones aceptadas).
-   Exclusión de directorios ignorados (`.git`, `node_modules`, etc.).
-   Representación jerárquica del árbol de archivos.

**Dependencias**

-   Sistema de archivos.

**Salida**

-   Objeto `CodeBase` con la lista de `CodeFile` representando el
    código fuente que será utilizado durante la evaluación.

------------------------------------------------------------------------

## Requirements Extractor

**Responsabilidad**

Obtiene los requerimientos funcionales desde un documento PDF de
entrada.

**Funciones principales**

-   Conversión del documento PDF a Markdown mediante Docling VLM.
-   Extracción estructurada de requerimientos mediante LLM.
-   Validación del formato obtenido (Pydantic).
-   Reintentos con backoff exponencial ante fallos transitorios del VLM.

**Dependencias**

-   ModelProvider para acceder al VLM y al LLM de extracción.

**Salida**

-   Objeto `ReqDocument` con la colección de `Requirement` extraídos.

------------------------------------------------------------------------

## AI Evaluator

**Responsabilidad**

Constituye el núcleo de la aplicación y coordina el proceso de
evaluación entre los requerimientos y la base de código.

**Funciones principales**

-   Recibe el código fuente y los requerimientos extraídos.
-   Construye los prompts según el modo de evaluación.
-   Invoca los modelos de lenguaje (modo agente con RAG o pipeline
    directo).
-   Consolida las respuestas y calcula la fidelidad de implementación.
-   Registra consumo de tokens mediante callbacks.

**Modos de evaluación**

-   **AGENT_AI**: Ciclo agéntico con RAG vectorial, 4 herramientas
    especializadas y límite de recursividad 25.
-   **LLM_PIPELINE**: Evaluación directa con contexto explícito, sin
    RAG.

**Dependencias**

-   Codebase Reader.
-   Requirement y ReqDocument (modelos de dominio).
-   ModelProvider (para obtener el LLM y embeddings).

**Salida**

-   Objeto `ReqFidelityReview` con veredictos, tokens y métricas.

------------------------------------------------------------------------

## Results Manager

**Responsabilidad**

Gestiona la persistencia y presentación de los resultados generados
durante la evaluación.

**Funciones principales**

-   Almacenamiento en memoria de revisiones históricas.
-   Formateo de resultados a texto legible.
-   Escritura de reportes a archivo en disco.

**Salida**

-   Archivo de reporte con el historial de evaluaciones.

# RefiService (Fachada)

**RefiService** es la fachada única del sistema. Toda la funcionalidad
del dominio se expone a través de esta clase, evitando que las capas
cliente accedan directamente a los módulos internos.

**Responsabilidades**

-   Gestión del workspace y contexto de archivos evaluados.
-   Creación, edición y eliminación de requerimientos.
-   Orquestación de la evaluación (dispatch a agent o pipeline).
-   Persistencia y consulta de resultados.
-   Configuración de modelos, modo de evaluación y depuración.

**Módulos que orquesta**

-   `CodeBaseReader` — acceso al repositorio de código.
-   `RequirementsExtractor` — creado bajo demanda para importación de
    PDF.
-   `Evaluator` — ejecución de la evaluación.
-   `ResultManager` — almacenamiento de resultados.
-   `ModelProvider` — resolución de modelos LLM, embeddings y VLM.

**Inicialización lazy**

`RequirementsExtractor` se instancia únicamente cuando el usuario
solicita importar un PDF por primera vez, evitando consumir recursos
innecesarios al arrancar la aplicación.

# ModelProvider

**ModelProvider** encapsula la selección y creación de modelos de
inteligencia artificial. Actúa como fachada que coordina catálogos y
fábricas para proveer instancias estándar de LangChain
(`BaseChatModel`, `Embeddings`) sin exponer los detalles de conexión a
la lógica de negocio.

**Proveedores soportados**

-   **Ollama** (local): modelos descubiertos dinámicamente vía API
    (`/api/tags`). Conexión verificada al iniciar.
-   **Gemini** (cloud): modelos configurados vía `google_genai`.
-   **OpenAI** (cloud): modelos vía API REST.
-   **Claude** (cloud): modelos chat sin soporte de embeddings ni VLM.

**Fallback automático**

Si Ollama no está disponible, el sistema redirige transparentemente
las peticiones al proveedor cloud sin intervención del usuario.

**Validación por operación**

Cada operación del sistema (evaluación, importación PDF) valida que
los modelos requeridos estén configurados antes de ejecutarse, elevando
excepciones claras cuando faltan componentes.

**Dependencias internas**

-   `ModelFactory` — construye instancias ejecutables de LangChain.
-   `ProviderCatalog` (y subclases) — descubren y clasifican modelos
    disponibles por proveedor.
-   `ModelConfig` — estructura de datos inmutable para configuración
    de un modelo.

# ModelConfig

**Responsabilidad**

Estructura de datos inmutable (`dataclass`) que representa la
configuración de un modelo de IA seleccionado.

**Campos**

-   `provider` (`LlmProvider | None`): proveedor propietario del
    modelo.
-   `model_id` (`str | None`): identificador único del modelo dentro
    del proveedor.
-   `category` (`str`): clasificación funcional — `chat`, `embedding`
    o `vlm`.

**Métodos**

-   `is_configured() -> bool`: retorna `True` cuando proveedor e
    identificador no son `None`.

**Uso**

Se utiliza como unidad de intercambio entre catálogos, fábricas y la
fachada `ModelProvider`.

# ModelFactory

**Responsabilidad**

Construye instancias ejecutables de LangChain (`BaseChatModel`,
`Embeddings`) y objetos Docling (`ApiVlmOptions`) a partir de un
`ModelConfig`. Aísla los detalles de conexión a cada proveedor.

**Constructor**

Recibe `local_ip`, `cloud_ip` y `temperature` como parámetros
globales aplicados a todas las instancias creadas.

**Métodos**

-   `create_llm(config, operation)`: crea un `BaseChatModel`
    según el proveedor.
    -   `Ollama` → `ChatOllama` con `base_url` local y formato JSON.
    -   `Gemini / OpenAI / Claude` → `init_chat_model` de LangChain.
-   `create_embeddings(config, operation)`: crea un objeto
    `Embeddings`.
    -   `Ollama` → `init_embeddings` con prefijo `ollama:`.
    -   `Gemini / OpenAI` → `init_embeddings` directo.
    -   `Claude` → eleva `ValueError` (no soportado).
-   `create_vlm_options(config, prompt, operation)`: devuelve un
    `ApiVlmOptions` para Docling.
    -   `Ollama` → endpoint local `/v1/chat/completions`.
    -   `OpenAI` → endpoint remoto con API key.
    -   `Gemini` → endpoint `generativelanguage.googleapis.com` con
        prefijo `google_genai:` eliminado.

**Excepciones**

-   `ModelConfigurationError` si `config` no está configurado.
-   `ValueError` si el proveedor no es soportado.

# Catálogos de Modelos

## ProviderCatalog (base)

**Responsabilidad**

Clase abstracta que define la interfaz para descubrir y clasificar
modelos de un proveedor determinado.

**Campos**

-   `provider` (`LlmProvider`): proveedor asociado.
-   `_cache` (`list[ModelConfig] | None`): caché de modelos
    descubiertos.
-   `_source` (`"remote" | "empty"`): origen de los datos del
    catálogo.
-   `_last_error` (`str | None`): último error de conexión registrado.

**Métodos**

-   `list_models() -> list[ModelConfig]`: retorna los modelos del
    caché (refresca si es necesario).
-   `refresh()`: fuerza la recarga desde la fuente (implementación
    específica por subclase).
-   `get_status() -> str`: describe el estado del catálogo.

---

## OllamaCatalog

**Responsabilidad**

Descubre modelos instalados en una instancia local de Ollama mediante
el endpoint `/api/tags`.

**Clasificación** (`_classify`)

-   `embedding`: nombres contienen `embed`, `nomic-embed`,
    `mxbai-embed`, `bge-`, `e5-`, `snowflake-arctic-embed`.
-   `vlm`: nombres contienen `vision`, `llava`, `bakllava`,
    `minicpm-v`, `moondream`, `granite3.2-vision`, `gemma3`.
-   `chat`: por defecto para el resto.

---

## OpenAICatalog

**Responsabilidad**

Lista modelos disponibles en la API de OpenAI.

**Clasificación** (`_classify`)

-   `embedding`: prefijo `text-embedding`.
-   `chat`: nombres que contienen `gpt-4o`, `gpt-4.1`, `gpt-5` o
    prefijo `gpt-`.

---

## GeminiCatalog

**Responsabilidad**

Lista modelos de Google Gemini. Consulta la API REST de
`generativelanguage.googleapis.com` cuando la API key está disponible.

**Clasificación** (`_classify`)

-   `embedding`: contiene `embedding`.
-   `chat`: contiene `gemini` y no contiene `image`, `tts` ni
    `preview`.
-   `vlm`: contiene `gemini` (fallback).

---

## ClaudeCatalog

**Responsabilidad**

Lista modelos de Anthropic Claude. Solo soporta categoría `chat` (sin
embeddings ni VLM).

**Clasificación**: todos los modelos se clasifican como `chat`.

# Enums de Dominio

## LlmProvider

Define los proveedores de modelos de lenguaje soportados por el
sistema.

-   `GEMINI` — Google Gemini (cloud).
-   `OLLAMA` — Ollama (local).
-   `OPENAI` — OpenAI (cloud).
-   `CLAUDE` — Anthropic Claude (cloud).

## EvaluationMode

Establece los modos de evaluación disponibles.

-   `LLM_PIPELINE` — Evaluación directa con contexto explícito, sin
    RAG.
-   `AGENT_AI` — Ciclo agéntico con RAG vectorial y herramientas
    especializadas.

## RealEvaluation

Resultado binario de la evaluación de un requerimiento.

-   `FULFILLED` — Requerimiento implementado.
-   `NOT_FULFILLED` — Requerimiento no implementado.

## RefiOperations

Identificador de las operaciones principales del sistema.

-   `EVALUATE_PIPELINE` — Ejecutar evaluación en modo pipeline.
-   `EVALUATE_AGENT` — Ejecutar evaluación en modo agente.
-   `IMPORT_PDF` — Importar documento de requerimientos.

# Excepciones de Dominio

## DomainError

Excepción base para todos los errores de dominio del sistema.

## ModelConfigurationError

Se eleva cuando un modelo requerido no está configurado para una
operación determinada.

-   `model_type`: tipo de modelo (`"llm"`, `"embedding"`, `"vlm"`).
-   `operation`: operación que requiere el modelo.

## ModelsNotConfiguredError

Se eleva cuando faltan múltiples modelos para una operación.

-   `missing_models`: lista de tipos de modelo faltantes.
-   `operation`: operación que requiere los modelos.

## ProviderConnectionError

Se eleva cuando no se puede conectar a un proveedor externo.

-   `provider`: nombre del proveedor.
-   `details`: información adicional del error.

# Proveedores Externos

## Cloud (remoto)

-   Google Gemini (gemini-3.1-flash-lite, gemini-embedding-2)

## Local (máquina del usuario)

-   Ollama (modelos descubiertos dinámicamente)

# Flujo de Dependencias

``` text
Working Directory
        │
        ▼
Codebase Reader ─────────────┐
        │                     │
        │                     ▼
        │               AI Evaluator ◄──── ModelProvider
        │                     │             (LLM / Embeddings / VLM)
        │                     ▼
        │               Results Manager
        │                     │
        ▼                     ▼
  RefiService ──────── Final Report
        │
        ▼
  Requirements Extractor
  (creado bajo demanda)
```

# Decisiones Arquitectónicas

-   **Alta cohesión:** cada módulo encapsula una única responsabilidad
    funcional.
-   **Bajo acoplamiento:** la interacción entre componentes ocurre
    mediante interfaces internas y RefiService como fachada única.
-   **Inversión de dependencias:** los módulos del dominio desconocen la
    implementación concreta de los proveedores de IA. Reciben
    instancias abstractas de LangChain.
-   **Extensibilidad:** nuevos proveedores o modelos pueden
    incorporarse modificando únicamente ModelProvider.
-   **Separación entre dominio e infraestructura:** la lógica de
    evaluación permanece aislada de detalles tecnológicos.
-   **Portabilidad:** el mismo núcleo funcional opera con modelos
    en la nube o locales mediante la misma interfaz.
-   **Simplicidad:** se evitan abstracciones cuyo único propósito sea
    cumplir un patrón arquitectónico. El tamaño del proyecto se
    beneficia de una estructura plana y directa.

En conjunto, esta organización facilita el mantenimiento y evolución del
sistema, permitiendo incorporar nuevas capacidades relacionadas con
modelos de lenguaje sin afectar los componentes responsables del
procesamiento del código fuente, la extracción de requerimientos o la
generación de resultados.
