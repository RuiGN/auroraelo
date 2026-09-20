"""Fronteira de autorização local: identidade atual, tenant e papel explícitos."""

from functools import wraps

from django.core.exceptions import PermissionDenied, RequestDataTooBig, ValidationError
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from clinics.policies import ClinicAuthorizationPolicy, has_active_clinic_role
from core.policies import current_actor_is_active

from .validation import PayloadTooLargeError


def require_actor(actor):
    if actor is None or not current_actor_is_active(actor):
        raise PermissionDenied("Autenticação ativa necessária.")


def require_domain_access(*, actor, clinic=None, mode="clinical"):
    require_actor(actor)
    if mode == "b2c":
        return
    if clinic is None:
        raise PermissionDenied("Clínica ativa necessária.")
    if mode == "clinical":
        allowed = ClinicAuthorizationPolicy().is_allowed(
            actor, clinic, "patient.clinical.read"
        )
    elif mode == "patient":
        allowed = has_active_clinic_role(
            clinic_id=clinic.pk,
            user_id=actor.pk,
            role="patient",
            on_date=timezone.localdate(),
        )
    else:
        allowed = False
    if not allowed:
        raise PermissionDenied("Acesso não autorizado.")


def domain_access(mode="clinical"):
    """A view valida autorização mesmo quando o middleware não foi executado."""

    def decorator(view):
        protected = csrf_protect(view)

        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                require_domain_access(
                    actor=request.user,
                    clinic=getattr(request, "clinic", None),
                    mode=mode,
                )
                return protected(request, *args, **kwargs)
            except PayloadTooLargeError, RequestDataTooBig:
                return JsonResponse(
                    {"success": False, "error": "Payload excede o limite."}, status=413
                )
            except ValidationError:
                return JsonResponse(
                    {"success": False, "error": "Dados inválidos."}, status=400
                )
            except Http404:
                return JsonResponse(
                    {"success": False, "error": "Registro indisponível."}, status=404
                )
            except PermissionDenied:
                status = 403 if request.user.is_authenticated else 401
                return JsonResponse(
                    {"success": False, "error": "Acesso não autorizado."}, status=status
                )

        # Inclui erros de autorização, validação e CSRF produzidos nesta fronteira.
        return never_cache(wrapped)

    return decorator
