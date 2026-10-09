"""Administración organizacional; las notas de expedientes no se exponen aquí."""
from django.contrib import admin
from django.db import transaction

from .models import AuditEvent, CourseGroup, Enrollment, Period, Profile, Student, SupportCase, TutorAssignment


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role"]
    list_filter = ["role"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]

    def get_readonly_fields(self, request, obj=None):
        return ["user"] if obj else []


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["code", "user"]
    search_fields = ["code", "user__username"]

    def get_readonly_fields(self, request, obj=None):
        return ["user", "code"] if obj else []


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ["name", "starts_on", "ends_on", "is_open"]


@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "period"]
    list_filter = ["period"]
    filter_horizontal = ["teachers"]

    def get_readonly_fields(self, request, obj=None):
        return ["period"] if obj else []


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "group"]
    list_filter = ["group__period", "group"]

    def get_readonly_fields(self, request, obj=None):
        return ["student", "group"] if obj else []


@admin.register(TutorAssignment)
class TutorAssignmentAdmin(admin.ModelAdmin):
    list_display = ["tutor", "student", "period"]
    list_filter = ["period", "tutor"]

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # La reasignación transfiere los casos existentes en el mismo periodo.
        for case in SupportCase.objects.select_for_update().filter(student=obj.student, period=obj.period).exclude(tutor=obj.tutor):
            case.tutor = obj.tutor
            case.version += 1
            case.save(update_fields=["tutor", "version", "updated_at"])
            AuditEvent.objects.create(author=request.user, action="reasignar_tutor", entity="supportcase", entity_id=case.pk)

    def get_readonly_fields(self, request, obj=None):
        return ["student", "period"] if obj else []


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "author", "action", "entity", "entity_id"]
    list_filter = ["action", "entity"]
    readonly_fields = ["author", "action", "entity", "entity_id", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
