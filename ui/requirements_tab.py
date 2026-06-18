import random
import string
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from requirements_extractor.req_document import Requirement

class RequirementsTab(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)

        lbl_form = tk.LabelFrame(self, text="Nuevo Requerimiento")
        lbl_form.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        lbl_form.columnconfigure(1, weight=1)

        ttk.Label(lbl_form, text="Descripción:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_req_desc = ttk.Entry(lbl_form)
        self.entry_req_desc.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(lbl_form, text="Tipo:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        self.req_type_var = tk.StringVar(value="FUNCTIONAL")
        radio_frame = ttk.Frame(lbl_form)
        radio_frame.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        ttk.Radiobutton(radio_frame, text="Funcional", variable=self.req_type_var, value="FUNCTIONAL").pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame, text="No Funcional", variable=self.req_type_var, value="NON_FUNCTIONAL").pack(side="left", padx=5)

        btn_add_req = ttk.Button(lbl_form, text="Agregar Requerimiento", command=self.add_requirement)
        btn_add_req.grid(row=2, column=1, sticky="e", padx=5, pady=10)

        lbl_reqs = tk.LabelFrame(self, text="Requerimientos Actuales")
        lbl_reqs.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        self.rowconfigure(1, weight=1)

        self.listbox_reqs = tk.Listbox(lbl_reqs)
        self.listbox_reqs.pack(fill="both", expand=True, padx=5, pady=5)

    def generate_requirement_id(self, length=3):
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choices(characters, k=length))

    def update_req_listbox(self):
        self.listbox_reqs.delete(0, tk.END)
        for index, req in enumerate(self.app.req_document.requirements, start=1):
            self.listbox_reqs.insert(tk.END, f"[{req.id}] ({req.type}) - {req.description}")

    def add_requirement(self):
        description = self.entry_req_desc.get().strip()
        if not description:
            messagebox.showwarning("Advertencia", "La descripción no puede estar vacía.")
            return

        req_type = self.req_type_var.get()
        req_id = self.generate_requirement_id()

        requirement = Requirement(id=req_id, description=description, type=req_type)
        self.app.req_document.add_requirement(requirement)

        self.app.log_message(f"Requerimiento agregado: [{req_id}] {description}")
        self.update_req_listbox()
        self.entry_req_desc.delete(0, tk.END)