# REFI ALPHA

REFI ALPHA es una aplicación de escritorio que evalúa qué tan bien un repositorio de código implementa un conjunto de requisitos de software. A partir de un PDF con la especificación y un directorio de código fuente, la aplicación extrae los requisitos, indexa la base de código y emite un veredicto por cada requisito usando un agente de IA.


## Qué hace

1. Carga un repositorio de código fuente
2. Indica los requerimientos funcionales y no funcionales cargando un documento asociado a los requerimientos del código fuente a auditar. 
3. Ejecuta una evaluación asistida por IA en dos modos principales: Pipeline Lineal (copiando el contenido del repositorio como *HumanMessage*) y Agente RAG (utilizando herramientas y embebiendo el código fuente en una bd vectorial)
4. Permite revisar y exportar resultados realizados durante la sesión

## Arquitectura

La aplicación está organizada como un monolito modular: un único proceso con módulos de responsabilidad bien definida y bajo acoplamiento.

### Componentes principales:

- **Codebase Reader**: recorre el directorio de trabajo, filtra archivos por extensión y entrega una representación del código al evaluador.
- **Requirements Extractor**: convierte el PDF a texto (con OCR cuando hace falta) y extrae los requisitos en un formato estructurado.
- **AI Evaluator**: núcleo del sistema. Orquesta el cruce entre requisitos y código, construye los prompts, invoca al LLM y consolida los veredictos.
- **Results Manager**: persiste y formatea los resultados de cada evaluación.
- **Models**: capa de abstracción sobre los proveedores de IA. Centraliza la comunicación con los modelos, la configuración del usuario y la selección del proveedor.

### Importante sobre la evaluación

- **Gestión de memoria**: el índice vectorial del código vive en RAM. Tras cada evaluación se libera con `clear_vector_store()`;
- **Recursión en uso de Tools**: El modo Agente RAG utiliza funciones (tools) de manera no determinista, por lo que fue colocado un límite de **25** calls para evitar un gasto excesivo de tokens de salida.


### Modelos utilizados

Dentro de la Aplicación actualmente se utilizan tres tipos de modelos:
- **LLM**: Para responder a las consultas del módulo de *AI EVALUATOR* y para extraer los requerimientos del Documento de Requerimientos una vez transformados de PDF a MD
- **VLM**: Necesario para aplicar visión sobre los Documentos PDF de los cuales se extraerán los requerimientos
- **Embedding**: Necesario para el *Modo Agente RAG (opción por defecto de evaluación)* Se encarga de guardar en una base de datos vectorial el código fuente a analizar.  

### UI / UX

Todo el código se comunica con el archivo principal *core/refi_service.py*, el cual sirve como punto de entrada para cualquier interfaz de usuario que desee acceder al funcionamiento del sistema. A esto se le conoce como patrón Facade, haciendo que la lógica de negocio sea replicable en cualquier interfaz gráfica o paradigma.

Actualmente está disponible el módulo **ui_pyqt**, que utiliza PyQt6 como Framework de UI


## Ejecución rápida (desde código fuente)

Requisitos: Python 3.10 o superior.

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt

# Interfaz principal (PyQt6)
python -m ui_pyqt

# Interfaz alternativa (Tkinter)
python main.py
```

## Configuración

Las claves de API y la configuración del proveedor son guardadas en memoria durante la ejecución de la aplicación. Para asegurar persistencia es necesario habilitar la carga de datos de archivos .env agregando la función load_dotenvs() en la interfaz de usuario.

```
GOOGLE_API_KEY=tu_clave
OPENAI_API_KEY=tu_clave
ANTHROPIC_API_KEY=tu_clave
```

## Compilación (empaquetado con PyInstaller)

El proyecto incluye scripts de build que crean un ejecutable autocontenido. La compilación es idéntica en concepto en ambos sistemas: crea un entorno virtual, instala dependencias, configura el `.env` si no existe y empaqueta con PyInstaller en modo `--onedir`.

### Linux

```bash
chmod +x build.sh
./build.sh
```

El ejecutable queda en `dist/refi-alpha/refi-alpha`.

Para ejecutarlo:

```bash
cd dist/refi-alpha
./refi-alpha
```

### Windows

Desde una terminal (cmd o PowerShell):

```bat
build.bat
```

El ejecutable queda en `dist\refi-alpha\refi-alpha.exe`.

Para ejecutarlo:

```bat
cd dist\refi-alpha
refi-alpha.exe
```

Notas sobre la compilación:

- El primer build puede tardar varios minutos por el tamaño de las dependencias (especialmente `docling`).
- El directorio `dist/refi-alpha` es completamente portable: pudiendose copiar a otra máquina del mismo sistema operativo sin necesidad de instalar Python.
- En Windows, es necesario tener Python 3.10+ en el PATH para proceder a la compilación.





## Aviso importante sobre los modelos

El correcto funcionamiento de este software está supeditado a la calidad de los modelos que se utilicen. La evaluación de fidelidad la realiza un LLM, por lo que los resultados (precisión, razonamiento, veredictos) dependen directamente del modelo elegido y de su capacidad de seguir instrucciones estructuradas.

Los proveedores soportados actualmente son:

- Google GenAI (Gemini)
- OpenAI
- Anthropic (Claude)
- Ollama (modelos locales)

