# Project Structure Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `routing-codex-models/` a self-contained project boundary with a package-only `skill/` directory, project-local agents, tests, docs, and byte-preserved references while reducing the repository root README to an index.

**Architecture:** Move existing files into the ownership layout defined by the approved design, then update every documentation, test, script, and configuration path literal to resolve from the new locations. Keep routing behavior, audit logic, prompts, test assertions, and copied reference bytes unchanged; use a structural contract check as the red/green gate for the refactor.

**Tech Stack:** Markdown, POSIX file moves/copies, Python 3 standard library (`unittest`, `py_compile`), the repository's `skill-creator/scripts/quick_validate.py`, and Git path/diff checks.

## Global Constraints

- The installable package is exactly `routing-codex-models/skill/` and contains only the skill entrypoint `SKILL.md`, `agents/openai.yaml`, and `scripts/audit-routing-session.py`.
- There is no project-root `routing-codex-models/SKILL.md` after the move.
- Global custom agent TOMLs remain separate under `routing-codex-models/agents/*.toml`.
- The root `README.md` is an index only; `routing-codex-models/README.md` is authoritative for install, use, and audit instructions.
- `routing-codex-models/.gitattributes` contains exactly `references/*.md -whitespace` so intentional hard-break trailing spaces in source references remain byte-preserved.
- Tests and existing project docs live under `routing-codex-models/tests/` and `routing-codex-models/docs/` respectively.
- Move the untracked Chinese Markdown into `routing-codex-models/references/` without changing its bytes or filename.
- Update every path literal and install/audit example to use the target package path and global TOML path separately.
- Do not change routing behavior, agent prompts, audit logic, test behavior, or file contents except required path/documentation references.
- Generated `__pycache__/` directories are verification artifacts only; remove only those generated directories during cleanup and never treat them as source.

---

### Task 1: Add the failing structural contract

**Files:**
- Create: `routing-codex-models/tests/test_project_structure.py`
- Test: `routing-codex-models/tests/test_project_structure.py`
- Create directory: `routing-codex-models/tests/`

**Interfaces:**
- Consumes: repository root resolved from `Path(__file__).resolve().parents[2]`.
- Produces: deterministic `unittest` failures for each target path that is absent or still at an old path; later tasks make the same tests pass.

- [ ] **Step 1: Create the test directory and write the failing contract test**

Run: `mkdir -p routing-codex-models/tests`

Create a standard-library test that asserts the target files/directories and README ownership, and asserts the old locations do not exist. Include exact assertions for:

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ProjectStructureContractTests(unittest.TestCase):
    def test_target_layout_and_ownership(self):
        expected_files = (
            "README.md",
            "routing-codex-models/README.md",
            "routing-codex-models/skill/SKILL.md",
            "routing-codex-models/skill/agents/openai.yaml",
            "routing-codex-models/skill/scripts/audit-routing-session.py",
            "routing-codex-models/agents/code-explorer.toml",
            "routing-codex-models/agents/code-reviewer.toml",
            "routing-codex-models/agents/complex-coder.toml",
            "routing-codex-models/agents/simple-coder.toml",
            "routing-codex-models/tests/test_audit_routing_session.py",
            "routing-codex-models/tests/test_skill_contract.py",
            "routing-codex-models/docs/superpowers/specs/2026-07-20-routing-enforcement-design.md",
            "routing-codex-models/docs/superpowers/plans/2026-07-20-routing-enforcement.md",
            "routing-codex-models/docs/superpowers/specs/2026-07-20-project-structure-design.md",
            "routing-codex-models/docs/superpowers/plans/2026-07-20-project-structure.md",
            "routing-codex-models/references/【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md",
        )
        for relative_path in expected_files:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

        old_paths = (
            "routing-codex-models/SKILL.md",
            "routing-codex-models/agents/openai.yaml",
            "routing-codex-models/scripts/audit-routing-session.py",
            "codex-agents/routing-codex-models",
            "tests/test_audit_routing_session.py",
            "tests/test_skill_contract.py",
            "docs/superpowers/specs/2026-07-20-routing-enforcement-design.md",
            "docs/superpowers/plans/2026-07-20-routing-enforcement.md",
            "【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md",
        )
        for relative_path in old_paths:
            with self.subTest(relative_path=relative_path):
                self.assertFalse((ROOT / relative_path).exists())

    def test_root_readme_is_index_and_project_readme_owns_instructions(self):
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        project_readme = (ROOT / "routing-codex-models/README.md").read_text(encoding="utf-8")
        self.assertIn("routing-codex-models", root_readme)
        self.assertNotIn("cp -R ./routing-codex-models ~/.codex/skills/", root_readme)
        self.assertIn("~/.codex/skills/", project_readme)
        self.assertIn("routing-codex-models/skill/", project_readme)
        self.assertIn("routing-codex-models/agents/", project_readme)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the red check before any move**

