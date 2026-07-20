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
|     Service Layer ◄────────┘                 |
|                                             |
+---------------------------------------------+
         │
         ▼
Cloud Providers / Local Providers
```

# Componentes del Dominio

## Codebase Reader

**Responsabilidad**

Realiza la lectura y análisis estructural del directorio de trabajo que
contiene el código fuente.

**Funciones principales**

-   Recorrido recursivo del proyecto.
-   Filtrado de archivos relevantes.
-   Exclusión de directorios ignorados (`.git`, `node_modules`, etc.).
-   Entrega del contenido fuente al evaluador.

**Dependencias**

-   Sistema de archivos.

**Salida**

-   Representación del código fuente que será utilizada durante la
    evaluación.

------------------------------------------------------------------------

## Requirements Extractor

**Responsabilidad**

Obtiene los requerimientos funcionales desde un documento de entrada.

**Funciones principales**

-   Conversión del documento a texto.
-   Uso de OCR cuando es necesario.
-   Extracción estructurada de requerimientos mediante LLM.
-   Validación del formato obtenido.

**Dependencias**

-   Service Layer para acceder al proveedor LLM.

**Salida**

-   Colección estructurada de requerimientos.

------------------------------------------------------------------------

## AI Evaluator

**Responsabilidad**

Constituye el núcleo de la aplicación y coordina el proceso de
evaluación entre los requerimientos y la base de código.

**Funciones principales**

-   Recibe el código fuente.
-   Recibe los requerimientos extraídos.
-   Construye los prompts.
-   Invoca los modelos de lenguaje.
-   Consolida las respuestas.
-   Calcula la fidelidad de implementación.

**Dependencias**

-   Codebase Reader.
-   Requirements Extractor.
-   Service Layer.

**Salida**

-   Resultado completo de la evaluación.

------------------------------------------------------------------------

## Results Manager

**Responsabilidad**

Gestiona la persistencia y presentación de los resultados generados
durante la evaluación.

**Funciones principales**

-   Organización de resultados.
-   Generación del reporte final.
-   Formateo de la salida.

**Salida**

-   Reporte final para el usuario.

# Capa de Servicios (Service Layer)

La **Service Layer** implementa el principio de **Separación de
Responsabilidades**, actuando como una capa de abstracción entre la
lógica de negocio y las tecnologías externas.

Su objetivo es evitar que los módulos del dominio dependan directamente
de APIs, SDKs o proveedores específicos de modelos de lenguaje.

## Model Provider

Encapsula la selección del proveedor de IA.

Permite utilizar distintos proveedores sin modificar la lógica de
negocio.

Ejemplos:

-   Google GenAI
-   OpenAI GPT
-   Anthropic Claude
-   Ollama

## LLM Communication

Centraliza toda la comunicación con modelos de lenguaje.

Responsabilidades:

-   Construcción de solicitudes.
-   Envío de prompts.
-   Manejo de respuestas.
-   Gestión de errores.
-   Reintentos.
-   Control de parámetros del modelo.

## User Settings

Centraliza la configuración definida por el usuario.

Ejemplos:

-   Modelo seleccionado.
-   Temperatura.
-   Proveedor.
-   Parámetros de inferencia.
-   Claves API.
-   Configuración de ejecución.

# Proveedores Externos

## Cloud Providers

Modelos consumidos mediante APIs remotas.

-   Google GenAI
-   OpenAI GPT
-   Anthropic Claude

## Local Providers

Modelos ejecutados en la máquina del usuario.

-   Ollama

# Flujo de Dependencias

``` text
Working Directory
        │
        ▼
Codebase Reader
        │
        ├───────────────┐
        ▼               │
                  AI Evaluator
        ▲               │
        │               ▼
Requirements Extractor
        │
        ▼
Service Layer
        │
        ▼
Model Providers
        │
        ▼
LLMs
        │
        ▼
Results Manager
        │
        ▼
Final Report
```

# Decisiones Arquitectónicas

-   **Alta cohesión:** cada módulo encapsula una única responsabilidad
    funcional.
-   **Bajo acoplamiento:** la interacción entre componentes ocurre
    mediante interfaces internas y la Service Layer.
-   **Inversión de dependencias:** los módulos del dominio desconocen la
    implementación concreta de los proveedores de IA.
-   **Extensibilidad:** nuevos proveedores, modelos o mecanismos de
    comunicación pueden incorporarse sin modificar el núcleo del
    sistema.
-   **Separación entre dominio e infraestructura:** la lógica de
    evaluación permanece aislada de detalles tecnológicos.
-   **Portabilidad:** el mismo núcleo funcional puede operar con modelos
    en la nube o locales mediante la misma interfaz de servicios.

En conjunto, esta organización facilita el mantenimiento y evolución del
sistema, permitiendo incorporar nuevas capacidades relacionadas con
modelos de lenguaje sin afectar los componentes responsables del
procesamiento del código fuente, la extracción de requerimientos o la
generación de resultados.
