"""JSON B2C isolado, sem prontuários, sessões de chat ou seleção de clínica."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.utils.translation import override
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from .recovery_access import AccessDeniedError, authorize
from .recovery_knowledge import (
    TOPICS,
    KnowledgeUnavailableError,
    read_corpus,
    redis_client,
    retrieve,
    strict_json,
    text,
)
from .recovery_provider import ProviderUnavailableError, configuration, generate
from .recovery_safety import IDENTITY, safety_response
from .recovery_usage import UsageExceededError, consume_usage


class RequestRejectedError(ValueError):
    def __init__(self, code: str, detail: str, status: int = 400) -> None:
        self.code, self.detail, self.status = code, detail, status
        super().__init__(detail)


def response(payload: dict[str, Any], status: int = 200) -> JsonResponse:
    result = JsonResponse({"identity": IDENTITY, **payload}, status=status)
    result["Cache-Control"] = "no-store"
    result["Content-Language"] = "pt-br"
    result["X-Content-Type-Options"] = "nosniff"
    return result


def _input(request: HttpRequest, assistant: bool) -> dict[str, Any]:
    if request.method != "POST":
        raise RequestRejectedError("method_not_allowed", _("Use POST."), 405)
    if request.GET or request.META.get("HTTP_X_CLINIC_ID"):
        raise RequestRejectedError(
            "invalid_input", _("Não envie seleção de clínica ou querystring.")
        )
    if request.content_type != "application/json":
        raise RequestRejectedError(
            "unsupported_media_type", _("Envie application/json."), 415
        )
    length = request.META.get("CONTENT_LENGTH", "0")
    if not str(length).isdigit() or int(length) > 16384:
        raise RequestRejectedError(
            "payload_too_large", _("Corpo acima do limite."), 413
        )
    if len(request.body) > 16384:
        raise RequestRejectedError(
            "payload_too_large", _("Corpo acima do limite."), 413
        )
    payload = strict_json(request.body)
    field = "message" if assistant else "query"
    allowed = {field, "language", "topics"} | ({"history"} if assistant else set())
    if not isinstance(payload, dict) or set(payload) - allowed or field not in payload:
        raise ValueError
    text(payload[field], 2000)
    topics = payload.setdefault("topics", [])
    if (
        not isinstance(topics, list)
        or len(topics) > 8
        or any(not isinstance(topic, str) or topic not in TOPICS for topic in topics)
        or len(set(topics)) != len(topics)
    ):
        raise ValueError
    history = payload.setdefault("history", [])
    if not isinstance(history, list) or len(history) > 6:
        raise ValueError
    for turn in history:
        if (
            not isinstance(turn, dict)
            or set(turn) != {"role", "content"}
            or turn["role"] not in {"user", "assistant"}
        ):
            raise ValueError
        text(turn["content"], 1000)
    if sum(len(turn["content"]) for turn in history) + len(payload[field]) > 8000:
        raise ValueError
    language = payload.setdefault("language", "pt-br")
    if language not in ("pt-br", "en", "es"):
        raise ValueError
    if language != "pt-br":
        raise RequestRejectedError(
            "unsupported_content_language",
            _(
                "O conteúdo educativo está disponível apenas em português do Brasil. "
                "As versões em inglês e espanhol ainda não foram validadas."
            ),
            422,
        )
    return payload


def _serve(request: HttpRequest, *, assistant: bool) -> JsonResponse:
    # A resposta educativa é deliberadamente pt-br, mesmo em sessão en/es.
    with override("pt-br"):
        try:
            if not request.user.is_authenticated:
                return response(
                    {"code": "authentication_required", "detail": _("Autentique-se.")},
                    401,
                )
            payload = _input(request, assistant)
            purpose = "recovery_ai" if assistant else "recovery_library"
            authorize(request.user, purpose)
            message = payload["message" if assistant else "query"]
            safety = safety_response(
                "\n".join(
                    [
                        message,
                        *(turn["content"] for turn in payload["history"]),
                    ]
                )
            )
            if safety is not None:
                return response(safety)
            if assistant:
                configuration()  # Kill switch antes da leitura; sem fallback LLM.
            with redis_client() as client:
                consume_usage(client, request.user.pk)
                corpus = read_corpus(
                    client, getattr(settings, "RECOVERY_KNOWLEDGE_VERSION", "")
                )
                sources = retrieve(corpus, query=message, topics=payload["topics"])
            if not sources:
                return response(
                    {
                        "code": "no_evidence",
                        "mode": "library",
                        "sources": [],
                        "detail": _(
                            "Não há evidência correspondente nesta biblioteca. "
                            "Não vou formular uma resposta sem fontes."
                        ),
                    },
                    422,
                )
            authorize(request.user, purpose)
            if assistant:
                result = generate(
                    message=message, history=payload["history"], sources=sources
                )
                authorize(request.user, purpose)
                configuration()  # Desativação durante a chamada descarta o resultado.
                return response(
                    {
                        "mode": "assistant",
                        **result,
                        "sources": sources,
                        "content_language": "pt-br",
                        "corpus_version": corpus.version,
                        "notice": _(
                            "Apoio educativo por IA, não terapia. "
                            "Confira as fontes e suas limitações com um profissional."
                        ),
                    }
                )
            return response(
                {
                    "mode": "library",
                    "retrieval": "lexical",
                    "sources": sources,
                    "corpus_version": corpus.version,
                    "content_language": "pt-br",
                    "quote_language": "original",
                    "supported_content_languages": ["pt-br"],
                    "notice": _(
                        "Trechos educativos, não terapia, diagnóstico "
                        "ou resposta clínica. "
                        "Busca textual sem embeddings ou treinamento. "
                        "As citações permanecem no idioma original da fonte."
                    ),
                }
            )
        except RequestRejectedError as exc:
            return response({"code": exc.code, "detail": exc.detail}, exc.status)
        except AccessDeniedError:
            return response(
                {
                    "code": "consent_required",
                    "detail": _("Acesso requer consentimento expresso vigente."),
                },
                403,
            )
        except ValueError, TypeError:
            return response(
                {
                    "code": "invalid_input",
                    "detail": _("Entrada inválida ou acima dos limites."),
                },
                400,
            )
        except ProviderUnavailableError:
            return response(
                {
                    "code": "assistant_unavailable",
                    "detail": _("Assistente de IA indisponível."),
                },
                503,
            )
        except UsageExceededError:
            limited = response(
                {
                    "code": "usage_limit",
                    "detail": _("Limite de uso atingido. Tente mais tarde."),
                },
                429,
            )
            limited["Retry-After"] = "60"
            return limited
        except KnowledgeUnavailableError:
            return response(
                {
                    "code": "knowledge_unavailable",
                    "detail": _("Biblioteca temporariamente indisponível."),
                },
                503,
            )


def recovery_csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    """Hook opcional para o principal; não libera CSRF nem qualquer outro endpoint."""
    if request.path in {"/api/v1/recovery/library/", "/api/v1/recovery/assistant/"}:
        with override("pt-br"):
            return response(
                {"code": "csrf_failed", "detail": _("Validação CSRF recusada.")}, 403
            )
    from django.views.csrf import csrf_failure

    return csrf_failure(request, reason=reason)


@csrf_protect
@sensitive_post_parameters()
def recovery_library(request: HttpRequest) -> JsonResponse:
    return _serve(request, assistant=False)


@csrf_protect
@sensitive_post_parameters()
def recovery_assistant(request: HttpRequest) -> JsonResponse:
    return _serve(request, assistant=True)
