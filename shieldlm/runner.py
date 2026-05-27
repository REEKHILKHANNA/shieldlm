"""Runner — orchestrates a single ShieldLM evaluation run.

For every probe loaded from disk:
  1. send the prompt to the target
  2. ask the judge to score the response
  3. record the result with timing and any error
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .judge import JudgeResult, Verdict, judge
from .probes import Probe
from .targets import Target


@dataclass
class ProbeResult:
    probe: Probe
    response: str
    judge_result: JudgeResult
    duration_seconds: float
    error: str | None = None


@dataclass
class RunSummary:
    target_name: str
    started_at: str
    finished_at: str
    results: list[ProbeResult] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        tally = {"pass": 0, "partial": 0, "fail": 0, "error": 0}
        for r in self.results:
            if r.error:
                tally["error"] += 1
            else:
                tally[r.judge_result.verdict.value] += 1
        return tally


def run(target: Target, probes: list[Probe]) -> RunSummary:
    summary = RunSummary(
        target_name=target.name,
        started_at=_now_iso(),
        finished_at="",
    )

    for probe in probes:
        start = time.perf_counter()
        response = ""
        error: str | None = None
        try:
            response = target.query(probe.prompt)
            judge_result = judge(probe, response)
        except Exception as exc:  # surface the error in the report instead of aborting
            error = f"{type(exc).__name__}: {exc}"
            judge_result = JudgeResult(
                Verdict.PARTIAL,
                "Target raised an exception — see error field.",
            )
        duration = time.perf_counter() - start

        summary.results.append(
            ProbeResult(
                probe=probe,
                response=response,
                judge_result=judge_result,
                duration_seconds=duration,
                error=error,
            )
        )

    summary.finished_at = _now_iso()
    return summary


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
