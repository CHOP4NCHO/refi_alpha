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
inteligencia artificial. Actúa como fábrica que provee instancias
estándar de LangChain (`BaseChatModel`, `Embeddings`) sin exponer los
detalles de conexión a la lógica de negocio.

**Proveedores soportados**

-   **Ollama** (local): modelos descubiertos dinámicamente vía API
    (`/api/tags`). Conexión verificada al iniciar.
-   **Gemini** (cloud): modelos estáticos configurados vía
    `google_genai`.

**Fallback automático**

Si Ollama no está disponible, el sistema redirige transparentemente
las peticiones al proveedor cloud sin intervención del usuario.

**Validación por operación**

Cada operación del sistema (evaluación, importación PDF) valida que
los modelos requeridos estén configurados antes de ejecutarse, elevando
excepciones claras cuando faltan componentes.

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
