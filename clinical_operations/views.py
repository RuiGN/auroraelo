"""API de sessão, CSRF obrigatório, sem conteúdo bruto em erros/auditoria."""

import json
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, RequestDataTooBig, ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from .forms import COMMANDS, validate_payload
from .selectors import list_resources, read_records
from .services import Conflict


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("Chave JSON duplicada.")
        result[key] = value
    return result


@never_cache
@csrf_protect
def endpoint(request, resource):
    if getattr(settings, "CLINICAL_OPERATIONS_ENABLED", False) is not True:
        return JsonResponse({"error": "clinical_operations_disabled"}, status=503)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "authentication_required"}, status=401)
    clinic = getattr(request, "clinic", None)
    if clinic is None:
        return JsonResponse({"error": "clinic_required"}, status=403)
    try:
        common = {"actor": request.user, "clinic_id": clinic.pk}
        if request.method == "GET" and resource in {
            "products",
            "lots",
            "movements",
            "encounters",
            "sessions",
            "enrollments",
            "records",
        }:
            allowed = (
                {"offset", "encounter_id"} if resource == "records" else {"offset"}
            )
            if set(request.GET) - allowed or any(
                len(request.GET.getlist(k)) != 1 for k in request.GET
            ):
                raise ValidationError("Consulta inválida.")
            offset = int(request.GET.get("offset", "0"))
            if not 0 <= offset <= 10000:
                raise ValidationError("Paginação inválida.")
            if resource == "records":
                encounter_id = UUID(request.GET.get("encounter_id", ""))
                rows = [
                    {"id": str(r.pk), "content": r.content, "created_at": r.created_at}
                    for r in read_records(
                        **common, encounter_id=encounter_id, offset=offset
                    )
                ]
            else:
                rows = list_resources(**common, resource=resource, offset=offset)
            return JsonResponse({"results": rows, "offset": offset, "limit": 100})
        if request.method != "POST":
            response = JsonResponse({"error": "method_not_allowed"}, status=405)
            response["Allow"] = "POST"
            return response
        if request.content_type != "application/json":
            return JsonResponse({"error": "json_required"}, status=415)
        if (
            int(request.META.get("CONTENT_LENGTH") or 0) > 16384
            or len(request.body) > 16384
        ):
            return JsonResponse({"error": "payload_too_large"}, status=413)
        try:
            payload = json.loads(request.body, object_pairs_hook=_pairs)
        except RecursionError as exc:
            raise ValidationError("JSON inválido.") from exc
        command, form = COMMANDS[resource]
        result = command(**common, **validate_payload(form, payload))
        return JsonResponse({"id": str(result.pk)}, status=201)
    except PermissionDenied:
        return JsonResponse({"error": "access_denied"}, status=403)
    except Conflict as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    except IntegrityError:
        return JsonResponse({"error": "integrity_conflict"}, status=409)
    except RequestDataTooBig:
        return JsonResponse({"error": "payload_too_large"}, status=413)
    except ValidationError, ValueError, TypeError, UnicodeDecodeError:
        return JsonResponse({"error": "invalid_payload"}, status=400)
