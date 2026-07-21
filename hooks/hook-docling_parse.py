from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files(
    'docling_parse',
    includes=['pdf_resources/**'],
)

hiddenimports = collect_submodules('docling_parse')
