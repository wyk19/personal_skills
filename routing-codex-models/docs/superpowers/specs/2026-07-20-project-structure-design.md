# Project Structure Design

## Purpose

Keep the repository root readable while making `routing-codex-models/` the complete, self-contained project boundary. The root README is an index; project installation, use, audit, tests, references, and design documents belong to the project directory.

## Target Layout

```text
README.md                         # repository index only
routing-codex-models/
  README.md                       # project install, use, and audit documentation
  skill/
    SKILL.md                      # only skill entrypoint and installable package
    agents/
      openai.yaml
    scripts/
      audit-routing-session.py
  agents/
    *.toml                         # global custom agent definitions
  tests/                            # project tests
  docs/                             # existing project documentation and specs
  references/                       # copied Chinese Markdown reference material
```

The installable package is exactly `routing-codex-models/skill/` and contains the only skill entrypoint, `SKILL.md`, plus `agents/openai.yaml` and `scripts/audit-routing-session.py`. There is no project-root `routing-codex-models/SKILL.md`. Global custom agent TOMLs remain separate under `routing-codex-models/agents/` because they are installed at the global agent scope rather than inside the skill package.

## Ownership Rules

- The root `README.md` lists the repository projects and links into `routing-codex-models/`; it does not duplicate project instructions.
- `routing-codex-models/README.md` is the authoritative guide for installing, using, and auditing this project.
- Skill package paths are resolved relative to `routing-codex-models/skill/`.
- Custom agent definitions are resolved from `routing-codex-models/agents/*.toml`.
- Tests and current project docs are moved under `routing-codex-models/tests/` and `routing-codex-models/docs/` respectively.
- The untracked copied Chinese Markdown is moved under `routing-codex-models/references/` without changing its contents.

## Path Updates

Every documentation, test, script, and configuration path literal must be updated to the target locations. References to the old root-level project files must point to `routing-codex-models/` or its designated subdirectory. Examples in install and audit instructions must use the concrete package paths and the global TOML path separately.

## Installation and Use Contract

Installation requires both deliverables:

1. Install or copy the complete skill package from `routing-codex-models/skill/`, including its `SKILL.md`, `agents/openai.yaml`, and `scripts/audit-routing-session.py` files.
2. Install or copy every required custom agent TOML from `routing-codex-models/agents/*.toml` into the global custom-agent location used by the host environment.

The project README must state that installing only the skill package or only the global agent TOMLs is incomplete. Usage and audit examples must reference the relocated script and the relocated agent definitions.

## Non-Goals

This design does not change routing behavior, agent prompts, audit logic, test behavior, or file contents. It defines ownership and paths only; implementation changes and unrelated repository cleanup are out of scope.
