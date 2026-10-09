"""Datos de exposición aislados: sólo se crean con petición explícita."""
import getpass
import os
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from portal.models import CourseGroup, Enrollment, Period, Profile, Student, TutorAssignment
from portal.services import save_indicator


class Command(BaseCommand):
    help = "Crea cuatro cuentas y un grupo ficticio sólo en desarrollo. Contraseña por entrada oculta o MESSI_DEMO_PASSWORD."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("La carga de demostración está deshabilitada en producción.")
        names = ["admin_demo", "docente_demo", "estudiante_demo", "tutor_demo"]
        User = get_user_model()
        if User.objects.filter(username__in=names).exists():
            raise CommandError("Ya existen cuentas de demostración. No se modificarán sus contraseñas ni datos.")
        password = os.environ.get("MESSI_DEMO_PASSWORD") or getpass.getpass("Contraseña para las cuatro cuentas ficticias: ")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        users = {}
        for role in ["admin", "docente", "estudiante", "tutor"]:
            users[role] = User.objects.create_user(f"{role}_demo", password=password,
                first_name={"admin": "Administración", "docente": "Docente", "estudiante": "Alumno", "tutor": "Tutor"}[role],
                last_name="Demostración", is_staff=role == "admin", is_superuser=role == "admin")
            Profile.objects.create(user=users[role], role=role)
        student = Student.objects.create(user=users["estudiante"], code="EST-001")
        period, _ = Period.objects.get_or_create(name="Demostración 2026", defaults={
            "starts_on": date(2026, 8, 1), "ends_on": date(2026, 12, 31), "is_open": True})
        group, _ = CourseGroup.objects.get_or_create(name="Grupo demo", subject="Matemáticas", period=period)
        group.teachers.add(users["docente"])
        enrollment = Enrollment.objects.create(student=student, group=group)
        TutorAssignment.objects.create(tutor=users["tutor"], student=student, period=period)
        save_indicator(users["docente"], enrollment.pk, "primer_parcial", 5, 70, 60, 0)
        self.stdout.write(self.style.SUCCESS("Cuentas ficticias creadas: " + ", ".join(names)))
        self.stdout.write("Usa la contraseña que proporcionaste. No se imprimió ni se guardó en texto plano.")
