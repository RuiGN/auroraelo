"""Validate compiled djangojs catalogs for the published launch languages."""

from __future__ import annotations

import argparse
import gettext
import json
import re
import subprocess
from pathlib import Path
from typing import cast

CatalogValue = str | dict[int, str]


def catalog(path: Path) -> dict[str | tuple[str, int], CatalogValue]:
    with path.open("rb") as source:
        translations = gettext.GNUTranslations(source)
    return cast(
        dict[str | tuple[str, int], CatalogValue], vars(translations)["_catalog"]
    )


def values(value: CatalogValue) -> list[str]:
    return list(value.values()) if isinstance(value, dict) else [value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/mindcare-djangojs-check.json")
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    placeholder = re.compile(r"%\([^)]+\)[#0 +\-]*[0-9.]*[a-zA-Z]")
    results: dict[str, object] = {"domain": "djangojs", "languages": {}, "passed": True}
    languages: dict[str, object] = cast(dict[str, object], results["languages"])
    for language in ("pt_BR", "en", "es"):
        po = root / "locale" / language / "LC_MESSAGES/djangojs.po"
        mo = po.with_suffix(".mo")
        checked = root / ".migration-runtime" / f"djangojs-{language}.mo"
        checked.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["msgfmt", "--check", str(po), "-o", str(checked)], check=True)
        compiled = catalog(checked)
        compiled.pop("", None)
        stale = not mo.exists() or checked.read_bytes() != mo.read_bytes()
        missing = [
            str(key) for key, value in compiled.items() if not any(values(value))
        ]
        placeholders = [
            str(key)
            for key, value in compiled.items()
            if any(
                sorted(
                    placeholder.findall(str(key[0] if isinstance(key, tuple) else key))
                )
                != sorted(placeholder.findall(text))
                for text in values(value)
            )
        ]
        languages[language] = {
            "keys_including_plural_forms": len(compiled),
            "stale_compiled_catalog": stale,
            "empty_entries": missing,
            "placeholder_errors": placeholders,
        }
        if stale or missing or placeholders:
            results["passed"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(f"djangojs catalog check: {'passed' if results['passed'] else 'failed'}")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
