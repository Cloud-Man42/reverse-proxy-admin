from pathlib import Path

import yaml
import pytest

from app.schemas.catalog import ApplicationTemplate, TemplateGroup, TemplateHeader


CATALOG_DIR = Path(__file__).resolve().parent.parent / "catalog"
GROUPS_FILE = CATALOG_DIR / "groups.yaml"
TEMPLATES_DIR = CATALOG_DIR / "templates"


def test_groups_yaml_validates():
    groups_data = yaml.safe_load(GROUPS_FILE.read_text(encoding="utf-8")) or []
    groups = [TemplateGroup.model_validate(item) for item in groups_data]
    slugs = [group.slug for group in groups]
    assert len(slugs) == len(set(slugs))
    assert len(groups) >= 17


def test_all_template_yaml_files_validate():
    templates: dict[str, ApplicationTemplate] = {}
    for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for raw in payload.get("templates", []):
            template = ApplicationTemplate.model_validate(raw)
            assert template.slug not in templates, f"duplicate slug {template.slug} in {path.name}"
            templates[template.slug] = template
    assert len(templates) >= 100


def test_template_required_fields_present():
    template = ApplicationTemplate(
        slug="sample-app",
        name="Sample App",
        description="Sample",
        group="monitoring-observability",
        category="Monitoring",
    )
    assert template.availability_level.value == "free"
    assert template.optimized is False


def test_template_header_rejects_unsafe_name():
    with pytest.raises(Exception):
        TemplateHeader(name="X-Evil\r\nHeader", value="safe")
