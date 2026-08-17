#!/usr/bin/env python3
"""Extract safe, time-bounded work evidence from local Codex session logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
    re.DOTALL,
)
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
ENVIRONMENT_CONTEXT_RE = re.compile(
    r"<environment_context>.*?</environment_context>", re.DOTALL
)


def parse_instant(value: str, argument_name: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        instant = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{argument_name} must be an ISO 8601 datetime: {value}"
        ) from exc
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise argparse.ArgumentTypeError(
            f"{argument_name} must include a UTC offset or Z: {value}"
        )
    return instant


def parse_optional_instant(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return parse_instant(value, "timestamp")
    except argparse.ArgumentTypeError:
        return None


def clean_text(value: Any, max_chars: int) -> tuple[str, bool]:
    if not isinstance(value, str):
        return "", False
    text = ENVIRONMENT_CONTEXT_RE.sub("", value)
    text = PRIVATE_KEY_RE.sub("[REDACTED PRIVATE KEY]", text)
    text = BEARER_RE.sub("Bearer [REDACTED]", text)
    text = SECRET_RE.sub(r"\1\2[REDACTED]", text)
    text = text.strip()
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars].rstrip() + "\n...[truncated]", True


def new_turn(timestamp: datetime, turn_id: Any = None) -> dict[str, Any]:
    return {
        "turn_id": turn_id if isinstance(turn_id, str) else None,
        "started_at": timestamp,
        "completed_at": None,
        "activity": [],
        "messages": [],
    }


def add_message(
    turn: dict[str, Any],
    role: str,
    timestamp: datetime,
    raw_text: Any,
    max_chars: int,
) -> None:
    text, truncated = clean_text(raw_text, max_chars)
    if not text:
        return
    key = (role, text)
    if any((item["role"], item["text"]) == key for item in turn["messages"]):
        return
    turn["messages"].append(
        {
            "role": role,
            "timestamp": timestamp,
            "text": text,
            "truncated": truncated,
        }
    )


def is_report_request(turn: dict[str, Any]) -> bool:
    user_text = "\n".join(
        item["text"] for item in turn["messages"] if item["role"] == "user"
    ).casefold()
    return "$summarize-codex-week" in user_text


def status_for_turn(
    turn: dict[str, Any], since: datetime, until: datetime
) -> str:
    started = turn["started_at"]
    completed = turn["completed_at"]
    completed_in_range = completed is not None and since <= completed < until
    if completed_in_range and started < since:
        return "continued_and_completed"
    if completed_in_range:
        return "completed"
    if started < since:
        return "continued"
    return "started_or_progressed"


def local_iso(value: datetime | None, timezone: ZoneInfo) -> str | None:
    return value.astimezone(timezone).isoformat() if value is not None else None


def serialize_turn(
    turn: dict[str, Any],
    since: datetime,
    until: datetime,
    timezone: ZoneInfo,
) -> dict[str, Any]:
    messages_in_range = [
        {
            **item,
            "timestamp": local_iso(item["timestamp"], timezone),
        }
        for item in turn["messages"]
        if since <= item["timestamp"] < until
    ]
    prior_user_messages = [
        item
        for item in turn["messages"]
        if item["role"] == "user" and item["timestamp"] < since
    ]
    context_before = []
    if prior_user_messages:
        item = prior_user_messages[-1]
        context_before.append(
            {
                **item,
                "timestamp": local_iso(item["timestamp"], timezone),
            }
        )
    activity_in_range = [
        timestamp for timestamp in turn["activity"] if since <= timestamp < until
    ]
    return {
        "turn_id": turn["turn_id"],
        "status": status_for_turn(turn, since, until),
        "started_at": local_iso(turn["started_at"], timezone),
        "completed_at": local_iso(turn["completed_at"], timezone),
        "evidence_event_count": len(activity_in_range),
        "context_before": context_before,
        "messages": messages_in_range,
    }


def extract_file(
    path: Path,
    since: datetime,
    until: datetime,
    max_chars: int,
) -> tuple[dict[str, Any], int, int]:
    session: dict[str, Any] = {
        "session_id": None,
        "cwd": None,
        "thread_source": None,
        "source_file": str(path),
        "turns": [],
    }
    turns: list[dict[str, Any]] = []
    current_turn: dict[str, Any] | None = None
    malformed_lines = 0
    timestamp_errors = 0

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                malformed_lines += 1
                continue

            timestamp = parse_optional_instant(record.get("timestamp"))
            if timestamp is None:
                timestamp_errors += 1
                continue

            record_type = record.get("type")
            payload = record.get("payload")
            if not isinstance(payload, dict):
                payload = {}
            payload_type = payload.get("type")

            if record_type == "session_meta":
                session["session_id"] = payload.get("session_id") or payload.get("id")
                session["cwd"] = payload.get("cwd")
                session["thread_source"] = payload.get("thread_source")
                continue

            if record_type == "event_msg" and payload_type == "task_started":
                if current_turn is not None:
                    turns.append(current_turn)
                started = parse_optional_instant(payload.get("started_at")) or timestamp
                current_turn = new_turn(started, payload.get("turn_id"))
                current_turn["activity"].append(timestamp)
                continue

            relevant_activity = (
                record_type == "event_msg"
                and payload_type
                in {"user_message", "agent_message", "task_complete"}
            ) or (
                record_type == "response_item"
                and payload_type in {"custom_tool_call", "custom_tool_call_output"}
            )
            if relevant_activity and current_turn is None:
                current_turn = new_turn(timestamp)
            if relevant_activity:
                current_turn["activity"].append(timestamp)

            if record_type == "event_msg" and payload_type == "user_message":
                add_message(current_turn, "user", timestamp, payload.get("message"), max_chars)
            elif (
                record_type == "event_msg"
                and payload_type == "agent_message"
                and payload.get("phase") == "final_answer"
            ):
                add_message(
                    current_turn,
                    "assistant",
                    timestamp,
                    payload.get("message"),
                    max_chars,
                )
            elif record_type == "event_msg" and payload_type == "task_complete":
                completed = parse_optional_instant(payload.get("completed_at")) or timestamp
                current_turn["completed_at"] = completed
                if not any(
                    item["role"] == "assistant" for item in current_turn["messages"]
                ):
                    add_message(
                        current_turn,
                        "assistant",
                        timestamp,
                        payload.get("last_agent_message"),
                        max_chars,
                    )
                turns.append(current_turn)
                current_turn = None

    if current_turn is not None:
        turns.append(current_turn)

    session["turns"] = [
        turn
        for turn in turns
        if any(since <= timestamp < until for timestamp in turn["activity"])
    ]
    return session, malformed_lines, timestamp_errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract time-bounded work evidence from Codex JSONL sessions."
    )
    parser.add_argument("--since", required=True, help="Inclusive ISO 8601 datetime.")
    parser.add_argument("--until", required=True, help="Exclusive ISO 8601 datetime.")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument(
        "--sessions-root",
        type=Path,
        default=Path.home() / ".codex" / "sessions",
    )
    parser.add_argument("--max-message-chars", type=int, default=2000)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--stats-only", action="store_true")
    parser.add_argument("--include-report-requests", action="store_true")
    parser.add_argument("--include-subagents", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        since = parse_instant(args.since, "--since")
        until = parse_instant(args.until, "--until")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if since >= until:
        parser.error("--since must be earlier than --until")
    if args.max_message_chars < 1:
        parser.error("--max-message-chars must be positive")
    try:
        timezone = ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError:
        parser.error(f"unknown timezone: {args.timezone}")
    if not args.sessions_root.is_dir():
        parser.error(f"sessions root does not exist: {args.sessions_root}")

    files = sorted(args.sessions_root.rglob("*.jsonl"))
    sessions = []
    malformed_lines = 0
    timestamp_errors = 0
    unreadable_files = []
    report_requests_excluded = 0
    subagent_files_excluded = 0

    for path in files:
        try:
            session, malformed, bad_timestamps = extract_file(
                path, since, until, args.max_message_chars
            )
        except OSError as exc:
            unreadable_files.append({"file": str(path), "error": str(exc)})
            continue
        malformed_lines += malformed
        timestamp_errors += bad_timestamps
        if session["thread_source"] == "subagent" and not args.include_subagents:
            if session["turns"]:
                subagent_files_excluded += 1
            continue
        if not args.include_report_requests:
            kept_turns = []
            for turn in session["turns"]:
                if is_report_request(turn):
                    report_requests_excluded += 1
                else:
                    kept_turns.append(turn)
            session["turns"] = kept_turns
        if not session["turns"]:
            continue
        session["turns"] = [
            serialize_turn(turn, since, until, timezone)
            for turn in session["turns"]
        ]
        session["source_file"] = str(path.relative_to(args.sessions_root))
        sessions.append(session)

    result: dict[str, Any] = {
        "schema_version": 1,
        "range": {
            "since": local_iso(since, timezone),
            "until_exclusive": local_iso(until, timezone),
            "timezone": args.timezone,
        },
        "stats": {
            "files_scanned": len(files),
            "sessions_in_range": len(sessions),
            "turns_in_range": sum(len(session["turns"]) for session in sessions),
            "report_requests_excluded": report_requests_excluded,
            "subagent_files_excluded": subagent_files_excluded,
            "malformed_lines": malformed_lines,
            "timestamp_errors": timestamp_errors,
            "unreadable_files": len(unreadable_files),
        },
        "warnings": unreadable_files,
    }
    if not args.stats_only:
        result["sessions"] = sessions

    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
        indent=2 if args.pretty else None,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
