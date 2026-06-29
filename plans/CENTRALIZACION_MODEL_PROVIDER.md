# Plan: Centralización de modelos con configuración en runtime

## Problema actual
- Nombres de modelo dispersos: `main.py` CONFIG, hardcoded en `model_provider.py`, `enums.py`, `ux_test.py`
- `local_embedding` y cloud embedding hardcodeados en `model_provider.py`
- `ollama_temperature` definido en CONFIG pero nunca usado
- `get_llm()` nunca se invoca (solo `get_multimodal_model()`)
- No hay switching real en runtime — el dropdown de UI solo cambia un label, no el modelo

## Objetivo
`ModelProvider` sea la **única fuente de verdad** para toda configuración de modelos, con capacidad de cambiar en runtime.

---

## Cambio 1: `core/model_provider.py` — Reestructurar constructor y agregar setters

**Constructor expandido** (sin strings hardcodeados):
```python
def __init__(
    self,
    ip: str,
    local_llm: str,
    fallback_llm: str,
    local_vlm: str | None = None,    # None = usar local_llm
    cloud_vlm: str = "",
    local_embedding: str = "",
    cloud_embedding: str = "",
    temperature: float = 0.1,
):
```

- `local_vlm`: si es None, usa `local_llm` para OCR (comportamiento actual)
- `local_embedding` y `cloud_embedding`: ya no hardcodeados

**Setters para runtime:**
```python
def set_llm(self, model: str) -> None: ...
def set_vlm(self, model: str) -> None: ...
def set_embedding(self, model: str) -> None: ...
def set_ollama_ip(self, ip: str) -> None: ...  # re-verifica conexión
```

**Propiedades para UI:**
```python
@property
def current_llm(self) -> str: ...
@property
def current_vlm(self) -> str: ...
@property
def current_embedding(self) -> str: ...
@property
def is_local(self) -> bool: ...  # reemplaza is_ollama_reachable en consumidores
```

**Getters actualizados** — usan estado mutable:
- `get_llm()` → usa `self._local_llm` o `self._fallback_llm`
- `get_vlm_options()` → usa `self._local_vlm` o `self._cloud_vlm`
- `get_embeddings()` → usa `self._local_embedding` o `self._cloud_embedding`
- Eliminar `get_multimodal_model()` (duplica `get_llm()`)

---

## Cambio 2: `main.py` — CONFIG centralizado

```python
CONFIG = {
    # ...existing UI config...
    "ollama_ip": "10.113.20.117",
    "local_llm": "gemma4:12b",
    "fallback_llm": "google_genai:gemini-3.1-flash-lite",
    "cloud_vlm": "gemini-2.5-flash-lite",
    "local_embedding": "qwen3-embedding",
    "cloud_embedding": "google_genai:models/gemini-embedding-2",
    "temperature": 0.1,
}
```

---

## Cambio 3: `core/refi_service.py` — Adaptar a nuevo ModelProvider

- Reemplazar `evaluator_llm: BaseChatModel` por usar `model_provider.get_llm()` directamente
- Eliminar `self._evaluator_llm` — siempre obtener el modelo del provider
- Agregar setter `current_llm` que llame `model_provider.set_llm()` y recree el `Evaluator`
- `current_vlm` setter que llame `model_provider.set_vlm()` y reinicie el extractor

---

## Cambio 4: `core/enums.py` — Corregir `LlmProvider`

- `GEMINI = "gemini"` (genérico, sin versión)
- `OLLAMA = "ollama"`
- El valor ya no es un nombre de modelo exacto, es un label de categoría

---

## Cambio 5: `ui/config_tab.py` — Switching real

- Conectar dropdown LLM a `model_provider.set_llm()` + recrear Evaluator
- Agregar dropdown VLM con `model_provider.set_vlm()`
- Agregar dropdown Embedding con `model_provider.set_embedding()`

---

## Cambio 6: `core/requirements_extractor/extractor.py` — Eliminar bypass

- Eliminar `init_chat_model()` directo en `get_requirements()`
- Siempre recibir `BaseChatModel` ya instanciado desde `RefiService`

---

## Cambio 7: `ux_test.py` — Actualizar test harness

- Adaptar llamada a `ModelProvider` con nuevos parámetros

---

## Archivos afectados (resumen)

| Archivo | Cambio |
|---------|--------|
| `core/model_provider.py` | Reestructurar constructor, agregar setters/properties |
| `main.py` | Expandir CONFIG, pasar todos los modelos |
| `core/refi_service.py` | Usar `model_provider.get_llm()`, agregar setters |
| `core/enums.py` | Corregir `LlmProvider` |
| `ui/config_tab.py` | Conectar a setters reales |
| `core/requirements_extractor/extractor.py` | Eliminar `init_chat_model` directo |
| `ux_test.py` | Actualizar llamada a `ModelProvider` |

## Orden de implementación
1. `model_provider.py` (base de todo)
2. `main.py` (config)
3. `refi_service.py` (consumidor principal)
4. `enums.py` (corrección menor)
5. `extractor.py` (eliminar bypass)
6. `ui/config_tab.py` (UI wiring)
7. `ux_test.py` (test harness)

## Inconsistencias detectadas (a corregir)

| Issue | Ubicación | Detalle |
|-------|-----------|---------|
| `ollama_temperature` sin usar | `main.py:29` | Definido en CONFIG pero nunca pasado a ModelProvider o ChatOllama |
| Mismatch de nombre de modelo | `enums.py:5` vs `main.py:26` | `LlmProvider.GEMINI = 'gemini3.1-flash'` vs string real `"google_genai:gemini-3.1-flash-lite"` |
| `get_llm()` nunca invocado | `main.py:46` | Solo se llama `get_multimodal_model()` |
| `test_extractor.py` roto | `test_extractor.py:31` | Falta argumento requerido `vlm_options` |
| Diferentes cloud VLM models | `main.py:28` vs `ux_test.py:36` | `"gemini-2.5-flash-lite"` vs `"paligemma-3b"` |
| `embedding_ref` string vacío | `refi_service.py:163` | Se pasa `""` al extractor, nunca se usa |
| Local embedding hardcodeado | `model_provider.py:27` | `"qwen3-embedding"` no configurable |
| Cloud embedding hardcodeado | `model_provider.py:87` | `"google_genai:models/gemini-embedding-2"` no configurable |
| Sin switching real en runtime | `ui/config_tab.py` | Dropdown solo cambia label, no modelo |
