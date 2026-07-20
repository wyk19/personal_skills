#!/usr/bin/env python3
"""Audit typed Codex routing evidence from session JSONL transcripts."""

import argparse
import json
import sys
from pathlib import Path


class EvidenceError(Exception):
    """The supplied transcript evidence cannot be trusted."""


def _records(path):
    records = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise EvidenceError(
                        f"invalid JSON in {path}:{line_number}: {exc}"
                    ) from exc
                if not isinstance(record, dict):
                    raise EvidenceError(
                        f"invalid JSON record in {path}:{line_number}: expected object"
                    )
                records.append((line_number, record))
    except OSError as exc:
        raise EvidenceError(f"cannot read {path}: {exc}") from exc
    return records


def _payload(record):
    payload = record.get("payload", {}) if isinstance(record, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _session_id(records):
    for _, record in records:
        if record.get("type") != "session_meta":
            continue
        value = _payload(record).get("id")
        if isinstance(value, str) and value:
            return value
    for _, record in records:
        if record.get("type") != "session_meta":
            continue
        value = _payload(record).get("session_id")
        if isinstance(value, str) and value:
            return value
    return None


def _turn_ids(records):
    ids = []
    for _, record in records:
        if record.get("type") != "turn_context":
            continue
        value = _payload(record).get("turn_id")
        if isinstance(value, str) and value:
            ids.append(value)
    return ids


def _select_turn(records, turn_id, latest_turn):
    ids = _turn_ids(records)
    if not ids:
        raise EvidenceError("root transcript has no turn_context with turn_id")
    if latest_turn:
        return ids[-1]
    if turn_id not in ids:
        raise EvidenceError(f"turn not found: {turn_id}")
    return turn_id


def _session_paths(sessions_dir):
    directory = Path(sessions_dir).expanduser()
    if not directory.is_dir():
        raise EvidenceError(f"sessions directory not found: {directory}")
    try:
        return sorted(directory.rglob("*.jsonl"))
    except OSError as exc:
        raise EvidenceError(f"cannot search sessions directory {directory}: {exc}") from exc


def _find_session(session_id, sessions_dir):
    paths = _session_paths(sessions_dir)
    suffix = f"{session_id}.jsonl"
    preferred = [path for path in paths if path.name.endswith(suffix)]
    fallback = [path for path in paths if path not in preferred]
    parse_errors = []
    for path in preferred + fallback:
        try:
            records = _records(path)
        except EvidenceError as exc:
            parse_errors.append(str(exc))
            continue
        if _session_id(records) == session_id:
            return path, records
    if parse_errors:
        raise EvidenceError(parse_errors[0])
    return None, []


def _find_root(target, sessions_dir):
    candidate = Path(target).expanduser()
    if candidate.is_file():
        return candidate, _records(candidate)
    return _find_session(target, sessions_dir)


def _arguments(payload, path, line_number):
    value = payload.get("arguments", {})
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise EvidenceError(
                f"invalid spawn arguments in {path}:{line_number}: {exc}"
            ) from exc
    if not isinstance(value, dict):
        raise EvidenceError(
            f"invalid spawn arguments in {path}:{line_number}: expected object"
        )
    return value


def _output_task_name(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, dict):
        return None
    task_name = value.get("task_name")
    return task_name if isinstance(task_name, str) and task_name else None


def _call_turn_id(payload):
    metadata = payload.get("internal_chat_message_metadata_passthrough", {})
    if not isinstance(metadata, dict):
        return None
    value = metadata.get("turn_id")
    return value if isinstance(value, str) and value else None


def _spawn_evidence(records, root_path, selected_turn):
    calls = []
    call_ids = set()
    start_records = {}
    output_records = {}
    errors = []
    for line_number, record in records:
        payload = _payload(record)
        if payload.get("type") == "function_call" and payload.get("name") == "spawn_agent":
            call_turn = _call_turn_id(payload)
            if call_turn is None:
                errors.append(
                    f"spawn in {root_path}:{line_number} missing call turn_id"
                )
                continue
            if call_turn != selected_turn:
                continue
            call_id = payload.get("call_id")
            if not isinstance(call_id, str) or not call_id:
                errors.append(f"spawn in {root_path}:{line_number} missing call_id")
                continue
            if call_id in call_ids:
                errors.append(
                    f"duplicate spawn call_id {call_id} in {root_path}:{line_number}"
                )
                continue
            call_ids.add(call_id)
            try:
                arguments = _arguments(payload, root_path, line_number)
            except EvidenceError as exc:
                errors.append(str(exc))
                continue
            calls.append(
                {
                    "call_id": call_id,
                    "line": line_number,
                    "arguments": arguments,
                    "turn_id": call_turn,
                }
            )
            continue
        if (
            record.get("type") == "event_msg"
            and payload.get("type") == "sub_agent_activity"
            and payload.get("kind") == "started"
        ):
            event_id = payload.get("event_id")
            if isinstance(event_id, str) and event_id:
                start_records.setdefault(event_id, []).append(
                    {"line": line_number, "payload": payload}
                )
            continue
        if payload.get("type") == "function_call_output":
            call_id = payload.get("call_id")
            if isinstance(call_id, str) and call_id:
                output_records.setdefault(call_id, []).append(
                    {
                        "line": line_number,
                        "task_name": _output_task_name(payload.get("output")),
                    }
                )

    for call in calls:
        call_id = call["call_id"]
        arguments = call["arguments"]
        task_name = arguments.get("task_name", "<unnamed>")
        starts = start_records.get(call_id, [])
        outputs = output_records.get(call_id, [])
        lifecycle_errors = []
        if len(starts) != 1:
            if starts:
                lifecycle_errors.append(
                    f"duplicate started event for {call_id} in {root_path}"
                )
            else:
                lifecycle_errors.append(
                    f"no successful started spawn for {arguments.get('agent_type', task_name)}: "
                    f"spawn {task_name} missing started event"
                )
        if len(outputs) != 1 or (outputs and outputs[0]["task_name"] is None):
            if len(outputs) > 1:
                lifecycle_errors.append(
                    f"duplicate function output for {call_id} in {root_path}"
                )
            else:
                lifecycle_errors.append(
                    f"no successful started spawn for {arguments.get('agent_type', task_name)}: "
                    f"spawn {task_name} missing successful output"
                )
        if lifecycle_errors:
            call["lifecycle_complete"] = False
            call["route_valid"] = False
            errors.extend(lifecycle_errors)
            continue

        start = starts[0]
        output = outputs[0]
        if not (call["line"] < start["line"] < output["line"]):
            call["lifecycle_complete"] = False
            call["route_valid"] = False
            errors.append(f"out-of-order spawn lifecycle for {call_id}")
            continue
        start_payload = start["payload"]
        child_id = start_payload.get("agent_thread_id")
        agent_path = start_payload.get("agent_path")
        requested_name = arguments.get("task_name")
        if not all(
            isinstance(value, str) and value
            for value in (child_id, agent_path, requested_name)
        ):
            call["lifecycle_complete"] = False
            call["route_valid"] = False
            errors.append(f"incomplete spawn lifecycle metadata for {call_id}")
            continue
        if (
            output["task_name"] != agent_path
            or agent_path.rstrip("/").split("/")[-1] != requested_name
        ):
            call["lifecycle_complete"] = False
            call["route_valid"] = False
            errors.append(f"spawn lifecycle task mismatch for {call_id}")
            continue
        call.update(
            {
                "lifecycle_complete": True,
                "route_valid": True,
                "child_id": child_id,
                "agent_path": agent_path,
            }
        )
    return calls, errors


def _child_metadata(records, child_id, root_id):
    metadata = None
    for line_number, record in records:
        if record.get("type") != "session_meta":
            continue
        payload = _payload(record)
        if payload.get("id") != child_id:
            continue
        source = payload.get("source", {})
        if not isinstance(source, dict):
            source = {}
        subagent = source.get("subagent", {})
        if not isinstance(subagent, dict):
            subagent = {}
        spawn = subagent.get("thread_spawn", {})
        if not isinstance(spawn, dict):
            spawn = {}
        parent_id = payload.get("parent_thread_id") or spawn.get("parent_thread_id")
        metadata = {
            "line": line_number,
            "parent_id": parent_id,
            "role": payload.get("agent_role") or spawn.get("agent_role"),
            "agent_path": payload.get("agent_path") or spawn.get("agent_path"),
        }
        break
    if metadata is None:
        return None, [f"child {child_id} missing matching session metadata"]
    errors = []
    if metadata["parent_id"] != root_id:
        errors.append(
            f"child {child_id} parent is {metadata['parent_id']}, expected {root_id}"
        )
    runs = []
    for _, record in records:
        if record.get("type") != "turn_context":
            continue
        payload = _payload(record)
        runs.append((payload.get("model"), payload.get("effort")))
    metadata["runs"] = runs
    return metadata, errors


def _model_errors(route, expected_role, expected_model, expected_effort):
    errors = []
    if not route.get("route_valid"):
        errors.append(f"invalid routing evidence for call {route['call_id']}")
    child = route.get("child")
    if child is None:
        errors.append(f"missing child session metadata for {expected_role}")
        return errors
    runs = child.get("runs", [])
    for observed in runs:
        if observed != (expected_model, expected_effort):
            errors.append(
                f"{expected_role} ran {observed[0]}/{observed[1]}, expected {expected_model}/{expected_effort}"
            )
            break
    return errors


def audit(target, expectations, sessions_dir, turn_id=None, latest_turn=False):
    try:
        root_path, root_records = _find_root(target, sessions_dir)
    except EvidenceError as exc:
        return 1, [], [str(exc)]
    if root_path is None:
        return 1, [], [f"session not found: {target}"]
    root_id = _session_id(root_records)
    if root_id is None:
        return 1, [], [f"root session metadata missing id: {root_path}"]

    try:
        selected_turn = _select_turn(root_records, turn_id, latest_turn)
    except EvidenceError as exc:
        return 1, [], [str(exc)]

    calls, errors = _spawn_evidence(root_records, root_path, selected_turn)

    expected_by_role = {}
    for expectation in expectations:
        parts = expectation.split(":")
        if len(parts) != 3 or not all(parts):
            errors.append(
                f"invalid expectation: {expectation} (expected ROLE:MODEL:EFFORT)"
            )
            continue
        route = tuple(parts)
        expected_by_role.setdefault(parts[0], []).append(route)

    typed_by_role = {}
    for call in calls:
        arguments = call["arguments"]
        task_name = arguments.get("task_name", "<unnamed>")
        role = arguments.get("agent_type")
        if not isinstance(role, str) or not role:
            errors.append(f"spawn {task_name} missing agent_type")
            continue
        typed_by_role.setdefault(role, []).append(call)
        if arguments.get("fork_turns") != "none":
            call["route_valid"] = False
            errors.append(
                f"spawn {task_name} fork_turns is \"{arguments.get('fork_turns')}\", expected \"none\""
            )

    for role in typed_by_role:
        if role not in expected_by_role:
            errors.append(
                f"unexpected typed role {role}; add --expect {role}:MODEL:EFFORT"
            )

    for role, expected_routes in expected_by_role.items():
        actual_count = len(typed_by_role.get(role, []))
        expected_count = len(expected_routes)
        if actual_count != expected_count:
            errors.append(
                f"expected {expected_count} {role} spawn(s), found {actual_count} in turn {selected_turn}"
            )
            if actual_count == 0:
                errors.append(f"missing typed spawn for {role}")
            if expected_count > 1 and actual_count < expected_count:
                errors.append(
                    f"missing distinct successful spawn for repeated expectation {role}"
                )

    child_ids = {}
    for role, role_calls in typed_by_role.items():
        for call in role_calls:
            if not call.get("lifecycle_complete"):
                continue
            child_id = call["child_id"]
            if child_id in child_ids:
                call["route_valid"] = False
                child_ids[child_id]["route_valid"] = False
                errors.append(
                    f"replayed child session {child_id} for call IDs "
                    f"{child_ids[child_id]['call_id']} and {call['call_id']}"
                )
            else:
                child_ids[child_id] = call
            try:
                child_path, child_records = _find_session(child_id, sessions_dir)
            except EvidenceError as exc:
                call["child"] = None
                call["route_valid"] = False
                errors.append(str(exc))
                continue
            if child_path is None:
                call["child"] = None
                call["route_valid"] = False
                errors.append(f"child session not found: {child_id}")
                continue
            child, child_errors = _child_metadata(child_records, child_id, root_id)
            call["child"] = child
            if child_errors:
                call["route_valid"] = False
            errors.extend(child_errors)
            if child is None:
                continue
            if child.get("role") != role:
                call["route_valid"] = False
                errors.append(
                    f"child {child_id} role is {child.get('role')}, expected {role}"
                )
            if child.get("agent_path") != call.get("agent_path"):
                call["route_valid"] = False
                errors.append(
                    f"child {child_id} path is {child.get('agent_path')}, expected {call.get('agent_path')}"
                )
            if not child.get("runs"):
                call["route_valid"] = False
                errors.append(f"missing child turn context for {role}")

    passes = []
    for role, expected_routes in expected_by_role.items():
        role_calls = typed_by_role.get(role, [])
        if len(role_calls) != len(expected_routes):
            continue
        unused = list(role_calls)
        for _, model, effort in expected_routes:
            selected = None
            selected_errors = None
            for candidate in unused:
                candidate_errors = _model_errors(candidate, role, model, effort)
                if not candidate_errors:
                    selected = candidate
                    selected_errors = []
                    break
                if selected is None:
                    selected = candidate
                    selected_errors = candidate_errors
            if selected is None:
                continue
            unused.remove(selected)
            if selected_errors:
                errors.extend(selected_errors)
            elif selected.get("route_valid") and selected.get("child"):
                passes.append(f"PASS {role} {model}/{effort}")
    if errors:
        return 1, [], errors
    return 0, passes, []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", help="root session ID or root JSONL path")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument(
        "--latest-turn",
        action="store_true",
        help="audit the last root turn_context in the transcript",
    )
    scope.add_argument(
        "--turn-id",
        metavar="TURN_ID",
        help="audit one root turn_context by turn ID",
    )
    parser.add_argument(
        "--expect",
        action="append",
        required=True,
        metavar="ROLE:MODEL:EFFORT",
        help="required route expectation; repeat for each distinct spawn",
    )
    parser.add_argument(
        "--sessions-dir",
        required=True,
        help="Codex sessions root containing root and child JSONL files",
    )
    args = parser.parse_args(argv)
    code, passes, errors = audit(
        args.session,
        args.expect,
        args.sessions_dir,
        turn_id=args.turn_id,
        latest_turn=args.latest_turn,
    )
    for line in passes:
        print(line)
    for line in errors:
        print(line, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
