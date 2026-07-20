# Plan de Mejora UI/UX — `ui_pyqt/`

> **IMPORTANTE:** Este es un plan de referencia. No ejecutar sin autorización explícita.

---

## Fase 0: Capa de Personalización CSS (NUEVA)

| Paso | Capa | Archivo | Acción |
|------|------|---------|--------|
| 0.1 | **UI** | Nuevo `ui_pyqt/theme_manager.py` | Crear `ThemeManager` con load/save/toggle/apply/get_palette_color |
| 0.2 | **UI** | Nuevo `~/.refi/config.json` | Archivo de config: `{"mode": "light"}` |
| 0.3 | **UI** | `ui_pyqt/__main__.py` | Crear `ThemeManager()`, pasarlo a `RefiMainWindow` |
| 0.4 | **UI** | `ui_pyqt/main_window.py:48` | Reemplazar `self.setStyleSheet(LIGHT_STYLESHEET)` → `theme_manager.apply_to(self)` |
| 0.5 | **UI** | `ui_pyqt/main_window.py:65-68` | Conectar `theme_button` → `theme_manager.toggle()` + `apply_to(self)` + actualizar texto |
| 0.6 | **UI** | `ui_pyqt/evaluation_page.py:128-136` | CSS inline `model_status` → `theme_manager.get_palette_color()` |
| 0.7 | **UI** | `ui_pyqt/evaluation_page.py:162-165` | CSS inline HTML resultados → colores de `theme_manager` |
| 0.8 | **UI** | `ui_pyqt/evaluation_page.py:82` | CSS inline empty state → `theme_manager.get_palette_color("text_muted")` |
| 0.9 | **UI** | `ui_pyqt/workspace_page.py:88,101` | `QColor("#26384a")` → `QColor(theme_manager.get_palette_color("text"))` |
| 0.10 | **UI** | `forms/main_window.ui:241` | Quitar `enabled=false` de `theme_button` |
| 0.11 | **UI** | `ui_pyqt/config_page.py` | Agregar combo "Tema" (Claro/Oscuro) que llame a `theme_manager.toggle()` |
| — | **core** | — | Sin cambios en core/ |

### Diseño de ThemeManager

**Archivo de configuración: `~/.refi/config.json`**

```json
{
  "mode": "dark"
}
```

**QSS custom del usuario: `~/.refi/style.qss`** (opcional)

El usuario puede crear este archivo para sobreescribir estilos. Se appendea al stylesheet base:

```qss
/* Personalización del usuario */
QPushButton[primary="true"] {
    background: #8b5cf6;
    border-color: #8b5cf6;
    border-radius: 20px;
}
```

**Estructura de `theme_manager.py`:**

```python
class ThemeManager:
    _USER_DIR = Path("~/.refi").expanduser()
    _CONFIG_FILE = _USER_DIR / "config.json"
    _CUSTOM_QSS_FILE = _USER_DIR / "style.qss"

    LIGHT_COLORS = {
        "text": "#243447",
        "text_muted": "#6f8093",
        "background": "#f4f7fb",
        "surface": "#ffffff",
        "border": "#dce4ee",
        "accent": "#168f76",
        "accent_hover": "#117963",
        "warning_bg": "#fff4c2",
        "warning_text": "#765a00",
        "info_bg": "#f5f8fb",
        "info_text": "#294057",
    }

    DARK_COLORS = {
        "text": "#dbe7f4",
        "text_muted": "#7f93aa",
        "background": "#08111f",
        "surface": "#0f1c2e",
        "border": "#20324a",
        "accent": "#63e6be",
        "accent_hover": "#7cebc9",
        "warning_bg": "#422006",
        "warning_text": "#fbbf24",
        "info_bg": "#1e293b",
        "info_text": "#e2e8f0",
    }

    def __init__(self):
        self._mode = "light"
        self._custom_qss = ""
        self._load()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_dark(self) -> bool:
        return self._mode == "dark"

    @property
    def t(self) -> dict:
        """Tokens activos para acceso rápido."""
        return self.DARK_COLORS if self._mode == "dark" else self.LIGHT_COLORS

    def toggle(self) -> str:
        self._mode = "dark" if self._mode == "light" else "light"
        self._save()
        return self._mode

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._save()

    def apply_to(self, widget: QWidget) -> None:
        base = DARK_STYLESHEET if self._mode == "dark" else LIGHT_STYLESHEET
        final = base + "\n" + self._custom_qss
        widget.setStyleSheet(final)

    def get_palette_color(self, token: str) -> str:
        palette = self.DARK_COLORS if self._mode == "dark" else self.LIGHT_COLORS
        return palette.get(token, "#ff00ff")

    def reload_custom_qss(self) -> None:
        if self._CUSTOM_QSS_FILE.exists():
            self._custom_qss = self._CUSTOM_QSS_FILE.read_text(encoding="utf-8")
        else:
            self._custom_qss = ""

    def _load(self) -> None:
        self._USER_DIR.mkdir(parents=True, exist_ok=True)
        if self._CONFIG_FILE.exists():
            data = json.loads(self._CONFIG_FILE.read_text())
            self._mode = data.get("mode", "light")
        self.reload_custom_qss()

    def _save(self) -> None:
        self._USER_DIR.mkdir(parents=True, exist_ok=True)
        self._CONFIG_FILE.write_text(json.dumps({"mode": self._mode}, indent=2))
```

