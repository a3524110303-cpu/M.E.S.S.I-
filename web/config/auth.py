"""Control compartido de intentos fallidos para todos los procesos WSGI."""

import math
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.forms.utils import ErrorDict
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters


@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class ThrottledLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        from portal.models import LoginAttempt

        # No se confía en X-Forwarded-For aportado por el visitante. Caddy envía
        # X-Real-IP; sólo se usa en producción detrás del puerto privado.
        ip = request.META.get("REMOTE_ADDR", "unknown")
        if settings.PRODUCTION:
            ip = request.META.get("HTTP_X_REAL_IP", ip)
        username = request.POST.get("username", "")[:150].casefold().strip()
        policies = {
            salted_hmac("messi.login.ip", ip).hexdigest(): settings.MESSI_LOGIN_IP_MAX_ATTEMPTS,
            salted_hmac("messi.login.account-ip", ip + "\0" + username).hexdigest(): settings.MESSI_LOGIN_MAX_ATTEMPTS,
        }
        now = timezone.now()
        window = timedelta(seconds=settings.MESSI_LOGIN_WINDOW_SECONDS)
        with transaction.atomic():
            attempts = []
            # Orden único para evitar bloqueos cruzados entre trabajadores.
            for key in sorted(policies):
                LoginAttempt.objects.get_or_create(key=key)
                attempt = LoginAttempt.objects.select_for_update().get(key=key)
                if attempt.blocked_until and attempt.blocked_until > now:
                    # Formulario sin validar: el bloqueo también evita el
                    # cálculo del hash de contraseña y consultas de usuario.
                    form = self.get_form_class()(request=request, initial={"username": username})
                    form._errors = ErrorDict()
                    form.cleaned_data = {}
                    form.add_error(None, "Demasiados intentos. Espera unos minutos e inténtalo de nuevo.")
                    response = self.form_invalid(form)
                    response.status_code = 429
                    response["Retry-After"] = str(max(1, math.ceil((attempt.blocked_until - now).total_seconds())))
                    return response
                if now - attempt.window_started >= window:
                    attempt.window_started = now
                    attempt.failures = 0
                    attempt.blocked_until = None
                attempts.append(attempt)

            form = self.get_form()
            if form.is_valid():
                # Una contraseña válida no borra el contador global de la IP.
                pair_key = salted_hmac("messi.login.account-ip", ip + "\0" + username).hexdigest()
                for attempt in attempts:
                    if attempt.key == pair_key:
                        attempt.failures = 0
                        attempt.blocked_until = None
                        attempt.window_started = now
                    attempt.save(update_fields=["failures", "blocked_until", "window_started"])
                return self.form_valid(form)

            for attempt in attempts:
                attempt.failures += 1
                if attempt.failures >= policies[attempt.key]:
                    attempt.blocked_until = now + timedelta(seconds=settings.MESSI_LOGIN_BLOCK_SECONDS)
                attempt.save(update_fields=["failures", "blocked_until", "window_started"])
            return self.form_invalid(form)
