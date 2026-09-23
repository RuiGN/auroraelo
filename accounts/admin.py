"""Safe administrative access to the configured project user."""

from typing import Any

from django.apps import apps
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.http import HttpRequest

from .models import User

ClinicMembership = apps.get_model("clinics", "ClinicMembership")


class ClinicMembershipInline(admin.TabularInline):  # type: ignore[type-arg]
    """Display technical membership state for inspection only.

    Membership changes must go through ``master_panel.user_services`` (global
    operators) or ``clinics.services`` (clinic administrators) so every
    creation, role change, suspension or reactivation is authorized, sets
    ``authorized_by`` and emits the ``membership_authorization_changed``
    audit event. This inline never accepts writes, closing a path that would
    otherwise mutate tenant membership without authorization or auditing.
    """

    model = ClinicMembership
    fk_name = "user"
    extra = 0
    fields = (
        "clinic",
        "role",
        "unit_name",
        "is_active",
        "valid_from",
        "valid_until",
        "authorized_by",
    )
    readonly_fields = fields

    def get_queryset(self, request: HttpRequest) -> models.QuerySet[Any]:
        """Use infrastructure scope only inside the global Admin."""
        queryset: models.QuerySet[Any] = (
            ClinicMembership.infrastructure_objects.select_related(
                "clinic", "authorized_by"
            )
        )
        return queryset

    def has_add_permission(
        self, request: HttpRequest, obj: models.Model | None = None
    ) -> bool:
        """Forbid Admin-created memberships; use the audited service instead."""
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: models.Model | None = None
    ) -> bool:
        """Forbid Admin-edited memberships; use the audited service instead."""
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: models.Model | None = None
    ) -> bool:
        """Forbid Admin-deleted memberships; use the audited service instead."""
        return False


@admin.register(User)
class AuroraUserAdmin(UserAdmin):  # type: ignore[type-arg]
    """Search users by canonical identity and inspect safe membership metadata."""

    inlines = (ClinicMembershipInline,)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    readonly_fields = (
        "id",
        "last_login",
        "date_joined",
        "security_state_changed_at",
        "credentials_changed_at",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identidade", {"fields": ("first_name", "last_name", "username")}),
        (
            "Permissões globais",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Preferências e segurança",
            {
                "fields": (
                    "preferred_layout",
                    "preferred_language",
                    "security_state_changed_at",
                    "credentials_changed_at",
                )
            },
        ),
        ("Datas", {"fields": ("last_login", "date_joined", "id")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                ),
            },
        ),
    )
