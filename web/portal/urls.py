from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("docente/", views.teacher, name="teacher"),
    path("docente/indicadores/<int:enrollment_id>/", views.indicator_edit, name="indicator_edit"),
    path("docente/importar/<int:group_id>/", views.import_indicators, name="import_indicators"),
    path("docente/calcular/<int:indicator_id>/", views.predict, name="predict"),
    path("docente/exportar/", views.export_indicators, name="export_indicators"),
    path("docente/plantilla/", views.import_template, name="import_template"),
    path("estudiante/", views.student, name="student"),
    path("estudiante/solicitar/", views.request_create, name="request_create"),
    path("tutor/", views.tutor, name="tutor"),
    path("tutor/casos/nuevo/", views.case_create, name="case_create"),
    path("casos/<int:case_id>/", views.case_detail, name="case_detail"),
    path("tutor/casos/<int:case_id>/seguimiento/", views.followup_create, name="followup_create"),
]
