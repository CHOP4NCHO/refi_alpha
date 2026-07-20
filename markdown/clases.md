# Descripción de Paquetes del Sistema

El sistema está organizado como un núcleo modular que concentra la lógica principal de evaluación de fidelidad de requerimientos. Cada paquete cumple una responsabilidad específica dentro del flujo general: cargar el código fuente, obtener los requerimientos, evaluar su cumplimiento mediante modelos de IA, gestionar los resultados y centralizar la configuración de modelos y preferencias.

---

## `core`

El paquete `core` representa el núcleo de la aplicación. Agrupa los módulos funcionales principales del sistema y las clases transversales necesarias para ejecutar el proceso completo de evaluación.

Dentro de `core` se encuentran los paquetes encargados de leer la base de código, extraer requerimientos, ejecutar evaluaciones, administrar resultados y gestionar la configuración de modelos y preferencias del usuario.

Este paquete puede ser utilizado desde distintas interfaces externas, como una interfaz gráfica, una CLI o una API, sin que estas deban conocer los detalles internos de cada módulo.

Responsabilidades principales:

- Contener la lógica central del sistema.
- Agrupar los módulos funcionales reutilizables.
- Mantener separadas las responsabilidades de lectura, extracción, evaluación, configuración y gestión de resultados.
- Servir como base común para distintas formas de interacción con la aplicación.

---

## `services`

El paquete `services` agrupa servicios internos compartidos por varios módulos del sistema. Su función es centralizar responsabilidades transversales, especialmente la configuración de la aplicación y la gestión de modelos de inteligencia artificial.

Este paquete no representa un actor externo ni una interfaz de usuario. Forma parte del sistema y proporciona capacidades comunes a los demás paquetes.

Responsabilidades principales:

- Gestionar la configuración global de la aplicación.
- Administrar la configuración de modelos de IA.
- Centralizar el acceso a proveedores de modelos.
- Validar que los modelos necesarios estén disponibles para cada operación.
- Abstraer la diferencia entre proveedores cloud y proveedores locales o abiertos.

Clases principales:

- `AppSettings`
- `ModelProvider`
- `ModelConfig`
- `ModelVendor`
- `ModelCategory`

---

### `AppSettings`

`AppSettings` representa la configuración general de la aplicación. Puede modelarse como `Singleton` en una aplicación de escritorio de un solo usuario, ya que mantiene preferencias globales compartidas durante la ejecución.

Esta clase almacena parámetros por defecto relacionados con el entorno de trabajo, el modo de evaluación, la ubicación de guardado de reportes y el prompt base del sistema.

Responsabilidades principales:

- Mantener preferencias globales del usuario.
- Definir el directorio de trabajo por defecto.
- Definir el modo de evaluación por defecto.
- Definir la ubicación por defecto para guardar reportes.
- Definir el prompt de sistema utilizado por los modelos de IA.

---

### `ModelProvider`

`ModelProvider` es el servicio interno responsable de gestionar los modelos de inteligencia artificial utilizados por el sistema. No es un actor externo, sino una clase interna que abstrae la comunicación con proveedores reales de modelos.

Puede modelarse como `Singleton` si la aplicación es monousuario y de escritorio, porque mantiene una configuración activa única de modelos durante la ejecución.

Responsabilidades principales:

- Configurar el LLM activo.
- Configurar el modelo VLM activo.
- Configurar el modelo de embeddings activo.
- Validar si los modelos requeridos están disponibles.
- Entregar instancias de modelos a los módulos que las necesitan.
- Centralizar el acceso a proveedores cloud y proveedores locales.
- Ocultar a los módulos internos los detalles concretos de cada proveedor.

`ModelProvider` es utilizado principalmente por el evaluador y por el extractor de requerimientos.

---

### `ModelConfig`

`ModelConfig` representa la configuración de un modelo específico. Contiene información mínima para identificar qué modelo se utilizará, a qué proveedor pertenece y cuál es su categoría funcional.

Responsabilidades principales:

- Identificar el proveedor del modelo.
- Identificar el nombre o identificador del modelo.
- Indicar la categoría del modelo.
- Permitir validar si una configuración de modelo está completa.

Ejemplos de categorías:

- LLM
- VLM
- Embeddings

---

### `ModelVendor`

`ModelVendor` representa los proveedores de modelos soportados por el sistema. En el diseño lógico, estos proveedores pueden agruparse en proveedores cloud y proveedores locales o abiertos.

