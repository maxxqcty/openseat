"""Validate the Grafana dashboard and alert rules without contacting Grafana."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD = ROOT / "observability" / "dashboard.json"
ALERTS = ROOT / "observability" / "alerts.yaml"
RUNBOOK = ROOT / "_docs" / "runbook.md"
README = ROOT / "observability" / "README.md"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
REQUIRED_ALERTS = {
    "OpenSeatDown",
    "OpenSeatHighErrorRate",
    "OpenSeatBookingErrors",
    "OpenSeatWaitlistStalled",
    "OpenSeatOverbooked",
}
REQUIRED_PANELS = {
    "Traffic (requests/s)",
    "5xx rate",
    "p95 latency",
    "Bookings by result",
    "Waitlist promotions",
    "Open seats with a waitlist",
    "Overbooked sessions",
}


def _dashboard() -> dict[str, Any]:
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _alerts() -> dict[str, Any]:
    data = yaml.safe_load(ALERTS.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _rules() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for group in _alerts()["groups"]:
        rules.extend(group["rules"])
    return rules


def test_dashboard_has_every_required_panel() -> None:
    titles = {panel["title"] for panel in _dashboard()["panels"]}
    assert titles >= REQUIRED_PANELS


def test_every_panel_filters_by_environment_and_version() -> None:
    for panel in _dashboard()["panels"]:
        targets = panel.get("targets", [])
        assert targets, panel["title"]
        for target in targets:
            expression = target["expr"]
            assert 'environment=~"$environment"' in expression, panel["title"]
            assert 'version=~"$version"' in expression, panel["title"]


def test_dashboard_exposes_environment_and_version_variables() -> None:
    variables = {item["name"]: item for item in _dashboard()["templating"]["list"]}
    assert {"environment", "version"} <= set(variables)
    assert variables["environment"]["multi"] is True
    assert variables["version"]["multi"] is True


def test_alert_rules_include_the_required_names_and_annotations() -> None:
    rules = _rules()
    titles = {rule["title"] for rule in rules}
    assert titles >= REQUIRED_ALERTS

    for rule in rules:
        annotations = rule["annotations"]
        assert annotations["owner"], rule["title"]
        assert annotations["dashboard_url"].startswith("https://"), rule["title"]
        assert annotations["runbook_url"].startswith("https://"), rule["title"]
        assert rule["labels"]["severity"] == "page", rule["title"]


def test_waitlist_alert_uses_the_documented_windows() -> None:
    rules = {rule["title"]: rule for rule in _rules()}
    assert rules["OpenSeatWaitlistStalled"]["for"] == "10m"
    assert rules["OpenSeatWaitlistStalledDev"]["for"] == "2m"
    assert rules["OpenSeatWaitlistStalled"]["labels"]["environment"] == "production"
    assert rules["OpenSeatWaitlistStalledDev"]["labels"]["environment"] == "development"


def test_alert_runbook_links_resolve_to_headings() -> None:
    headings = {
        line.lstrip("#").strip().lower()
        for line in RUNBOOK.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    }
    for rule in _rules():
        anchor = rule["annotations"]["runbook_url"].rsplit("#", 1)[-1]
        assert anchor in headings, rule["title"]


def test_dashboard_and_alerts_contain_no_email_addresses() -> None:
    for path in (DASHBOARD, ALERTS):
        text = path.read_text(encoding="utf-8")
        assert not EMAIL_RE.search(text), path


def test_observability_readme_documents_setup_and_evidence() -> None:
    text = README.read_text(encoding="utf-8")
    for phrase in (
        "Grafana Cloud setup",
        "Import the dashboard",
        "Import the alert rules",
        "Verify an alert",
        "Evidence status",
    ):
        assert phrase in text