**Flujo de carga:**

```
1. App arranca
2. ThemeManager lee ~/.refi/config.json → obtiene "mode": "dark"
3. ThemeManager carga DARK_STYLESHEET como base
4. Si existe ~/.refi/style.qss → lo lee y APPENDEA al stylesheet base
5. apply_to(window) aplica el QSS resultante
6. El usuario puede:
   - Editar ~/.refi/style.qss para personalizar
   - Cambiar mode desde la UI (toggle light/dark)
```

---

## Fase 1: Dark Theme funcional

| Paso | Capa | Archivo | Acción |
|------|------|---------|--------|
| 1.1 | **UI** | `ui_pyqt/theme.py` | Agregar reglas faltantes al `DARK_STYLESHEET`: `QStatusBar`, `QDialog`, `QMessageBox`, `QFileDialog` |
| 1.2 | **UI** | `ui_pyqt/theme_manager.py` | Asegurar que `LIGHT_COLORS` y `DARK_COLORS` tengan todos los tokens necesarios |
| 1.3 | **UI** | Todos los pages | Wrapper `_show_messagebox(type, title, text)` que aplique `setStyleSheet()` al QMessageBox antes de mostrarlo (workaround Qt) |
| 1.4 | **UI** | `ui_pyqt/evaluation_page.py:128-136` | `model_status` CSS → palette dinámica (complemento a 0.6) |
| 1.5 | **UI** | `ui_pyqt/workspace_page.py:88,101` | Confirmar que colores de tree items funcionan en dark |
| — | **core** | — | Sin cambios en core/ |

### Problemas conocidos del dark theme

1. **QMessageBox/QDialog nativos no respetan el QSS** — Usar `QMessageBox.setStyleSheet()` antes de `exec()` o reemplazar por `QDialog` custom
2. **Colores hardcodeados en `workspace_page.py:88,101`** — `QColor("#26384a")` no funciona en dark
3. **CSS inline en `evaluation_page.py:162-165`** — Colores fijos que no se adaptan al tema
4. **`model_status` CSS inline en `evaluation_page.py:128-136`** — Colores hardcodeados
5. **StatusBar sin estilos** — Agregar `QStatusBar` al QSS

---

## Fase 2: Progreso real en evaluaciones

| Paso | Capa | Archivo | Acción |
|------|------|---------|--------|
| 2.1 | **core** | `core/evaluator_agent/evaluator.py` | Agregar `progress_callback: Callable[[int, int], None] \| None = None` a `eval_requirement_agent()` y `eval_requirement_llm()`. Emitir después de cada requerimiento evaluado. |
| 2.2 | **core** | `core/evaluator_agent/evaluation_runner.py` | Pasar `progress_callback` desde `perform_agent_evaluation()` y `perform_pipeline_evaluation()` |
| 2.3 | **core** | `core/refi_service.py` | Agregar parámetro `progress_callback` a `evaluate()` y pasarlo a los runners |
| 2.4 | **UI** | `ui_pyqt/workers.py` | Agregar signal `progress = pyqtSignal(int, int)` a `WorkerSignals` |
| 2.5 | **UI** | `ui_pyqt/main_window.py` | Crear lambda `progress_cb` que emita `worker.signals.progress` y pasarlo a `service.evaluate(progress_callback=...)` |
| 2.6 | **UI** | `ui_pyqt/evaluation_page.py` | Método `update_progress(current, total)` que cambie `QProgressBar` a modo determinado (0-100), actualice valor y muestre "Evaluando 3/12..." |
| 2.7 | **core** | `core/requirements_extractor/extractor.py` | Agregar `progress_callback` a `get_requirements()` para progreso de conversión PDF |
| 2.8 | **UI** | `forms/evaluation_page.ui` | Agregar `QLabel` junto a `progress` para texto descriptivo |
| 2.9 | **UI** | `ui_pyqt/main_window.py` | Conectar `worker.signals.progress` a `evaluation_page.update_progress()` |

