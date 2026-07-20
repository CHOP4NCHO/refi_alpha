# Plan: Catálogos Dinámicos y Proveedores Independientes por Categoría

## Objetivo
Permitir que la app configure simultáneamente proveedores distintos para cada categoría de modelo:

- LLM: por ejemplo Claude.
- Embeddings: por ejemplo OpenAI.
- VLM/OCR: por ejemplo Ollama.

La lógica de negocio no debe conocer esta combinación. `RefiService`, `Evaluator` y `RequirementsExtractor` deben seguir consumiendo capacidades por categoría: `get_llm()`, `get_embeddings()` y `get_vlm_options()`. El cambio debe concentrarse en `ModelProvider` y clases de soporte nuevas por encima o alrededor de él, separando responsabilidades sin romper el flujo actual.

---

## Estado Actual
- `ModelProvider` ya mantiene tres configuraciones independientes:
  - `_llm_config`
  - `_embedding_config`
  - `_vlm_config`
- Cada una es un `ModelConfig(provider, model_id, category)`, por lo que conceptualmente ya permite mezclar proveedores.
- La UI PyQt separa combos por categoría.
- El catálogo todavía se construye principalmente desde `ModelProvider.list_models()`.
- `Ollama` se lista dinámicamente desde `/api/tags`.
- Los providers cloud usan catálogos estáticos o semiestáticos.

Limitación principal:
- `ModelProvider` mezcla demasiadas responsabilidades:
  - descubrir modelos;
  - clasificar modelos;
  - validar credenciales;
  - construir instancias LLM;
  - construir embeddings;
  - construir opciones VLM;
  - mantener estado activo por categoría.

---

## Diseño Propuesto

### 1. Mantener `ModelProvider` como fachada de aplicación
`ModelProvider` debe seguir siendo la API consumida por el core:

```python
model_provider.get_llm()
model_provider.get_embeddings()
model_provider.get_vlm_options()
model_provider.set_llm(config)
model_provider.set_embedding(config)
model_provider.set_vlm(config)
model_provider.list_models()
```

Esto evita romper la lógica de negocio.

Cambio conceptual:
- `ModelProvider` deja de saber todos los detalles de cada proveedor.
- Delegará descubrimiento y construcción a clases especializadas.

---

## Nuevas Clases Sugeridas

### `ProviderCatalog`
Responsable de listar y clasificar modelos de un proveedor.

```python
class ProviderCatalog:
    provider: LlmProvider

    def list_models(self) -> list[ModelConfig]:
        ...

    def refresh(self) -> None:
        ...
```

Implementaciones:
- `OllamaCatalog`
- `OpenAICatalog`
- `GeminiCatalog`
- `ClaudeCatalog`

Responsabilidades:
- Consultar API remota o local.
- Clasificar modelos como `chat`, `embedding` o `vlm`.
- Aplicar fallback estático si falla la consulta.
- No construir instancias LangChain ni Docling.

### `ModelFactory`
Responsable de construir objetos ejecutables a partir de `ModelConfig`.

```python
class ModelFactory:
    def create_llm(self, config: ModelConfig):
        ...

    def create_embeddings(self, config: ModelConfig):
        ...

    def create_vlm_options(self, config: ModelConfig, prompt: str):
        ...
```

Responsabilidades:
- Resolver `init_chat_model`.
- Resolver `init_embeddings`.
- Resolver `ChatOllama`.
- Resolver `ApiVlmOptions`.
- Validar incompatibilidades técnicas por categoría.

### `ProviderCredentials`
Responsable de leer credenciales de sesión.

```python
class ProviderCredentials:
    def get_api_key(self, provider: LlmProvider) -> str:
        ...

    def has_credentials(self, provider: LlmProvider) -> bool:
        ...
```

Por ahora puede seguir usando `os.environ`:
- Gemini -> `GOOGLE_API_KEY`
- OpenAI -> `OPENAI_API_KEY`
- Claude -> `ANTHROPIC_API_KEY`
- Ollama -> no requiere API key

### `ModelSelection`
Opcional, para explicitar la configuración simultánea activa.

```python
@dataclass
class ModelSelection:
    llm: ModelConfig
    embedding: ModelConfig
    vlm: ModelConfig
```

No es obligatorio si se mantienen `_llm_config`, `_embedding_config` y `_vlm_config`, pero ayuda a documentar que la selección es por categoría y no por proveedor global.

---

## Reglas de Independencia por Categoría

### LLM
Puede usar:
- Ollama
- Gemini
- OpenAI
- Claude

Construcción:
- Ollama -> `ChatOllama`
- Gemini/OpenAI/Claude -> `init_chat_model(config.model_id)`

### Embeddings
Puede usar:
- Ollama
- Gemini
- OpenAI

No usar:
- Claude, porque Anthropic no ofrece embeddings equivalentes compatibles con el flujo actual.

Construcción:
- Ollama -> `init_embeddings("ollama:{model_id}", base_url=...)`
- Gemini/OpenAI -> `init_embeddings(config.model_id)`

