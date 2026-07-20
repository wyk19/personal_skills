import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = REPO_ROOT / "routing-codex-models" / "scripts" / "audit-routing-session.py"


class RoutingSessionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sessions_dir = Path(self.temp_dir.name)
        self.root_id = "019f0000-0000-7000-8000-000000000001"
        self.turn_id = "019f0000-0000-7000-8000-000000001001"

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_jsonl(self, name, records):
        path = self.sessions_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )
        return path

    def root_meta(self):
        return {
            "type": "session_meta",
            "payload": {
                "id": self.root_id,
                "session_id": self.root_id,
                "source": "cli",
                "thread_source": "user",
            },
        }

    def turn_context(self, turn_id=None):
        return {
            "type": "turn_context",
            "payload": {"turn_id": turn_id or self.turn_id},
        }

    def root_records(self, *records, turn_id=None):
        return [self.root_meta(), self.turn_context(turn_id), *records]

    def spawn_call(
        self, task_name, fork_turns, agent_type=None, call_id=None, turn_id=None
    ):
        arguments = {
            "task_name": task_name,
            "fork_turns": fork_turns,
            "message": "bounded test task",
        }
        if agent_type is not None:
            arguments["agent_type"] = agent_type
        return {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "spawn_agent",
                "arguments": json.dumps(arguments),
                "call_id": call_id or f"call_{task_name}",
                "internal_chat_message_metadata_passthrough": {
                    "turn_id": turn_id or self.turn_id
                },
            },
        }

    def spawn_started(self, task_name, child_id, call_id=None):
        return {
            "type": "event_msg",
            "payload": {
                "type": "sub_agent_activity",
                "event_id": call_id or f"call_{task_name}",
                "agent_thread_id": child_id,
                "agent_path": f"/root/{task_name}",
                "kind": "started",
            },
        }

    def spawn_output(self, task_name, call_id=None, output_task_name=None):
        return {
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": call_id or f"call_{task_name}",
                "output": json.dumps(
                    {"task_name": output_task_name or f"/root/{task_name}"}
                ),
            },
        }

    def successful_spawn(
        self,
        task_name,
        fork_turns,
        agent_type,
        child_id,
        call_id=None,
        turn_id=None,
    ):
        return [
            self.spawn_call(
                task_name, fork_turns, agent_type, call_id, turn_id
            ),
            self.spawn_started(task_name, child_id, call_id),
            self.spawn_output(task_name, call_id),
        ]

    def child_records(self, role, model, effort, child_id, task_name=None):
        agent_path = f"/root/{task_name or role or 'generic'}"
        return [
            {
                "type": "session_meta",
                "payload": {
                    "session_id": self.root_id,
                    "id": child_id,
                    "source": {
                        "subagent": {
                            "thread_spawn": {
                                "parent_thread_id": self.root_id,
                                "depth": 1,
                                "agent_path": agent_path,
                                "agent_role": role,
                            }
                        }
                    },
                    "thread_source": "subagent",
                    "agent_role": role,
                    "agent_path": agent_path,
                },
            },
            {
                "type": "turn_context",
                "payload": {"model": model, "effort": effort},
            },
        ]

    def run_audit(self, *expectations, turn_id=None):
        command = [
            sys.executable,
            str(AUDIT_SCRIPT),
            self.root_id,
            "--sessions-dir",
            str(self.sessions_dir),
        ]
        if turn_id is None:
            command.append("--latest-turn")
        else:
            command.extend(["--turn-id", turn_id])
        for expectation in expectations:
            command.extend(["--expect", expectation])
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def test_accepts_typed_luna_implementation_and_sol_review(self):
        simple_id = "019f0000-0000-7000-8000-000000000002"
        review_id = "019f0000-0000-7000-8000-000000000003"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", simple_id
                ),
                *self.successful_spawn(
                    "review_change", "none", "code_reviewer", review_id
                ),
            ),
        )
        self.write_jsonl(
            "simple-child.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                simple_id,
                "implement_change",
            ),
        )
        self.write_jsonl(
            "review-child.jsonl",
            self.child_records(
                "code_reviewer",
                "gpt-5.6-sol",
                "high",
                review_id,
                "review_change",
            ),
        )

        result = self.run_audit(
            "simple_coder:gpt-5.6-luna:medium",
            "code_reviewer:gpt-5.6-sol:high",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS simple_coder", result.stdout)
        self.assertIn("PASS code_reviewer", result.stdout)

    def test_rejects_parent_fallback_and_generic_reviewer(self):
        self.write_jsonl(
            "root.jsonl",
            self.root_records(self.spawn_call("task8_review", "all")),
        )
        self.write_jsonl(
            "generic-child.jsonl",
            self.child_records(
                None,
                "gpt-5.6-terra",
                "high",
                "019f0000-0000-7000-8000-000000000004",
            ),
        )

        result = self.run_audit("code_reviewer:gpt-5.6-sol:high")

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing typed spawn for code_reviewer", result.stderr)
        self.assertIn("task8_review", result.stderr)
        self.assertIn("missing agent_type", result.stderr)

    def test_rejects_wrong_fork_model_and_effort(self):
        child_id = "019f0000-0000-7000-8000-000000000005"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "all", "simple_coder", child_id
                ),
            ),
        )
        self.write_jsonl(
            "simple-child.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-terra",
                "high",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn('fork_turns is "all", expected "none"', result.stderr)
        self.assertIn("gpt-5.6-terra/high", result.stderr)
        self.assertIn("gpt-5.6-luna/medium", result.stderr)
        self.assertNotIn("PASS simple_coder", result.stdout)

    def test_wrong_fork_never_prints_pass(self):
        child_id = "019f0000-0000-7000-8000-000000000026"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "all", "simple_coder", child_id
                ),
            ),
        )
        self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertNotIn("PASS simple_coder", result.stdout)

    def test_requires_at_least_one_expectation(self):
        self.write_jsonl("root.jsonl", self.root_records())

        result = self.run_audit()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--expect", result.stderr)
        self.assertIn("required", result.stderr)

    def test_rejects_stale_same_role_child_without_successful_start(self):
        stale_id = "019f0000-0000-7000-8000-000000000006"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                self.spawn_call("implement_change", "none", "simple_coder"),
                self.spawn_output("implement_change"),
            ),
        )
        self.write_jsonl(
            "stale-child.jsonl",
            self.child_records(
                "simple_coder", "gpt-5.6-luna", "medium", stale_id
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("no successful started spawn", result.stderr)

    def test_uses_started_child_id_instead_of_unlinked_same_role_child(self):
        stale_id = "019f0000-0000-7000-8000-000000000007"
        linked_id = "019f0000-0000-7000-8000-000000000008"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", linked_id
                ),
            ),
        )
        self.write_jsonl(
            "a-stale-child.jsonl",
            self.child_records(
                "simple_coder", "gpt-5.6-luna", "medium", stale_id
            ),
        )
        self.write_jsonl(
            "z-linked-child.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-sol",
                "high",
                linked_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("gpt-5.6-sol/high", result.stderr)

    def test_repeated_expectations_require_distinct_successful_spawns(self):
        child_id = "019f0000-0000-7000-8000-000000000009"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", child_id
                ),
            ),
        )
        self.write_jsonl(
            "simple-child.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit(
            "simple_coder:gpt-5.6-luna:medium",
            "simple_coder:gpt-5.6-luna:medium",
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count("PASS simple_coder"), 0)
        self.assertIn("distinct successful spawn", result.stderr)

    def test_root_path_discovers_child_in_another_date_directory(self):
        child_id = "019f0000-0000-7000-8000-000000000010"
        root_path = self.write_jsonl(
            "2026/07/19/root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", child_id
                ),
            ),
        )
        self.write_jsonl(
            "2026/07/20/simple-child.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )
        command = [
            sys.executable,
            str(AUDIT_SCRIPT),
            str(root_path),
            "--sessions-dir",
            str(self.sessions_dir),
            "--latest-turn",
            "--expect",
            "simple_coder:gpt-5.6-luna:medium",
        ]

        result = subprocess.run(command, capture_output=True, text=True, check=False)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_malformed_root_evidence_fails_closed(self):
        child_id = "019f0000-0000-7000-8000-000000000011"
        root_path = self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", child_id
                ),
            ),
        )
        with root_path.open("a", encoding="utf-8") as handle:
            handle.write("{malformed\n")
        self.write_jsonl(
            "simple-child.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid JSON", result.stderr)

    def test_malformed_linked_child_evidence_fails_closed(self):
        child_id = "019f0000-0000-7000-8000-000000000012"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", child_id
                ),
            ),
        )
        child_path = self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )
        with child_path.open("a", encoding="utf-8") as handle:
            handle.write("not-json\n")

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid JSON", result.stderr)

    def test_spawn_without_success_output_does_not_count(self):
        child_id = "019f0000-0000-7000-8000-000000000013"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                self.spawn_call("implement_change", "none", "simple_coder"),
                self.spawn_started("implement_change", child_id),
            ),
        )
        self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("no successful started spawn", result.stderr)

    def test_rejects_duplicate_spawn_call_ids(self):
        child_id = "019f0000-0000-7000-8000-000000000014"
        duplicate_id = "call_duplicate"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                self.spawn_call(
                    "implement_change", "none", "simple_coder", duplicate_id
                ),
                self.spawn_call(
                    "implement_change", "none", "simple_coder", duplicate_id
                ),
                self.spawn_started("implement_change", child_id, duplicate_id),
                self.spawn_output("implement_change", duplicate_id),
            ),
        )
        self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate spawn call_id", result.stderr)

    def test_rejects_out_of_order_spawn_lifecycle(self):
        child_id = "019f0000-0000-7000-8000-000000000015"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                self.spawn_started("implement_change", child_id),
                self.spawn_call("implement_change", "none", "simple_coder"),
                self.spawn_output("implement_change"),
            ),
        )
        self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("out-of-order spawn lifecycle", result.stderr)

    def test_unreadable_linked_child_evidence_fails_closed(self):
        child_id = "019f0000-0000-7000-8000-000000000016"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", child_id
                ),
            ),
        )
        child_path = self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )
        child_path.chmod(0)
        try:
            result = self.run_audit("simple_coder:gpt-5.6-luna:medium")
        finally:
            child_path.chmod(0o600)

        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read", result.stderr)

    def test_latest_turn_does_not_reuse_success_from_earlier_turn(self):
        old_turn = "019f0000-0000-7000-8000-000000001002"
        old_child = "019f0000-0000-7000-8000-000000000017"
        self.write_jsonl(
            "root.jsonl",
            [
                self.root_meta(),
                self.turn_context(old_turn),
                *self.successful_spawn(
                    "old_implementation",
                    "none",
                    "simple_coder",
                    old_child,
                    turn_id=old_turn,
                ),
                self.turn_context(),
                self.spawn_call(
                    "latest_implementation", "none", "simple_coder"
                ),
                self.spawn_output("latest_implementation"),
            ],
        )
        self.write_jsonl(
            f"child-{old_child}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                old_child,
                "old_implementation",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("latest_implementation", result.stderr)
        self.assertIn("missing started event", result.stderr)

    def test_generic_spawn_in_selected_turn_is_always_an_error(self):
        child_id = "019f0000-0000-7000-8000-000000000018"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", child_id
                ),
                self.spawn_call("generic_review", "none"),
            ),
        )
        self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("spawn generic_review missing agent_type", result.stderr)

    def test_any_ledger_error_suppresses_all_pass_output(self):
        child_id = "019f0000-0000-7000-8000-000000000027"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", child_id
                ),
                self.spawn_call("generic_review", "none"),
            ),
        )
        self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("spawn generic_review missing agent_type", result.stderr)
        self.assertIn("missing started event", result.stderr)
        self.assertIn("missing successful output", result.stderr)
        self.assertNotIn("PASS", result.stdout)

    def test_unexpected_typed_role_requires_an_expectation(self):
        simple_id = "019f0000-0000-7000-8000-000000000019"
        review_id = "019f0000-0000-7000-8000-000000000020"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", simple_id
                ),
                *self.successful_spawn(
                    "review_change", "none", "code_reviewer", review_id
                ),
            ),
        )
        self.write_jsonl(
            f"child-{simple_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                simple_id,
                "implement_change",
            ),
        )
        self.write_jsonl(
            f"child-{review_id}.jsonl",
            self.child_records(
                "code_reviewer",
                "gpt-5.6-sol",
                "high",
                review_id,
                "review_change",
            ),
        )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("unexpected typed role code_reviewer", result.stderr)
        self.assertIn("add --expect", result.stderr)

    def test_repeated_expectations_reject_replayed_child_uuid(self):
        child_id = "019f0000-0000-7000-8000-000000000021"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change",
                    "none",
                    "simple_coder",
                    child_id,
                    "call_first",
                ),
                *self.successful_spawn(
                    "implement_change",
                    "none",
                    "simple_coder",
                    child_id,
                    "call_second",
                ),
            ),
        )
        self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )

        result = self.run_audit(
            "simple_coder:gpt-5.6-luna:medium",
            "simple_coder:gpt-5.6-luna:medium",
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn(f"replayed child session {child_id}", result.stderr)

    def test_explicit_turn_id_audits_only_that_turn(self):
        old_turn = "019f0000-0000-7000-8000-000000001003"
        old_child = "019f0000-0000-7000-8000-000000000022"
        self.write_jsonl(
            "root.jsonl",
            [
                self.root_meta(),
                self.turn_context(old_turn),
                *self.successful_spawn(
                    "old_implementation",
                    "none",
                    "simple_coder",
                    old_child,
                    turn_id=old_turn,
                ),
                self.turn_context(),
                self.spawn_call("latest_generic", "none"),
            ],
        )
        self.write_jsonl(
            f"child-{old_child}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                old_child,
                "old_implementation",
            ),
        )

        result = self.run_audit(
            "simple_coder:gpt-5.6-luna:medium", turn_id=old_turn
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS simple_coder", result.stdout)

    def test_requires_exactly_one_turn_scope(self):
        self.write_jsonl("root.jsonl", self.root_records())
        command = [
            sys.executable,
            str(AUDIT_SCRIPT),
            self.root_id,
            "--sessions-dir",
            str(self.sessions_dir),
            "--expect",
            "simple_coder:gpt-5.6-luna:medium",
        ]

        result = subprocess.run(command, capture_output=True, text=True, check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--latest-turn", result.stderr)
        self.assertIn("--turn-id", result.stderr)
        self.assertIn("required", result.stderr)

    def test_explicit_unknown_turn_id_fails_closed(self):
        child_id = "019f0000-0000-7000-8000-000000000025"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_change", "none", "simple_coder", child_id
                ),
            ),
        )
        self.write_jsonl(
            f"child-{child_id}.jsonl",
            self.child_records(
                "simple_coder",
                "gpt-5.6-luna",
                "medium",
                child_id,
                "implement_change",
            ),
        )
        missing_turn = "019f0000-0000-7000-8000-000000009999"

        result = self.run_audit(
            "simple_coder:gpt-5.6-luna:medium", turn_id=missing_turn
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn(f"turn not found: {missing_turn}", result.stderr)

    def test_extra_same_role_spawn_fails_exact_count(self):
        first_child = "019f0000-0000-7000-8000-000000000023"
        second_child = "019f0000-0000-7000-8000-000000000024"
        self.write_jsonl(
            "root.jsonl",
            self.root_records(
                *self.successful_spawn(
                    "implement_first",
                    "none",
                    "simple_coder",
                    first_child,
                    "call_first",
                ),
                *self.successful_spawn(
                    "implement_second",
                    "none",
                    "simple_coder",
                    second_child,
                    "call_second",
                ),
            ),
        )
        for child_id, task_name in (
            (first_child, "implement_first"),
            (second_child, "implement_second"),
        ):
            self.write_jsonl(
                f"child-{child_id}.jsonl",
                self.child_records(
                    "simple_coder",
                    "gpt-5.6-luna",
                    "medium",
                    child_id,
                    task_name,
                ),
            )

        result = self.run_audit("simple_coder:gpt-5.6-luna:medium")

        self.assertEqual(result.returncode, 1)
        self.assertIn("expected 1 simple_coder spawn(s), found 2", result.stderr)


if __name__ == "__main__":
    unittest.main()