### Cambios en core/

**`evaluator.py`** — Agregar progress_callback:

```python
def eval_requirement_agent(
    self,
    requirement: Requirement,
    log_callback=None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> SingleRequirementEval:
    # ... evaluación existente ...
    if progress_callback:
        progress_callback(current_index, total_requirements)
```

**`evaluation_runner.py`** — Pasar callback:

```python
def perform_agent_evaluation(
    evaluator,
    requirements,
    log_callback=None,
    progress_callback=None,
):
    for index, req in enumerate(requirements):
        result = evaluator.eval_requirement_agent(
            req,
            log_callback=log_callback,
        )
        if progress_callback:
            progress_callback(index + 1, len(requirements))
```

**`refi_service.py`** — Agregar parámetro:

```python
def evaluate(self, log_callback=None, progress_callback=None):
    # ...
    perform_agent_evaluation(
        evaluator=self._evaluator,
        requirements=...,
        log_callback=log_callback,
        progress_callback=progress_callback,
    )
```

### Cambios en UI/

**`workers.py`** — Nuevo signal:

```python
class WorkerSignals(QObject):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(object, str)
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # NUEVO: (current, total)
    finished = pyqtSignal()
```

**`evaluation_page.py`** — Progreso visible:

```python
def update_progress(self, current: int, total: int) -> None:
    self.progress.setMaximum(total)
    self.progress.setValue(current)
    self.progress_label.setText(f"Evaluando {current}/{total}...")

def set_busy(self, busy: bool) -> None:
    self.run_button.setEnabled(not busy)
    self.progress.setVisible(busy)
    self.progress_label.setVisible(busy)
    if not busy:
        self.progress.setMaximum(0)  # Reset a indeterminado
        self.progress_label.setText("")
    self.run_button.setText("…  Evaluación en curso" if busy else "▶  Iniciar evaluación")
```

---

## Fase 3: Búsqueda y filtros

| Paso | Capa | Archivo | Acción |
|------|------|---------|--------|
| 3.1 | **UI** | `forms/workspace_page.ui` | Agregar `QLineEdit` con placeholder "Filtrar archivos..." encima del `QTreeWidget` |
| 3.2 | **UI** | `ui_pyqt/workspace_page.py` | Conectar `QLineEdit.textChanged` a filtrado del árbol con `QTreeWidgetItemIterator` — match case-insensitive contra nombre de archivo |
| 3.3 | **UI** | `forms/requirements_page.ui` | Agregar `QLineEdit` con placeholder "Filtrar requerimientos..." encima de la tabla |
| 3.4 | **UI** | `ui_pyqt/requirements_page.py` | Conectar `QLineEdit.textChanged` a filtrado de la tabla — match contra ID y descripción |
| 3.5 | **UI** | `ui_pyqt/workspace_page.py` | Hacer refresh incremental: en vez de `tree.clear()` + reconstruir, comparar items existentes y agregar/quitar solo diferencias |
| — | **core** | — | Sin cambios en core/ |

### Filtrado del árbol (3.2)

```python
def _filter_tree(self, text: str) -> None:
    text = text.lower()
    iterator = QTreeWidgetItemIterator(self.tree)
    while iterator.value():
        item = iterator.value()
        path_string = item.data(0, Qt.ItemDataRole.UserRole)
        if path_string:
            # Es archivo: ocultar/mostrar según match
            visible = text in Path(path_string).name.lower() if text else True
            item.setHidden(not visible)
        else:
            # Es directorio: mostrar si tiene hijos visibles
            has_visible = any(
                not item.child(i).isHidden() for i in range(item.childCount())
            )
            item.setHidden(not has_visible and bool(text))
        iterator += 1
```