### VLM / OCR para PDF
Puede usar:
- Ollama, vía endpoint local compatible con OpenAI.
- Gemini, vía endpoint compatible configurado en `cloud_ip`.
- OpenAI, vía `https://api.openai.com/v1/chat/completions`.

No usar por ahora:
- Claude, porque el flujo actual usa `Docling ApiVlmOptions` y no un adaptador Anthropic Messages API.

Construcción:
- `ModelFactory.create_vlm_options(config, prompt)` debe validar provider + categoría antes de crear opciones.

---

## Catálogos Dinámicos por Proveedor

### Ollama
Endpoint:

```text
GET http://{local_ip}:11434/api/tags
```

Clasificación por nombre:
- `embed`, `embedding`, `nomic-embed`, `mxbai-embed`, `bge-`, `e5-` -> `embedding`
- `vision`, `llava`, `bakllava`, `minicpm-v`, `moondream`, `gemma3` -> `vlm`
- resto -> `chat`

### OpenAI
Endpoint:

```text
GET https://api.openai.com/v1/models
Authorization: Bearer $OPENAI_API_KEY
```

Clasificación:
- `text-embedding-*` -> `embedding`
- modelos de texto generativo -> `chat`
- modelos multimodales compatibles con imágenes -> también `vlm`

Nota:
- El mismo modelo OpenAI puede aparecer dos veces con categorías distintas si sirve como LLM y VLM.
- Para `chat` y `embedding`, usar prefijo compatible con LangChain si corresponde: `openai:{model_id}`.
- Para `vlm`, usar el ID esperado por `ApiVlmOptions`.

### Gemini
Endpoint:
- Usar API de listado de Google Generative Language.

Clasificación:
- modelos embedding -> `embedding`
- modelos generativos -> `chat`
- modelos multimodales -> `vlm`

Nota:
- Puede requerir normalización distinta para LangChain y para VLM Docling.

### Claude
Endpoint:

```text
GET https://api.anthropic.com/v1/models
x-api-key: $ANTHROPIC_API_KEY
anthropic-version: 2023-06-01
```

Clasificación:
- modelos Claude -> `chat`
- no crear `embedding`
- no crear `vlm` en esta etapa

---

## Cache y Fallback

Cada `ProviderCatalog` debe manejar cache por sesión:

```python
self._cache: list[ModelConfig] | None
self._last_error: str | None
self._source: Literal["remote", "static", "empty"]
```

Reglas:
- Si hay credencial, intentar remoto.
- Si remoto falla, usar estático.
- Si no hay credencial, usar estático.
- Si el proveedor no soporta una categoría, no inventar modelos.
- `list_models()` no debe lanzar por errores de red.

`ModelProvider` puede exponer información de estado opcional:

```python
def get_catalog_status(self, provider: LlmProvider) -> str:
    ...
```

Esto permitiría que la UI muestre:
- `Catálogo remoto cargado`.
- `Usando fallback estático`.
- `Proveedor sin credencial`.
- `Error remoto: ...`.

---

## Cambios en `ModelProvider`

### Constructor
Agregar dependencias opcionales con defaults internos:

```python
def __init__(..., catalogs: dict[LlmProvider, ProviderCatalog] | None = None, factory: ModelFactory | None = None):
```

Si no se inyectan, `ModelProvider` crea:
- `OllamaCatalog`
- `GeminiCatalog`
- `OpenAICatalog`
- `ClaudeCatalog`
- `ModelFactory`

### Estado activo
Mantener selección independiente:

```python
self._llm_config: ModelConfig
self._embedding_config: ModelConfig
self._vlm_config: ModelConfig
```

No introducir `current_provider` como verdad global. Si se mantiene por compatibilidad, debe documentarse como “provider del LLM activo”, no de toda la configuración.

### `list_models()`
Debe devolver la unión de catálogos:

```python
def list_models(self) -> list[ModelConfig]:
    models = []
    for catalog in self._catalogs.values():
        models.extend(catalog.list_models())
    return dedupe_models(models)
```

Deduplicación:
- clave: `(provider, model_id, category)`

### `get_llm()`
Delegar a factory:

```python
return self._factory.create_llm(self._llm_config)
```

### `get_embeddings()`
Delegar a factory:

```python
return self._factory.create_embeddings(self._embedding_config)
```

### `get_vlm_options()`
Delegar a factory:

```python
return self._factory.create_vlm_options(self._vlm_config, prompt)
```

---

## Cambios en UI PyQt

### Objetivo UI
La UI debe dejar claro que se configura por categoría, no por proveedor global.

Propuesta:
- Mantener un selector de proveedor para cargar credenciales/catálogo.
- Mantener tres combos separados:
  - LLM
  - Embeddings
  - VLM
- Cada combo debe mostrar modelos de todos los proveedores compatibles con esa categoría, no solo del provider seleccionado.

Ejemplo visual de opciones:

```text
Claude - claude-sonnet-4-6
OpenAI - gpt-5-mini
Ollama - llama3.2
```

