# Mejoras de la interfaz de MESSI 0.4.0

Fecha: 8 de octubre de 2026, America/Mexico_City. Se comparó la interfaz 0.3.0 con la implementación final 0.4.0 de `app.py` y `src/messi/presentation.py`, sus pruebas y las capturas reales de la entrega 3. Las prioridades y contratos de esta auditoría guiaron las mejoras para Docente, Estudiante y Tutor; los resultados observados se registran al final del documento.

La base funciona y conserva mensajes de éxito después de guardar. La principal dificultad es la jerarquía: demasiadas instrucciones, botones y tablas tienen el mismo peso visual. El usuario debe deducir el siguiente paso y recorrer una página larga. La nueva dirección combina teal, navy, fondo cálido y acento ámbar, con una cabecera breve, navegación por rol, bloques de tarea, pasos y cifras de resumen tomadas de datos reales de la sesión.

## Prioridades del flujo

| Prioridad | Vista y punto concreto | Cambio propuesto | Criterio para comprobarlo |
| --- | --- | --- | --- |
| P1 | Docente: ingreso, datos válidos, guardar y calcular aparecen como bloques consecutivos sin guía de avance | Mostrar tres pasos claros: ingresar, revisar, obtener resultado. Diferenciar acción principal de cálculo y acciones auxiliares de plantilla/carga anterior/guardado | Una persona identifica cómo cargar y qué pulsar después; los pasos reflejan estado real de la sesión |
| P1 | Docente: `Calcular riesgo de demostración` ya guarda predicciones automáticamente; el guardado de indicadores tiene otro botón | Explicar junto a la acción qué queda guardado y mostrar resultado disponible frente a guardado confirmado | Si SQLite falla, la puntuación permanece disponible y el aviso dice que no se guardó; nunca se pinta un paso de guardado exitoso sin éxito real |
| P1 | Tutor: tablas de solicitudes, apoyos e historial muestran `student_id`, `support_type`, `created_at`, `notes`, IDs internos e ISO UTC | Etiquetas en español, código visible, acuerdo/mensaje/estado y fecha legible; conservar ID técnico cuando se necesita seleccionar apoyo | Los títulos se entienden sin leer el esquema de la base; se preservan los valores y no se cambia su significado |
| P1 | Tutor: indicadores, solicitudes, acuerdo, lista de apoyos, selección e historial obligan a mucho desplazamiento | Agrupar revisar solicitudes, registrar acuerdo y actualizar apoyo con encabezados/pasos; mostrar resumen de solicitudes/apoyos y acercar historial al apoyo elegido | Se entiende qué solicitud se atiende y qué apoyo se actualiza; la selección mantiene el ID correcto después de rerun |
| P1 | Errores: mensajes de validación llegan desde el contrato con nombres como `nota_parcial`; los de persistencia incluyen SQLite | Encabezado que explique qué corregir y siguiente acción, con detalle técnico secundario cuando ayude al equipo | Una nota 12 indica rango 0–10; una solicitud vacía pide completar mensaje; errores de guardado conservan los campos |
| P1 | Estudiante: formulario simple con texto genérico, sin expectativa clara después del envío | Tarjeta de solicitud con código, mensaje y botón principal; explicación breve de que el tutor revisará y de que no hace falta alerta | Se puede enviar sin modelo/predicción; se ve confirmación e ID de solicitud; después de error permanecen código/mensaje |
| P2 | Docente: tabla de puntuaciones tiene checkbox de alerta, valor decimal y origen técnico | Resumen con número de estudiantes y casos para revisar; tabla con etiqueta textual de revisión y puntuación formateada de manera consistente | Se distinguen los casos con/sin marca sin depender sólo del color; umbral inclusivo 0.5 y salida CSV mantienen contrato |
| P2 | Estados vacíos de Tutor/Docente sólo dicen que todavía no hay registros | Explicar la siguiente acción disponible en el mismo bloque | Cero solicitudes no bloquea registrar apoyo; cero predicciones no bloquea solicitudes ni acompañamiento |
| P2 | El selector horizontal de cuatro fuentes y tablas amplias necesitan revisión en ancho estrecho | Controles que envuelvan o se apilen, botones amplios y bloques verticales; tablas con desplazamiento propio | En 390 px de ancho se ven etiquetas y acciones; no hay desbordamiento horizontal de toda la página |
| P2 | Mensajes de demostración están repetidos antes de las tareas y resultados | Mantener alcance visible en una nota breve de la cabecera y detalle contextual junto al resultado | Se sigue leyendo que los datos son ficticios y que los roles no autentican, sin ocupar toda la primera pantalla |

