# Ajuste de la comprobación de aislamiento en Windows

Fecha: 8 de octubre de 2026. Versión de la aplicación: 0.3.0.

La [ejecución inicial de GitHub Actions](https://github.com/a3524110303-cpu/M.E.S.S.I-/actions/runs/37753086652)
falló en una aserción de `test_desktop.py`. La prueba comparaba la ruta física
devuelta por `database_path()` con el nombre textual del directorio temporal.
Windows puede proporcionar `TMP` con un alias corto 8.3, como `RUNNER~1`,
mientras que `Path.resolve()` devuelve su nombre largo. Son el mismo directorio,
pero `is_relative_to()` compara componentes de ruta y no resuelve esos alias.

Se corrigió únicamente la aserción de la prueba: ambos lados se normalizan con
`resolve()` antes de comprobar la pertenencia al directorio temporal. Se
conservan también las comprobaciones de restauración de `MESSI_DATA_DIR`,
eliminación de temporales y ausencia de escrituras en la carpeta original del
usuario. No se cambió código de la aplicación, modelo, ejecutable o instalador.

Validación local en Windows 11 x64 con Python 3.13:

- Reproducción previa con `TMP`, `TEMP` y `TMPDIR` apuntando a un alias 8.3 real,
  obtenido mediante `GetShortPathNameW`: la prueba original falló de la misma
  forma que en CI. Se confirmó que alias y nombre largo resolvían a la misma carpeta.
- Después del ajuste, las seis pruebas de `test_desktop.py` aprobaron con ese
  entorno de alias corto; código de salida 0.
- Las mismas seis pruebas aprobaron con el entorno temporal habitual; código
  de salida 0.

La confirmación de CI posterior al commit se registra en la nueva ejecución
de GitHub Actions. Este ajuste no requiere reconstruir los binarios.
