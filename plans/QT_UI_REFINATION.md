# Cambios Solicitados
Debes implementar estos cambios sin romper la lógica de la Aplicación. Por esta vez, si necesitas hacer cambios en los módulos principales o en la lógica del servicio principal, házmelo saber y yo te autorizaré

## Aspectos Generales

### Sidebar
- Eliminar el subtexto de **"Requirements Fidelity"** y **"Prototype 2 (WIP)"**, dejando esos espacios en blanco.

### Apariencia
- Establecer el **modo claro como predeterminado**.
- Deshabilitar el botón para cambiar a modo oscuro.

### Widget de título por pestaña
- Definir estáticamente los límites de ancho de sus componentes.
- Evitar que el largo del título de la pestaña desplace el resto de los elementos del layout horizontal.

### Topbar de cada componente
- Eliminar el label de subtítulo.
- Reemplazarlo por un botón para visualizar información de uso de la pestaña actual.

### Widgets de estadísticas
- Eliminar los widgets de:
  - Archivos
  - Requisitos
  - Informe

---

## Pestaña 1: Workspace

### Widget de Working Tree
- Eliminar la columna **"Estado"**.
- Agregar dos tipos de iconos:
  - Directorios
  - Archivos
- Utilizar el mismo color de fuente para directorios y archivos (actualmente los archivos se visualizan más opacos).
- Ordenar los elementos de forma descendente por:
  1. Tipo
  2. Nombre
- Agregar funcionalidad de **Drag & Drop** para enviar archivos del proyecto al contexto desde la UI.

---

## Pestaña 2: Requerimientos

### Distribución
- Invertir el orden de aparición entre:
  - Widget **Importar desde PDF**
  - Widget **Nuevo Requerimiento**

### Widget de Nuevo Requerimiento
- Cambiar el label principal a:
  - **"Agregar Nuevo Requerimiento"**
- Permitir agregar un **ID opcional**, ubicado a la izquierda del texto del requerimiento.

### Widget de Requerimientos Actuales
- Permitir eliminar un requerimiento de la lista.
- Permitir cambiar el tipo de un requerimiento entre:
  - Funcional
  - No Funcional

---

## Pestaña 3: Evaluación

### Widget de Ejecutar Evaluación
- Mover aquí el componente de resumen ubicado actualmente en la cabecera:
  - Archivos
  - Requisitos
  - Informe
- Mostrar una vista previa con posibilidad de expandir para visualizar más detalles de las fases anteriores:
  - Workspace
  - Requerimientos
- Eliminar el label **"Lista para comenzar"**.

---

## Pestaña 4

### Widget de Comportamiento
- Cambiar el texto:
  - `"Modo debug"` → `"Modo Debug"`

### Widget de Modelos
- Agregar un tooltip para cada parámetro de configuración con una breve descripción de su función.
