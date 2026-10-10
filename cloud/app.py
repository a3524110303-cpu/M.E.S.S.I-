"""MESSI para Streamlit Community Cloud, sobre el servicio MySQL compartido.

No inicia un servidor Django: usa sus modelos, autenticación y servicios
directamente. Los únicos estados escolares se guardan en la sesión del usuario.
"""
from pathlib import Path
import csv
import io
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from cloud.runtime import initialize
from cloud.auth import login, logout
from cloud import presentation as ui

CUT = "primer_parcial"
PAGE_SIZE = 20
CHOICE_LIMIT = 200


def _key(user, section):
    return f"messi-ui-{user.pk}-{section}"


def _forget(prefix):
    for name in list(st.session_state):
        if name.startswith(prefix):
            del st.session_state[name]


def _done(user, message, reset_prefix=None):
    if reset_prefix:
        _forget(reset_prefix)
    st.session_state[_key(user, "flash")] = message
    st.rerun()


def _page(user, queryset, name, size=PAGE_SIZE):
    """Cuenta la consulta, pero obtiene solamente una página de registros."""
    count = queryset.count()
    pages = max(1, (count + size - 1) // size)
    key = _key(user, f"page-{name}")
    if key in st.session_state and st.session_state[key] > pages:
        st.session_state[key] = pages
    if pages > 1:
        page = int(st.number_input("Página", min_value=1, max_value=pages, value=1, step=1, key=key))
        st.caption(f"Página {page} de {pages} · {count} registros")
    else:
        page = 1
        st.caption(f"{count} registros")
    return list(queryset[(page - 1) * size:page * size])


def _pick(user, label, rows, name, formatter=str):
    options = {item.pk: item for item in rows}
    if not options:
        return None
    key = _key(user, name)
    if key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]
    selected = st.selectbox(label, list(options), format_func=lambda pk: formatter(options[pk]), key=key)
    return options.get(selected)


def _table(rows):
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.caption("Todavía no hay registros en este espacio.")


def _teacher(user):
    from django.db.models import OuterRef, Q, Subquery
    from portal import services
    from portal.models import Prediction

    ui.header(st, "ESPACIO DOCENTE", "Conoce cómo va tu grupo.", "Captura indicadores y revisa las señales de apoyo de tus estudiantes.")
    search = st.text_input("Buscar grupo o materia", key=_key(user, "group-search"), max_chars=100)
    groups = services.visible_groups(user).filter(Q(name__icontains=search) | Q(subject__icontains=search)).order_by("name", "subject", "pk")
    group = _pick(user, "Grupo y materia", list(groups[:CHOICE_LIMIT]), "group", lambda item: f"{item.name} · {item.subject} · {item.period.name}")
    if group is None:
        st.info("No tienes grupos asignados con este criterio. El administrador debe asignar tus grupos e inscribir a sus estudiantes.")
        return
    enrollment_qs = services.teacher_enrollments(user, group.pk)
    indicators_qs = services.visible_indicators(user).filter(enrollment__group=group, cut=CUT)
    c1, c2, c3 = st.columns(3)
    c1.metric("Estudiantes del grupo", enrollment_qs.count())
    c2.metric("Indicadores capturados", indicators_qs.count())
    c3.metric("Periodo", "Abierto" if group.period.is_open else "Cerrado")
    capture, imports, exports = st.tabs(["Captura y análisis", "Importar archivo", "Exportar indicadores"])
    with capture:
        st.subheader("Indicadores del primer parcial")
        enrollments = _page(user, enrollment_qs.order_by("student__code", "pk"), f"enrollments-{group.pk}")
        latest_prediction = Prediction.objects.filter(indicator_id=OuterRef("pk")).order_by("-created_at", "-pk").values("pk")[:1]
        indicator_map = {item.enrollment_id: item for item in indicators_qs.filter(enrollment_id__in=[item.pk for item in enrollments]).annotate(latest_prediction_id=Subquery(latest_prediction))}
        latest = {}
        for item in services.visible_predictions(user).filter(pk__in=[item.latest_prediction_id for item in indicator_map.values() if item.latest_prediction_id is not None]):
            latest[item.indicator_id] = item
        rows = []
        for enrollment in enrollments:
            indicator = indicator_map.get(enrollment.pk)
            prediction = latest.get(indicator.pk) if indicator else None
            signal = "Sin indicadores" if not indicator else "Pendiente de cálculo"
            score = "—"
            if prediction:
                signal = "Desactualizado" if not prediction.is_current else "Revisar apoyo" if prediction.alert else "Sin alerta del modelo"
                score = f"{prediction.score * 100:.1f} / 100"
            rows.append({"Código": enrollment.student.code, "Estudiante": ui.person(enrollment.student.user), "Calificación": float(indicator.grade) if indicator else None, "Asistencia (%)": float(indicator.attendance) if indicator else None, "Tareas (%)": float(indicator.homework) if indicator else None, "Análisis": signal, "Puntuación": score})
        _table(rows)
        enrollment = _pick(user, "Estudiante de esta página", enrollments, f"edit-student-{group.pk}", lambda item: str(item.student))
        if enrollment is not None:
            indicator = indicator_map.get(enrollment.pk)
            prefix = _key(user, f"indicator-{enrollment.pk}")
            st.session_state.setdefault(prefix + "-version", indicator.version if indicator else 0)
            st.caption(f"Datos del primer parcial · Versión del formulario: {st.session_state[prefix + '-version']}")
            if st.button("Recargar datos del estudiante", key=prefix + "-reload"):
                _forget(prefix)
                st.rerun()
            if group.period.is_open:
                with st.form(prefix):
                    a, b, c = st.columns(3)
                    grade = a.number_input("Calificación", min_value=0.0, max_value=10.0, value=float(indicator.grade) if indicator else 0.0, step=0.1, key=prefix + "-grade")
                    attendance = b.number_input("Asistencia (%)", min_value=0.0, max_value=100.0, value=float(indicator.attendance) if indicator else 0.0, step=1.0, key=prefix + "-attendance")
                    homework = c.number_input("Tareas entregadas (%)", min_value=0.0, max_value=100.0, value=float(indicator.homework) if indicator else 0.0, step=1.0, key=prefix + "-homework")
                    saved = st.form_submit_button("Guardar indicadores", type="primary")
                if saved:
                    try:
                        services.save_indicator(user, enrollment.pk, CUT, grade, attendance, homework, st.session_state[prefix + "-version"])
                    except Exception as exc:
                        ui.error(st, exc)
                    else:
                        _done(user, "Indicadores guardados. Ya puedes calcular el riesgo con estos datos.", prefix)
                if indicator:
                    st.caption("El cálculo usa los indicadores guardados. Primero guarda si modificaste el formulario.")
                    if st.button("Calcular riesgo demostrativo", key=prefix + "-predict", type="primary"):
                        try:
                            services.calculate_risk(user, indicator.pk, st.session_state[prefix + "-version"])
                        except Exception as exc:
                            ui.error(st, exc)
                        else:
                            _done(user, "Análisis completado. Revisa la puntuación y el contexto antes de decidir el apoyo.")
            else:
                st.info("La captura de este periodo está cerrada.")
    with imports:
        _teacher_import(user, group)
    with exports:
        _teacher_export(user, group)
    ui.model_note(st)


