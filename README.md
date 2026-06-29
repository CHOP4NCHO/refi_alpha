# REFI ALPHA - Contexto del Proyecto

Este documento sirve como referencia de contexto para futuras sesiones de desarrollo de **REFI ALPHA** (Requirements Fidelity), evitando el agotamiento de la ventana de contexto de los modelos de lenguaje.

---

## 📌 Descripción General
**REFI ALPHA** es un prototipo funcional diseñado para automatizar y evaluar la fidelidad de la implementación de requisitos de software frente a un repositorio de código real. Combina un pipeline de extracción visual/textual de requerimientos (PDF), un lector y mapeador de repositorios de código, y un agente evaluador inteligente basado en **LangChain** que utiliza capacidades de **RAG (Retrieval-Augmented Generation)** en memoria y un conjunto de herramientas de análisis para emitir veredictos técnicos sobre el nivel de cumplimiento del sistema.

---

## 🧱 Módulos Principales (The 4 Core Modules)

### 1. Requirements Extractor (`requirements_extractor/`)
Responsable de procesar, digitalizar y extraer requerimientos estructurados desde especificaciones de diseño o matrices de conformidad en formato PDF.
* **Tecnología Clave:** Usa la librería **Docling** (IBM) configurada con pipelines visuales de lenguaje (VLM) para realizar parsing estructurado de layouts y OCR a Markdown.
* **Componentes:**
  * `extractor.py`: Define la clase `RequirementsExtractor` la cual llama de forma remota/local a modelos visuales de Ollama para OCR-izar páginas completas y estructurar los requisitos mediante esquemas de Pydantic.
  * `req_document.py`: Contiene los modelos de datos base `Requirement` y `ReqDocument`.

### 2. Codebase Reader (`codebase_reader/`)
Se encarga de mapear, estructurar y cargar el repositorio objetivo del usuario bajo un árbol lógico jerárquico.
* **Componentes:**
  * `code_file.py`: Define el objeto `CodeFile` que representa un archivo físico individual, con métodos optimizados como `get_raw_content()`, `get_file_content()` para lectura indexada de líneas, y `get_code_snippet(...)`.
  * `codebase.py`: Representa la base de código completa (`CodeBase`), escaneando recursivamente el directorio objetivo en busca de archivos que cumplan con la constante `ACCEPTED_EXTENSIONS` (ej: `.kt`, `.py`, `.ts`, `.java`, etc.).
  * `codebase_reader.py`: Expone utilidades para interactuar con la base de código (ej: navegar directorios, formatear el árbol de trabajo, obtener archivos por índice, etc.).

### 3. Evaluator Agent (`evaluator_agent/`)
El motor de inteligencia artificial que audita los requisitos contrastándolos con la base de código.
* **Componentes:**
  * `evaluator.py`: Define el núcleo de evaluación `Evaluator`. Implementa:
    * `build_vector_store(...)`: Segmenta el repositorio completo en fragmentos superpuestos de 50 líneas y crea una base de datos vectorial en memoria (`InMemoryVectorStore`).
    * `clear_vector_store()`: Libera inmediatamente el espacio en memoria RAM.
    * `eval_requirement_agent(...)`: Ejecuta el ciclo agéntico completo. Si la base vectorial está inicializada, utiliza un pipeline RAG con un límite alto de recursividad (`recursion_limit=25`) para evitar fallos de parada.
  * `tools.py`: Contiene el arsenal de herramientas (*toolbelt*) del agente:
    * `resolve_file_path()`: Utilidad de resolución de rutas ultra-resiliente (absolutas, relativas, difusas o por nombre de archivo).
    * `query_codebase_rag()`: Búsqueda semántica en la base vectorial del repositorio.
    * `get_file_structure_summary()`: Mapeador estructural agnóstico (usa AST para Python y expresiones regulares de alto rendimiento para Kotlin, TypeScript, Java, etc.).
    * `read_specific_file_lines()`: Lectura quirúrgica por rangos de línea.
    * `check_test_coverage_proximity()`: Localización inteligente de especificaciones y tests unitarios.

