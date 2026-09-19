"""Extract a declared UI scope and check its locally compiled translation catalogs.

Requires the project's Python environment and GNU gettext. Does not change catalogs
or enable languages. This scoped check is not acceptance of the complete UI.
"""

from __future__ import annotations

import argparse
import gettext
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

CatalogKey = str | tuple[str, int]


def compiled_catalog(path: Path) -> dict[CatalogKey, str]:
    with path.open("rb") as source:
        translator = gettext.GNUTranslations(source)
    # gettext exposes lookup methods but no public enumeration API. Enumeration
    # distinguishes a deliberately identical translation from a missing entry.
    return cast(dict[CatalogKey, str], vars(translator)["_catalog"])


def run_check(scope: Path, output: Path, pot_output: Path) -> bool:
    root = Path(__file__).resolve().parent.parent
    files: list[str] = json.loads(scope.read_text())["files"]
    missing: dict[str, list[str]] = {}
    placeholder_errors: dict[str, list[str]] = {}
    stale: list[str] = []
    placeholder = re.compile(r"%\([^)]+\)[#0 +\-]*[0-9.]*[a-zA-Z]")
    with tempfile.TemporaryDirectory(prefix="mindcare-ui-catalogs-") as directory:
        staging = Path(directory)
        for name in files:
            source = (root / name).resolve()
            if not source.is_relative_to(root) or not source.is_file():
                raise ValueError(f"Invalid source path: {name}")
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        (staging / "locale").mkdir()
        extraction = (
            "from django.conf import settings; "
            "settings.configure(USE_I18N=True, LOCALE_PATHS=[], INSTALLED_APPS=[]); "
            "import django; django.setup(); "
            "from django.core.management import call_command; "
            "call_command('makemessages', locale=['en'], keep_pot=True, "
            "no_wrap=True, verbosity=0)"
        )
        subprocess.run([sys.executable, "-c", extraction], cwd=staging, check=True)
        pot = staging / "locale/django.pot"
        pot_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pot, pot_output)
        identity = staging / "identity.po"
        identity_mo = staging / "identity.mo"
        subprocess.run(["msgen", str(pot), "-o", str(identity)], check=True)
        identity.write_text(
            identity.read_text()
            .replace(
                "nplurals=INTEGER; plural=EXPRESSION;", "nplurals=2; plural=(n != 1);"
            )
            .replace("charset=CHARSET", "charset=UTF-8")
        )
        subprocess.run(["msgfmt", str(identity), "-o", str(identity_mo)], check=True)
        required = compiled_catalog(identity_mo)
        required.pop("", None)
        for language in ("pt_BR", "en", "es"):
            source = root / "locale" / language / "LC_MESSAGES/django.po"
            compiled = source.with_suffix(".mo")
            checked = staging / f"{language}.mo"
            subprocess.run(
                ["msgfmt", "--check", str(source), "-o", str(checked)], check=True
            )
            if not compiled.exists() or checked.read_bytes() != compiled.read_bytes():
                stale.append(language)
            catalog = compiled_catalog(checked)
            missing[language] = [str(key) for key in required if not catalog.get(key)]
            placeholder_errors[language] = [
                str(key)
                for key, original in required.items()
                if catalog.get(key)
                and sorted(placeholder.findall(original))
                != sorted(placeholder.findall(catalog[key]))
            ]
    passed = (
        not stale and not any(missing.values()) and not any(placeholder_errors.values())
    )
    result = {
        "scope": str(scope),
        "source_files": len(files),
        "required_catalog_keys_including_plural_forms": len(required),
        "missing": missing,
        "placeholder_errors": placeholder_errors,
        "stale_compiled_catalogs": stale,
        "passed": passed,
        "publication_acceptance": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        f"Scoped catalog check: {'passed' if passed else 'failed'}; "
        f"{len(required)} keys"
    )
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope", type=Path, default=Path("docs/migration/shared-ui-scope.json")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/migration/evidence/shared-ui-catalog-check.json"),
    )
    parser.add_argument(
        "--pot-output", type=Path, default=Path("docs/migration/evidence/shared-ui.pot")
    )
    args = parser.parse_args()
    return 0 if run_check(args.scope, args.output, args.pot_output) else 1


if __name__ == "__main__":
    raise SystemExit(main())
