# ShieldLM

> Red-teaming and adversarial evaluation for LLM-powered agents.

## The problem

Production AI agents are being deployed faster than they're being tested. Recent incidents — including an AI coding agent that wiped a production database and its backups in seconds — point to a gap most teams haven't closed: structured adversarial evaluation before release.

ShieldLM is a red-teaming framework that pressure-tests LLM agents against known failure modes before they reach production.

## What it tests

ShieldLM runs adversarial probes across these categories:

- **Prompt injection** — direct and indirect attempts to override system instructions, including injections delivered through tool results, retrieved documents, and user-supplied content
- **Jailbreak resistance** — eliciting prohibited outputs through role-play, encoding tricks, multi-turn manipulation, and context-stuffing
- **Tool misuse** — destructive or unauthorized tool calls triggered by adversarial input (file deletion, database operations, unauthorized API calls)
- **Data exfiltration** — probing for system-prompt leakage, training-data regurgitation, and PII exposure
- **Instruction-hierarchy violations** — testing whether the agent respects the trust levels of system, developer, user, and tool-result inputs

> _Edit this list to match the probe categories you've actually implemented._

## How it works

1. **Attack library** — curated adversarial prompts categorized by attack vector, drawn from OWASP LLM Top 10, published red-team research, and original probes
2. **Target adapter** — pluggable interface for the LLM or agent under test (Claude, GPT, Gemini, or a custom agent endpoint)
3. **Eval harness** — runs each probe, captures outputs, and scores against a rubric (pass / partial / fail) with reproducibility metadata
4. **Report generator** — produces a structured findings report with severity, reproducibility rate, and suggested mitigation

## Sample findings

> _Fill in 2–3 real examples from your runs. Hiring managers and recruiters skim straight to this table — it's the part of the README that proves the project is real._

| Attack vector | Target | Severity | Reproducibility | Status |
|---|---|---|---|---|
| Indirect prompt injection via tool result | [agent under test] | High | 8/10 runs | Mitigated |
| Multi-turn role-play jailbreak | [agent under test] | Medium | 5/10 runs | Open |
| Destructive tool call via crafted input | [agent under test] | Critical | 3/10 runs | Mitigated |

## Why this matters for AI product teams

Most enterprises rolling out agents in 2026 don't have a structured red-team process. ShieldLM is built on the assumption that adversarial evaluation should sit alongside accuracy evals and latency benchmarks — as a release gate, not an afterthought.

For teams shipping LLM agents in regulated sectors (BFSI, healthcare, government), this kind of evaluation is moving from "nice to have" to audit requirement. JPMorgan reclassified AI from R&D to core infrastructure in May 2026, with cybersecurity hardening as one of three focus areas. That signals the bar.

## Getting started

```bash
git clone https://github.com/[your-handle]/shieldlm
cd shieldlm
pip install -r requirements.txt

cp config.example.yaml config.yaml
# Set your target endpoint and API key in config.yaml

python -m shieldlm run --probe-set prompt_injection --target claude
```

> _Adjust the commands to match your actual CLI / module structure._

## Roadmap

- [ ] Expanded probe library (currently [X] probes across [Y] categories)
- [ ] CI/CD integration so probe runs gate releases
- [ ] Auto-generated mitigation suggestions per finding
- [ ] Pass-rate dashboard tracked across model versions

## Background

I built ShieldLM because the gap between demoing an AI agent and deploying one safely is widening, and most teams are skipping structured red-teaming entirely. The probe library draws on the OWASP LLM Top 10, Anthropic's responsible scaling framework, and published adversarial ML research.

This is a side project, built in the open, with the goal of making release-gate adversarial evaluation a default practice rather than a specialist concern.

## Author

**Reekhil Khanna** — Senior PM transitioning into AI product roles. Currently building Orion (LangGraph-based job-hunting agent), ShieldLM, and HerPurse.

[LinkedIn](https://www.linkedin.com/in/reekhil-khanna-51603a67/)
