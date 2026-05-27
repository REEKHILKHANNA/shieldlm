"""Load adversarial probes from YAML files in the probes/ directory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Probe:
    id: str
    category: str
    name: str
    description: str
    prompt: str
    expected_behavior: str
    severity_if_compromised: str
    references: list[str] = field(default_factory=list)
    status: str = "open"
    source_file: str = ""


def load_probes(directory: str | Path) -> list[Probe]:
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Probe directory not found: {directory}")

    probes: list[Probe] = []
    seen_ids: set[str] = set()

    for yaml_file in sorted(directory.glob("*.yaml")):
        with yaml_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for entry in data.get("probes", []):
            probe = Probe(
                id=entry["id"],
                category=entry["category"],
                name=entry["name"],
                description=entry.get("description", "").strip(),
                prompt=entry["prompt"].strip(),
                expected_behavior=entry["expected_behavior"],
                severity_if_compromised=entry["severity_if_compromised"],
                references=list(entry.get("references", [])),
                status=entry.get("status", "open"),
                source_file=yaml_file.name,
            )
            if probe.id in seen_ids:
                raise ValueError(
                    f"Duplicate probe id '{probe.id}' in {yaml_file.name}"
                )
            seen_ids.add(probe.id)
            probes.append(probe)

    return probes