def _teacher_import(user, group):
    from messi.data import load_csv, load_excel
    from portal import services
    from django.core.exceptions import ValidationError

    st.subheader("Importar indicadores del grupo")
    st.caption("CSV UTF-8 o Excel .xlsx · Hasta 5 MB y 10,000 filas · Estudiantes previamente inscritos en esta materia.")
    st.code("id_estudiante,nota_parcial,asistencia,tareas_entregadas", language=None)
    st.download_button("Descargar plantilla CSV", "\ufeffid_estudiante,nota_parcial,asistencia,tareas_entregadas\n", file_name="plantilla_messi.csv", mime="text/csv", key=_key(user, f"template-{group.pk}"))
    if not group.period.is_open:
        st.info("La captura de este periodo está cerrada.")
        return
    prefix = _key(user, f"import-{group.pk}")
    with st.form(prefix + "-read"):
        upload = st.file_uploader("Archivo CSV o Excel", type=["csv", "xlsx"], key=prefix + "-file")
        submitted = st.form_submit_button("Revisar archivo")
    if submitted:
        st.session_state.pop(prefix + "-preview", None)
        try:
            if upload is None:
                raise ValidationError("Selecciona un archivo CSV o Excel.")
            if upload.size > 5 * 1024 * 1024:
                raise ValidationError("El archivo supera el límite de 5 MB.")
            raw = upload.getvalue()
            records = load_excel(raw, allow_temporary_ids=False) if upload.name.lower().endswith(".xlsx") else load_csv(raw)
            codes = [row["id_estudiante"] for row in records]
            enrolled = list(services.teacher_enrollments(user, group.pk).filter(student__code__in=codes)[:10001])
            if len(enrolled) != len(records):
                raise ValidationError("El archivo contiene códigos que no están inscritos en esta materia. Revisa el grupo y los códigos.")
            versions = {item.pk: 0 for item in enrolled}
            versions.update({item.enrollment_id: item.version for item in services.visible_indicators(user).filter(enrollment_id__in=list(versions), cut=CUT)[:10001]})
            st.session_state[prefix + "-preview"] = {"records": records, "versions": versions}
        except Exception as exc:
            ui.error(st, exc)
    preview = st.session_state.get(prefix + "-preview")
    if preview:
        st.success(f"Archivo validado: {len(preview['records'])} estudiantes. Vista previa de hasta 20 filas.")
        _table(preview["records"][:PAGE_SIZE])
        st.warning("Guardar actualiza los indicadores de los estudiantes incluidos. Si alguien los cambió después de esta revisión, se rechazará toda la importación.")
        with st.form(prefix + "-commit"):
            commit = st.form_submit_button("Guardar importación", type="primary")
        if commit:
            try:
                services.import_indicators(user, group.pk, CUT, preview["records"], preview["versions"])
            except Exception as exc:
                ui.error(st, exc)
            else:
                _forget(_key(user, "indicator-"))
                _done(user, f"Se importaron {len(preview['records'])} estudiantes.", prefix)
        if st.button("Descartar revisión", key=prefix + "-discard"):
            _forget(prefix)
            st.rerun()


