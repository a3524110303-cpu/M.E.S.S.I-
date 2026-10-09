"""Portal web de MESSI: navegación por rol y formularios con CSRF."""

import csv
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import F
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from messi.data import load_csv, load_excel, ValidationError as DataValidationError
from messi.model import ModelUnavailable

from . import services
from .forms import CUTS, CaseForm, FollowUpForm, ImportForm, IndicatorForm, RequestForm
from .models import Enrollment, Indicator, Period, Prediction, TutorAssignment


def role_required(role):
    def decorate(view):
        @login_required
        @wraps(view)
        def guarded(request, *args, **kwargs):
            if services.role_for(request.user) != role:
                raise PermissionDenied("Tu cuenta no tiene acceso a esta sección.")
            return view(request, *args, **kwargs)
        return guarded
    return decorate


def _page(request, queryset, parameter="page", size=20):
    return Paginator(queryset, size).get_page(request.GET.get(parameter))


def _context(request, **kwargs):
    return {"role": services.role_for(request.user), "cut_choices": CUTS, "cut_label": dict(CUTS).get(kwargs.get("cut"), "Primer parcial"), **kwargs}


def _cut(value):
    return value if value in dict(CUTS) else "primer_parcial"


def _pk(value):
    try:
        result = int(value)
        if result < 1:
            raise ValueError
        return result
    except (TypeError, ValueError, OverflowError):
        raise Http404("El identificador del registro no es válido.") from None


def _form_error(form, exc):
    errors = exc.messages if isinstance(exc, ValidationError) else [str(exc)]
    for error in errors:
        form.add_error(None, error)


def _predictions(user):
    return services.visible_predictions(user).filter(alert=True).select_related("indicator__enrollment__student__user", "indicator__enrollment__group__period").order_by("-created_at")


@login_required
def dashboard(request):
    role = services.role_for(request.user)
    destination = {"docente": "portal:teacher", "estudiante": "portal:student", "tutor": "portal:tutor"}.get(role)
    if destination:
        return redirect(destination)
    return render(request, "portal/dashboard.html", _context(request))


@role_required("docente")
def teacher(request):
    groups = services.visible_groups(request.user).select_related("period").order_by("name", "subject")
    selected_group = None
    group_id = request.GET.get("group")
    if group_id:
        selected_group = get_object_or_404(groups, pk=_pk(group_id))
    elif groups.exists():
        selected_group = groups.first()
    cut = _cut(request.GET.get("cut"))
    enrollments = services.teacher_enrollments(request.user, selected_group.pk).select_related("student__user", "group__period").order_by("student__code") if selected_group else Enrollment.objects.none()
    page = _page(request, enrollments)
    page_enrollments = list(page.object_list)
    current_indicators = {item.enrollment_id: item for item in services.visible_indicators(request.user).filter(enrollment_id__in=[item.pk for item in page_enrollments], cut=cut)}
    prediction_map = {}
    for prediction in Prediction.objects.filter(indicator__in=list(current_indicators.values())).select_related("indicator").order_by("-created_at"):
        prediction_map.setdefault(prediction.indicator_id, prediction)
    rows = [{"enrollment": enrollment, "indicator": current_indicators.get(enrollment.pk), "prediction": prediction_map.get(current_indicators[enrollment.pk].pk) if enrollment.pk in current_indicators else None} for enrollment in page_enrollments]
    return render(request, "portal/teacher.html", _context(request, groups=groups, selected_group=selected_group, cut=cut, page=page, rows=rows, enrollment_count=enrollments.count(), captured_count=services.visible_indicators(request.user).filter(enrollment__in=enrollments, cut=cut).count()))


@role_required("docente")
def indicator_edit(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment.objects.filter(group__in=services.visible_groups(request.user)).select_related("student__user", "group__period"), pk=enrollment_id)
    cut = _cut(request.POST.get("cut") if request.method == "POST" else request.GET.get("cut"))
    indicator = services.visible_indicators(request.user).filter(enrollment=enrollment, cut=cut).first()
    initial = {"cut": cut, "expected_version": indicator.version if indicator else 0}
    if indicator:
        initial.update(grade=indicator.grade, attendance=indicator.attendance, homework=indicator.homework)
    form = IndicatorForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            services.save_indicator(request.user, enrollment_id, **form.cleaned_data)
        except (ValidationError, services.ConflictError) as exc:
            _form_error(form, exc)
        else:
            messages.success(request, "Indicadores guardados. Ya puedes calcular el riesgo con estos datos.")
            return redirect(f"{_teacher_url()}?group={enrollment.group_id}&cut={cut}")
    return render(request, "portal/indicator_form.html", _context(request, form=form, enrollment=enrollment, cut=cut, indicator=indicator))