### 4. Result Manager (`result_manager/`)
Administra la persistencia de las evaluaciones de fidelidad generadas por el sistema.
* **Componentes:**
  * `result_manager.py`: Guarda y recupera objetos serializados de tipo revisión histórica de fidelidad (`ReqFidelityReview`).
  * `req_fidelity_review.py`: Modela de forma detallada las propiedades de la revisión actual, incluyendo fechas, veredictos agénticos estructurados, consumo de tokens y modos de ejecución.

---

## 💻 Interfaz de Usuario (`ui/`)

La interfaz de usuario está construida sobre la librería estándar **Tkinter** de Python, modernizada y estilizada con **`ttkbootstrap`** (tema central: `"cosmo"`). Su estructura está dividida en un componente de navegación por pestañas (`Notebook`) y una consola inferior de depuración:

1. **Pestaña 1: Espacio de Trabajo (`workingtree_tab.py`)**:
   - Muestra de forma interactiva el árbol de archivos (`Treeview`) del repositorio de código cargado.
   - Permite al usuario alternar mediante clics qué archivos formarán parte del contexto inicial explícito.
   - Cuenta con un botón para cambiar dinámicamente el directorio del espacio de trabajo.
2. **Pestaña 2: Requerimientos (`requirements_tab.py`)**:
   - Interfaz para cargar archivos PDF con requisitos de software.
   - Presenta un visor interactivo de los requerimientos extraídos con su estado actual de análisis.
3. **Pestaña 3: Evaluación y Resultados (`evaluation_tab.py`)**:
   - Muestra el veredicto en tiempo real emitido por el agente de IA para cada requisito analizado (cumplido, no cumplido, razonamiento detallado y estadísticas generales).
4. **Consola de Logs (`log_console.py`)**:
   - Una sección de salida de texto fija en la parte inferior de la ventana que registra de forma detallada las acciones del sistema, estado de las herramientas, llamadas a la API y el ciclo RAG.

---

## ⚙️ Punto de Entrada (`main.py`)

El archivo `main.py` orquesta la inicialización completa y el arranque de la aplicación.
* **CONFIG (Centralización de Variables):**
  Almacena configuraciones del prototipo, geometría inicial de la ventana, temas de estilos visuales, directorio de trabajo predeterminado, y modelos LLM asignados para el análisis en la nube u Ollama local.
* **ModelProvider (`model_provider.py`):**
  Clase encargada de comprobar si el puerto local de Ollama está activo (`11434`). Si es accesible, provee el LLM (`gemma4:12b`) y sus correspondientes embeddings locales; si no es accesible, redirige transparentemente las peticiones a la nube usando la API de Google GenAI (`gemini-3.1-flash-lite` y `gemini-embedding-2`).
* **Ciclo de Vida de Ejecución:**
  Instancia el bucle de eventos visuales (`root.mainloop()`) asociando los módulos centrales de evaluación y provisión de modelos a la aplicación Tkinter (`RefiApp`).

---

## 💡 Prácticas de Desarrollo y Mantenimiento

* **Idioma de Trabajo:** Todo el código fuente funcional (métodos, lógica, variables) y sus respectivos comentarios técnicos deben escribirse y mantenerse en **inglés**. Las salidas hacia el usuario final (interfaces visuales, reportes generados y prompts agénticos de decisión final) se formulan y responden en **español**.
* **Gestión de Memoria:** Garantizar siempre la llamada a `clear_vector_store()` dentro de bloques `finally` al concluir cualquier sesión de evaluación para evitar fugas y consumo innecesario de RAM.
* **Estabilidad de Parada:** El límite de recursividad del agente debe mantenerse alto (`recursion_limit: 25`) para tolerar múltiples llamadas recursivas de descubrimiento semántico complejas.
