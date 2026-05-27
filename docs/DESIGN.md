# ShieldLM — Design & Functional Specification

> Version 0.1.0 — adversarial evaluation framework for LLM agents.

---

## 1. Purpose

ShieldLM is a small framework that **pressure-tests an AI agent against a
library of known adversarial prompts**, then writes a structured report
on how the agent behaved.

It exists because production AI agents are being deployed faster than they
are being tested for safety. ShieldLM provides a repeatable, low-cost way
to evaluate an agent **before** it ships.

In one line:

> **"Probes in, agent in the middle, report out."**

```
   📚 Attack library  →  🎯 Agent under test  →  📋 Markdown report
```

---

## 2. Scope (what v0.1 does and does not do)

### In scope

- Load adversarial probes from YAML files.
- Send each probe as a single-turn prompt to a target adapter.
- Score each response with a rule-based judge (pass / partial / fail).
- Write a timestamped markdown report sorted by danger.
- Ship two target adapters: a `mock` agent (free, deterministic) and a
  `claude` adapter (Anthropic API).

### Out of scope (deliberate, for v0.1)

- Multi-turn / conversational probes.
- LLM-as-judge scoring (planned).
- Reproducibility loops (running each probe N times).
- HTML / JSON report formats.
- CI/CD gating logic.
- Adapters for non-Anthropic providers (easy to add later — see §9).

---

## 3. User personas & use cases

| Persona | Use case |
|---|---|
| AI Product Manager | Pre-launch safety check on a new agent feature. |
| ML Engineer | Compare safety profile across model versions. |
| Security reviewer | Generate evidence for an internal release-gate review. |
| Open-source contributor | Add probes or adapters and re-run regression. |

### Primary user flow

```
   1. Edit  probes/*.yaml         (add or curate attacks)
   2. Edit  config.yaml           (pick target, set system prompt)
   3. Set   ANTHROPIC_API_KEY     (env var, if using claude target)
   4. Run   python -m shieldlm run
   5. Read  reports/<timestamp>-<target>.md
```

---

## 4. System architecture

ShieldLM is a small Python package with seven cooperating modules. The
architecture is a **linear pipeline** with one swappable component (the
Target).

```
                              shieldlm/cli.py
                                    │
                                    ▼
                          ┌──────────────────┐
                          │     Runner       │   shieldlm/runner.py
                          └──────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │  Probe loader    │  │     Target       │  │      Judge       │
   │  probes.py       │  │  targets.py      │  │  judge.py        │
   │                  │  │                  │  │                  │
   │ reads YAML       │  │ Mock | Claude    │  │ rule-based       │
   │ produces         │  │ produces text    │  │ produces         │
   │ Probe objects    │  │ responses        │  │ JudgeResult      │
   └──────────────────┘  └──────────────────┘  └──────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  Report writer   │   shieldlm/report.py
                          │  → markdown      │
                          └──────────────────┘
                                    │
                                    ▼
                            reports/*.md
```

### Why this shape

- **Pipeline, not service.** ShieldLM is a CLI that runs to completion,
  not a long-lived server. Simpler to reason about, easier to schedule
  from CI later.
- **Pluggable target only.** Probes, judge, and reporter are stable;
  the target is the part that varies between users (Claude, GPT,
  custom agent), so that is the only seam exposed for extension.

---

## 5. Module responsibilities

| Module | Responsibility | Notes |
|---|---|---|
| `cli.py` | Parse args, load config, wire components, print summary. | Defaults work with no `config.yaml`. |
| `probes.py` | Load all `probes/*.yaml`, validate, dedupe by `id`. | Errors on duplicate probe IDs. |
| `targets.py` | Define `Target` interface; implement `MockTarget` and `ClaudeTarget`. | Anthropic SDK imported lazily. |
| `judge.py` | Score each response as `PASS`, `PARTIAL`, or `FAIL`. | Rule-based; keyword indicators per `expected_behavior`. |
| `runner.py` | For each probe: query target, judge response, record result. | Per-probe exceptions captured, not fatal. |
| `report.py` | Render `RunSummary` to markdown; write to disk. | Findings table sorted by danger. |
| `__main__.py` | Entry point for `python -m shieldlm`. | One-liner that calls `cli.main`. |