Ejemplos de proveedores cloud:

- Gemini
- OpenAI
- Anthropic

Ejemplos de proveedores locales o abiertos:

- Ollama
- llama.cpp
- LM Studio

En el diagrama de clases, `ModelVendor` puede representarse como una enumeración o como una abstracción de proveedor, según el nivel de detalle deseado.

---

## `codebase_reader`

El paquete `codebase_reader` se encarga de cargar, representar y consultar la base de código que será evaluada. Su responsabilidad es transformar un directorio de trabajo en una estructura navegable de archivos de código.

Este paquete no debe depender de los módulos de evaluación ni de extracción de requerimientos. Su función es independiente: leer y organizar archivos.

Responsabilidades principales:

- Cargar un directorio de trabajo.
- Representar una base de código.
- Identificar archivos relevantes.
- Leer contenido de archivos.
- Obtener fragmentos específicos de código.
- Construir una representación tipo árbol del proyecto.

Clases principales:

- `CodeBaseReader`
- `CodeBase`
- `CodeFile`
- `FileContent`

---

### `CodeBaseReader`

`CodeBaseReader` proporciona una interfaz de acceso para consultar una `CodeBase`. Permite navegar archivos, obtener directorios, leer archivos por índice o ruta, y construir una representación del árbol del proyecto.

Responsabilidades principales:

- Gestionar el acceso a una `CodeBase`.
- Obtener archivos específicos.
- Leer contenido de archivos.
- Generar la estructura del proyecto.
- Servir como fuente de información para el evaluador.

---

### `CodeBase`

`CodeBase` representa el repositorio o directorio de trabajo cargado por el sistema. Contiene la ruta raíz, un nombre descriptivo y la lista de archivos encontrados.

Responsabilidades principales:

- Representar el proyecto cargado.
- Mantener la lista de archivos de código.
- Aplicar reglas de exclusión o ignorados.
- Servir como contenedor de `CodeFile`.

Relación principal:

- Una `CodeBase` contiene cero o más `CodeFile`.

---

### `CodeFile`

`CodeFile` representa un archivo individual dentro de la base de código. Permite leer el contenido completo del archivo o recuperar fragmentos específicos por líneas.

Responsabilidades principales:

- Representar la ruta de un archivo.
- Leer el contenido crudo del archivo.
- Obtener el contenido estructurado por líneas.
- Obtener fragmentos de código específicos.

---

### `FileContent`

`FileContent` representa una línea individual de un archivo. Se utiliza para estructurar el contenido de un `CodeFile` en líneas numeradas.

Responsabilidades principales:

- Almacenar el número de línea.
- Almacenar el contenido textual de la línea.

---

## `requirements_extractor`

El paquete `requirements_extractor` se encarga de representar, cargar y extraer requerimientos. Puede recibir requerimientos manuales o generar un documento de requerimientos a partir de un archivo, como un PDF.

Este paquete depende de librerías externas como Docling para conversión documental y de modelos de IA para interpretar el contenido del documento.

Responsabilidades principales:

- Representar requerimientos individuales.
- Agrupar requerimientos en documentos.
- Extraer requerimientos desde documentos.
- Convertir documentos a contenido procesable.
- Utilizar modelos de IA para identificar requerimientos.
- Validar el tipo de requerimiento.

Clases principales:

- `Requirement`
- `ReqDocument`
- `RequirementExtractor`
- `RequirementType`

Dependencias externas:

- `Docling`
- `LangChain`

---

### `Requirement`

`Requirement` representa un requerimiento de software. Contiene un identificador, una descripción textual y un tipo.

Cada requerimiento puede ser gestionado individualmente o como parte de un `ReqDocument`.

Responsabilidades principales:

- Representar un requerimiento individual.
- Almacenar su identificador.
- Almacenar su descripción.
- Almacenar su tipo.
- Ser utilizado como unidad básica de evaluación.

---

### `RequirementType`

`RequirementType` representa la clasificación de un requerimiento. Puede modelarse como enumeración.

Tipos principales:

- `FUNCTIONAL`
- `NON_FUNCTIONAL`

Responsabilidades principales:

- Restringir los tipos válidos de requerimiento.
- Evitar valores arbitrarios o inconsistentes.
- Facilitar la validación del dominio.

---

### `ReqDocument`

