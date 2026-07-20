import unittest
from pathlib import Path


SKILL_PATH = Path(__file__).resolve().parents[1] / "routing-codex-models" / "SKILL.md"
README_PATH = Path(__file__).resolve().parents[1] / "README.md"


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")

    def test_dispatch_gate_is_mandatory(self):
        self.assertIn("## Non-Negotiable Dispatch Gate", self.skill)
        self.assertIn("typed dispatch is mandatory", self.skill)
        self.assertIn("before any implementation work", self.skill)

    def test_parent_thread_fallback_is_forbidden(self):
        self.assertIn("Small, urgent, and sequential tasks are not exceptions", self.skill)
        self.assertIn(
            "must not inspect implementation details, edit files, write tests, or implement",
            self.skill,
        )
        self.assertNotIn("continue in the current thread", self.skill.lower())

    def test_routing_requires_observable_typed_spawn(self):
        self.assertIn("Routing is active only after a successful typed spawn", self.skill)
        self.assertIn('agent_type', self.skill)
        self.assertIn('fork_turns="none"', self.skill)

    def test_missing_capability_fails_closed(self):
        self.assertIn("ROUTING_UNAVAILABLE: <exact runtime error>", self.skill)
        self.assertIn("stop before code inspection or mutation", self.skill)

    def test_missing_model_fails_closed_without_degradation(self):
        self.assertIn(
            "If a configured model is unavailable, report `ROUTING_UNAVAILABLE:",
            self.skill,
        )
        self.assertIn("stop without fallback", self.skill)
        self.assertNotIn("报告降级", self.readme)
        self.assertIn("ROUTING_UNAVAILABLE", self.readme)

    def test_exploration_or_review_never_authorizes_parent_implementation(self):
        self.assertIn(
            "A successful `code_explorer` or `code_reviewer` spawn never authorizes",
            self.skill,
        )

    def test_readme_documents_turn_scope_and_audit_boundary(self):
        self.assertIn("--latest-turn", self.readme)
        self.assertIn("--turn-id TURN_ID", self.readme)
        self.assertIn("每个 `spawn_agent`", self.readme)
        self.assertIn("不解析不可靠的 shell 命令", self.readme)
        self.assertIn("Skill 的 fail-closed 行为契约", self.readme)
        self.assertIn(
            "Every implementation and review correction remains owned by `simple_coder` or `complex_coder`",
            self.skill,
        )


if __name__ == "__main__":
    unittest.main()
