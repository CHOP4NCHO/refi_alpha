# REFI ALPHA · PyQt6 UI

Interfaz alternativa y autónoma basada en PyQt6. No reemplaza la UI existente de
Tkinter; ambas consumen la misma instancia de `RefiService`.

## Ejecución

```bash
pip install PyQt6
python -m ui_pyqt
```

También puedes integrarla desde otro punto de entrada:

```python
from ui_pyqt import RefiMainWindow

window = RefiMainWindow(service=my_refi_service)
window.show()
```

Las extracciones de PDF y las evaluaciones se ejecutan mediante el pool de hilos de
Qt, manteniendo responsiva la ventana y entregando los resultados de vuelta al hilo
gráfico mediante señales.

## Edición visual

Los formularios están en `ui_pyqt/forms/` y se cargan directamente en tiempo de
ejecución. Puedes abrir cualquiera con Qt Designer, por ejemplo:

```bash
designer ui_pyqt/forms/main_window.ui
```

No es necesario ejecutar `pyuic6` después de guardarlos. Conserva los nombres de
objeto usados desde Python (por ejemplo `run_button`, `pages` o `info_button`) para
que sus señales y datos continúen conectados.
