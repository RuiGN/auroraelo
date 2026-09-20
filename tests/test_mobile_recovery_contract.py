"""Gates estáticos mobile; não substituem Jest, export ou dispositivo."""

import json
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]


def json_object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return cast(dict[str, object], value)


@pytest.mark.parametrize("app", ["b2c", "connected"])
def test_mobile_has_executable_typescript_and_locked_dependencies(app: str) -> None:
    root = ROOT / "mobile" / app
    manifest = json_object(json.loads((root / "package.json").read_text()))
    assert {"typecheck", "test", "export"} <= json_object(manifest["scripts"]).keys()
    main = manifest["main"]
    assert isinstance(main, str)
    assert (root / main).is_file()
    assert (root / "tsconfig.json").is_file()
    assert (root / "package-lock.json").is_file()
    for path in (root / "src").rglob("*.tsx"):
        assert "<!--" not in path.read_text(), path


@pytest.mark.parametrize("app", ["b2c", "connected"])
def test_mobile_config_does_not_claim_unimplemented_native_capabilities(
    app: str,
) -> None:
    path = ROOT / "mobile" / app / "app.json"
    assert path.is_file()
    config = json_object(json_object(json.loads(path.read_text()))["expo"])
    name = config["name"]
    assert isinstance(name, str)
    assert name.startswith("Aurora Elo")
    assert json_object(config["android"])["permissions"] == []
    assert "NSLocationWhenInUseUsageDescription" not in json_object(
        json_object(config["ios"]).get("infoPlist", {})
    )
    if "icon" in config:
        icon = config["icon"]
        assert isinstance(icon, str)
        assert (path.parent / icon).is_file()
