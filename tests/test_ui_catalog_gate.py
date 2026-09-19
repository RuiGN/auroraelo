"""Exercise the catalog release guard against isolated, deliberately broken copies."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCOPE = Path("docs/migration/translated-ui-scope.json")


@pytest.mark.parametrize("scenario", ("valid", "missing", "fuzzy", "stale"))
def test_catalog_gate_rejects_incomplete_delivered_ui(
    tmp_path: Path, scenario: str
) -> None:
    """Run the same extractor as CI without modifying the working catalogs."""
    files = json.loads((ROOT / SCOPE).read_text())["files"]
    for name in [*files, str(SCOPE), "scripts/check_ui_catalogs.py"]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    shutil.copytree(ROOT / "locale", tmp_path / "locale")

    source = tmp_path / "locale/en/LC_MESSAGES/django.po"
    content = source.read_text()
    target = 'msgid "E-mail"\nmsgstr "Email"'
    assert target in content, "Choose a translated entry from the delivered UI scope"
    replacements = {
        "missing": 'msgid "E-mail"\nmsgstr ""',
        "fuzzy": "#, fuzzy\n" + target,
        "stale": 'msgid "E-mail"\nmsgstr "Email address"',
    }
    if scenario != "valid":
        source.write_text(content.replace(target, replacements[scenario], 1))
    if scenario in ("missing", "fuzzy"):
        subprocess.run(
            ["msgfmt", "--check", str(source), "-o", str(source.with_suffix(".mo"))],
            check=True,
            capture_output=True,
        )

    result = subprocess.run(
        [
            sys.executable,
            str(tmp_path / "scripts/check_ui_catalogs.py"),
            "--scope",
            str(SCOPE),
            "--output",
            str(tmp_path / "check.json"),
            "--pot-output",
            str(tmp_path / "scope.pot"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == (0 if scenario == "valid" else 1), result.stderr
    report = json.loads((tmp_path / "check.json").read_text())
    assert report["passed"] is (scenario == "valid")
    assert report["publication_acceptance"] is False
    if scenario == "stale":
        assert report["stale_compiled_catalogs"] == ["en"]
        assert not any(report["missing"].values())
    elif scenario in ("missing", "fuzzy"):
        assert "E-mail" in report["missing"]["en"]
        assert report["stale_compiled_catalogs"] == []