`ReqDocument` representa un documento contenedor de requerimientos. Puede estar asociado a un archivo de origen y contiene una colección de `Requirement`.

Responsabilidades principales:

- Representar un documento de requerimientos.
- Almacenar la ruta del documento original.
- Almacenar el nombre del documento.
- Contener una lista de requerimientos.
- Permitir agregar o eliminar requerimientos.

Relación principal:

- Un `ReqDocument` contiene cero o más `Requirement`.

---

### `RequirementExtractor`

`RequirementExtractor` es responsable de extraer requerimientos desde documentos. Utiliza herramientas externas para convertir documentos y modelos de IA para interpretar el contenido extraído.

Responsabilidades principales:

- Cargar un documento de entrada.
- Convertir el documento a un formato procesable.
- Invocar modelos de IA para extraer requerimientos.
- Construir un `ReqDocument` con los requerimientos extraídos.
- Validar que los modelos requeridos estén disponibles.

Dependencias principales:

- Usa `Docling` para la conversión documental.
- Usa modelos obtenidos mediante `ModelProvider`.
- Puede usar componentes de `LangChain` para interactuar con modelos de lenguaje.

---

## `evaluator`

El paquete `evaluator` contiene la lógica de evaluación de requerimientos contra una base de código. Su función es determinar si los requerimientos definidos están satisfechos por el código analizado.

Este paquete utiliza modelos de IA, información de la base de código y los requerimientos cargados o extraídos.

Responsabilidades principales:

- Recibir una lista de requerimientos.
- Recibir archivos o contexto de código.
- Evaluar cada requerimiento.
- Ejecutar evaluación en modo pipeline o modo agente.
- Construir una revisión completa de fidelidad.
- Registrar consumo de tokens y metadatos de evaluación.

Clases principales:

- `Evaluator`
- `SingleRequirementEval`
- `ReqFidelityReview`
- `RAGToolSet`

Dependencias externas:

- `LangChain`

---

### `Evaluator`

`Evaluator` es el motor central de evaluación. Recibe requerimientos, contexto de código y modelos de IA para determinar si cada requerimiento está satisfecho.

Responsabilidades principales:

- Cargar requerimientos a evaluar.
- Cargar archivos de código como contexto.
- Ejecutar evaluación directa con LLM.
- Ejecutar evaluación mediante agente.
- Construir un vector store cuando se utiliza RAG.
- Producir resultados individuales de evaluación.
- Producir una revisión completa de evaluación.

Relaciones principales:

- Usa `Requirement`.
- Usa `CodeFile`.
- Usa modelos obtenidos desde `ModelProvider`.
- Produce `SingleRequirementEval`.
- Produce `ReqFidelityReview`.

---

### `RAGToolSet`

`RAGToolSet` agrupa herramientas utilizadas por el evaluador cuando trabaja en modo agente o con recuperación de información.

Puede modelarse como `Singleton` si las herramientas son compartidas durante una sesión de evaluación, aunque debe cuidarse que no conserve estado inválido cuando cambia el proyecto o la base de código.

Responsabilidades principales:

- Consultar la base de código mediante recuperación semántica.
- Leer líneas específicas de archivos.
- Obtener estructura de archivos.
- Verificar proximidad o cobertura de pruebas.
- Exponer herramientas para agentes de IA.

---

### `SingleRequirementEval`

`SingleRequirementEval` representa el resultado de evaluar un único requerimiento.

Responsabilidades principales:

- Conservar la descripción original del requerimiento.
- Registrar el razonamiento producido durante la evaluación.
- Indicar si el requerimiento fue cumplido o no.

---

### `ReqFidelityReview`

`ReqFidelityReview` representa el resultado completo de una evaluación. Agrupa los resultados individuales de cada requerimiento y conserva metadatos asociados a la ejecución.

Responsabilidades principales:

- Agrupar resultados individuales.
- Registrar fecha de evaluación.
- Registrar tokens de entrada y salida.
- Registrar modelo o proveedor utilizado.
- Registrar modo de evaluación.
- Registrar tiempo de respuesta.
- Servir como base para generar reportes.

Relación principal:

- Un `ReqFidelityReview` contiene cero o más `SingleRequirementEval`.

---

## `results_manager`

El paquete `results_manager` se encarga de administrar las evaluaciones guardadas y generar representaciones exportables o consultables de los resultados.

