# Dependencias incluidas en MESSI 0.3.0

El instalador contiene Python, SQLite, Streamlit, pandas, NumPy, SciPy,
scikit-learn, joblib, openpyxl y PyArrow, además de sus dependencias transitivas.
El modelo incluido se genera con los datos sintéticos del repositorio MESSI.

Las carpetas `*.dist-info` de `_internal` conservan metadatos y archivos de
licencia distribuidos por las dependencias. Los componentes científicos incluyen
sus bibliotecas nativas. Se distribuyen además las licencias de Python y Tcl/Tk.
Estas licencias no sustituyen la licencia que el equipo decida para su código.

- Python: licencia PSF; https://docs.python.org/3/license.html
- SQLite: dominio público; https://www.sqlite.org/copyright.html
- Streamlit, PyArrow: Apache 2.0.
- pandas, NumPy, SciPy, scikit-learn, joblib: BSD.
- openpyxl: MIT.
- PyInstaller: GPL con excepción para distribuir los ejecutables generados.

Fuentes y versiones del entorno están en `requirements.txt` y
`requirements-build.txt`. MySQL no está incluido en el ejecutable local.
