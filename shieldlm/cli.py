"""Command-line interface for ShieldLM."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from . import __version__
from .probes import load_probes
from .report import write_report
from .runner import run
from .targets import get_target


_DEFAULTS = {
    "target": {"name": "mock"},
    "probes": {"directory": "probes"},
    "reports": {"directory": "reports"},
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="shieldlm",
        description="Adversarial evaluation for LLM agents.",
    )
    parser.add_argument("--version", action="version", version=f"shieldlm {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run", help="Run probes against a target")
    run_p.add_argument(
        "--target",
        help="Override the target name (e.g. mock, claude).",
    )
    run_p.add_argument(
        "--config",
        default="config.yaml",
        help="Path to a YAML config file (default: config.yaml).",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        return _cmd_run(args)
    return 1


def _cmd_run(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    if args.target:
        config["target"]["name"] = args.target

    probe_dir = config["probes"]["directory"]
    report_dir = config["reports"]["directory"]
    target_name = config["target"]["name"]

    print(f"Loading probes from {probe_dir}/ ...")
    probes = load_probes(probe_dir)
    print(f"Loaded {len(probes)} probe(s).")

    target_kwargs = config["target"].get(target_name, {}) or {}
    target = get_target(target_name, **target_kwargs)
    print(f"Running probes against target '{target.name}' ...")

    summary = run(target, probes)

    counts = summary.counts
    print(
        f"Done — pass {counts['pass']} | partial {counts['partial']} | "
        f"fail {counts['fail']} | error {counts['error']}"
    )

    report_path = write_report(summary, report_dir)
    print(f"Report written to {report_path}")
    return 0


def _load_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        # Fall back to baked-in defaults so the tool works out of the box.
        return _deep_copy_defaults()

    with config_path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    merged = _deep_copy_defaults()
    for section, values in loaded.items():
        if isinstance(values, dict) and isinstance(merged.get(section), dict):
            merged[section].update(values)
        else:
            merged[section] = values
    return merged


def _deep_copy_defaults() -> dict:
    return {k: dict(v) for k, v in _DEFAULTS.items()}


if __name__ == "__main__":
    sys.exit(main())