Run: `python routing-codex-models/tests/test_project_structure.py -v`

Expected: FAIL because the current tree still has the package files at the project root, agent TOMLs under `codex-agents/`, tests at `tests/`, and the Chinese Markdown at the repository root.

- [ ] **Step 3: Confirm the red gate before moving source files**

Record the failing output, then continue to Task 2 without committing; the final approved restructuring is committed only after all verification gates pass.

### Task 2: Move the package and project-owned files

**Files:**
- Move: `routing-codex-models/SKILL.md` -> `routing-codex-models/skill/SKILL.md`
- Move: `routing-codex-models/agents/openai.yaml` -> `routing-codex-models/skill/agents/openai.yaml`
- Move: `routing-codex-models/scripts/audit-routing-session.py` -> `routing-codex-models/skill/scripts/audit-routing-session.py`
- Move: `codex-agents/routing-codex-models/*.toml` -> `routing-codex-models/agents/*.toml`
- Move: `tests/test_audit_routing_session.py` -> `routing-codex-models/tests/test_audit_routing_session.py`
- Move: `tests/test_skill_contract.py` -> `routing-codex-models/tests/test_skill_contract.py`
- Move: `docs/superpowers/specs/2026-07-20-routing-enforcement-design.md` -> `routing-codex-models/docs/superpowers/specs/2026-07-20-routing-enforcement-design.md`
- Move: `docs/superpowers/plans/2026-07-20-routing-enforcement.md` -> `routing-codex-models/docs/superpowers/plans/2026-07-20-routing-enforcement.md`
- Move: `【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md` -> `routing-codex-models/references/【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md`
- Create directories: `routing-codex-models/skill/agents/`, `routing-codex-models/skill/scripts/`, `routing-codex-models/agents/`, `routing-codex-models/tests/`, `routing-codex-models/docs/superpowers/plans/`, `routing-codex-models/references/`

**Interfaces:**
- Consumes: the current paths listed above.
- Produces: the target tree consumed by the structural test and by subsequent path updates.

- [ ] **Step 1: Create target directories and move tracked files with Git-aware moves**

Run these commands from the repository root, preserving the Chinese filename exactly:

```bash
mkdir -p routing-codex-models/skill/agents routing-codex-models/skill/scripts routing-codex-models/agents routing-codex-models/tests routing-codex-models/docs/superpowers/plans routing-codex-models/references
git mv routing-codex-models/SKILL.md routing-codex-models/skill/SKILL.md
git mv routing-codex-models/agents/openai.yaml routing-codex-models/skill/agents/openai.yaml
git mv routing-codex-models/scripts/audit-routing-session.py routing-codex-models/skill/scripts/audit-routing-session.py
git mv codex-agents/routing-codex-models/*.toml routing-codex-models/agents/
git mv tests/test_audit_routing_session.py tests/test_skill_contract.py routing-codex-models/tests/
git mv docs/superpowers/specs/2026-07-20-routing-enforcement-design.md routing-codex-models/docs/superpowers/specs/2026-07-20-routing-enforcement-design.md
git mv docs/superpowers/plans/2026-07-20-routing-enforcement.md routing-codex-models/docs/superpowers/plans/2026-07-20-routing-enforcement.md
```

Remove now-empty source directories only when they contain no other files: `codex-agents/routing-codex-models/`, `codex-agents/`, `tests/`, and the old `docs/superpowers/specs/` and `docs/superpowers/plans/` directories as applicable. Do not remove unrelated root files or any generated cache yet.

- [ ] **Step 2: Record the untracked reference digest before moving it**

Run: `sha256sum "【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md"`

Save the printed digest as the expected value for the next step. Do not edit, normalize, or re-save the Markdown.

- [ ] **Step 3: Move the untracked reference with plain `mv`**

Run:

```bash
mv "【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md" "routing-codex-models/references/【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md"
sha256sum "routing-codex-models/references/【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md"
```

Expected: the target digest exactly matches the value recorded in Step 2 and the source path no longer exists.

- [ ] **Step 4: Run the structural test**

Run: `python routing-codex-models/tests/test_project_structure.py -v`

Expected: the target-path assertions pass except for path/content assertions still awaiting README and import updates in Tasks 3 and 4; no source path should be recreated.

### Task 3: Split and correct README and path literals