def _teacher_url():
    from django.urls import reverse
    return reverse("portal:teacher")


@role_required("docente")
def import_indicators(request, group_id):
    group = get_object_or_404(services.visible_groups(request.user).select_related("period"), pk=group_id)
    cut = _cut(request.POST.get("cut") if request.method == "POST" else request.GET.get("cut"))
    enrollments = services.teacher_enrollments(request.user, group_id)
    versions = {str(item.pk): 0 for item in enrollments}
    versions.update({str(item.enrollment_id): item.version for item in services.visible_indicators(request.user).filter(enrollment__in=enrollments, cut=cut)})
    snapshot = signing.dumps({"user": request.user.pk, "group": group_id, "cut": cut, "versions": versions}, salt="messi-import-v1", compress=True)
    form = ImportForm(request.POST or None, request.FILES or None, initial={"cut": cut, "snapshot": snapshot})
    if request.method == "POST" and form.is_valid():
        try:
            payload = signing.loads(form.cleaned_data["snapshot"], salt="messi-import-v1", max_age=3600)
            if payload.get("user") != request.user.pk or payload.get("group") != group_id or payload.get("cut") != form.cleaned_data["cut"]:
                raise ValidationError("La captura de versiones no corresponde a este grupo. Recarga la página e intenta de nuevo.")
            upload = form.cleaned_data["file"]
            raw = upload.read(5 * 1024 * 1024 + 1)
            records = load_excel(raw, allow_temporary_ids=False) if upload.name.lower().endswith(".xlsx") else load_csv(raw)
            services.import_indicators(request.user, group_id, form.cleaned_data["cut"], records, {int(key): value for key, value in payload["versions"].items()})
        except signing.BadSignature:
            form.add_error(None, "El formulario venció o cambió. Recarga esta página antes de importar.")
        except (ValidationError, DataValidationError, services.ConflictError) as exc:
            _form_error(form, exc)
        else:
            messages.success(request, f"Se importaron {len(records)} estudiantes. Los datos del grupo están disponibles para análisis.")
            return redirect(f"{_teacher_url()}?group={group_id}&cut={cut}")
    return render(request, "portal/import_form.html", _context(request, form=form, group=group, cut=cut))


@role_required("docente")
@require_POST
def predict(request, indicator_id):
    indicator = get_object_or_404(services.visible_indicators(request.user).select_related("enrollment"), pk=indicator_id)
    try:
        version = int(request.POST.get("expected_version", ""))
    except ValueError:
        messages.error(request, "Recarga el grupo para calcular con la versión actual de los indicadores.")
    else:
        try:
            services.calculate_risk(request.user, indicator_id, version)
        except ModelUnavailable:
            messages.error(request, "El modelo demostrativo no está disponible. Pide al administrador que revise su instalación. Las solicitudes y el seguimiento siguen disponibles.")
        except (ValidationError, services.ConflictError) as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, "Análisis completado. Revisa la puntuación y el contexto antes de tomar una decisión.")
    return redirect(f"{_teacher_url()}?group={indicator.enrollment.group_id}&cut={indicator.cut}")


