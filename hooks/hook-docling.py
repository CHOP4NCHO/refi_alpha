from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_entry_point,
    collect_submodules,
)

# Archivos de datos propios de Docling
datas = collect_data_files("docling")

# Plugins registrados bajo [project.entry-points.docling]
entrypoint_datas, entrypoint_hiddenimports = collect_entry_point("docling")

datas += entrypoint_datas

hiddenimports = (
    collect_submodules("docling")
    + entrypoint_hiddenimports
    + [
        "docling.models.plugins.defaults",
    ]
)
