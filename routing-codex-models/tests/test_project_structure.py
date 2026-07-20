from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ProjectStructureContractTests(unittest.TestCase):
    def test_target_layout_and_ownership(self):
        expected_files = (
            "README.md",
            "routing-codex-models/README.md",
            "routing-codex-models/.gitattributes",
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
            "routing-codex-models/" + "SKILL.md",
            "routing-codex-models/" + "agents/openai.yaml",
            "routing-codex-models/" + "scripts/audit-routing-session.py",
            "codex-agents/" + "routing-codex-models",
            "tests/" + "test_audit_routing_session.py",
            "tests/" + "test_skill_contract.py",
            "docs/superpowers/" + "specs/2026-07-20-routing-enforcement-design.md",
            "docs/superpowers/" + "plans/2026-07-20-routing-enforcement.md",
            "【拯救_5.6_Sol（1）】开箱即用、快速高效、减少上下文腐烂的Codex子代理实践_-_开发调优.md",
        )
        for relative_path in old_paths:
            with self.subTest(relative_path=relative_path):
                self.assertFalse((ROOT / relative_path).exists())

    def test_reference_markdown_whitespace_policy(self):
        gitattributes_path = ROOT / "routing-codex-models/.gitattributes"
        self.assertTrue(gitattributes_path.is_file())
        self.assertEqual(
            gitattributes_path.read_text(encoding="utf-8"),
            "references/*.md -whitespace\n",
        )

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
