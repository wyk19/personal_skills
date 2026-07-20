# Fail-Closed Codex Model Routing

## Problem

`routing-codex-models` can be discovered and read while the parent agent still performs coding work itself. The observed failure used two loopholes in the current instructions:

- a "single sequential task" was treated as permission to stay in the parent thread;
- a generic `spawn_agent` call without `agent_type` was treated as adequate delegation.

That behavior defeats the Skill's purpose because neither the selected custom role nor its Luna/Sol model policy is applied.

## Design

When the coding gate matches, typed dispatch is mandatory before implementation work begins. The parent may classify the request, coordinate workers, reconcile evidence, and run final verification, but it must not inspect implementation details, edit files, write tests, or implement the change before a successful routed dispatch.

Every routed call must include both:

- `agent_type` set to one of `code_explorer`, `simple_coder`, `complex_coder`, or `code_reviewer`;
- `fork_turns="none"`.

Small, urgent, and sequential tasks are not exceptions. A sequential task means one typed worker runs at a time. It does not mean the parent becomes the worker.

If the runtime rejects `agent_type` or the selected custom agent, routing fails closed. The parent reports `ROUTING_UNAVAILABLE` with the exact error and stops before code inspection or mutation. It must not claim that routing is active until a typed spawn succeeds.

## Evidence And Audit

A standard-library audit script will inspect Codex session JSONL files. Given a root session ID and expected role/model/effort triples, it verifies:

- the parent called `spawn_agent` with the expected `agent_type`;
- the call used `fork_turns="none"`;
- a child session started with the expected `agent_role`;
- the child ran the configured model and reasoning effort.

The audit is intentionally independent of the agent's prose claims.

## Hook Decision

No global hook is installed in this change. Stable Codex hook inputs do not provide a reliable, documented way for a global `PreToolUse` hook to distinguish the routing parent from every routed child while preserving unrelated sessions. A global write blocker would therefore risk blocking legitimate child work or unrelated tasks. The Skill contract prevents silent fallback, and the audit makes routing observable; a hook can be added later as a separately scoped opt-in if the runtime exposes a robust parent/child identity field.

## Acceptance Criteria

1. The former "single sequential task" rationale is explicitly forbidden.
2. Unsupported typed routing stops before parent-thread implementation.
3. Generic subagents and role-like `task_name` values do not count as routing.
4. Portable unit tests cover passing and failing session transcripts.
5. A disposable end-to-end Codex session produces a typed child with the configured model and passes the audit.
