---
name: summarize-codex-week
description: Summarize work recorded in local Codex session logs for a user-selected time range. Use when the user asks for a Codex work report or weekly summary using expressions such as this week, last week, recent days, 本周, 上周, 最近几天, an explicit date range such as 7.20-7.24, or the calendar week containing a date.
---

# Summarize Codex Work

Generate an evidence-based work report from local Codex session events. Treat event timestamps,
not session filenames or session start dates, as the source of truth.

## Resolve the Time Range

Use the user's timezone. Default to `Asia/Shanghai` when the user does not specify one.

- Interpret `本周` or `this week` as local Monday 00:00 through now.
- Interpret `上周` or `last week` as the previous local Monday 00:00 through the current Monday 00:00.
- Interpret `最近 N 天` or `last N days` as a rolling N x 24-hour range ending now.
- Interpret an explicit date range such as `7.20-7.24` as both dates inclusive. Pass the day after the stated end date as the exclusive upper bound.
- Interpret `7.20 那周` or `the week of 7/20` as the complete Monday-through-Sunday calendar week containing that date.
- Use the current year when the user omits a year. Ask for confirmation when that produces a future range or the expression remains ambiguous.

Always show the resolved local range and timezone in the report. Use a half-open interval internally:
`since <= event timestamp < until`.

## Extract Session Evidence

Run `scripts/extract_weekly_sessions.py` relative to this file. Pass explicit offset-aware ISO 8601
values; do not pass natural-language dates to the script. First run with `--stats-only` to size the
result. For more than 50 matching turns, use `--max-message-chars 800`; otherwise keep the default.

```bash
python3 scripts/extract_weekly_sessions.py \
  --since 2026-07-20T00:00:00+08:00 \
  --until 2026-07-25T00:00:00+08:00 \
  --timezone Asia/Shanghai \
  --pretty
```

The script recursively scans all `~/.codex/sessions/**/*.jsonl` files because a session that
started in an earlier week can contain events from the requested range. It emits JSON to stdout
and does not modify session logs or create report files. It excludes subagent and approval-guardian
sessions by default so that internal review traffic is not reported as user work. Use
`--include-subagents` only when the user explicitly asks to audit that activity.

If the output is unexpectedly large, rerun with a smaller range or lower
`--max-message-chars`. Do not select files only from date-named directories.

## Build the Report

Use the extracted `sessions[].turns[]` records as evidence. Group related work by repository or
project using `cwd`, then by outcome rather than by conversation chronology.

Report these sections when supported by evidence:

1. Statistics range and coverage
2. Completed work
3. Work started or continued
4. Tests and validation
5. Key decisions
6. Remaining issues and next steps

Apply these attribution rules:

- Describe a turn with status `continued_and_completed` as work completed in the range after starting earlier.
- Describe `continued` as progress carried over from before the range.
- Describe `started_or_progressed` as started or advanced in the range; do not claim completion.
- Claim a file change, test result, commit, or delivery only when a user or final assistant message supports it.
- Treat `context_before` as background only. Do not count it as work performed in the range.
- Consolidate repeated attempts and follow-up corrections into one outcome.
- State uncertainty briefly when the record lacks a final result.
- Do not reproduce secrets, raw prompts, or long source snippets in the report.

Respond in the user's language. Default to chat output. Create or update a report file only when
the user explicitly requests that file modification.

## Verify Coverage

Before presenting the report, check `stats` and `warnings` in the extractor output. State when no
matching events were found or malformed/unreadable records may make the report incomplete.