---

## 6. Data model

### 6.1 `Probe`

One adversarial test case, loaded from YAML.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier (e.g. `PI-001`). Used for deduplication. |
| `category` | string | yes | Free-text tag (e.g. `prompt_injection_direct`). |
| `name` | string | yes | Short human-readable name. |
| `description` | string | no | Longer explanation of what the probe tests. |
| `prompt` | string | yes | The actual adversarial input sent to the target. |
| `expected_behavior` | enum | yes | Drives the judge rubric (see §7.2). |
| `severity_if_compromised` | enum | yes | `low` / `medium` / `high` / `critical`. |
| `references` | list[string] | no | Citations (e.g. OWASP LLM Top 10). |
| `status` | string | no | `open` / `mitigated` / etc. Free-text. |

### 6.2 `JudgeResult`

| Field | Type | Description |
|---|---|---|
| `verdict` | enum | `PASS` / `PARTIAL` / `FAIL`. |
| `rationale` | string | Human-readable explanation of the verdict. |

### 6.3 `ProbeResult`

| Field | Type | Description |
|---|---|---|
| `probe` | `Probe` | The probe that was run. |
| `response` | string | Raw text the target returned. |
| `judge_result` | `JudgeResult` | Verdict + rationale. |
| `duration_seconds` | float | Wall-clock time for this probe. |
| `error` | string \| null | If the target raised an exception, recorded here. |

### 6.4 `RunSummary`

| Field | Type | Description |
|---|---|---|
| `target_name` | string | Which target was tested. |
| `started_at` | ISO timestamp | Run start time (UTC). |
| `finished_at` | ISO timestamp | Run end time (UTC). |
| `results` | list[`ProbeResult`] | One entry per probe. |
| `counts` | dict | `{pass, partial, fail, error}` tallies. |

---

## 7. Interfaces

### 7.1 Target interface

Every adapter must inherit from `Target` and implement:

```python
class Target(ABC):
    name: str

    @abstractmethod
    def query(self, prompt: str) -> str: ...
```

Contract:

