# Routing Enforcement Implementation Plan

**Goal:** Make `routing-codex-models` fail closed and provide transcript-level proof that the intended custom agent, model, effort, and isolation settings were used.

**Architecture:** Strengthen the prose contract in `routing-codex-models/skill/SKILL.md`, add a standalone JSONL audit CLI inside the Skill package, and cover it with synthetic transcript tests. Keep model selection in the existing custom-agent TOML files.

**Tech Stack:** Markdown, Python 3 standard library, `unittest`, Codex JSONL session logs.

### Task 1: Lock the failure mode with tests

**Files:**
- Create: `routing-codex-models/tests/test_audit_routing_session.py`
- Create: `routing-codex-models/tests/test_skill_contract.py`

Add synthetic parent/child transcripts for a generic Terra reviewer, a correct typed Luna/Sol route, wrong effort, and wrong `fork_turns`. Add static contract checks for mandatory dispatch, forbidden parent fallback, and the `ROUTING_UNAVAILABLE` failure signal. Run the suite and confirm it fails before implementation exists.

### Task 2: Implement session auditing

**Files:**
- Create: `routing-codex-models/skill/scripts/audit-routing-session.py`

Find the root transcript by session ID or explicit path, parse parent `spawn_agent` calls and descendant session metadata, compare each `--expect ROLE:MODEL:EFFORT` value, and return a non-zero exit code with concrete diagnostics on mismatch.

### Task 3: Enforce fail-closed routing

**Files:**
- Modify: `routing-codex-models/skill/SKILL.md`
- Modify: `routing-codex-models/README.md`

Add a non-negotiable dispatch gate, explicit parent restrictions, successful-spawn proof rules, and red-flag rationalizations. Replace current-thread fallback with an exact fail-closed response. Document audit usage and limitations.

### Task 4: Verify and deploy

Run unit tests, Skill validation, TOML/YAML parsing, and a disposable end-to-end Codex task. Audit the generated session. Copy the updated Skill package to `~/.codex/skills/routing-codex-models`, compare installed files, review the diff, commit, and push `main`.