def _teacher_export(user, group):
    from portal import services

    st.subheader("Exportar indicadores del grupo")
    st.caption("Solo incluye los indicadores de la materia seleccionada. Hasta 10,000 filas por descarga.")
    prepared_key = _key(user, f"export-prepared-{group.pk}")
    if st.button("Preparar CSV", key=_key(user, f"export-prepare-{group.pk}")):
        st.session_state[prepared_key] = True
    if not st.session_state.get(prepared_key):
        return
    # La sesión conserva únicamente que se pidió una exportación. Los datos se
    # vuelven a consultar con el alcance actual, incluso después de una edición.
    rows = list(services.visible_indicators(user).filter(enrollment__group=group, cut=CUT).order_by("enrollment__student__code", "pk")[:10001])
    if len(rows) > 10000:
        st.error("El grupo supera el límite de exportación. Solicita al administrador una exportación institucional.")
        return
    buffer = io.StringIO(newline="")
    buffer.write("\ufeff")
    writer = csv.writer(buffer)
    writer.writerow(["id_estudiante", "nota_parcial", "asistencia", "tareas_entregadas"])
    for item in rows:
        writer.writerow([item.enrollment.student.code, item.grade, item.attendance, item.homework])
    data = buffer.getvalue()
    st.caption("El archivo contiene los datos disponibles al preparar esta vista. Actualiza tu espacio para revisar cambios posteriores.")
    st.download_button("Descargar CSV", data, file_name="indicadores_messi.csv", mime="text/csv", key=_key(user, f"export-download-{group.pk}"))


def _student(user):
    from portal import services
    from portal.models import Period, Enrollment

    ui.header(st, "ESPACIO ESTUDIANTE", "No tienes que resolverlo solo.", "Solicita apoyo y consulta los acuerdos y avances con tu tutor.")
    st.info("Puedes pedir ayuda aunque el sistema no genere una alerta académica.")
    cases_tab, request_tab, indicators_tab = st.tabs(["Mi acompañamiento", "Mis solicitudes", "Mis indicadores"])
    with cases_tab:
        st.subheader("Mis acuerdos de apoyo")
        cases = _page(user, services.visible_cases(user).defer("internal_notes").order_by("-updated_at", "-pk"), "student-cases")
        _table([{"Caso": item.pk, "Periodo": item.period.name, "Tutor": ui.person(item.tutor), "Estado": item.status, "Acuerdo": item.agreement} for item in cases])
        case = _pick(user, "Consultar un caso de esta página", cases, "student-case", lambda item: f"#{item.pk} · {item.period.name} · {item.status}")
        if case:
            _case_detail(user, case, tutor_mode=False)
    with request_tab:
        st.subheader("Pedir apoyo")
        periods = list(Period.objects.filter(pk__in=Enrollment.objects.filter(student__user=user).values("group__period_id"), is_open=True).distinct().order_by("-starts_on", "pk")[:CHOICE_LIMIT])
        if periods:
            with st.form(_key(user, "request"), clear_on_submit=True):
                period = st.selectbox("Periodo escolar", [item.pk for item in periods], format_func=lambda pk: str(next(item for item in periods if item.pk == pk)))
                message = st.text_area("¿En qué necesitas apoyo?", max_chars=1000, placeholder="Cuéntanos qué se te dificulta y qué apoyo necesitas.")
                submitted = st.form_submit_button("Enviar solicitud", type="primary")
            if submitted:
                try:
                    services.create_request(user, period, message)
                except Exception as exc:
                    ui.error(st, exc)
                else:
                    _done(user, "Tu solicitud se envió. Tu tutor podrá revisarla y acordar los siguientes pasos.")
        else:
            st.info("No tienes inscripciones en un periodo abierto. Solicita al administrador que revise tu inscripción.")
        st.subheader("Mis solicitudes enviadas")
        requests = _page(user, services.visible_requests(user).order_by("-created_at", "-pk"), "student-requests")
        _table([{"Fecha": ui.date_label(item.created_at), "Periodo": item.period.name, "Solicitud": item.message, "Estado": item.status} for item in requests])
    with indicators_tab:
        st.subheader("Mis indicadores académicos")
        indicators = _page(user, services.visible_indicators(user).order_by("enrollment__group__subject", "pk"), "student-indicators")
        _table([{"Materia": item.enrollment.group.subject, "Grupo": item.enrollment.group.name, "Periodo": item.enrollment.group.period.name, "Corte": "Primer parcial" if item.cut == CUT else item.cut, "Calificación": float(item.grade), "Asistencia (%)": float(item.attendance), "Tareas (%)": float(item.homework)} for item in indicators])


