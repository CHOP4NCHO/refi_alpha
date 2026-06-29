# REFI ALPHA - Contexto del Proyecto

Este documento sirve como referencia de contexto para futuras sesiones de desarrollo de **REFI ALPHA** (Requirements Fidelity), evitando el agotamiento de la ventana de contexto de los modelos de lenguaje.

---

## 📌 Descripción General
**REFI ALPHA** es un prototipo funcional diseñado para automatizar y evaluar la fidelidad de la implementación de requisitos de software frente a un repositorio de código real. Combina un pipeline de extracción visual/textual de requerimientos (PDF), un lector y mapeador de repositorios de código, y un agente evaluador inteligente basado en **LangChain** que utiliza capacidades de **RAG (Retrieval-Augmented Generation)** en memoria y un conjunto de herramientas de análisis para emitir veredictos técnicos sobre el nivel de cumplimiento del sistema.

---

## 🏗️ Arquitectura General

El proyecto se estructura en dos capas principales:

### Capa Core (`core/`)

Contiene toda la lógica de negocio y se expone al exterior a través de `RefiService`. Sus submódulos son:

| Módulo | Archivo(s) | Responsabilidad |
|---|---|---|
| **Orquestación** | `refi_service.py` | `RefiService` — fachada única que la UI u otros clientes usan para acceder a toda la funcionalidad del sistema. |
| **Modelos** | `model_provider.py` | `ModelProvider` — gestiona la conexión local a Ollama (IP configurable, puerto `11434`) y el fallback transparente a modelos cloud (`google_genai`). Provee LLM, embeddings y opciones VLM. |
| **Enumeraciones** | `enums.py` | `LlmProvider` (GEMINI, OLLAMA), `EvaluationMode` (AGENT_AI, LLM_PIPELINE), `RealEvaluation` (FULFILLED, NOT_FULFILLED). |
| **Codebase Reader** | `codebase_reader/` | Escaneo recursivo del repositorio objetivo, filtrado por extensiones aceptadas, y representación jerárquica (`CodeFile`, `CodeBase`, `CodeBaseReader`). |
| **Requirements Extractor** | `requirements_extractor/` | Procesamiento de PDFs mediante Docling + VLM (Ollama o cloud) para extraer requerimientos estructurados (`Requirement`, `ReqDocument`). |
| **Evaluator Agent** | `evaluator_agent/` | Motor de IA con dos modos de evaluación (`perform_agent_evaluation` y `perform_pipeline_evaluation`), RAG vectorial en memoria, seguimiento de tokens (`token_tracker.py`) y herramientas de análisis (`tools.py`). |
| **Result Manager** | `result_manager/` | Persistencia y recuperación de revisiones de fidelidad (`ReqFidelityReview`) serializadas. |

### Capa UI (`ui/`)

Interfaz gráfica construida con **Tkinter** + **ttkbootstrap** (tema `"cosmo"`). Consume exclusivamente `RefiService` de la capa Core.

| Componente | Archivo | Descripción |
|---|---|---|
| **Ventana Principal** | `main_window.py` | `RefiApp` — orquesta el `Notebook` de pestañas y la consola inferior. |
| **Pestaña 1: Espacio de Trabajo** | `workingtree_tab.py` | Árbol interactivo (`Treeview`) del repositorio cargado; permite seleccionar archivos para el contexto inicial. |
| **Pestaña 2: Requerimientos** | `requirements_tab.py` | Carga de PDFs, visualización de requerimientos extraídos y su estado de análisis. |
| **Pestaña 3: Evaluación** | `evaluation_tab.py` | Veredicto en tiempo real del agente para cada requerimiento, con estadísticas generales. |
| **Pestaña 4: Configuración** | `config_tab.py` | Ajustes en tiempo real: modo debug, proveedor LLM, modo de evaluación y tipo de evaluación batch. |
| **Consola de Logs** | `log_console.py` | Sección fija en la parte inferior que registra acciones del sistema, llamadas a API, y ciclo RAG. |

---

## ⚙️ Punto de Entrada (`main.py`)

El archivo `main.py` orquesta la inicialización completa:

1. **CONFIG** — Diccionario centralizado con geometría de ventana, tema, directorio de trabajo, modelos LLM (`gemini-3.1-flash-lite` como fallback cloud, `gemma4:12b` como local Ollama), IP de Ollama (`10.113.20.117`) y flags de depuración.
2. **ModelProvider** — Comprueba disponibilidad de Ollama en `{ip}:11434`. Si accesible, usa modelo local + embeddings `qwen3-embedding`; si no, redirige a `google_genai` con `gemini-embedding-2`.
3. **RefiService** — Instancia los módulos core con la configuración y el LLM resuelto.
4. **RefiApp** — Crea la ventana Tkinter y lanza `root.mainloop()`.

---

## 🧠 Evaluator Agent — Modos de Evaluación

El sistema soporta dos modos de evaluación seleccionables desde la UI (Pestaña 4):

| Modo | Función | Descripción |
|---|---|---|
| **AGENT_AI** (`agent`) | `perform_agent_evaluation()` | Ciclo agéntico completo con RAG vectorial, límite de recursividad `25`, y búsqueda semántica en el repositorio. |
| **LLM_PIPELINE** (`llm_pipeline`) | `perform_pipeline_evaluation()` | Evaluación directa mediante prompt con el contexto explícito, sin RAG. |

Ambos modos generan un `ReqFidelityReview` con fechas, veredictos, tokens consumidos y tiempo de respuesta.

---

## 💡 Prácticas de Desarrollo y Mantenimiento

* **Idioma de Trabajo:** Todo el código fuente funcional (métodos, lógica, variables) y sus respectivos comentarios técnicos deben escribirse y mantenerse en **inglés**. Las salidas hacia el usuario final (interfaces visuales, reportes generados y prompts agénticos de decisión final) se formulan y responden en **español**.
* **Gestión de Memoria:** Garantizar siempre la llamada a `clear_vector_store()` dentro de bloques `finally` al concluir cualquier sesión de evaluación para evitar fugas y consumo innecesario de RAM.
* **Estabilidad de Parada:** El límite de recursividad del agente debe mantenerse alto (`recursion_limit: 25`) para tolerar múltiples llamadas recursivas de descubrimiento semántico complejas.
