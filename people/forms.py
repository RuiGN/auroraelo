"""Forms for tenant-scoped people management."""

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from .presentation import GENDER_LABELS


class PatientProfileForm(forms.Form):
    """Collect the minimized initial patient record with localized labels."""

    full_name = forms.CharField(label=_("Nome completo"), max_length=255)
    social_name = forms.CharField(
        label=_("Nome social"), max_length=255, required=False
    )
    birth_date = forms.DateField(
        label=_("Data de nascimento"), widget=forms.DateInput(attrs={"type": "date"})
    )
    gender = forms.ChoiceField(
        label=_("Gênero (opcional)"),
        required=False,
        choices=(("", _("Não informado")), *GENDER_LABELS.items()),
    )
    email = forms.EmailField(label=_("E-mail"))
    phone = forms.CharField(label=_("Telefone"), max_length=32, required=False)
    language_code = forms.CharField(label=_("Idioma"), initial="pt-BR", max_length=16)
    timezone_name = forms.CharField(
        label=_("Fuso horário"), initial="America/Sao_Paulo", max_length=64
    )
    accessibility_preferences = forms.CharField(
        label=_("Preferências de acessibilidade"),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    address_line = forms.CharField(label=_("Endereço"), max_length=255, required=False)
    address_city = forms.CharField(label=_("Cidade"), max_length=120, required=False)
    address_state = forms.CharField(label=_("UF"), max_length=2, required=False)
    address_postal_code = forms.CharField(label=_("CEP"), max_length=16, required=False)
    address_purpose = forms.CharField(
        label=_("Finalidade do endereço"), max_length=255, required=False
    )
    emergency_contact_name = forms.CharField(
        label=_("Contato de emergência — nome"), max_length=255, required=False
    )
    emergency_contact_phone = forms.CharField(
        label=_("Contato de emergência — telefone"), max_length=32, required=False
    )
    emergency_contact_purpose = forms.CharField(
        label=_("Finalidade do contato de emergência"), max_length=255, required=False
    )

    def clean(self) -> dict[str, Any]:
        """Assemble optional structured payloads and enforce their purpose."""
        cleaned = dict(super().clean() or {})
        address = {
            "line": (cleaned.get("address_line") or "").strip(),
            "city": (cleaned.get("address_city") or "").strip(),
            "state": (cleaned.get("address_state") or "").strip(),
            "postal_code": (cleaned.get("address_postal_code") or "").strip(),
        }
        address = {key: value for key, value in address.items() if value}
        emergency_contact = {
            "name": (cleaned.get("emergency_contact_name") or "").strip(),
            "phone": (cleaned.get("emergency_contact_phone") or "").strip(),
        }
        emergency_contact = {
            key: value for key, value in emergency_contact.items() if value
        }
        if address and not (cleaned.get("address_purpose") or "").strip():
            self.add_error(
                "address_purpose", _("Informe a finalidade para registrar o endereço.")
            )
        if (
            emergency_contact
            and not (cleaned.get("emergency_contact_purpose") or "").strip()
        ):
            self.add_error(
                "emergency_contact_purpose",
                _("Informe a finalidade para o contato de emergência."),
            )
        cleaned["address"] = address
        cleaned["emergency_contact"] = emergency_contact
        for key in (
            "address_line",
            "address_city",
            "address_state",
            "address_postal_code",
            "emergency_contact_name",
            "emergency_contact_phone",
        ):
            cleaned.pop(key, None)
        return cleaned