Responsabilidades principales:

- Guardar evaluaciones realizadas.
- Recuperar evaluaciones previas.
- Formatear evaluaciones.
- Exportar reportes.
- Administrar rutas y nombres de guardado por defecto.

Clases principales:

- `ResultManager`
- `ReviewFormatter`
- `StringFormatter`
- `JsonFormatter`

---

### `ResultManager`

`ResultManager` administra una colección de revisiones de fidelidad. Permite agregar nuevas evaluaciones, recuperar evaluaciones guardadas, formatearlas y persistirlas en archivos.

Responsabilidades principales:

- Mantener la lista de evaluaciones guardadas.
- Agregar nuevas revisiones.
- Recuperar una revisión por índice.
- Formatear una revisión.
- Guardar una revisión en disco.
- Usar diferentes estrategias de formateo.

Relaciones principales:

- Administra objetos `ReqFidelityReview`.
- Usa `ReviewFormatter` para formatear resultados.

---

### `ReviewFormatter`

`ReviewFormatter` representa una interfaz para definir estrategias de formateo de reportes.

Responsabilidades principales:

- Definir una operación común de formateo.
- Permitir múltiples formatos de salida.
- Desacoplar `ResultManager` del formato concreto del reporte.

Implementaciones principales:

- `StringFormatter`
- `JsonFormatter`

---

### `StringFormatter`

`StringFormatter` implementa el formateo de una evaluación como texto legible.

Responsabilidades principales:

- Generar reportes en formato textual.
- Producir una salida adecuada para lectura humana.
- Facilitar exportación simple a archivos `.txt`.

---

### `JsonFormatter`

`JsonFormatter` implementa el formateo de una evaluación como JSON.

Responsabilidades principales:

- Generar reportes estructurados.
- Facilitar integración con otras herramientas.
- Permitir almacenamiento o intercambio de resultados en formato machine-readable.

---

## Dependencias externas

El sistema utiliza librerías externas que no forman parte del núcleo y no se modelan como actores en diagramas de clases. Se representan como paquetes o componentes externos.

---

### `Docling`

`Docling` es una dependencia externa utilizada principalmente por `requirements_extractor`.

Responsabilidades dentro del sistema:

- Convertir documentos de entrada.
- Procesar archivos como PDFs.
- Entregar contenido documental en un formato que pueda ser interpretado por el extractor.

El sistema no controla internamente esta librería; solo depende de ella para la conversión documental.

---

### `LangChain`

`LangChain` es una dependencia externa utilizada para interactuar con modelos de lenguaje, embeddings, agentes y herramientas de recuperación.

Responsabilidades dentro del sistema:

- Proporcionar abstracciones para LLM.
- Proporcionar abstracciones para embeddings.
- Facilitar la creación de agentes.
- Facilitar la integración con vector stores.
- Permitir callbacks o seguimiento de tokens, si se utiliza.

El sistema depende de LangChain como infraestructura técnica, pero no lo considera parte del dominio.

---

### Proveedores externos de modelos

Los proveedores externos son entidades fuera del sistema que ofrecen modelos de inteligencia artificial. Son accedidos indirectamente mediante `ModelProvider`.

Se pueden clasificar en dos grupos:

### Cloud Providers

Proveedores alojados en la nube, por ejemplo:

- Gemini
- OpenAI
- Anthropic

### Local Providers

Proveedores locales o abiertos, por ejemplo:

- Ollama
- llama.cpp
- LM Studio

Estos proveedores no forman parte del núcleo de la aplicación. El sistema los utiliza a través de la capa de servicios internos encargada de gestionar modelos.

---

# Flujo general del sistema

El sistema recibe como entrada una base de código y un conjunto de requerimientos. La base de código es cargada por `codebase_reader`, mientras que los requerimientos pueden cargarse manualmente o extraerse desde documentos mediante `requirements_extractor`.

Luego, `evaluator` analiza los requerimientos contra el código utilizando modelos de IA proporcionados por `ModelProvider`. Como resultado, se genera un `ReqFidelityReview`, que contiene los resultados individuales de cada requerimiento evaluado.

Finalmente, `results_manager` administra la evaluación generada, permite revisarla posteriormente y exportarla como reporte en diferentes formatos.

El sistema mantiene configuraciones globales mediante `AppSettings` y centraliza la gestión de modelos mediante `ModelProvider`.