@role_required("docente")
def import_template(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="plantilla_messi.csv"'
    response.write("\ufeff")
    csv.writer(response).writerow(["id_estudiante", "nota_parcial", "asistencia", "tareas_entregadas"])
    return response


@role_required("docente")
def export_indicators(request):
    indicators = services.visible_indicators(request.user).select_related("enrollment__student", "enrollment__group__period").order_by("enrollment__student__code", "cut")
    if request.GET.get("group"):
        group = get_object_or_404(services.visible_groups(request.user), pk=_pk(request.GET["group"]))
        indicators = indicators.filter(enrollment__group=group)
    if request.GET.get("cut"):
        indicators = indicators.filter(cut=_cut(request.GET["cut"]))
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="indicadores_messi.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["id_estudiante", "periodo", "grupo", "materia", "parcial", "nota_parcial", "asistencia", "tareas_entregadas", "version"])
    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
    for indicator in indicators.iterator():
        group = indicator.enrollment.group
        writer.writerow([safe(indicator.enrollment.student.code), safe(group.period.name), safe(group.name), safe(group.subject), indicator.cut, indicator.grade, indicator.attendance, indicator.homework, indicator.version])
    return response


@role_required("estudiante")
def student(request):
    requests = services.visible_requests(request.user).select_related("period").order_by("-created_at")
    cases = services.visible_cases(request.user).select_related("period", "tutor").order_by("-updated_at")
    indicators = services.visible_indicators(request.user).select_related("enrollment__group__period").order_by("enrollment__group__subject", "cut")
    return render(request, "portal/student.html", _context(request, request_page=_page(request, requests, "requests_page", 10), cases_page=_page(request, cases, "cases_page", 10), indicators_page=_page(request, indicators, "indicators_page", 10), request_count=requests.count(), case_count=cases.count()))


@role_required("estudiante")
def request_create(request):
    periods = Period.objects.filter(pk__in=Enrollment.objects.filter(student__user=request.user).values("group__period_id"), is_open=True).distinct().order_by("-starts_on")
    form = RequestForm(request.POST or None, periods=periods)
    if request.method == "POST" and form.is_valid():
        try:
            services.create_request(request.user, form.cleaned_data["period"].pk, form.cleaned_data["message"])
        except (ValidationError, services.ConflictError) as exc:
            _form_error(form, exc)
        else:
            messages.success(request, "Tu solicitud se envió. Tu tutor podrá revisarla y registrar un acuerdo contigo.")
            return redirect("portal:student")
    return render(request, "portal/request_form.html", _context(request, form=form, has_periods=periods.exists()))


@role_required("tutor")
def tutor(request):
    requests = services.visible_requests(request.user).select_related("student__user", "period").order_by("-created_at")
    cases = services.visible_cases(request.user).select_related("student__user", "period").order_by("-updated_at")
    predictions = _predictions(request.user)
    return render(request, "portal/tutor.html", _context(request, requests_page=_page(request, requests, "requests_page", 10), cases_page=_page(request, cases, "cases_page", 10), alerts_page=_page(request, predictions, "alerts_page", 10), pending_count=requests.filter(status="Pendiente").count(), active_count=cases.exclude(status="Cerrado").count(), student_count=services.visible_students(request.user).count()))


@role_required("tutor")
def case_create(request):
    periods = Period.objects.filter(pk__in=TutorAssignment.objects.filter(tutor=request.user).values("period_id"), is_open=True).distinct().order_by("-starts_on")
    requests = services.visible_requests(request.user).filter(status="Pendiente").select_related("student__user", "period")
    predictions = _predictions(request.user)
    # A stale prediction stays visible in the history but cannot open a new case.
    predictions = predictions.filter(indicator_version=F("indicator__version"), case__isnull=True)
    initial = {}
    if request.GET.get("request"):
        linked = get_object_or_404(requests, pk=_pk(request.GET["request"]))
        initial = {"student": linked.student_id, "period": linked.period_id, "request": linked.pk}
    elif request.GET.get("prediction"):
        linked = get_object_or_404(predictions, pk=_pk(request.GET["prediction"]))
        initial = {"student": linked.indicator.enrollment.student_id, "period": linked.indicator.enrollment.group.period_id, "prediction": linked.pk}
    form = CaseForm(request.POST or None, initial=initial, students=services.visible_students(request.user).select_related("user"), periods=periods, requests=requests, predictions=predictions)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            case = services.create_case(request.user, data["student"].pk, data["period"].pk, data["agreement"], internal_notes=data["internal_notes"], request_id=data["request"].pk if data["request"] else None, prediction_id=data["prediction"].pk if data["prediction"] else None)
        except (ValidationError, services.ConflictError) as exc:
            _form_error(form, exc)
        else:
            messages.success(request, "Caso creado. El estudiante ya puede consultar el acuerdo de apoyo.")
            return redirect("portal:case_detail", case_id=case.pk)
    return render(request, "portal/case_form.html", _context(request, form=form))


@login_required
def case_detail(request, case_id):
    role = services.role_for(request.user)
    if role not in ("tutor", "estudiante"):
        raise PermissionDenied("Tu cuenta no tiene acceso a los casos de apoyo.")
    case = get_object_or_404(services.visible_cases(request.user).select_related("student__user", "period", "tutor", "request", "prediction__indicator"), pk=case_id)
    from .models import FollowUp
    followups = FollowUp.objects.filter(case=case).select_related("author").order_by("-created_at")
    form = FollowUpForm(initial={"expected_version": case.version, "status": case.status}) if role == "tutor" else None
    return render(request, "portal/case_detail.html", _context(request, case=case, followups=_page(request, followups, "page", 20), form=form))


@role_required("tutor")
@require_POST
def followup_create(request, case_id):
    case = get_object_or_404(services.visible_cases(request.user).select_related("student__user", "period", "tutor", "request", "prediction__indicator"), pk=case_id)
    form = FollowUpForm(request.POST)
    if form.is_valid():
        try:
            services.add_followup(request.user, case_id, **form.cleaned_data)
        except (ValidationError, services.ConflictError) as exc:
            _form_error(form, exc)
        else:
            messages.success(request, "Seguimiento guardado y estado actualizado.")
            return redirect("portal:case_detail", case_id=case_id)
    from .models import FollowUp
    return render(request, "portal/case_detail.html", _context(request, case=case, followups=_page(request, FollowUp.objects.filter(case=case).select_related("author").order_by("-created_at")), form=form))