def _tutor(user):
    from portal import services

    ui.header(st, "ESPACIO TUTOR", "Convierte las señales en apoyo.", "Escucha las solicitudes, acuerda acciones y acompaña los avances de tus estudiantes asignados.")
    requests_qs = services.visible_requests(user)
    cases_qs = services.visible_cases(user)
    a, b, c = st.columns(3)
    a.metric("Estudiantes asignados", services.visible_students(user).count())
    b.metric("Solicitudes por atender", requests_qs.filter(status="Pendiente").count())
    c.metric("Casos activos", cases_qs.exclude(status="Cerrado").count())
    requests_tab, alerts_tab, new_tab, cases_tab = st.tabs(["Solicitudes", "Alertas", "Acordar apoyo", "Seguimiento"])
    with requests_tab:
        st.subheader("Solicitudes de mis estudiantes")
        requests = _page(user, requests_qs.order_by("-created_at", "-pk"), "tutor-requests")
        _table([{"Solicitud": item.pk, "Estudiante": str(item.student), "Periodo": item.period.name, "Mensaje": item.message, "Estado": item.status, "Fecha": ui.date_label(item.created_at)} for item in requests])
    with alerts_tab:
        st.subheader("Señales del modelo para revisar con contexto")
        alerts = _page(user, services.visible_predictions(user).filter(alert=True).order_by("-created_at", "-pk"), "tutor-alerts")
        _table([{"Alerta": item.pk, "Código": item.indicator.enrollment.student.code, "Materia": item.indicator.enrollment.group.subject, "Periodo": item.indicator.enrollment.group.period.name, "Puntuación / 100": round(item.score * 100, 1), "Indicadores": item.indicator_version, "Vigencia": "Vigente" if item.is_current else "Desactualizada", "Fecha": ui.date_label(item.created_at)} for item in alerts])
        ui.model_note(st)
    with new_tab:
        _new_case(user)
    with cases_tab:
        st.subheader("Casos de acompañamiento")
        cases = _page(user, cases_qs.order_by("-updated_at", "-pk"), "tutor-cases")
        _table([{"Caso": item.pk, "Estudiante": str(item.student), "Periodo": item.period.name, "Estado": item.status, "Acuerdo": item.agreement, "Actualizado": ui.date_label(item.updated_at)} for item in cases])
        case = _pick(user, "Abrir caso de esta página", cases, "tutor-case", lambda item: f"#{item.pk} · {item.student.code} · {item.status}")
        if case:
            _case_detail(user, case, tutor_mode=True)


