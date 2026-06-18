from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk

class WorkingtreeTab(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app 
        self._build_ui()

    def _build_ui(self):
        # Configurar pesos para que la interfaz sea completamente responsiva
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)  # La fila 2 (paneles) se expande verticalmente

        # --- Fila 0: Información del Workspace ---
        ttk.Label(self, text="Espacio de Trabajo Actual:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        workspace_name = self.app.codebase.name if (hasattr(self.app, 'codebase') and self.app.codebase) else "Ninguno"
        self.lbl_workspace = ttk.Label(self, text=workspace_name, font=("Arial", 10, "bold"))
        self.lbl_workspace.grid(row=0, column=1, sticky="w", padx=10, pady=10)
        
        btn_change_ws = ttk.Button(self, text="Cambiar Directorio", command=self.set_worktree)
        btn_change_ws.grid(row=0, column=2, padx=10, pady=10)

        # --- Fila 1: Añadir por Ruta Manual (Conservando comportamiento original) ---
        lbl_add = ttk.Labelframe(self, text="Añadir Código Fuente por Ruta")
        lbl_add.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)
        lbl_add.columnconfigure(1, weight=1)

        ttk.Label(lbl_add, text="Ruta relativa:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.entry_filepath = ttk.Entry(lbl_add)
        self.entry_filepath.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.entry_filepath.bind("<Return>", lambda event: self.add_codefile()) # Ejecutar al pulsar Enter

        btn_add = ttk.Button(lbl_add, text="Añadir", command=self.add_codefile, bootstyle="secondary")
        btn_add.grid(row=0, column=2, padx=10, pady=10)

        # --- Fila 2: Panel Dividido de Archivos (Lado a Lado) ---
        panes_frame = ttk.Frame(self)
        panes_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
        panes_frame.columnconfigure(0, weight=1)
        panes_frame.columnconfigure(1, weight=1)
        panes_frame.rowconfigure(0, weight=1)

        # Subpanel Izquierdo: Árbol de Trabajo
        lbl_tree = ttk.Labelframe(panes_frame, text="Estructura del Proyecto (Click para añadir/quitar)")
        lbl_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        lbl_tree.columnconfigure(0, weight=1)
        lbl_tree.rowconfigure(0, weight=1)

        self.tree_workspace = ttk.Treeview(lbl_tree, show="tree", selectmode="none")
        self.tree_workspace.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=5)
        
        tree_scroll = ttk.Scrollbar(lbl_tree, orient="vertical", command=self.tree_workspace.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        self.tree_workspace.configure(yscrollcommand=tree_scroll.set)
        
        self.tree_workspace.bind("<ButtonRelease-1>", self.on_tree_click)

        # Subpanel Derecho: Contexto Seleccionado
        lbl_files = ttk.Labelframe(panes_frame, text="Archivos en Contexto (Doble click para quitar)")
        lbl_files.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
        lbl_files.columnconfigure(0, weight=1)
        lbl_files.rowconfigure(0, weight=1)

        self.listbox_files = tk.Listbox(lbl_files, highlightthickness=0, selectmode="browse")
        self.listbox_files.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=5)
        
        list_scroll = ttk.Scrollbar(lbl_files, orient="vertical", command=self.listbox_files.yview)
        list_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        self.listbox_files.configure(yscrollcommand=list_scroll.set)
        
        self.listbox_files.bind("<Double-Button-1>", self.on_listbox_remove)

        # Inicializar vistas
        self.update_workspace_tree()
        self.update_file_listbox()

    def add_codefile(self):
        """Permite escribir manualmente una ruta relativa o directorio para indexarlo."""
        selected_path = self.entry_filepath.get().strip()
        if not selected_path:
            messagebox.showwarning("Advertencia", "Debes ingresar una ruta válida.")
            return

        if not hasattr(self.app, 'codebase') or not self.app.codebase:
            messagebox.showerror("Error", "No hay un espacio de trabajo activo.")
            return

        try:
            base_path = Path(self.app.codebase.path)
            complete_path = base_path / selected_path

            if complete_path.is_dir():
                added = 0
                for file_path in complete_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            # Buscar el CodeFile existente dentro del codebase para mantener referencias
                            codefile = next(f for f in self.app.codebase.files if Path(f.path) == file_path)
                            if codefile not in self.app.file_context:
                                self.app.file_context.append(codefile)
                                added += 1
                        except StopIteration:
                            pass
                self.app.log_message(f"Directorio agregado recursivamente: {selected_path} ({added} archivos)")
            else:
                try:
                    codefile = next(f for f in self.app.codebase.files if Path(f.path) == complete_path)
                    if codefile not in self.app.file_context:
                        self.app.file_context.append(codefile)
                        self.app.log_message(f"Archivo agregado: {selected_path}")
                    else:
                        self.app.log_message(f"El archivo ya está en el contexto: {selected_path}")
                except StopIteration:
                    messagebox.showerror("Error", f"El archivo '{selected_path}' no se encuentra en el CodeBase actual o su extensión no está permitida.")
                    return

            # Sincronizar ambas listas visuales inmediatamente
            self.update_file_listbox()
            self.sync_tree_states()
            self.entry_filepath.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error", f"Error agregando archivo: {str(e)}")

    def update_workspace_tree(self):
        """Reconstruye por completo el árbol jerárquico según el CodeBase."""
        self.tree_workspace.delete(*self.tree_workspace.get_children())
        if not hasattr(self.app, 'codebase') or not self.app.codebase:
            return

        base_path = Path(self.app.codebase.path)
        nodes = {"": ""} 

        try:
            sorted_files = sorted(self.app.codebase.files, key=lambda f: str(f.path))
        except Exception:
            sorted_files = self.app.codebase.files

        for file_obj in sorted_files:
            try:
                rel_path = Path(file_obj.path).relative_to(base_path)
            except ValueError:
                continue

            parts = rel_path.parts
            current_rel = Path()
            parent_id = ""

            for part in parts[:-1]:
                current_rel = current_rel / part
                current_rel_str = str(current_rel)
                if current_rel_str not in nodes:
                    node_id = self.tree_workspace.insert(parent_id, "end", text=f"📁 {part}", open=False)
                    nodes[current_rel_str] = node_id
                parent_id = nodes[current_rel_str]

            filename = parts[-1]
            in_context = file_obj in self.app.file_context
            prefix = "✅ " if in_context else "📄 "

            self.tree_workspace.insert(
                parent_id,
                "end",
                text=f"{prefix}{filename}",
                values=(str(file_obj.path),)
            )

    def sync_tree_states(self, parent=""):
        """Recorre de forma rápida el árbol visual para reflejar los cambios hechos manualmente."""
        for item_id in self.tree_workspace.get_children(parent):
            values = self.tree_workspace.item(item_id, "values")
            if values:  
                file_path_str = values[0]
                in_context = any(str(f.path) == file_path_str for f in self.app.file_context)
                prefix = "✅ " if in_context else "📄 "
                filename = Path(file_path_str).name
                self.tree_workspace.item(item_id, text=f"{prefix}{filename}")
            else:  
                self.sync_tree_states(item_id)

    def update_file_listbox(self):
        """Actualiza el listado plano de archivos activos a la derecha."""
        self.listbox_files.delete(0, tk.END)
        base_path = Path(self.app.codebase.path) if (hasattr(self.app, 'codebase') and self.app.codebase) else None
        
        for index, file_obj in enumerate(self.app.file_context, start=1):
            if base_path:
                try:
                    display_path = Path(file_obj.path).relative_to(base_path)
                except ValueError:
                    display_path = Path(file_obj.path).name
            else:
                display_path = Path(file_obj.path).name
                
            self.listbox_files.insert(tk.END, f"{index}. {display_path}")

    def set_worktree(self):
        """Cambia el directorio raíz del espacio de trabajo."""
        selected_path = filedialog.askdirectory(title="Selecciona el nuevo espacio de trabajo")
        if not selected_path:
            self.app.log_message("Cambio de espacio de trabajo cancelado.")
            return

        try:
            path = Path(selected_path)
            name = path.name
            
            from codebase_reader.codebase import CodeBase
            self.app.codebase = CodeBase(path=selected_path, name=name)
            if hasattr(self.app, 'codebase_reader') and self.app.codebase_reader:
                self.app.codebase_reader.codebase = self.app.codebase
            
            self.lbl_workspace.config(text=name)
            self.app.log_message(f"Espacio de trabajo cambiado a: {name}")
            
            self.app.file_context.clear()
            self.update_workspace_tree()
            self.update_file_listbox()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.app.log_message(f"Error cambiando workspace: {e}")

    def on_tree_click(self, event):
        """Alterna el estado de un archivo al hacer click en el árbol."""
        item_id = self.tree_workspace.identify_row(event.y)
        if not item_id:
            return
        
        values = self.tree_workspace.item(item_id, "values")
        if not values:
            return 

        file_path_str = values[0]
        file_obj = None
        
        for f in self.app.codebase.files:
            if str(f.path) == file_path_str:
                file_obj = f
                break
                
        if file_obj:
            if file_obj in self.app.file_context:
                self.app.file_context.remove(file_obj)
                self.app.log_message(f"Quitado del contexto: {Path(file_path_str).name}")
            else:
                self.app.file_context.append(file_obj)
                self.app.log_message(f"Añadido al contexto: {Path(file_path_str).name}")
                
            in_context = file_obj in self.app.file_context
            prefix = "✅ " if in_context else "📄 "
            filename = Path(file_path_str).name
            self.tree_workspace.item(item_id, text=f"{prefix}{filename}")
            
            self.update_file_listbox()

    def on_listbox_remove(self, event):
        """Quita un archivo del contexto al hacer doble click en la lista derecha."""
        selection = self.listbox_files.curselection()
        if not selection:
            return
        
        index = selection[0]
        if 0 <= index < len(self.app.file_context):
            removed_file = self.app.file_context.pop(index)
            self.app.log_message(f"Quitado del contexto: {Path(removed_file.path).name}")
            
            self.update_file_listbox()
            self.sync_tree_states()