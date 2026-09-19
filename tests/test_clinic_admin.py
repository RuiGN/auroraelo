"""Admin infrastructure regressions for clinic tenant models and auth redirect."""

from __future__ import annotations

import pytest
from django import forms
from django.contrib.admin.sites import AdminSite
from django.test import Client, RequestFactory
from django.urls import reverse

from clinics.admin import ClinicAdmin, ClinicMembershipAdmin
from clinics.models import Clinic, ClinicMembership
from tests.factories import ClinicFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_membership_admin_form_uses_infrastructure_clinic_queryset() -> None:
    """Building the membership form can enumerate clinics only inside admin."""
    clinic = Clinic.infrastructure_objects.create(name="Clínica Admin", slug="admin")
    request = RequestFactory().get("/admin/clinics/clinicmembership/add/")
    model_admin = ClinicMembershipAdmin(ClinicMembership, AdminSite())

    form_class = model_admin.get_form(request)
    clinic_field = form_class.base_fields["clinic"]

    assert isinstance(clinic_field, forms.ModelChoiceField)
    assert clinic_field.queryset is not None
    assert list(clinic_field.queryset) == [clinic]


def test_admin_login_redirects_to_account_login(client: Client) -> None:
    """S08.07: Admin login URL routes to account login with next=/admin/."""
    response = client.get(reverse("admin_login"))
    assert response.status_code == 302
    target = f"{reverse('account_login')}?next=%2Fadmin%2F"
    assert response.headers["Location"] == target


def test_anonymous_access_to_admin_index_redirects_to_login(client: Client) -> None:
    """S08.07: Anonymous user visiting /admin/ is redirected to admin login."""
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response.headers["Location"]


def test_non_staff_access_to_admin_index_redirects_to_login(client: Client) -> None:
    """S08.07: Non-staff authenticated user visiting /admin/ is redirected."""
    user = UserFactory.create(is_staff=False, is_superuser=False)
    client.force_login(user)
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response.headers["Location"]


def test_staff_user_can_access_admin_index_and_clinic_changelist(
    client: Client,
) -> None:
    """S08.07: Staff user with permissions views admin index and changelist."""
    staff = UserFactory.create(is_staff=True, is_superuser=True)
    ClinicFactory.create(name="Clínica Homologada")
    client.force_login(staff)

    response = client.get("/admin/")
    assert response.status_code == 200
    assert "Django" in response.content.decode()

    clinic_response = client.get("/admin/clinics/clinic/")
    assert clinic_response.status_code == 200
    assert "Clínica Homologada" in clinic_response.content.decode()


def test_clinic_admin_slug_is_readonly_on_existing_instance() -> None:
    """S08.07: ClinicAdmin locks slug field on existing instances."""
    clinic = Clinic.infrastructure_objects.create(
        name="Clínica Imutável", slug="imutavel"
    )
    request = RequestFactory().get(f"/admin/clinics/clinic/{clinic.pk}/change/")
    model_admin = ClinicAdmin(Clinic, AdminSite())

    readonly_existing = model_admin.get_readonly_fields(request, clinic)
    assert "slug" in readonly_existing

    readonly_new = model_admin.get_readonly_fields(request, None)
    assert "slug" not in readonly_new


def test_clinic_membership_admin_formfield_for_foreignkey() -> None:
    """S08.07: ClinicMembershipAdmin returns infrastructure queryset for clinic fk."""
    clinic = Clinic.infrastructure_objects.create(name="Clínica FK", slug="fk")
    request = RequestFactory().get("/admin/clinics/clinicmembership/add/")
    model_admin = ClinicMembershipAdmin(ClinicMembership, AdminSite())

    db_field = ClinicMembership._meta.get_field("clinic")
    field = model_admin.formfield_for_foreignkey(db_field, request)
    assert isinstance(field, forms.ModelChoiceField)
    assert field.queryset is not None
    assert clinic in list(field.queryset)