def _new_case(user):
    from django.db.models import F, Q
    from portal import services
    from portal.models import Period, TutorAssignment

    st.subheader("Acordar un apoyo concreto")
    origin = st.radio("Origen del apoyo", ["Solicitud", "Alerta vigente", "Conversación"], horizontal=True, key=_key(user, "case-origin"))
    request_id = prediction_id = None
    student_id = period_id = None
    if origin == "Solicitud":
        choices = _page(user, services.visible_requests(user).filter(status="Pendiente", period__is_open=True).order_by("-created_at", "-pk"), "case-source-requests")
        linked = _pick(user, "Solicitud que se atenderá", choices, "case-request", lambda item: f"#{item.pk} · {item.student.code} · {item.period.name}")
        if linked:
            student_id, period_id, request_id = linked.student_id, linked.period_id, linked.pk
            st.write(linked.message)
    elif origin == "Alerta vigente":
        choices = _page(user, services.visible_predictions(user).filter(alert=True, indicator_version=F("indicator__version"), case__isnull=True, indicator__enrollment__group__period__is_open=True).order_by("-created_at", "-pk"), "case-source-alerts")
        linked = _pick(user, "Alerta que se revisará", choices, "case-prediction", lambda item: f"#{item.pk} · {item.indicator.enrollment.student.code} · {item.indicator.enrollment.group.subject}")
        if linked:
            student_id, period_id, prediction_id = linked.indicator.enrollment.student_id, linked.indicator.enrollment.group.period_id, linked.pk
            st.caption(f"Puntuación {linked.score * 100:.1f} / 100 · Una conversación debe dar contexto a esta señal.")
    else:
        search = st.text_input("Buscar estudiante asignado", key=_key(user, "case-student-search"), max_chars=100)
        students = list(services.visible_students(user).filter(Q(code__icontains=search) | Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search) | Q(user__username__icontains=search)).order_by("code")[:CHOICE_LIMIT])
        selected = _pick(user, "Estudiante", students, "case-student")
        if selected:
            periods = list(Period.objects.filter(pk__in=TutorAssignment.objects.filter(tutor=user, student=selected).values("period_id"), is_open=True).order_by("-starts_on", "pk")[:CHOICE_LIMIT])
            period = _pick(user, "Periodo escolar asignado", periods, f"case-period-{selected.pk}")
            if period:
                student_id, period_id = selected.pk, period.pk
    if student_id is None or period_id is None:
        st.info("No hay un estudiante y periodo disponibles con este criterio. Revisa las asignaciones o selecciona otro origen.")
        return
    with st.form(_key(user, "new-case"), clear_on_submit=True):
        agreement = st.text_area("Acuerdo de apoyo visible al estudiante", max_chars=1000, placeholder="Define acciones, responsables y fecha de revisión.")
        internal = st.text_area("Notas privadas del tutor", max_chars=1000, help="Solo las verá el tutor asignado.")
        submitted = st.form_submit_button("Crear caso de apoyo", type="primary")
    if submitted:
        try:
            services.create_case(user, student_id, period_id, agreement, internal_notes=internal, request_id=request_id, prediction_id=prediction_id)
        except Exception as exc:
            ui.error(st, exc)
        else:
            _done(user, "Caso creado. El estudiante ya puede consultar el acuerdo de apoyo.")


def _case_detail(user, case, tutor_mode):
    from portal import services
    from portal.models import FollowUp, SupportCase

    st.divider()
    st.subheader(f"Caso #{case.pk} · {case.status}")
    st.caption(f"{case.period.name} · Tutor: {ui.person(case.tutor)}")
    st.markdown("**Acuerdo de apoyo**")
    st.write(case.agreement)
    if tutor_mode and case.internal_notes:
        with st.expander("Nota privada del tutor"):
            st.write(case.internal_notes)
    st.markdown("**Historia del acompañamiento**")
    followup_qs = FollowUp.objects.filter(case=case).select_related("author").order_by("-created_at", "-pk")
    if not tutor_mode:
        followup_qs = followup_qs.defer("internal_notes")
    followups = _page(user, followup_qs, f"followups-{case.pk}")
    if not followups:
        st.caption("El próximo avance iniciará la historia de este acompañamiento.")
    for followup in followups:
        st.markdown(f"**{ui.date_label(followup.created_at)} · {followup.status}**")
        st.write(followup.notes)
        st.caption(ui.person(followup.author))
        if tutor_mode and followup.internal_notes:
            with st.expander(f"Nota privada del avance #{followup.pk}"):
                st.write(followup.internal_notes)
    if not tutor_mode:
        return
    prefix = _key(user, f"followup-{case.pk}")
    st.session_state.setdefault(prefix + "-version", case.version)
    if st.button("Recargar seguimiento del caso", key=prefix + "-reload"):
        _forget(prefix)
        st.rerun()
    st.caption(f"Versión del formulario: {st.session_state[prefix + '-version']}. Si otro registro cambia el caso, tendrás que revisar la actualización antes de guardar.")
    with st.form(prefix):
        notes = st.text_area("Avance y próximos pasos visibles al estudiante", max_chars=1000, key=prefix + "-notes")
        internal = st.text_area("Notas privadas del avance", max_chars=1000, key=prefix + "-internal")
        statuses = [choice[0] for choice in SupportCase.STATUSES]
        status = st.selectbox("Estado del caso", statuses, index=statuses.index(case.status), key=prefix + "-status")
        submitted = st.form_submit_button("Guardar seguimiento", type="primary")
    if submitted:
        try:
            services.add_followup(user, case.pk, notes, internal, status, st.session_state[prefix + "-version"])
        except Exception as exc:
            ui.error(st, exc)
        else:
            _done(user, "Seguimiento guardado y estado actualizado.", prefix)


