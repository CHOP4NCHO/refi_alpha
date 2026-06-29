import tkinter as tk
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk


class RequirementsTab(ttk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)

        pdf_frame = tk.LabelFrame(self, text="Importar Requerimientos desde PDF")
        pdf_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        pdf_frame.columnconfigure(0, weight=1)

        self.pdf_status_var = tk.StringVar(
            value="Selecciona un documento para extraer sus requerimientos."
        )
        ttk.Label(pdf_frame, textvariable=self.pdf_status_var).grid(
            row=0, column=0, sticky="w", padx=5, pady=8
        )
        self.btn_import_pdf = ttk.Button(
            pdf_frame,
            text="Seleccionar PDF y extraer",
            command=self.import_pdf,
        )
        self.btn_import_pdf.grid(row=0, column=1, sticky="e", padx=5, pady=8)

        lbl_form = tk.LabelFrame(self, text="Nuevo Requerimiento")
        lbl_form.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
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
        lbl_reqs.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=(5, 10))
        self.rowconfigure(2, weight=1)

        self.listbox_reqs = tk.Listbox(lbl_reqs)
        self.listbox_reqs.pack(fill="both", expand=True, padx=5, pady=5)

    def import_pdf(self):
        pdf_path = filedialog.askopenfilename(
            title="Seleccionar documento de requerimientos",
            filetypes=[("Documentos PDF", "*.pdf")],
        )
        if not pdf_path:
            return

        if self.app.service.get_requirements() and not messagebox.askyesno(
            "Reemplazar requerimientos",
            "La extracción reemplazará los requerimientos actuales. ¿Deseas continuar?",
        ):
            return

        path = Path(pdf_path)
        self.btn_import_pdf.configure(state="disabled")
        self.pdf_status_var.set(f"Extrayendo requerimientos de {path.name}…")
        self.app.log_message(f"Iniciando extracción desde PDF: {path}")
        threading.Thread(
            target=self._extract_pdf,
            args=(path,),
            daemon=True,
        ).start()

    def _extract_pdf(self, pdf_path: Path):
        try:
            document = self.app.service.extract_requirements_from_pdf(pdf_path)
        except Exception as error:
            error_message = (
                str(error).strip()
                or "Ocurrió un error inesperado durante la extracción."
            )
            self._schedule_ui(self._finish_pdf_error, error_message)
            return

        self._schedule_ui(
            self._finish_pdf_success,
            document.name,
            len(document.requirements),
        )

    def _schedule_ui(self, callback, *args):
        """Return worker-thread results to Tk without leaving the button locked."""
        try:
            self.after(0, callback, *args)
        except (RuntimeError, tk.TclError):
            # The window was closed while extraction was still running.
            return

    def _finish_pdf_success(self, document_name: str, requirement_count: int):
        self.btn_import_pdf.configure(state="normal")
        self.pdf_status_var.set(
            f"{document_name}: {requirement_count} requerimiento(s) extraído(s)."
        )
        self.update_req_listbox()
        self.app.log_message(
            f"Extracción completada: {requirement_count} requerimiento(s) cargado(s)."
        )
        messagebox.showinfo(
            "Extracción completada",
            f"Se extrajeron {requirement_count} requerimiento(s) desde {document_name}.",
        )

    def _finish_pdf_error(self, error_message: str):
        self.btn_import_pdf.configure(state="normal")
        self.pdf_status_var.set("No fue posible extraer los requerimientos del PDF.")
        self.app.log_message(f"Error durante la extracción del PDF: {error_message}")
        messagebox.showerror("Error de extracción", error_message)

    def update_req_listbox(self):
        self.listbox_reqs.delete(0, tk.END)
        for index, req in enumerate(self.app.service.get_requirements(), start=1):
            self.listbox_reqs.insert(tk.END, f"[{req.id}] ({req.type}) - {req.description}")

    def add_requirement(self):
        description = self.entry_req_desc.get().strip()
        if not description:
            messagebox.showwarning("Advertencia", "La descripción no puede estar vacía.")
            return

        req_type = self.req_type_var.get()
        requirement = self.app.service.add_requirement(description=description, req_type=req_type)

        self.app.log_message(f"Requerimiento agregado: [{requirement.id}] {description}")
        self.update_req_listbox()
        self.entry_req_desc.delete(0, tk.END)