Al seleccionar:
- LLM Claude
- Embeddings OpenAI
- VLM Ollama

La UI debe mostrar:

```text
LLM activo: Claude / claude-sonnet-4-6
Embeddings activos: OpenAI / text-embedding-3-large
VLM activo: Ollama / llava
```

### Entrada manual
Mantener combos editables.

Cuando el usuario escribe un modelo manual:
- Debe elegir provider y categoría.
- La UI crea `ModelConfig(provider, model_id, category)`.

Si se quiere evitar ambigüedad, agregar junto a cada combo un selector de provider por categoría:

```text
LLM provider: [Claude]      LLM model: [claude-sonnet-4-6]
Embedding provider: [OpenAI] Embedding model: [text-embedding-3-large]
VLM provider: [Ollama]       VLM model: [llava]
```

Esta es la opción recomendada porque hace explícita la independencia simultánea.

---

## Orden de Implementación

1. Crear módulo nuevo para catálogos, por ejemplo `core/model_catalogs.py`.
2. Definir `ProviderCatalog` base y clases `OllamaCatalog`, `OpenAICatalog`, `GeminiCatalog`, `ClaudeCatalog`.
3. Crear `core/model_factory.py` con `ModelFactory`.
4. Mover lógica de construcción desde `ModelProvider` hacia `ModelFactory`.
5. Mover lógica de listado/clasificación desde `ModelProvider` hacia catálogos.
6. Mantener `ModelProvider` como fachada con los mismos métodos públicos.
7. Ajustar `list_models()` para devolver todos los modelos de todos los catálogos.
8. Ajustar UI PyQt para poblar combos por categoría usando todos los proveedores compatibles.
9. Agregar selector de provider por categoría si los combos editables quedan ambiguos.
10. Añadir estados de catálogo por proveedor.
11. Probar combinaciones mixtas:
    - LLM Claude + embeddings OpenAI + VLM Ollama.
    - LLM Gemini + embeddings Ollama + VLM OpenAI.
    - LLM OpenAI + embeddings Gemini + VLM Gemini.

---

## Criterios de Aceptación

- La app permite activar proveedores distintos simultáneamente por categoría.
- `RefiService.evaluate()` no cambia su lógica de negocio.
- `RequirementsExtractor` sigue recibiendo `llm_ref`, `embedding_ref` y `vlm_options` ya resueltos.
- `ModelProvider.validate_for_agent()` sigue validando LLM + embeddings sin importar proveedor.
- `ModelProvider.validate_for_pdf_import()` sigue validando VLM sin importar proveedor.
- Claude puede seleccionarse como LLM mientras embeddings o VLM vienen de otro proveedor.
- Los errores de credencial/conexión son por proveedor y no bloquean otros proveedores ya configurados.
- Sin credenciales, la app conserva fallback estático y entrada manual.
- `list_models()` no rompe la UI aunque un proveedor remoto falle.

---

## Pruebas

### Unitarias o scripts simples
- `ModelProvider` con selección mixta:
  - `_llm_config.provider == CLAUDE`
  - `_embedding_config.provider == OPENAI`
  - `_vlm_config.provider == OLLAMA`
- `validate_for_agent()` pasa con LLM Claude + embeddings OpenAI.
- `validate_for_pdf_import()` pasa con VLM Ollama.
- `list_models()` deduplica por `(provider, model_id, category)`.
- Catálogos remotos caen a fallback si `requests.get` falla.
- `ModelFactory` rechaza Claude embeddings y Claude VLM con error de dominio claro.

### UI offscreen
- Cargar `ConfigPage`.
- Seleccionar modelos de proveedores diferentes por categoría.
- Confirmar que cada setter actualiza solo su categoría.
- Confirmar que cambiar provider para cargar credencial no borra modelos activos de otras categorías.

### Manual
- Configurar:
  - LLM: Claude Sonnet.
  - Embeddings: OpenAI `text-embedding-3-large`.
  - VLM: Ollama `llava`.
- Importar PDF.
- Ejecutar evaluación modo agente.
- Cambiar solo embeddings y repetir evaluación.
- Cambiar solo VLM y repetir importación PDF.

---

## Riesgos y Decisiones

- **No romper core:** mantener `ModelProvider` como fachada pública.
- **Separación real:** catálogos no construyen modelos; factory no lista modelos.
- **Claude VLM:** no soportarlo hasta implementar adaptador específico.
- **Claude embeddings:** no soportarlo porque Anthropic no ofrece servicio equivalente.
- **Provider global:** evitar usar un único provider global como estado de ejecución.
- **Credenciales:** mantener API keys en memoria de sesión, sin persistencia en disco.
- **Catálogo dinámico:** usar fallback estático para mantener UX estable.

---

## Resultado Esperado
La configuración de modelos queda verdaderamente modular: cada categoría puede usar un proveedor distinto al mismo tiempo, los catálogos se consultan dinámicamente cuando es posible, y la lógica de negocio sigue trabajando con capacidades abstractas en lugar de proveedores concretos.
