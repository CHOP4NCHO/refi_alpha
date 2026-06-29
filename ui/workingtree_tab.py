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
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        # --- Row 0: Workspace info ---
        ttk.Label(self, text="Espacio de Trabajo Actual:").grid(row=0, column=0, sticky="w", padx=10, pady=10)

        workspace_name = self.app.service.codebase.name if self.app.service.codebase else "Ninguno"
        self.lbl_workspace = ttk.Label(self, text=workspace_name, font=("Arial", 10, "bold"))
        self.lbl_workspace.grid(row=0, column=1, sticky="w", padx=10, pady=10)

        btn_change_ws = ttk.Button(self, text="Cambiar Directorio", command=self.set_worktree)
        btn_change_ws.grid(row=0, column=2, padx=10, pady=10)

        # --- Row 1: Manual path entry ---
        lbl_add = ttk.Labelframe(self, text="Añadir Código Fuente por Ruta")
        lbl_add.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)
        lbl_add.columnconfigure(1, weight=1)

        ttk.Label(lbl_add, text="Ruta relativa:").grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.entry_filepath = ttk.Entry(lbl_add)
        self.entry_filepath.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.entry_filepath.bind("<Return>", lambda event: self.add_codefile())

        btn_add = ttk.Button(lbl_add, text="Añadir", command=self.add_codefile, bootstyle="secondary")
        btn_add.grid(row=0, column=2, padx=10, pady=10)

        # --- Row 2: Split pane (tree + context list) ---
        panes_frame = ttk.Frame(self)
        panes_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
        panes_frame.columnconfigure(0, weight=1)
        panes_frame.columnconfigure(1, weight=1)
        panes_frame.rowconfigure(0, weight=1)

        # Left: project tree
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

        # Right: selected context files
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

        # Initial render
        self.update_workspace_tree()
        self.update_file_listbox()

    def add_codefile(self):
        selected_path = self.entry_filepath.get().strip()
        if not selected_path:
            messagebox.showwarning("Advertencia", "Debes ingresar una ruta válida.")
            return

        if not self.app.service.codebase:
            messagebox.showerror("Error", "No hay un espacio de trabajo activo.")
            return

        try:
            base_path = Path(self.app.service.codebase.path)
            complete_path = base_path / selected_path

            if complete_path.is_dir():
                added = self.app.service.add_directory_to_context(complete_path)
                self.app.log_message(f"Directorio agregado recursivamente: {selected_path} ({added} archivos)")
            else:
                self.app.service.add_file_to_context(complete_path)
                self.app.log_message(f"Archivo agregado: {selected_path}")

            self.update_file_listbox()
            self.sync_tree_states()
            self.entry_filepath.delete(0, tk.END)

        except FileNotFoundError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error agregando archivo: {str(e)}")

    def update_workspace_tree(self):
        self.tree_workspace.delete(*self.tree_workspace.get_children())
        codebase = self.app.service.codebase
        if not codebase:
            return

        base_path = Path(codebase.path)
        nodes = {"": ""}

        try:
            sorted_files = sorted(codebase.files, key=lambda f: str(f.path))
        except Exception:
            sorted_files = codebase.files

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
                    node_id = self.tree_workspace.insert(parent_id, "end", text=f"\U0001f4c1 {part}", open=False)
                    nodes[current_rel_str] = node_id
                parent_id = nodes[current_rel_str]

            filename = parts[-1]
            in_context = file_obj in self.app.service.file_context
            prefix = "\u2705 " if in_context else "\U0001f4c4 "

            self.tree_workspace.insert(
                parent_id,
                "end",
                text=f"{prefix}{filename}",
                values=(str(file_obj.path),),
            )

    def sync_tree_states(self, parent=""):
        for item_id in self.tree_workspace.get_children(parent):
            values = self.tree_workspace.item(item_id, "values")
            if values:
                file_path_str = values[0]
                in_context = any(str(f.path) == file_path_str for f in self.app.service.file_context)
                prefix = "\u2705 " if in_context else "\U0001f4c4 "
                filename = Path(file_path_str).name
                self.tree_workspace.item(item_id, text=f"{prefix}{filename}")
            else:
                self.sync_tree_states(item_id)

    def update_file_listbox(self):
        self.listbox_files.delete(0, tk.END)
        codebase = self.app.service.codebase
        base_path = Path(codebase.path) if codebase else None

        for index, file_obj in enumerate(self.app.service.file_context, start=1):
            if base_path:
                try:
                    display_path = Path(file_obj.path).relative_to(base_path)
                except ValueError:
                    display_path = Path(file_obj.path).name
            else:
                display_path = Path(file_obj.path).name

            self.listbox_files.insert(tk.END, f"{index}. {display_path}")

    def set_worktree(self):
        selected_path = filedialog.askdirectory(title="Selecciona el nuevo espacio de trabajo")
        if not selected_path:
            self.app.log_message("Cambio de espacio de trabajo cancelado.")
            return

        try:
            name = Path(selected_path).name
            self.app.service.set_workdir(selected_path, name)
            self.lbl_workspace.config(text=name)
            self.app.log_message(f"Espacio de trabajo cambiado a: {name}")
            self.update_workspace_tree()
            self.update_file_listbox()

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.app.log_message(f"Error cambiando workspace: {e}")

    def on_tree_click(self, event):
        item_id = self.tree_workspace.identify_row(event.y)
        if not item_id:
            return

        values = self.tree_workspace.item(item_id, "values")
        if not values:
            return

        file_path_str = values[0]
        file_obj = None

        for f in self.app.service.codebase.files:
            if str(f.path) == file_path_str:
                file_obj = f
                break

        if file_obj:
            if file_obj in self.app.service.file_context:
                self.app.service.remove_file_from_context(Path(file_path_str))
                self.app.log_message(f"Quitado del contexto: {Path(file_path_str).name}")
            else:
                self.app.service.file_context.append(file_obj)
                self.app.log_message(f"Añadido al contexto: {Path(file_path_str).name}")

            in_context = file_obj in self.app.service.file_context
            prefix = "\u2705 " if in_context else "\U0001f4c4 "
            filename = Path(file_path_str).name
            self.tree_workspace.item(item_id, text=f"{prefix}{filename}")

            self.update_file_listbox()

    def on_listbox_remove(self, event):
        selection = self.listbox_files.curselection()
        if not selection:
            return

        index = selection[0]
        file_context = self.app.service.file_context
        if 0 <= index < len(file_context):
            removed_file = file_context.pop(index)
            self.app.log_message(f"Quitado del contexto: {Path(removed_file.path).name}")
            self.update_file_listbox()
            self.sync_tree_states()