**Files:**
- Modify: `README.md`
- Create: `routing-codex-models/README.md`
- Modify: `routing-codex-models/docs/superpowers/specs/2026-07-20-routing-enforcement-design.md`
- Modify: `routing-codex-models/docs/superpowers/plans/2026-07-20-routing-enforcement.md`

**Interfaces:**
- Consumes: moved files from Task 2 and the current combined README content.
- Produces: root index links, authoritative project install/use/audit documentation, and executable path references rooted at `routing-codex-models/skill/` or `routing-codex-models/agents/`.

- [ ] **Step 1: Reduce the root README to an index**

Keep the repository title, a concise Chinese description, and the Skill index link. Replace the duplicated project structure, installation, routing behavior, audit, and “添加新的 Skill” instructions with links to `./routing-codex-models/README.md`; do not leave install command examples in the root README.

- [ ] **Step 2: Create the project README from the moved project documentation**

Move all routing, installation, use, fail-closed dispatch, audit, behavior-boundary, and new-Skill instructions into `routing-codex-models/README.md`. Update examples exactly as follows:

```bash
mkdir -p ~/.codex/skills/routing-codex-models ~/.codex/agents
cp -R ./routing-codex-models/skill/. ~/.codex/skills/routing-codex-models/
cp ./routing-codex-models/agents/*.toml ~/.codex/agents/
python routing-codex-models/skill/scripts/audit-routing-session.py SESSION_ID \
  --sessions-dir ~/.codex/sessions \
  --latest-turn \
  --expect simple_coder:gpt-5.6-luna:medium \
  --expect code_reviewer:gpt-5.6-sol:high
```

State explicitly that copying only `routing-codex-models/skill/` or only `routing-codex-models/agents/*.toml` is incomplete. Link the design/spec and plan using paths under `routing-codex-models/docs/`.

- [ ] **Step 3: Update relocated test and documentation path literals without changing behavior**

In the relocated Python tests, replace fixture/module paths that assumed root-level `SKILL.md`, `agents/openai.yaml`, `scripts/audit-routing-session.py`, `tests/`, or `codex-agents/` with paths derived from the project root and new `skill/` and `agents/` directories. Update the relocated older plan/spec documentation links to point within `routing-codex-models/docs/`. Keep the skill package, agent TOML, function names, assertions, parser behavior, prompts, and command-line semantics byte-for-byte unchanged unless a path literal must change.

- [ ] **Step 4: Check for stale path literals**

Run:

```bash
rg -n --hidden --glob '!*.pyc' 'routing-codex-models/(SKILL\.md|scripts/|agents/openai\.yaml)|(^|[[:space:]`(])codex-agents/routing-codex-models|(^|[[:space:]`(])tests/|(^|[[:space:]`(])docs/superpowers/(specs|plans)/' README.md routing-codex-models/README.md routing-codex-models/skill routing-codex-models/tests routing-codex-models/docs/superpowers/specs/2026-07-20-routing-enforcement-design.md routing-codex-models/docs/superpowers/plans/2026-07-20-routing-enforcement.md
```

Expected: no matches in the scanned runtime, tests, README files, or relocated older docs. The implementation plan is intentionally excluded because it documents the source and target move paths.

### Task 4: Update tests and verify the full project contract

**Files:**
- Modify: `routing-codex-models/tests/test_audit_routing_session.py`
- Modify: `routing-codex-models/tests/test_skill_contract.py`
- Modify: `routing-codex-models/tests/test_project_structure.py`

**Interfaces:**
- Consumes: relocated tests and implementation paths from Tasks 2 and 3.
- Produces: tests runnable from the repository root with no dependence on the pre-refactor layout.

- [ ] **Step 1: Make test imports and fixture paths project-relative**

Use `Path(__file__).resolve().parents[1]` as the `routing-codex-models/` project root in both moved tests. Resolve the audit script at `PROJECT_ROOT / "skill/scripts/audit-routing-session.py"` and the Skill entrypoint at `PROJECT_ROOT / "skill/SKILL.md"`; preserve all test cases and expected behavior.

- [ ] **Step 2: Run the required unit-test command**

Run: `python -m unittest discover -s routing-codex-models/tests -v`

Expected: all discovered tests pass, including the structural contract and existing audit/skill contract tests.

- [ ] **Step 3: Compile the relocated audit script**

Run: `python -m py_compile routing-codex-models/skill/scripts/audit-routing-session.py`

Expected: exit code 0. Any generated `routing-codex-models/skill/scripts/__pycache__/` is verification output only.

- [ ] **Step 4: Run skill creator validation**

Run: `python /home/wangyankang/.codex/skills/.system/skill-creator/scripts/quick_validate.py routing-codex-models/skill`

Expected: validation succeeds for the package containing exactly `SKILL.md`, `agents/openai.yaml`, and `scripts/audit-routing-session.py`.

### Task 5: Final structural and diff checks

**Files:**
- Verify: `README.md`
- Verify: `routing-codex-models/README.md`
- Verify: `routing-codex-models/.gitattributes`
- Verify: `routing-codex-models/skill/`
- Verify: `routing-codex-models/agents/`
- Verify: `routing-codex-models/tests/`
- Verify: `routing-codex-models/docs/`
- Verify: `routing-codex-models/references/`

**Interfaces:**
- Consumes: the complete moved and path-corrected project.
- Produces: evidence that the implementation is limited to the approved structure refactor and has no whitespace or stale-tree regressions.

- [ ] **Step 1: Assert the exact target tree and old-path absence**

Run:

```bash
find routing-codex-models -type f -not -path '*/__pycache__/*' | sort
test -f README.md
test -f routing-codex-models/README.md
test -f routing-codex-models/skill/SKILL.md
test -f routing-codex-models/skill/agents/openai.yaml
test -f routing-codex-models/skill/scripts/audit-routing-session.py
test -f routing-codex-models/agents/code-explorer.toml
test -f routing-codex-models/agents/code-reviewer.toml
test -f routing-codex-models/agents/complex-coder.toml
test -f routing-codex-models/agents/simple-coder.toml
test -f routing-codex-models/tests/test_audit_routing_session.py
test -f routing-codex-models/tests/test_skill_contract.py
test -f routing-codex-models/tests/test_project_structure.py
test -f 'routing-codex-models/references/【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md'
test ! -e routing-codex-models/SKILL.md
test ! -e routing-codex-models/agents/openai.yaml
test ! -e routing-codex-models/scripts/audit-routing-session.py
test ! -e codex-agents/routing-codex-models
test ! -e tests/test_audit_routing_session.py
test ! -e tests/test_skill_contract.py
test ! -e '【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md'
```

Expected: every `test` succeeds and the file list contains no source file outside the target project boundary except the root index.

- [ ] **Step 2: Recheck reference byte identity**

Compare the post-move SHA-256 digest with the digest recorded in Task 2. A mismatch is a failure requiring restoration from Git and a repeat of the move without content conversion.

Also run `git check-attr whitespace -- "routing-codex-models/references/【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md"`; expected output ends with `whitespace: unset`. The reference digest must remain `419166edc3f8fc4fcc48b26ce2c5eb2f8fb7be1e0720edcdd3d029f16fa94cb2`.

- [ ] **Step 3: Run whitespace and final test checks**

Run: `git diff --check`

Then rerun exactly: `python -m unittest discover -s routing-codex-models/tests -v`.

Expected: both commands exit 0.

- [ ] **Step 4: Remove verification-only caches**

After all commands finish, remove only generated `__pycache__/` directories under `routing-codex-models/skill/` and `routing-codex-models/tests/` (and any pre-existing `routing-codex-models/scripts/__pycache__/` left by the old location if still present). Do not delete source files, reference material, or unrelated caches.

- [ ] **Step 5: Review, commit, push, and verify the final diff**

First remove verification-only caches as described in Step 4, then run:

```bash
git status --short
git diff --stat
git add -A -- README.md routing-codex-models codex-agents/routing-codex-models tests docs/superpowers
git diff --cached --check
git commit -m "refactor: organize routing skill project structure"
git push origin main
test "$(git rev-parse HEAD)" = "$(git ls-remote origin refs/heads/main | awk '{print $1}')"
```

Expected: the status and stat show only approved restructuring, `git diff --cached --check` is clean, the commit succeeds, push updates `origin/main`, and the final `test` confirms local `HEAD` equals the remote `main` commit. Generated caches must not appear in the staged diff.

## Self-Review Checklist

- **Spec coverage:** Tasks 1-5 cover the target layout, ownership rules, all path updates, the two-part installation contract, non-goals, both existing root-doc moves, byte-preserved reference move, RED-before-moves gate, GREEN verification, generated-cache cleanup, and GitHub commit/push parity verification.
- **Placeholder scan:** No unresolved placeholder markers or unspecified error-handling steps appear; every action has a concrete path, command, or content requirement.
- **Path/type consistency:** The structural test and all later tasks use `routing-codex-models/skill/` for the installable package, `routing-codex-models/agents/*.toml` for global agents, and `routing-codex-models/tests/` for test discovery consistently.
