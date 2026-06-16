from pathlib import Path


def test_readme_doc_links_exist() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    for link in [
        "docs/deployment-docker.md",
        "docs/configuration.md",
        "docs/commands.md",
        "docs/search.md",
        "docs/cookies.md",
        "docs/troubleshooting.md",
        "docs/roadmap.md",
        "docs/beta-checklist.md",
        "docs/migrations.md",
        "docs/release-template.md",
        "CHANGELOG.md",
    ]:
        assert link in readme
        assert Path(link).exists()
