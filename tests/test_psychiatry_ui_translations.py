"""Tradução das telas sanitizadas; sem banco ou aceite clínico."""

import gettext as python_gettext
import json
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext, override

SURFACES = (
    "addiction_dashboard.html",
    "anamnesis.html",
    "beds.html",
    "crisis_protocol.html",
    "mobile_b2c.html",
    "mobile_connected.html",
    "patients.html",
    "telepsychiatry_room.html",
    "twelve_steps_anamnesis.html",
)
LANGUAGES = ("pt-br", "en", "es")
LOCALES = {"pt-br": "pt_BR", "en": "en", "es": "es"}

# Expectativas literais, independentes do retorno de gettext/HTML sob teste.
COPY = {
    "connected": (
        "A agenda, as prescrições, o registro de tomadas e o SOS estão "
        "indisponíveis nesta prévia. Esta página não confirma tratamento ou "
        "atendimento.",
        "Scheduling, prescriptions, dose tracking and SOS are unavailable in "
        "this preview. This page does not confirm treatment or care.",
        "La agenda, las recetas, el registro de tomas y el SOS no están "
        "disponibles en esta vista previa. Esta página no confirma tratamiento "
        "ni atención.",
    ),
    "beds": (
        "A consulta de ocupação, a admissão e as comunicações de internação "
        "estão indisponíveis nesta interface. Nenhuma vaga está confirmada.",
        "Occupancy information, admissions and inpatient communications are "
        "unavailable in this interface. No bed availability is confirmed.",
        "La consulta de ocupación, los ingresos y las comunicaciones de "
        "hospitalización no están disponibles en esta interfaz. No se confirma "
        "ninguna plaza.",
    ),
    "telepsychiatry": (
        "A sala de vídeo, o registro da consulta e a emissão ou assinatura de "
        "documentos estão indisponíveis nesta interface.",
        "The video room, consultation records and document issuance or signing "
        "are unavailable in this interface.",
        "La sala de vídeo, el registro de la consulta y la emisión o firma de "
        "documentos no están disponibles en esta interfaz.",
    ),
    "steps_title": (
        "Anamnese dos 12 passos",
        "12-step intake assessment",
        "Evaluación inicial de los 12 pasos",
    ),
    "patient_actions": (
        "Cadastro, edição e exportação estão indisponíveis nesta interface.",
        "Creating, editing and exporting records are unavailable in this interface.",
        "La creación, edición y exportación de registros no están disponibles "
        "en esta interfaz.",
    ),
    "patients_readonly": (
        "Consulta somente leitura dos pacientes disponíveis para este acesso. "
        "A lista exibe até 50 registros autorizados; não representa o total da "
        "clínica.",
        "Read-only view of patients available with this access. The list shows "
        "up to 50 authorized records; it does not represent the clinic's total.",
        "Consulta de solo lectura de los pacientes disponibles con este "
        "acceso. La lista muestra hasta 50 registros autorizados; no "
        "representa el total de la clínica.",
    ),
    "recovery_readonly": (
        "Consulta somente leitura dos perfis de recuperação autorizados. A "
        "lista exibe até 15 registros; não representa o total da clínica.",
        "Read-only view of authorized recovery profiles. The list shows up to "
        "15 records; it does not represent the clinic's total.",
        "Consulta de solo lectura de los perfiles de recuperación autorizados. "
        "La lista muestra hasta 15 registros; no representa el total de la "
        "clínica.",
    ),
    "intake_link": (
        "Consultar disponibilidade da anamnese",
        "Check intake assessment availability",
        "Consultar la disponibilidad de la evaluación inicial",
    ),
    "steps_link": (
        "Consultar disponibilidade da anamnese dos 12 passos",
        "Check 12-step intake assessment availability",
        "Consultar la disponibilidad de la evaluación inicial de los 12 pasos",
    ),
    "no_writes": (
        "Esta página não grava dados nem envia notificações.",
        "This page does not save data or send notifications.",
        "Esta página no guarda datos ni envía notificaciones.",
    ),
    "unavailable": (
        "Indisponível nesta interface",
        "Unavailable in this interface",
        "No disponible en esta interfaz",
    ),
    "cvv": (
        "Ligar para o CVV: 188 (Brasil)",
        "Call CVV: 188 (Brazil)",
        "Llamar al CVV: 188 (Brasil)",
    ),
    "samu": (
        "Ligar para o SAMU: 192 (Brasil)",
        "Call SAMU: 192 (Brazil)",
        "Llamar al SAMU: 192 (Brasil)",
    ),
    "empty": (
        "Nenhum paciente disponível para este acesso.",
        "No patients available with this access.",
        "No hay pacientes disponibles con este acceso.",
    ),
    "sos": (
        "O acionamento de SOS pelo portal está indisponível. Não há plantão, "
        "monitoramento ou envio de ajuda por esta página.",
        "SOS activation through the portal is unavailable. This page does not "
        "provide an on-call service, monitoring or dispatch of help.",
        "La activación de SOS a través del portal no está disponible. Esta "
        "página no ofrece servicio de guardia, seguimiento ni envío de ayuda.",
    ),
    "intake": (
        "O formulário de anamnese está indisponível até a homologação da "
        "integração. Não é possível inserir, salvar ou anexar dados nesta "
        "página.",
        "The intake assessment form is unavailable until the integration is "
        "approved. You cannot enter, save or attach data on this page.",
        "El formulario de evaluación inicial no está disponible hasta la "
        "aprobación de la integración. No es posible introducir, guardar ni "
        "adjuntar datos en esta página.",
    ),
    "steps": (
        "O formulário de etapas está indisponível até a homologação da "
        "integração. Não há avanço de etapas, salvamento automático ou "
        "consolidação nesta página.",
        "The step-by-step form is unavailable until the integration is "
        "approved. This page does not advance steps, automatically save or "
        "consolidate data.",
        "El formulario por etapas no está disponible hasta la aprobación de la "
        "integración. Esta página no permite avanzar etapas, guardar "
        "automáticamente ni consolidar datos.",
    ),
    "recovery": (
        "O registro de fissura e os indicadores de recuperação estão "
        "indisponíveis nesta interface. Não há monitoramento nem intervenção "
        "automática.",
        "Craving records and recovery indicators are unavailable in this "
        "interface. There is no monitoring or automatic intervention.",
        "El registro de deseos intensos de consumo o de jugar y los "
        "indicadores de recuperación no están disponibles en esta interfaz. No "
        "hay seguimiento ni intervención automática.",
    ),
    "b2c": (
        "O registro de humor, o diário e a contratação de assinatura estão "
        "indisponíveis nesta prévia. Nenhum histórico ou benefício de "
        "assinatura é exibido.",
        "Mood tracking, the journal and subscription sign-up are unavailable "
        "in this preview. No history or subscription benefits are displayed.",
        "El registro del estado de ánimo, el diario y la contratación de una "
        "suscripción no están disponibles en esta vista previa. No se muestra "
        "ningún historial ni beneficio de suscripción.",
    ),
    "patients_title": (
        "Pacientes disponíveis para consulta",
        "Patients available to view",
        "Pacientes disponibles para consulta",
    ),
    "profile": (
        "Perfil vinculado à sua conta nesta clínica",
        "Profile linked to your account at this clinic",
        "Perfil vinculado a tu cuenta en esta clínica",
    ),
    "record": ("Prontuário", "Medical record", "Historia clínica"),
    "back": (
        "Voltar para recuperação",
        "Back to recovery",
        "Volver a recuperación",
    ),
}
SURFACE_COPY = {
    "addiction_dashboard.html": (
        "recovery",
        "steps_link",
        "patients_title",
        "recovery_readonly",
        "record",
    ),
    "anamnesis.html": ("intake",),
    "beds.html": ("beds",),
    "crisis_protocol.html": ("sos", "samu", "cvv"),
    "mobile_b2c.html": ("b2c",),
    "mobile_connected.html": ("connected", "profile"),
    "patients.html": ("patients_readonly", "record", "patient_actions", "intake_link"),
    "telepsychiatry_room.html": ("telepsychiatry",),
    "twelve_steps_anamnesis.html": ("steps_title", "steps", "back"),
}
SAFETY_COPY = (
    (
        "Este portal não é um serviço de emergência e não oferece "
        "monitoramento contínuo.",
        "This portal is not an emergency service and does not provide "
        "continuous monitoring.",
        "Este portal no es un servicio de emergencias y no ofrece seguimiento "
        "continuo.",
    ),
    (
        "No Brasil, em emergência, ligue 192 (SAMU). Para apoio emocional, 188 "
        "(CVV). Em outros países, procure o serviço local de emergência.",
        "In Brazil, in an emergency, call 192 (SAMU). For emotional support, "
        "call 188 (CVV). In other countries, contact your local emergency "
        "service.",
        "En Brasil, en una emergencia, llama al 192 (SAMU). Para apoyo "
        "emocional, al 188 (CVV). En otros países, contacta con el servicio "
        "local de emergencias.",
    ),
)


