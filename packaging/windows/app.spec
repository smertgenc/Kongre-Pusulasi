# One-directory distribution: no self-extraction, UPX or runtime dependency download.
from pathlib import Path
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

root = Path(SPECPATH).parents[1]
work = root / 'build' / 'windows'
ocr = Path(os.environ['AHP_OCR_DIR'])
datas = [(str(work/'research-code-manifest.json'),'.'),(str(root/'VERSION'),'.'), (str(root/'static'),'static'),
         (str(root/'app/intelligence_config.json'),'app'),
         (str(root/'analiz/hesaplama_sonuclari.json'),'analiz'),
         (str(ocr),'ocr')]
datas += collect_data_files('webview') + collect_data_files('reportlab')
datas += collect_data_files('pythonnet',includes=['runtime/Python.Runtime.dll'])
# Keep the pinned CLR/WebView loaders at their package-relative paths. Build
# validation and the frozen UI smoke test verify them before installer creation.
binaries = collect_dynamic_libs('clr_loader') + collect_dynamic_libs('webview')
a = Analysis([str(root/'desktop_main.py')],pathex=[str(root)],datas=datas,
    binaries=binaries,
    hiddenimports=collect_submodules('uvicorn') + collect_submodules('sqlalchemy.dialects.sqlite') +
                  ['webview.platforms.winforms','webview.platforms.edgechromium','clr','clr_loader','pythonnet',
                   'reportlab.graphics.barcode.common','PIL.ImageWin'],
    excludes=['PyQt5','PyQt6','PySide2','PySide6','cefpython3','gi','tkinter','pytest','numpy','openpyxl'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='AHP-Congress-Analyzer',
          debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,
          disable_windowed_traceback=True,icon=str(root/'packaging/windows/app.ico'),
          version=str(work/'version-info.txt'),uac_admin=False)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='AHP-Congress-Analyzer')