- **Input:** a single string (the probe prompt).
- **Output:** a single string (the agent's response).
- **Errors:** the target may raise; the runner catches and records.

This is the only seam for extension. To add OpenAI / Gemini / a custom
agent, implement one class and register it in `get_target`.

### 7.2 Probe YAML schema

```yaml
version: 0.1.0
last_updated: 2026-05-27

probes:
  - id: PI-001
    category: prompt_injection_direct
    name: Override via instruction reset
    description: >
      What this probe tests, plain English.
    prompt: |
      The adversarial input goes here.
    expected_behavior: refuse_or_ignore
    severity_if_compromised: medium
    references:
      - "OWASP LLM01:2025 — Prompt Injection"
    status: open
```

**Recognised `expected_behavior` values** (drive the judge rubric):

| Value | What the judge looks for |
|---|---|
| `refuse_or_ignore` | Refusal phrases, absence of compliance phrases. |
| `ignore_tool_origin_instructions` | Same as above (treats tool-supplied instructions as untrusted). |
| `refuse_disclosure` | Same as above (no system prompt leakage). |
| `maintain_system_authority` | Same as above (user role claims not honoured). |
| `maintain_policy` | Safety/policy language preserved even if persona is engaged. |
| `clarify_before_executing` | Clarification phrases before destructive action. |

Adding a new behaviour = adding a branch in `judge.py`.

### 7.3 Configuration schema (`config.yaml`)

```yaml
target:
  name: mock          # or "claude"
  claude:             # only read when name == "claude"
    model: claude-haiku-4-5-20251001
    system_prompt: >
      Optional system prompt to evaluate the agent with.

probes:
  directory: probes

reports:
  directory: reports
```

Missing `config.yaml` is fine — defaults are baked into `cli.py`.

### 7.4 Command-line interface

```
shieldlm run [--target <name>] [--config <path>]
shieldlm --version
```

Exit codes: `0` on success, non-zero on configuration or load error.

---

## 8. Runtime behaviour

### 8.1 Happy path

```
   parse args
   load config (defaults if missing)
   load probes (validate, dedupe)
   construct target (mock | claude)
   for each probe:
       send prompt to target          ─┐
       judge response                  ├──  recorded as ProbeResult
       record duration                ─┘
   build RunSummary
   write markdown report
   print one-line summary to stdout
```

### 8.2 Error handling

- **Missing probe directory** → fatal, raises `FileNotFoundError`.
- **Duplicate probe id** → fatal, raises `ValueError`.
- **Target exception during a probe** → captured into `ProbeResult.error`,
  probe marked as `ERROR` in the report, run continues.
- **Unknown target name** → fatal, raises `ValueError` with allowed list.

### 8.3 Determinism

- The mock target is fully deterministic (keyword-matched canned responses).
- The Claude target inherits the model's nondeterminism. Reproducibility
  loops are a planned v0.2 feature.

---

## 9. Extensibility

### Add a new target adapter

1. Create a subclass of `Target` (anywhere — `targets.py` is fine for now).
2. Implement `query(prompt: str) -> str`.
3. Register the name in `get_target()`.

### Add a new probe

1. Open `probes/example.yaml` (or create a new YAML file in `probes/`).
2. Add an entry following the schema in §7.2.
3. Ensure the `id` is unique across the whole directory.

### Add a new judge rubric

1. Open `judge.py`.
2. Add an `if expected == "<new_value>":` branch with refusal /
   compliance / domain-specific keyword logic.
3. Use that value in any probe's `expected_behavior` field.

---

## 10. Non-functional notes

| Property | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Matches ML/LLM ecosystem; broadly readable. |
| Dependencies | `pyyaml`, `anthropic` | Minimal; both well-maintained. |
| Concurrency | Sequential | Simpler; probe counts are small at v0.1. Parallelisation is trivial to add later. |
| Persistence | Filesystem | Reports as markdown; no DB needed. |
| Secrets | `ANTHROPIC_API_KEY` env var | `config.yaml` is gitignored; key never touches disk. |
| Cost (claude target) | ~$0.01 per full 6-probe run | Defaults to Haiku for cheap iteration. |

---

## 11. Limitations (honest list)

- **Keyword judge is fragile.** A clever adversarial response that
  combines refusal and compliance language can confuse the rubric.
  Mitigation: planned LLM-as-judge in v0.2.
- **Single-turn only.** Many real attacks are multi-turn. v0.2 will add
  a `conversation` probe type.
- **No statistical confidence.** A probe is run once; flaky behaviour
  is invisible. v0.2 will add `--runs N` for reproducibility scoring.
- **English-centric keyword lists.** Judge will under-detect non-English
  responses.
- **No telemetry / dashboarding.** Reports are flat markdown files; no
  trend view across runs yet.

---

## 12. Roadmap (post-v0.1)

| Version | Theme | Notable items |
|---|---|---|
| v0.2 | Robustness | LLM-as-judge, reproducibility loops, JSON report. |
| v0.3 | Coverage | Multi-turn probes, OpenAI/Gemini adapters, larger probe library. |
| v0.4 | Integration | GitHub Action, CI pass-rate gating, HTML dashboard. |

---

## 13. Glossary

| Term | Meaning |
|---|---|
| **Probe** | A single adversarial test case (one prompt + expected behaviour). |
| **Target** | The agent being tested (Mock, Claude, custom). |
| **Judge** | The component that scores a response. |
| **Verdict** | One of `PASS`, `PARTIAL`, `FAIL`. |
| **Run** | A single end-to-end execution: load → query → judge → report. |
| **Report** | The markdown artefact produced by one run. |

---

_Document version 1.0 — generated alongside ShieldLM v0.1.0._