### Filtrado de tabla (3.4)

```python
def _filter_table(self, text: str) -> None:
    text = text.lower()
    for row in range(self.table.rowCount()):
        id_item = self.table.item(row, 0)
        desc_item = self.table.item(row, 2)
        id_match = text in id_item.text().lower() if id_item else False
        desc_match = text in desc_item.text().lower() if desc_item else False
        self.table.setRowHidden(row, not (id_match or desc_match) if text else False)
```

---

## Fase 5: UX polish

| Paso | Capa | Archivo | Acción |
|------|------|---------|--------|
| 5.1 | **UI** | `ui_pyqt/main_window.py:107-108` | No ocultar sidebar automáticamente después de `show_page()` en modo compact |
| 5.2 | **UI** | `ui_pyqt/workspace_page.py:189-199` | Antes de `set_workdir()`, si `file_context` o `get_requirements()` no están vacíos, mostrar `QMessageBox.question` de confirmación |
| 5.3 | **UI** | `ui_pyqt/evaluation_page.py:38` | Mostrar `state_label` con texto descriptivo ("Lista para comenzar" / "Evaluando...") en vez de ocultarlo |
| 5.4 | **UI** | `ui_pyqt/evaluation_page.py` | Botón "Exportar" con `QFileDialog.getSaveFileName` → exportar review a JSON |
| 5.5 | **UI** | Todos los pages | Extraer helper `_populate_combo(combo, items, current)` para el patrón de refill repetido |
| 5.6 | **UI** | Todos los pages | Extraer helper `_safe_operation(fn, error_title)` para el patrón `try/except → QMessageBox` |
| 5.7 | **core** | `core/refi_service.py` | Renombrar `_update_evaluator_llm()` → `update_evaluator_llm()` y `_reset_requirements_extractor()` → `reset_requirements_extractor()` (quitar `_` de métodos públicos) |

### Código duplicado a refactorizar

**Helper `_populate_combo` (5.5):**

```python
def _populate_combo(combo: QComboBox, items: list[tuple[str, any]], current=None) -> None:
    combo.blockSignals(True)
    combo.clear()
    for label, data in items:
        combo.addItem(label, data)
    if current is not None:
        for index in range(combo.count()):
            if combo.itemData(index) == current:
                combo.setCurrentIndex(index)
                break
    combo.blockSignals(False)
```

**Helper `_safe_operation` (5.6):**

```python
def _safe_operation(parent: QWidget, fn, error_title: str = "Error"):
    try:
        return fn()
    except Exception as error:
        QMessageBox.critical(parent, error_title, str(error))
        return None
```

### Métodos a renombrar en core/ (5.7)

| Antes | Después | Archivo |
|-------|---------|---------|
| `_update_evaluator_llm()` | `update_evaluator_llm()` | `refi_service.py` |
| `_reset_requirements_extractor()` | `reset_requirements_extractor()` | `refi_service.py` |

Actualizado en `config_page.py:129,140,151`:
- `self.service._update_evaluator_llm()` → `self.service.update_evaluator_llm()`
- `self.service._reset_requirements_extractor()` → `self.service.reset_requirements_extractor()`

---

## Resumen de capas por fase

| Fase | Capas modificadas | Archivos core/ | Archivos ui_pyqt/ |
|------|-------------------|----------------|-------------------|
| 0 | UI solamente | 0 | 8 archivos + 1 nuevo + 1 .ui |
| 1 | UI solamente | 0 | 4 archivos + 1 .ui |
| 2 | **core + UI** | 3 archivos | 4 archivos + 1 .ui |
| 3 | UI solamente | 0 | 4 archivos + 2 .ui |
| 5 | **core + UI** | 1 archivo | 5 archivos |

## Orden de ejecución recomendado

```
0. ThemeManager + integración
1. Dark theme funcional
5.7 (renombrar métodos core — primero para desbloquear 5.5-5.6)
5.5 + 5.6 (helpers refactor)
5.1-5.4 (UX polish)
2. Progreso real (core + UI)
3. Filtros
```

## Estimación de esfuerzo

| Fase | Días |
|------|------|
| 0. Capa de personalización | 2-3 |
| 1. Dark theme | 1-2 |
| 2. Progreso real | 2-3 |
| 3. Filtros | 1 |
| 5. UX polish | 1-2 |
| **Total** | **~7-11 días** |