def _admin(user):
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from django.utils import timezone
    from portal import organization
    from portal.models import CourseGroup, Period, Profile, Student, TutorAssignment

    User = get_user_model()
    ui.header(st, "ORGANIZACIÓN ESCOLAR", "Prepara el ciclo de acompañamiento.", "Crea cuentas, grupos e inscripciones. Asigna cada docente y tutor a su espacio de trabajo.")
    st.info("La administración organiza los accesos. La captura académica corresponde al docente y las notas privadas al tutor asignado.")
    accounts_tab, periods_tab, groups_tab, enrollments_tab, tutors_tab = st.tabs(["Cuentas", "Periodos", "Grupos", "Inscripciones", "Tutores"])
    with accounts_tab:
        with st.form(_key(user, "new-account"), clear_on_submit=True):
            st.subheader("Crear cuenta")
            username = st.text_input("Usuario nuevo", max_chars=150)
            first_name = st.text_input("Nombre", max_chars=150)
            last_name = st.text_input("Apellidos", max_chars=150)
            role = st.selectbox("Rol de la cuenta nueva", [value for value, _ in Profile.Role.choices], format_func=lambda value: dict(Profile.Role.choices)[value])
            code = st.text_input("Código de estudiante", max_chars=12, help="Para estudiantes: EST- seguido de 3 a 8 dígitos. Déjalo vacío para los demás roles.")
            password = st.text_input("Contraseña inicial", type="password", max_chars=128, help="Usa al menos 12 caracteres y evita contraseñas comunes.")
            confirm = st.text_input("Confirmar contraseña", type="password", max_chars=128)
            submitted = st.form_submit_button("Crear cuenta", type="primary")
        if submitted:
            if password != confirm:
                st.error("Las contraseñas no coinciden.")
            else:
                try:
                    organization.create_account(user, username, password, first_name, last_name, role, student_code=code)
                except Exception as exc:
                    ui.error(st, exc)
                else:
                    _done(user, "Cuenta creada. Entrega las credenciales al titular por el canal de tu institución.")
        st.caption("Crear una cuenta de docente no la asigna a un grupo. Completa la asignación en Grupos.")
        search = st.text_input("Buscar cuenta", key=_key(user, "account-search"), max_chars=100)
        accounts = _page(user, User.objects.select_related("profile").filter(Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)).order_by("username", "pk"), "admin-accounts")
        _table([{"Usuario": item.username, "Nombre": ui.person(item), "Rol": "Administrador" if item.is_superuser else item.profile.get_role_display() if hasattr(item, "profile") else "Sin perfil", "Activa": item.is_active} for item in accounts])
    with periods_tab:
        with st.form(_key(user, "new-period"), clear_on_submit=True):
            st.subheader("Crear periodo escolar")
            name = st.text_input("Nombre del periodo", max_chars=80)
            start = st.date_input("Inicio", value=timezone.localdate())
            end = st.date_input("Fin", value=timezone.localdate())
            is_open = st.checkbox("Captura abierta", value=True)
            submitted = st.form_submit_button("Crear periodo", type="primary")
        if submitted:
            try:
                organization.create_period(user, name, start, end, is_open=is_open)
            except Exception as exc:
                ui.error(st, exc)
            else:
                _done(user, "Periodo escolar creado.")
        periods = _page(user, Period.objects.order_by("-starts_on", "pk"), "admin-periods")
        _table([{"Periodo": item.name, "Inicio": item.starts_on, "Fin": item.ends_on, "Captura": "Abierta" if item.is_open else "Cerrada"} for item in periods])
    with groups_tab:
        st.caption("Crear una cuenta no asigna automáticamente un grupo al docente.")
        st.subheader("Crear grupo y materia")
        period_choices = list(Period.objects.filter(is_open=True).order_by("-starts_on", "pk")[:CHOICE_LIMIT])
        teacher_search = st.text_input("Buscar docente para el grupo", key=_key(user, "admin-teacher-search"), max_chars=100)
        teacher_choices = list(User.objects.filter(profile__role="docente", is_active=True).filter(Q(username__icontains=teacher_search) | Q(first_name__icontains=teacher_search) | Q(last_name__icontains=teacher_search)).order_by("username")[:CHOICE_LIMIT])
        creation_teachers = {item.pk: item for item in teacher_choices}
        if not period_choices:
            st.caption("Crea primero un periodo abierto.")
        else:
            with st.form(_key(user, "new-group"), clear_on_submit=True):
                name = st.text_input("Nombre del grupo", max_chars=80)
                subject = st.text_input("Materia", max_chars=100)
                period_id = st.selectbox("Periodo del grupo", [item.pk for item in period_choices], format_func=lambda pk: str(next(item for item in period_choices if item.pk == pk)))
                teacher_ids = st.multiselect("Docentes del grupo", list(creation_teachers), format_func=lambda pk: f"{ui.person(creation_teachers[pk])} (@{creation_teachers[pk].username})")
                submitted = st.form_submit_button("Crear grupo", type="primary")
            if submitted:
                try:
                    organization.create_group(user, name, subject, period_id, teacher_ids)
                except Exception as exc:
                    ui.error(st, exc)
                else:
                    _done(user, "Grupo y materia creados con sus docentes.")
        st.divider()
        st.subheader("Asignar docente a un grupo existente")
        st.caption("Esta acción agrega un docente y conserva los que ya están asignados al grupo.")
        group_search = st.text_input("Buscar grupo existente", key=_key(user, "assign-group-search"), max_chars=100)
        existing_groups = list(CourseGroup.objects.select_related("period").filter(Q(name__icontains=group_search) | Q(subject__icontains=group_search) | Q(period__name__icontains=group_search)).order_by("name", "subject", "pk")[:CHOICE_LIMIT])
        assignment_search = st.text_input("Buscar docente para asignar", key=_key(user, "assign-teacher-search"), max_chars=150)
        assignment_teachers = list(User.objects.filter(profile__role="docente", is_active=True).filter(Q(username__icontains=assignment_search) | Q(first_name__icontains=assignment_search) | Q(last_name__icontains=assignment_search)).order_by("username")[:CHOICE_LIMIT])
        if existing_groups and assignment_teachers:
            with st.form(_key(user, "assign-teacher")):
                assignment_group = _pick(user, "Grupo existente", existing_groups, "assign-existing-group")
                assignment_teacher = _pick(user, "Docente a asignar", assignment_teachers, "assign-existing-teacher", lambda item: f"{ui.person(item)} (@{item.username})")
                submitted = st.form_submit_button("Asignar docente", type="primary")
            if submitted:
                try:
                    organization.assign_teacher(user, assignment_teacher.pk, assignment_group.pk)
                except Exception as exc:
                    ui.error(st, exc)
                else:
                    _done(user, "Docente asignado. Ya puede consultar el grupo desde su cuenta.")
        elif not existing_groups:
            st.info("No hay grupos con este criterio. Crea un grupo o ajusta la búsqueda.")
        else:
            st.info("No hay docentes activos con este criterio. Ajusta la búsqueda o revisa la cuenta en Cuentas.")
        st.subheader("Grupos y docentes asignados")
        groups = _page(user, CourseGroup.objects.select_related("period").prefetch_related("teachers").order_by("name", "subject", "pk"), "admin-groups")
        _table([{"Grupo": item.name, "Materia": item.subject, "Periodo": item.period.name, "Docentes asignados": ", ".join(f"{ui.person(teacher)} (@{teacher.username})" for teacher in item.teachers.all()) or "Sin docentes asignados"} for item in groups])
    with enrollments_tab:
        st.subheader("Inscribir a un estudiante")
        student_search = st.text_input("Buscar estudiante para inscripción", key=_key(user, "admin-enroll-search"), max_chars=100)
        students = list(Student.objects.select_related("user").filter(user__is_active=True).filter(Q(code__icontains=student_search) | Q(user__first_name__icontains=student_search) | Q(user__last_name__icontains=student_search)).order_by("code")[:CHOICE_LIMIT])
        groups = list(CourseGroup.objects.select_related("period").filter(period__is_open=True).order_by("name", "subject", "pk")[:CHOICE_LIMIT])
        if students and groups:
            with st.form(_key(user, "new-enrollment")):
                student_id = st.selectbox("Estudiante a inscribir", [item.pk for item in students], format_func=lambda pk: str(next(item for item in students if item.pk == pk)))
                group_id = st.selectbox("Grupo y materia de inscripción", [item.pk for item in groups], format_func=lambda pk: str(next(item for item in groups if item.pk == pk)))
                submitted = st.form_submit_button("Inscribir estudiante", type="primary")
            if submitted:
                try:
                    organization.enroll_student(user, student_id, group_id)
                except Exception as exc:
                    ui.error(st, exc)
                else:
                    _done(user, "Estudiante inscrito en el grupo.")
        else:
            st.caption("Crea primero una cuenta de estudiante y un grupo de un periodo abierto.")
        from portal.models import Enrollment
        enrollment_rows = _page(user, Enrollment.objects.select_related("student__user", "group__period").order_by("student__code", "pk"), "admin-enrollments")
        _table([{"Estudiante": str(item.student), "Grupo": item.group.name, "Materia": item.group.subject, "Periodo": item.group.period.name} for item in enrollment_rows])
    with tutors_tab:
        st.subheader("Asignar tutor por estudiante y periodo")
        tutor_search = st.text_input("Buscar tutor", key=_key(user, "admin-tutor-search"), max_chars=100)
        tutors = list(User.objects.filter(profile__role="tutor", is_active=True).filter(Q(username__icontains=tutor_search) | Q(first_name__icontains=tutor_search) | Q(last_name__icontains=tutor_search)).order_by("username")[:CHOICE_LIMIT])
        student_search = st.text_input("Buscar estudiante para tutoría", key=_key(user, "admin-tutored-search"), max_chars=100)
        students = list(Student.objects.select_related("user").filter(user__is_active=True).filter(Q(code__icontains=student_search) | Q(user__first_name__icontains=student_search) | Q(user__last_name__icontains=student_search)).order_by("code")[:CHOICE_LIMIT])
        selected = _pick(user, "Estudiante que recibirá tutoría", students, "admin-tutored-student")
        if selected and tutors:
            from portal.models import Enrollment
            periods = list(Period.objects.filter(pk__in=Enrollment.objects.filter(student=selected).values("group__period_id"), is_open=True).distinct().order_by("-starts_on", "pk")[:CHOICE_LIMIT])
            if periods:
                with st.form(_key(user, "new-tutor-assignment")):
                    tutor_id = st.selectbox("Tutor asignado", [item.pk for item in tutors], format_func=lambda pk: ui.person(next(item for item in tutors if item.pk == pk)))
                    period_id = st.selectbox("Periodo de la tutoría", [item.pk for item in periods], format_func=lambda pk: str(next(item for item in periods if item.pk == pk)))
                    submitted = st.form_submit_button("Asignar tutor", type="primary")
                if submitted:
                    try:
                        organization.assign_tutor(user, tutor_id, selected.pk, period_id)
                    except Exception as exc:
                        ui.error(st, exc)
                    else:
                        _done(user, "Tutor asignado al estudiante en este periodo.")
            else:
                st.caption("Inscribe al estudiante en un periodo abierto antes de asignar su tutor.")
        else:
            st.caption("Crea primero cuentas de estudiante y tutor.")
        assignments = _page(user, TutorAssignment.objects.select_related("student__user", "tutor", "period").order_by("student__code", "pk"), "admin-tutor-assignments")
        _table([{"Estudiante": str(item.student), "Tutor": ui.person(item.tutor), "Periodo": item.period.name} for item in assignments])
    st.caption("Los selectores muestran hasta 200 opciones. Usa los filtros de búsqueda si una persona no aparece.")