## Contratos que deben permanecer correctos

Al cambiar de fuente, la versión 0.3.0 elimina datos y predicciones preparados. Lo comprueba `test_changing_source_clears_old_data_and_predictions`. Una mejora visual debe conservar ese contrato o modificarlo expresamente con pruebas representativas; no debe insinuar que conserva la preparación cuando la elimina.

El pegado/archivo inválido descarta el conjunto preparado y sus predicciones. La captura directa inválida conserva las filas previamente aceptadas y sus campos pendientes. Son comportamientos distintos: la captura de pegado con nota 12 no acredita conservación de filas ni la corrección QA-04 de captura directa.

Guardar indicadores ocurre sólo al solicitarlo. Calcular guarda predicciones y permite conservar el resultado en sesión aun si falla su persistencia. Cambiar indicadores invalida una predicción anterior. Los resúmenes y pasos deben representar estos hechos, sin confundir resultado visible con registro guardado.

Solicitudes y apoyos funcionan sin alerta. Campos inválidos permanecen para corregirse; campos válidos se limpian después del éxito; la confirmación de seguimiento sobrevive al rerun. La apariencia nueva debe preservar esos comportamientos revalidados por Víctor y por la integración posterior.

Los KPI pueden contar estudiantes, casos con marca, solicitudes y apoyos por estado. No hay un campo de eficacia, de éxito escolar ni de casos revisados por humanos que permita mostrar esos indicadores como hechos. Una cifra de riesgo sigue siendo puntuación sintética de demostración.

## Criterios de accesibilidad y revisión visual

