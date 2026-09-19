"""Retired second-factor entry points must not return to the account surface."""

import pytest
from django.apps import apps
from django.urls import NoReverseMatch, reverse


@pytest.mark.parametrize("name", ["UserMFA", "MFARecoveryCode"])
def test_mfa_models_are_not_registered(name):
    with pytest.raises(LookupError):
        apps.get_model("accounts", name)
    assert apps.get_model("accounts", "AccountSession") is not None


@pytest.mark.parametrize(
    "name", ["mfa_enroll", "mfa_verify", "administrative_mfa_reset"]
)
def test_mfa_routes_are_removed(name):
    with pytest.raises(NoReverseMatch):
        reverse(name)
