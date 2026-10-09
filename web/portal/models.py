"""Expedientes compartidos. La autorización se aplica en servicios y vistas."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q, F


class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        TEACHER = "docente", "Docente"
        STUDENT = "estudiante", "Estudiante"
        TUTOR = "tutor", "Tutor"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField("Rol", max_length=16, choices=Role.choices)

    def __str__(self):
        return f"{self.user} — {self.get_role_display()}"

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"
        constraints = [models.CheckConstraint(condition=Q(role__in=["admin", "docente", "estudiante", "tutor"]), name="profile_valid_role")]


class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student")
    code = models.CharField("Código", max_length=12, unique=True, validators=[RegexValidator(r"\AEST-[0-9]{3,8}\Z", "Usa EST- seguido de 3 a 8 dígitos.")])

    def __str__(self):
        return f"{self.code} · {self.user.get_full_name() or self.user.username}"

    def clean(self):
        if self.user_id and not Profile.objects.filter(user_id=self.user_id, role="estudiante").exists():
            raise ValidationError("El usuario del alumno debe tener un perfil de estudiante.")

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = ["code"]


class Period(models.Model):
    name = models.CharField("Nombre", max_length=80, unique=True)
    starts_on = models.DateField("Inicio")
    ends_on = models.DateField("Fin")
    is_open = models.BooleanField("Captura abierta", default=True)

    def __str__(self):
        return self.name

    def clean(self):
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError("El fin del periodo debe ser posterior al inicio.")

    class Meta:
        verbose_name = "Periodo"
        verbose_name_plural = "Periodos"
        ordering = ["-starts_on"]
        constraints = [models.CheckConstraint(condition=Q(ends_on__gte=F("starts_on")), name="period_valid_dates")]


class CourseGroup(models.Model):
    name = models.CharField("Grupo", max_length=80)
    subject = models.CharField("Materia", max_length=100)
    period = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="groups", verbose_name="Periodo")
    teachers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="teaching_groups", verbose_name="Docentes", blank=True, limit_choices_to={"profile__role": "docente", "is_active": True})

    def __str__(self):
        return f"{self.name} · {self.subject} · {self.period}"

    class Meta:
        verbose_name = "Grupo y materia"
        verbose_name_plural = "Grupos y materias"
        ordering = ["name", "subject"]
        constraints = [models.UniqueConstraint(fields=["name", "subject", "period"], name="unique_course_group")]


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrollments", verbose_name="Estudiante")
    group = models.ForeignKey(CourseGroup, on_delete=models.PROTECT, related_name="enrollments", verbose_name="Grupo y materia")

    def __str__(self):
        return f"{self.student.code} · {self.group}"

    class Meta:
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"
        constraints = [models.UniqueConstraint(fields=["student", "group"], name="unique_enrollment")]


class TutorAssignment(models.Model):
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tutor_assignments", verbose_name="Tutor", limit_choices_to={"profile__role": "tutor", "is_active": True})
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="tutor_assignments", verbose_name="Estudiante")
    period = models.ForeignKey(Period, on_delete=models.PROTECT, verbose_name="Periodo")

    def clean(self):
        if self.tutor_id and not Profile.objects.filter(user_id=self.tutor_id, role="tutor", user__is_active=True).exists():
            raise ValidationError("Asigna una cuenta activa con rol de tutor.")
        if self.student_id and self.period_id and not Enrollment.objects.filter(student_id=self.student_id, group__period_id=self.period_id).exists():
            raise ValidationError("El estudiante debe estar inscrito en este periodo.")

    def __str__(self):
        return f"{self.tutor} · {self.student.code} · {self.period}"

    class Meta:
        verbose_name = "Asignación de tutor"
        verbose_name_plural = "Asignaciones de tutores"
        constraints = [models.UniqueConstraint(fields=["student", "period"], name="one_tutor_per_student_period")]


class Indicator(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name="indicators")
    cut = models.CharField("Corte", max_length=40, default="primer_parcial", validators=[RegexValidator(r"\A[a-z0-9_]{1,40}\Z", "Usa letras minúsculas, números o guion bajo.")])
    grade = models.DecimalField("Calificación", max_digits=4, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(10)])
    attendance = models.DecimalField("Asistencia (%)", max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    homework = models.DecimalField("Tareas (%)", max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.enrollment} · {self.cut}"

    class Meta:
        ordering = ["enrollment__student__code", "cut"]
        constraints = [
            models.UniqueConstraint(fields=["enrollment", "cut"], name="unique_indicator_cut"),
            models.CheckConstraint(condition=Q(grade__gte=0, grade__lte=10), name="indicator_grade_range"),
            models.CheckConstraint(condition=Q(attendance__gte=0, attendance__lte=100), name="indicator_attendance_range"),
            models.CheckConstraint(condition=Q(homework__gte=0, homework__lte=100), name="indicator_homework_range"),
            models.CheckConstraint(condition=Q(version__gte=1), name="indicator_positive_version"),
        ]


class Prediction(models.Model):
    indicator = models.ForeignKey(Indicator, on_delete=models.PROTECT, related_name="predictions")
    indicator_version = models.PositiveIntegerField()
    grade = models.DecimalField(max_digits=4, decimal_places=2)
    attendance = models.DecimalField(max_digits=5, decimal_places=2)
    homework = models.DecimalField(max_digits=5, decimal_places=2)
    score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    threshold = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    model_version = models.CharField(max_length=64)
    alert = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_current(self):
        return self.indicator_version == self.indicator.version

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["indicator", "indicator_version", "model_version"], name="unique_prediction_version"),
            models.CheckConstraint(condition=Q(score__gte=0, score__lte=1, threshold__gt=0, threshold__lt=1), name="prediction_valid_score"),
        ]


class HelpRequest(models.Model):
    STATUSES = [("Pendiente", "Pendiente"), ("Atendida", "Atendida")]
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="requests")
    period = models.ForeignKey(Period, on_delete=models.PROTECT)
    message = models.CharField("Solicitud", max_length=1000)
    status = models.CharField(max_length=20, choices=STATUSES, default="Pendiente")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(status__in=["Pendiente", "Atendida"]), name="request_valid_status")]


class SupportCase(models.Model):
    STATUSES = [("Pendiente", "Pendiente"), ("En seguimiento", "En seguimiento"), ("Cerrado", "Cerrado")]
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="cases")
    period = models.ForeignKey(Period, on_delete=models.PROTECT)
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cases")
    request = models.OneToOneField(HelpRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="case")
    prediction = models.OneToOneField(Prediction, null=True, blank=True, on_delete=models.PROTECT, related_name="case")
    agreement = models.CharField("Acuerdo visible al estudiante", max_length=1000)
    internal_notes = models.CharField("Nota interna", max_length=1000, blank=True)
    status = models.CharField("Estado", max_length=20, choices=STATUSES, default="Pendiente")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.CheckConstraint(condition=Q(status__in=["Pendiente", "En seguimiento", "Cerrado"], version__gte=1), name="case_valid_status_version")]


class FollowUp(models.Model):
    STATUSES = SupportCase.STATUSES
    case = models.ForeignKey(SupportCase, on_delete=models.PROTECT, related_name="followups")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    notes = models.CharField("Avance visible al estudiante", max_length=1000)
    internal_notes = models.CharField("Nota interna", max_length=1000, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(status__in=["Pendiente", "En seguimiento", "Cerrado"]), name="followup_valid_status")]


class AuditEvent(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    entity = models.CharField(max_length=40)
    entity_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class LoginAttempt(models.Model):
    key = models.CharField(max_length=64, unique=True)
    failures = models.PositiveIntegerField(default=0)
    window_started = models.DateTimeField(auto_now_add=True)
    blocked_until = models.DateTimeField(null=True, blank=True)
