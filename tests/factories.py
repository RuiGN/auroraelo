"""Synthetic Factory Boy factories for automated tests only."""

from __future__ import annotations

from datetime import date
from typing import Any

from factory.declarations import Iterator, LazyFunction, Sequence, SubFactory
from factory.django import DjangoModelFactory

from accounts.models import User
from clinics.models import Clinic, ClinicMembership


def synthetic_cpf(number: int) -> str:
    """Return a unique, valid, obviously fake CPF for the ``number``-th user."""
    base = f"{(100_000_000 + number * 7_919) % 1_000_000_000:09d}"
    digits = base
    for length in (9, 10):
        total = sum(
            int(digit) * weight
            for digit, weight in zip(digits, range(length + 1, 1, -1), strict=True)
        )
        digits += str((total * 10) % 11 % 10)
    return digits


class UserFactory(DjangoModelFactory[User]):
    """Create a unique synthetic user with no usable credential."""

    class Meta:
        model = User

    username = Sequence(  # type: ignore[no-untyped-call]
        lambda number: f"usuario-sintetico-{number}"
    )
    email = Sequence(  # type: ignore[no-untyped-call]
        lambda number: f"usuario{number}@example.test"
    )
    cpf = Sequence(synthetic_cpf)  # type: ignore[no-untyped-call]
    first_name = Iterator(  # type: ignore[no-untyped-call]
        ("Ana", "Bruno", "Carla", "Diego")
    )
    last_name = "Exemplo"

    @classmethod
    def create(cls, **kwargs: Any) -> User:
        """Create and return the concrete user type for strict test typing."""
        return super().create(**kwargs)

    @classmethod
    def _create(cls, model_class: type[Any], *args: Any, **kwargs: Any) -> Any:
        user = model_class.objects.create_user(*args, **kwargs)
        user.set_unusable_password()
        user.save(update_fields=("password",))
        return user


class ClinicFactory(DjangoModelFactory[Clinic]):
    """Create an isolated clinic with an explicitly synthetic PT-BR label."""

    class Meta:
        model = Clinic

    name = Sequence(  # type: ignore[no-untyped-call]
        lambda number: f"Clínica Sintética {number}"
    )
    slug = Sequence(  # type: ignore[no-untyped-call]
        lambda number: f"clinica-sintetica-{number}"
    )
    is_demo = False

    @classmethod
    def create(cls, **kwargs: Any) -> Clinic:
        """Create and return the concrete clinic type for strict test typing."""
        return super().create(**kwargs)

    @classmethod
    def _create(cls, model_class: type[Any], *args: Any, **kwargs: Any) -> Any:
        return model_class.infrastructure_objects.create(*args, **kwargs)


class ClinicMembershipFactory(DjangoModelFactory[ClinicMembership]):
    """Create one synthetic, isolated clinic authorization relationship."""

    class Meta:
        model = ClinicMembership

    user = SubFactory(UserFactory)  # type: ignore[no-untyped-call]
    clinic = SubFactory(ClinicFactory)  # type: ignore[no-untyped-call]
    role = ClinicMembership.Role.THERAPIST
    valid_from = LazyFunction(date.today)  # type: ignore[no-untyped-call]

    @classmethod
    def create(cls, **kwargs: Any) -> ClinicMembership:
        """Create and return the concrete membership type for strict test typing."""
        return super().create(**kwargs)

    @classmethod
    def _create(cls, model_class: type[Any], *args: Any, **kwargs: Any) -> Any:
        return model_class.infrastructure_objects.create(*args, **kwargs)