def main():
    st.set_page_config(page_title="MESSI · Acompañamiento escolar", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
    ui.style(st)
    if not initialize(st):
        st.title("MESSI · Configuración pendiente")
        st.caption("El portal requiere su servicio de datos compartido antes de permitir el acceso.")
        st.stop()
    if "_messi_auth_user_id" not in st.session_state:
        ui.header(st, "ACOMPAÑAMIENTO ESCOLAR", "MESSI en línea", "Un espacio compartido para docentes, estudiantes y tutores. Cada persona accede con su propia cuenta.")
        st.markdown('<div class="messi-banner"><strong>El apoyo comienza con una conexión.</strong><p>Registrar indicadores, escuchar solicitudes y acompañar los avances desde cualquier dispositivo.</p></div>', unsafe_allow_html=True)
    user = login(st)
    if user is None:
        st.stop()
    from portal import services
    role = services.role_for(user)
    with st.sidebar:
        st.title("MESSI")
        st.caption("Acompañamiento escolar")
        st.divider()
        st.write(ui.person(user))
        st.caption({"admin": "Administrador", "docente": "Docente", "estudiante": "Estudiante", "tutor": "Tutor"}.get(role, "Sin rol asignado"))
        if st.button("Actualizar mi espacio", key=_key(user, "refresh")):
            _forget(_key(user, ""))
            st.rerun()
        if st.button("Cerrar sesión", key="cloud_logout"):
            logout(st)
            st.rerun()
        st.divider()
        st.caption("Cada cuenta ve su información y sus asignaciones. Los registros se guardan en la base de datos compartida.")
    flash = st.session_state.pop(_key(user, "flash"), None)
    if flash:
        st.success(flash)
    try:
        view = {"admin": _admin, "docente": _teacher, "estudiante": _student, "tutor": _tutor}.get(role)
        if view is None:
            st.warning("Tu cuenta no tiene un rol asignado. Contacta al administrador de tu institución.")
        else:
            view(user)
    except Exception as exc:
        ui.error(st, exc)
    st.divider()
    st.caption("MESSI · Detección, apoyo y seguimiento. La decisión de apoyo corresponde al equipo escolar.")


if __name__ == "__main__":
    main()
