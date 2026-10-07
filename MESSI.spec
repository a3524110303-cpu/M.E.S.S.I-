# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH)
datas = [(str(root / "app.py"), "."),
         (str(root / "models" / "messi_demo.joblib"), "models"),
         (str(root / "models" / "messi_demo.json"), "models"),
         (str(root / "data" / "synthetic" / "students_demo.csv"), "data/synthetic"),
         (str(root / "data" / "synthetic" / "Plantilla_MESSI.xlsx"), "data/synthetic")]
datas += [(str(Path(sys.base_prefix) / "LICENSE.txt"), "licenses/Python"),
          (str(Path(sys.base_prefix) / "tcl" / "tk8.6" / "license.terms"), "licenses/Tk"),
          (str(root / "installer" / "licenses" / "Tcl.txt"), "licenses/Tcl")]
datas += collect_data_files("streamlit")
for package in ("streamlit", "scikit-learn", "pandas", "numpy", "scipy", "joblib", "openpyxl", "pyarrow"):
    datas += copy_metadata(package, recursive=True)
hiddenimports = ["app", "sklearn.neural_network", "sklearn.preprocessing", "sklearn.pipeline"]
hiddenimports += collect_submodules("messi")
hiddenimports += collect_submodules("streamlit", filter=lambda name: not name.startswith("streamlit.hello"))
a = Analysis(["messi_desktop.py"], pathex=[str(root / "src"), str(root)], binaries=[], datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["mysql", "matplotlib", "IPython", "pytest", "torch", "tensorflow"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MESSI", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    disable_windowed_traceback=False, uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="MESSI")
