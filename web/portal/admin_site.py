from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError
from django.urls import reverse

from config.auth import ThrottledLoginView


class MessiAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        from .services import role_for
        if role_for(user) != "admin":
            raise ValidationError("Esta cuenta no tiene acceso a la administración.", code="invalid_login")


class MessiAdminSite(AdminSite):
    site_header = "Administración de MESSI"
    site_title = "MESSI"
    index_title = "Cuentas y organización escolar"

    def has_permission(self, request):
        from .services import role_for
        return request.user.is_active and request.user.is_staff and role_for(request.user) == "admin"

    def login(self, request, extra_context=None):
        context = {**self.each_context(request), "title": "Iniciar sesión", "app_path": request.get_full_path(),
            "username": request.user.get_username(), **(extra_context or {})}
        if request.method == "GET" and self.has_permission(request):
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(reverse("admin:index", current_app=self.name))
        request.current_app = self.name
        return ThrottledLoginView.as_view(template_name="admin/login.html",
            authentication_form=MessiAdminAuthenticationForm, extra_context=context,
            redirect_authenticated_user=False)(request)