La paleta se debe medir sobre los colores implementados: texto normal con contraste al menos 4.5:1 y texto grande al menos 3:1 según [W3C contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Para los botones teal, utilizar una combinación medida; el ámbar puede identificar atención mediante fondo suave y texto oscuro. Los estados deben tener palabras además de color.

Con teclado, la navegación por rol, radios, entradas, desplegables, botones y descarga deben mantener un foco visible; el CSS no debe eliminarlo. La revisión usa Tab, Shift+Tab, flechas y Enter sin depender del ratón, conforme al criterio de [foco visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html).

Los formularios deben conservar etiquetas visibles y ayuda breve; el placeholder no sustituye a una etiqueta. Al ampliar o estrechar la página se deben apilar controles y conservar texto/acciones visibles. Las tablas pueden necesitar desplazamiento propio, mientras el resto de la vista debe redistribuirse, según la guía de [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html). Estas revisiones parciales no equivalen a una certificación completa WCAG ni a una prueba con lectores de pantalla.

## Revisión funcional después de aplicar el diseño

| Recorrido | Resultado exigido | Evidencia prevista |
| --- | --- | --- |
| Docente vacío y con tres estudiantes | Acción siguiente clara, tabla y cifras correctas; cálculo/descarga disponibles con datos válidos | Capturas de escritorio y navegador de ancho estrecho |
| Captura directa inválida y corrección | Conserva campos tras error, acepta y limpia tras éxito | AppTest existente y recorrido en navegador |
| Pegado con nota 12 | Rechaza rango y retira resultados preparados | Test existente y captura del mensaje |
| Guardado y cálculo con/sin almacenamiento | Sólo confirma guardado cuando ocurre; conserva resultado si falla SQLite | `test_app.py` y pruebas de persistencia |
| Estudiante sin predicción | Solicitud válida se guarda; mensaje vacío conserva campos | AppTest y confirmación real |
| Tutor solicitud, apoyo e historial | IDs correctos, estado y notas persistentes, confirmación después de rerun | AppTest y recorrido real |
| Teclado y viewport estrecho | Controles operables, foco visible, textos y acciones completos | Observación real en navegador; emulación de ancho no se presenta como teléfono físico |

Las pruebas UI actuales usan índices como `button[0]`, `selectbox[2]` y `dataframe[-1]`, además de encabezados exactos. Al introducir pasos, tarjetas y tablas nuevas, esos índices pueden cambiar. Se deben adaptar los selectores a claves estables o etiquetas y conservar las aserciones sobre comportamiento y persistencia. El adaptador FakeUI necesita soportar los nuevos contenedores del diseño sin sustituir pruebas reales de Streamlit.

## Resultado observado de 0.4.0

Se revisaron visualmente las capturas reales `evidencias/capturas_interfaz_04/01_docente_inicio.png` y `02_captura_directa.png`, además del código de `app.py` y `src/messi/presentation.py`. La cabecera navy/teal, la navegación de roles, los tres pasos del Docente, el formulario en dos columnas y el botón principal verde son legibles y tienen una jerarquía más clara. La captura inicial distingue ingreso, guardado y cálculo/descarga. La captura directa muestra etiquetas completas, ayuda del código, placeholders de rango/ejemplo y estado vacío con siguiente acción. En las áreas capturadas no se observaron superposiciones ni controles recortados.

Las capturas `03_tabla_pegada.png`, `04_datos_guardados.png` y `05_resultado_modelo.png` muestran la entrada por tabla, validación, confirmación de guardado y resultado. El resumen de tres estudiantes, nota promedio 7.0 y asistencia promedio 82% corresponde a las tres filas visibles: EST-401 (5.8/70/50), EST-402 (8.2/92/88) y EST-403 (7.0/85/80). El resultado presenta tres puntuaciones y dos casos para revisar, alcance sintético junto a la tabla, confirmación de guardado y botón de descarga visible. La marca de revisión se expresa mediante checkbox y encabezado textual, además del resumen; no depende sólo de color.

Las capturas `06_solicitud_entrada.png` y `07_solicitud_registrada.png` muestran el formulario del Estudiante junto a tres pasos sobre qué ocurre después del envío. Se explica que puede solicitar apoyo sin alerta y que esta demostración local no envía notificaciones: el tutor debe abrir su vista. La confirmación visible en la captura final indica solicitud 2 registrada y los campos se presentan limpios después del éxito. Estos registros documentan un recorrido interno con datos ficticios; no acreditan la prueba con persona ajena exigida en la entrega 3.

La captura final `12_validacion_invalida.png` muestra la fila pegada con nota 12 y el mensaje de rechazo completo: «Revisa los datos antes de continuar. Fila 2: nota_parcial debe estar entre 0 y 10». Queda visible qué campo corregir y su rango permitido. Se acredita rechazo de pegado inválido, no conservación de otras filas ni el caso distinto de captura directa.

Las capturas finales `08_tutor_bandeja.png` y `09_tutor_acuerdo.png` muestran dos solicitudes, cero apoyos activos antes de registrar el acuerdo y dos casos del conjunto visible para revisar. Los encabezados y captions definen qué cuenta cada cifra. La bandeja permite elegir una solicitud, leer su mensaje completo y utilizar su código en el formulario situado al lado. La solicitud seleccionada corresponde a EST-401; el acuerdo preparado mantiene ese mismo código y muestra el tipo «Tutoría académica» y la nota ficticia. El detalle de sólo lectura se ve oscuro y legible después de la corrección del estilo; integración confirmó en DOM `rgb(18,44,57)`.

Las capturas `10_seguimiento_entrada.png` y `11_seguimiento_guardado.png` muestran el apoyo 1 de EST-401: primero en estado Pendiente, después En seguimiento. El selector conserva el mismo folio y código. La tabla de historial contiene seguimiento 1 asociado al apoyo 1; el campo de nota queda limpio tras guardar. El formulario y el historial se presentan juntos en dos columnas. Las tablas amplias conservan su propio desplazamiento; la captura del historial no muestra todas sus columnas ni toda la nota a la vez. Integración verificó en la base de prueba final dos solicitudes, un apoyo y un seguimiento, además de tres estudiantes y tres predicciones con dos marcas para revisar.

Los pasos están conectados al conjunto cargado, a su huella de guardado confirmado y al resultado disponible. El código añade confirmación de persistencia y separa resultado visible de guardado. La presentación del Tutor traduce una copia de las filas, conservando los valores de almacenamiento; las fechas con zona horaria se convierten a la hora local del equipo. La lectura de implementación y las capturas del Tutor muestran etiquetas españolas y fechas locales legibles sin alterar los valores guardados.

Se calcularon relaciones de contraste mediante luminancia relativa sRGB sobre los valores CSS. Integración confirmó también en el DOM del navegador que el caption y su párrafo usan `rgb(82,103,115)`, equivalente a `#526773`; la apariencia más tenue de algunas letras en la imagen no demuestra otro color aplicado.

| Elemento | Texto o indicador | Fondo | Contraste calculado | Resultado |
| --- | --- | --- | --- | --- |
| Texto/título de página | `#122c39` | `#f5f8f7` | 13.60:1 | Supera 4.5:1 |
| Título en tarjeta blanca | `#122c39` | `#ffffff` | 14.53:1 | Supera 4.5:1 |
| Caption de página | `#526773` | `#f5f8f7` | 5.54:1 | Supera 4.5:1 |
| Caption de tarjeta/sidebar | `#526773` | `#ffffff` | 5.92:1 | Supera 4.5:1 |
| Detalle de solicitud de sólo lectura corregido | `#122c39` | `#f8fbfa` | 13.96:1 | Supera 4.5:1 |
| Botón teal principal | `#ffffff` | `#167a72` | 5.17:1 | Supera 4.5:1 |
| Botón principal hover | `#ffffff` | `#11645e` | 6.98:1 | Supera 4.5:1 |
| Título del héroe, peor extremo del gradiente | `#ffffff` | `#1a514f` | 9.00:1 | Supera 4.5:1 |
| Texto secundario del héroe, peor extremo | `#d6ebe5` | `#1a514f` | 7.23:1 | Supera 4.5:1 |
| Badge de sidebar | `#155d55` | `#e6f3ee` | 6.75:1 | Supera 4.5:1 |
| Marca/borde seleccionado en sidebar | `#167a72` | `#e6f3ee` | 4.54:1 | Supera 3:1 |
| Foco ámbar corregido en tarjeta | `#a45d13` | `#ffffff` | 5.06:1 | Supera 3:1 |
| Foco ámbar corregido en página | `#a45d13` | `#f5f8f7` | 4.73:1 | Supera 3:1 |
| Foco ámbar corregido en entrada | `#a45d13` | `#f8fbfa` | 4.86:1 | Supera 3:1 |

Se detectó que el ámbar inicial `#d99535` sólo alcanzaba 2.53:1 contra blanco y 2.37:1 contra el fondo de página. Integración lo sustituyó por `#a45d13` antes del cierre. El indicador de foco personalizado requiere contraste de al menos 3:1 contra el color adyacente según [W3C contraste no textual](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html). La relación estática corregida se verificó. En el ejecutable reconstruido, integración comprobó mediante teclado y DOM que el textarea del Estudiante tenía `:focus-visible` activo y `outline: rgb(164,93,19) solid 3px`, equivalente al ámbar corregido; Tab permitió avanzar al botón Enviar. Este recorrido parcial no comprueba todos los widgets y roles.

Integración detectó también que el detalle de solicitud de sólo lectura heredaba de Streamlit `rgba(18,44,57,.4)`, que reduce la legibilidad. Al componer ese color sobre el fondo de entrada `#f8fbfa`, el contraste calculado es aproximadamente 2.34:1. Se corrigió el texto a navy opaco `#122c39`, incluida la propiedad de relleno de texto y `opacity:1`, y la etiqueta a `#526773`. Los colores corregidos superan 4.5:1 sobre sus fondos; se confirmó la lectura clara en las capturas finales 08 y 09, y el color de texto aplicado en el DOM. Es un contenido que se debe poder leer, aun cuando el campo no sea editable.

La captura actual `13_movil_estudiante.png` se revisó visualmente a 390 × 844 px: el formulario está apilado, el mensaje de confirmación se distribuye en varias líneas y las etiquetas, entrada y botón Enviar quedan dentro del ancho visible. El navegador del ejecutable informó `pageWidth=390` y área principal `clientWidth=380`, igual a `scrollWidth=380`; en esa vista no hay desbordamiento horizontal de página. La imagen guardada muestra el campo y su caret. La captura adicional de escritorio `13b_foco_teclado.png` acredita visualmente el aro ámbar alrededor del botón Enviar, distinguible sobre el fondo blanco de la tarjeta, y completa el dato de foco confirmado en DOM.

Calidad comunicó la suite final de la fuente 0.4.0: 161 pruebas, 154 aprobadas, siete MySQL omitidas y cero fallidas. Incluye una AppTest que selecciona entre dos solicitudes del Tutor, copia sólo el código del estudiante, conserva tipo de apoyo/notas y acuerdo existente, y no escribe hasta enviar el formulario. Integración informó la reconstrucción definitiva del paquete después de corregir foco y texto de sólo lectura y de integrar la selección/copia de solicitudes. Las verificaciones del ejecutable y empaquetado están registradas en las evidencias de la entrega; la revisión de ancho estrecho y DOM descrita arriba se realizó sobre el ejecutable con el foco corregido.

La auditoría AST final de las API públicas de la aplicación revisó 73 funciones, clases y métodos, sin docstrings faltantes; el detalle está en `../entrega_2/evidencias/auditoria_docstrings.json`. Se mantiene el criterio de excluir nombres con prefijo `_` y clases locales de implementación.

Esta auditoría no editó `app.py`, `presentation.py`, pruebas ni DOCX y no realizó una prueba externa con persona ajena. La observación del navegador con ancho emulado no constituye una prueba en teléfono físico, con lectores de pantalla ni una evaluación completa WCAG. El recorrido visual solicitado de los tres roles y las revisiones parciales de contraste, teclado y ancho estrecho quedan documentados con las evidencias descritas.
