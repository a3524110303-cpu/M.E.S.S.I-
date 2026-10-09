"""Formularios del portal; los permisos y las escrituras viven en services."""

from django import forms

from .models import Period, Student, HelpRequest, Prediction, SupportCase

CUTS = [("primer_parcial", "Primer parcial")]

class IndicatorForm(forms.Form):
    cut = forms.ChoiceField(choices=CUTS, widget=forms.HiddenInput)
    grade = forms.DecimalField(label="Calificación", min_value=0, max_value=10, decimal_places=2, max_digits=4, widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0 a 10"}))
    attendance = forms.DecimalField(label="Asistencia (%)", min_value=0, max_value=100, decimal_places=2, max_digits=5, widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0 a 100"}))
    homework = forms.DecimalField(label="Tareas entregadas (%)", min_value=0, max_value=100, decimal_places=2, max_digits=5, widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0 a 100"}))
    expected_version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)


class ImportForm(forms.Form):
    cut = forms.ChoiceField(choices=CUTS, widget=forms.HiddenInput)
    file = forms.FileField(label="Archivo CSV o Excel", widget=forms.ClearableFileInput(attrs={"accept": ".csv,.xlsx"}))
    snapshot = forms.CharField(widget=forms.HiddenInput)

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El archivo supera el límite de 5 MB.")
        if not upload.name.lower().endswith((".csv", ".xlsx")):
            raise forms.ValidationError("Selecciona un archivo .csv o .xlsx.")
        return upload


class RequestForm(forms.Form):
    period = forms.ModelChoiceField(label="Periodo escolar", queryset=Period.objects.none(), empty_label="Selecciona un periodo")
    message = forms.CharField(label="¿En qué necesitas apoyo?", max_length=1000, widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Cuéntanos qué se te dificulta y qué apoyo necesitas."}))

    def __init__(self, *args, periods, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["period"].queryset = periods


class CaseForm(forms.Form):
    student = forms.ModelChoiceField(label="Estudiante", queryset=Student.objects.none(), empty_label="Selecciona un estudiante")
    period = forms.ModelChoiceField(label="Periodo escolar", queryset=Period.objects.none(), empty_label="Selecciona un periodo")
    request = forms.ModelChoiceField(label="Solicitud de apoyo", required=False, queryset=HelpRequest.objects.none(), empty_label="Sin solicitud vinculada")
    prediction = forms.ModelChoiceField(label="Alerta académica", required=False, queryset=Prediction.objects.none(), empty_label="Sin alerta vinculada")
    agreement = forms.CharField(label="Acuerdo de apoyo", max_length=1000, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Define las acciones, responsables y fecha de revisión. El estudiante puede leer este acuerdo."}))
    internal_notes = forms.CharField(label="Notas privadas del tutor", required=False, max_length=1000, widget=forms.Textarea(attrs={"rows": 3}), help_text="Solo son visibles para el tutor asignado. No incluyas información innecesaria.")

    def __init__(self, *args, students, periods, requests, predictions, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = students
        self.fields["period"].queryset = periods
        self.fields["request"].queryset = requests
        self.fields["prediction"].queryset = predictions
        self.fields["request"].label_from_instance = lambda item: f"#{item.pk} · {item.student.code} · {item.period.name}"
        self.fields["prediction"].label_from_instance = lambda item: f"#{item.pk} · {item.indicator.enrollment.student.code} · {item.indicator.enrollment.group.subject}"


class FollowUpForm(forms.Form):
    notes = forms.CharField(label="Avance y próximos pasos", max_length=1000, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Describe los avances y los próximos pasos. El estudiante puede leer este seguimiento."}))
    internal_notes = forms.CharField(label="Notas privadas del tutor", required=False, max_length=1000, widget=forms.Textarea(attrs={"rows": 3}))
    status = forms.ChoiceField(label="Estado del caso", choices=SupportCase._meta.get_field("status").choices)
    expected_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
