"""Focused tests for executable data and schema migration helpers."""

from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace
from typing import Any

import pytest

content_migration = import_module(
    "content.migrations.0009_content_same_tenant_invariant"
)
identity_migration = import_module("accounts.migrations.0003_email_identity_security")


class RecordingSchemaEditor:
    def __init__(self, vendor: str) -> None:
        self.connection = SimpleNamespace(vendor=vendor)
        self.executed: list[str] = []

    def execute(self, statement: str) -> None:
        self.executed.append(statement)


@pytest.mark.parametrize(
    "operation",
    [content_migration.apply_invariants, content_migration.drop_invariants],
)
def test_content_invariant_migration_fails_closed_for_unknown_database(
    operation: Any,
) -> None:
    editor = RecordingSchemaEditor("mysql")

    with pytest.raises(
        NotImplementedError,
        match="unsupported on vendor mysql",
    ):
        operation(None, editor)

    assert editor.executed == []


class FakeUserQuerySet:
    def __init__(self, users: list[SimpleNamespace]) -> None:
        self.users = users

    def all(self) -> FakeUserQuerySet:
        return self

    def only(self, *fields: str) -> list[SimpleNamespace]:
        assert fields == ("id", "email")
        return self.users


class FakeUserManager:
    def __init__(self, users: list[SimpleNamespace]) -> None:
        self.queryset = FakeUserQuerySet(users)
        self.bulk_updates: list[tuple[list[SimpleNamespace], tuple[str, ...]]] = []

    def all(self) -> FakeUserQuerySet:
        return self.queryset.all()

    def bulk_update(
        self, users: list[SimpleNamespace], fields: tuple[str, ...]
    ) -> None:
        self.bulk_updates.append((list(users), fields))


def _migration_apps(
    users: list[SimpleNamespace],
) -> tuple[SimpleNamespace, FakeUserManager]:
    manager = FakeUserManager(users)
    user_model = SimpleNamespace(objects=manager)

    def get_model(app_label: str, model_name: str) -> SimpleNamespace:
        assert (app_label, model_name) == ("accounts", "User")
        return user_model

    return SimpleNamespace(get_model=get_model), manager


def test_email_identity_migration_canonicalizes_only_changed_users_in_one_batch() -> (
    None
):
    changed = SimpleNamespace(id="changed", email="  USER@Example.COM ")
    unchanged = SimpleNamespace(id="unchanged", email="ready@example.com")
    apps, manager = _migration_apps([changed, unchanged])

    identity_migration.canonicalize_existing_emails(apps, object())

    assert changed.email == "user@example.com"
    assert unchanged.email == "ready@example.com"
    assert manager.bulk_updates == [([changed], ("email",))]


def test_email_identity_migration_skips_empty_bulk_update() -> None:
    user = SimpleNamespace(id="unchanged", email="ready@example.com")
    apps, manager = _migration_apps([user])

    identity_migration.canonicalize_existing_emails(apps, object())

    assert manager.bulk_updates == []


def test_email_identity_migration_rejects_blank_identifier() -> None:
    apps, manager = _migration_apps([SimpleNamespace(id="blank-user", email=" \t ")])

    with pytest.raises(RuntimeError, match="blank-user has no e-mail identifier"):
        identity_migration.canonicalize_existing_emails(apps, object())

    assert manager.bulk_updates == []


def test_email_identity_migration_rejects_case_insensitive_duplicate() -> None:
    apps, manager = _migration_apps(
        [
            SimpleNamespace(id="first-user", email="duplicate@example.com"),
            SimpleNamespace(id="second-user", email=" DUPLICATE@EXAMPLE.COM "),
        ]
    )

    with pytest.raises(RuntimeError) as error:
        identity_migration.canonicalize_existing_emails(apps, object())

    assert "first-user and second-user" in str(error.value)
    assert manager.bulk_updates == []