def test_sanitized_psychiatry_surfaces_belong_to_cumulative_translation_scope() -> None:
    scope = json.loads(
        (
            Path(settings.BASE_DIR) / "docs/migration/translated-ui-scope.json"
        ).read_text()
    )["files"]
    expected = {f"psychiatry/templates/psychiatry/{name}" for name in SURFACES}
    assert expected <= set(scope)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("key", COPY)
def test_sanitized_copy_is_explicitly_compiled_and_uses_real_gettext(language, key):
    messages = COPY[key]
    expected = messages[LANGUAGES.index(language)]
    path = (
        Path(settings.BASE_DIR) / "locale" / LOCALES[language] / "LC_MESSAGES/django.mo"
    )
    with path.open("rb") as source:
        catalog = python_gettext.GNUTranslations(source)
    # Identidade pt-br/es legítima não pode esconder ausência no MO.
    assert vars(catalog)["_catalog"].get(messages[0]) == expected
    with override(language):
        assert gettext(messages[0]) == expected


class RenderedPage(HTMLParser):
    """Inspeção do HTML real, sem traduzir expectativas pelo sistema sob teste."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.forms = []
        self.links = {}
        self._link = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            self.forms.append(attributes)
        if tag == "a":
            self._link = attributes.get("href")
            self.links.setdefault(self._link, "")

    def handle_endtag(self, tag):
        if tag == "a":
            self._link = None

    def handle_data(self, data):
        self.text.append(data)
        if self._link is not None:
            self.links[self._link] += data


@pytest.fixture
def synthetic_render(rf, settings):
    settings.LANGUAGES = [(code, code) for code in LANGUAGES]

    def render(surface, language, *, populated=True):
        request = rf.get("/synthetic-i18n/")
        request.user = AnonymousUser()
        request.LANGUAGE_CODE = language
        # Objetos apenas de contexto: não simulam autorização, persistência ou API.
        patient = SimpleNamespace(
            full_name="Pessoa Sintética <script>nunca executar</script>",
            record_number="SINTETICO-I18N-001",
        )
        context = {
            "patient": patient if populated else None,
            "patients": [patient] if populated else [],
            "profiles": [SimpleNamespace(patient=patient)] if populated else [],
        }
        with override(language):
            html = render_to_string(f"psychiatry/{surface}", context, request=request)
        page = RenderedPage()
        page.feed(html)
        return html, page, patient

    return render


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("surface", SURFACES)
def test_nine_sanitized_surfaces_render_translated_limits(
    surface, language, synthetic_render
):
    html, page, patient = synthetic_render(surface, language)
    text = " ".join(page.text)
    index = LANGUAGES.index(language)
    keys = SURFACE_COPY[surface]
    if surface != "patients.html":
        keys += ("unavailable", "no_writes")
    for key in keys:
        assert COPY[key][index] in text
    for messages in SAFETY_COPY:
        assert messages[index] in text
    assert f'lang="{language}"' in html
    # O seletor de idioma é o único formulário; nenhum formulário clínico ativo.
    assert page.forms
    assert all(
        form.get("action") == reverse("account_set_language") for form in page.forms
    )
    assert 'data-ai-status="disabled"' in html
    if surface in (
        "patients.html",
        "addiction_dashboard.html",
        "mobile_connected.html",
    ):
        assert str(escape(patient.full_name)) in html
        assert patient.full_name not in html
    if surface in ("patients.html", "addiction_dashboard.html"):
        assert patient.record_number in text
        assert COPY["empty"][index] not in text
    if surface == "crisis_protocol.html":
        assert page.links["tel:192"] == COPY["samu"][index]
        assert page.links["tel:188"] == COPY["cvv"][index]
        assert {href for href in page.links if href and href.startswith("tel:")} == {
            "tel:192",
            "tel:188",
        }


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize(
    "surface", ("patients.html", "addiction_dashboard.html", "mobile_connected.html")
)
def test_empty_synthetic_context_does_not_invent_patient_data(
    surface, language, synthetic_render
):
    html, page, patient = synthetic_render(surface, language, populated=False)
    text = " ".join(page.text)
    index = LANGUAGES.index(language)
    assert patient.record_number not in html
    assert str(escape(patient.full_name)) not in html
    if surface == "mobile_connected.html":
        assert COPY["profile"][index] not in text
        assert COPY["connected"][index] in text
        assert COPY["no_writes"][index] in text
    else:
        assert COPY["empty"][index] in text
