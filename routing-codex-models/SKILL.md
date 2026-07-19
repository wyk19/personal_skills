---
name: routing-codex-models
description: Use when a request requires codebase exploration, code changes, debugging, refactoring, testing, or code review and model-aware delegation should balance cost, speed, and correctness.
---

# Routing Codex Models

## Overview

Route programming work by uncertainty, blast radius, and verification risk. Keep the main agent responsible for decomposition, evidence reconciliation, and final verification.

## Gate

If the request does not require code inspection, modification, debugging, testing, refactoring, or review, continue normally without starting the coding team. This includes ordinary conversation, writing-only work, and design discussion that has not reached implementation.

## Route Work

| Observable condition | Agent | Model policy |
| --- | --- | --- |
| Ownership or execution path is unknown | `code_explorer` | Luna, medium, read-only |
| Verification command is unknown, even if code scope is known | `code_explorer` | Luna, medium, read-only; locate relevant tests and commands |
| Target files, behavior, boundary, and verification command are all known | `simple_coder` | Luna, medium |
| Architecture is unclear; multiple modules, concurrency, security, or data integrity are involved; or Luna failed substantively | `complex_coder` | Sol, high |
| Substantive implementation needs independent review | `code_reviewer` | Sol, high, read-only |

Do not route work to Terra. Use Luna for cheap bounded execution and Sol when reasoning depth materially affects correctness.

## Orchestrate

1. Classify the request at the gate.
2. For every routed dispatch, call `spawn_agent` with `agent_type` set exactly to the table's agent and `fork_turns="none"`. Use `task_name` only as a distinct lowercase snake_case instance label; it does not select the custom agent or model.
3. Dispatch independent exploration lanes in parallel only when their scopes do not overlap.
4. Give every worker an objective, owned scope, evidence, constraints, verification status (`known: <command>` or `unknown: discover it`), and required return shape.
5. Serialize overlapping writes. State file ownership before genuinely disjoint parallel writes.
6. Escalate a Luna task to `complex_coder` when it reports uncertainty, expands scope, or fails verification for a substantive reason. Do not repeatedly retry Luna.
7. Dispatch `code_reviewer` after substantive implementation. Keep review independent and read-only.
8. Inspect cited code and fresh verification output before accepting any subagent result.

## Example

For an explicit one-file literal change with a named test, dispatch `simple_coder`. If it discovers an undocumented shared interface, stop that attempt and send the gathered evidence to `complex_coder`; use `code_reviewer` after the resulting substantive change.

## Handle Missing Capabilities

- Attempt the routed `agent_type` call. Only if the runtime rejects `agent_type` or the named agent is unavailable, say so and continue in the current thread using the same role boundary. Do not claim model routing occurred.
- If a configured model is unavailable, stop retrying that agent and report the exact model ID.
- If agents disagree, inspect their evidence before deciding.

## Common Mistakes

- Starting the team for ordinary conversation or design-only work.
- Passing a role name only as `task_name`; that creates a labeled generic agent and does not apply the role's model configuration.
- Sending an unclear task to `simple_coder` merely to save quota.
- Running agents with overlapping write ownership.
- Letting `code_reviewer` edit the implementation.
- Treating a subagent summary as verification evidence.
