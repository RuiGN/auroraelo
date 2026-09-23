"""Static file storage used by production deployments.

``whitenoise.storage.CompressedManifestStaticFilesStorage`` is strict: every
``{% static %}`` reference must exist in the collected manifest. Vendored admin
themes can reference a directory instead of a file (Jazzmin's
``admin/base.html`` resolves ``vendor/bootswatch`` as the base for its theme
switcher), which raised ``ValueError`` and turned every admin page into a 500 in
production. This storage keeps hashing and compression while serving such legacy
references through their unhashed URL.
"""

from __future__ import annotations

import warnings
from urllib.parse import urljoin

from whitenoise.storage import CompressedManifestStaticFilesStorage


class TolerantCompressedManifestStaticFilesStorage(
    CompressedManifestStaticFilesStorage
):
    """Manifest storage that degrades gracefully on unknown references."""

    manifest_strict = False

    def url(self, name: str, force: bool = False) -> str:
        """Return the hashed URL when known; otherwise the plain static URL."""
        try:
            return super().url(name, force=force)
        except ValueError:
            warnings.warn(
                f"Static reference '{name}' is not part of the collected "
                "manifest; serving it unhashed.",
                RuntimeWarning,
                stacklevel=2,
            )
            return urljoin(self.base_url, name)
