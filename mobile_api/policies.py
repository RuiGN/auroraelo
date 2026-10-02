"""Public authorization interface for the patient mobile API domain.

Access is not granted through ``ACTION_ROLES``: a session exists only for an identity
that holds the ``patient`` role in an active clinic, and that decision is re-checked on
every request (see ``mobile_api.services``).
"""

from core.policies import AuthorizationPolicy as AuthorizationPolicy

__all__ = ["AuthorizationPolicy"]
