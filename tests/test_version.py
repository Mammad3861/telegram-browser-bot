import tomllib
from pathlib import Path

from app.version import APP_VERSION


def test_version_consistency() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    readme = Path("README.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert APP_VERSION == "1.10.1-alpha.1"
    assert pyproject["project"]["version"] == APP_VERSION
    assert f"v{APP_VERSION}" in readme
    assert f"v{APP_VERSION}" in changelog
