---
name: coding-workflow
description: Use when a coding task may modify repository files or change behavior and the appropriate level of planning, debugging, approval, and verification needs to be selected; do not use for read-only questions or analysis.
---

# Coding Workflow

Choose the lightest workflow that is sufficient for the task. Optimize for
useful progress, not ceremony.

## Route the Task

### Fast

Use for a small, explicit change with a local effect: one or two files,
configuration, documentation, formatting, or a narrow bug fix.

- Read only the context needed to avoid a wrong edit.
- Do not create a plan document.
- Do not invoke subagents, worktrees, or TDD by default.

### Standard

Use for a bounded multi-file change or a behavior change with clear scope.

- Inspect the relevant code, tests, and local conventions.
- Present a short in-chat proposal covering files, behavior, and verification.
- Do not create a plan document unless the user asks for one or it will be
  reused outside the current task.

### Deep

Use for a new subsystem, public interface, cross-module architecture change,
long-running work, or work intended to continue across sessions.

- Compare viable approaches and record the chosen design.
- Create a design or implementation plan only when it will be reused.
- Break the work into independently testable deliverables.

## Approval Gate

Before any file modification, show the exact target paths, intended changes,
and reasons. Wait for explicit user approval for those changes. Approval for
one set of files does not authorize unrelated files or external side effects.

Ask separately before destructive operations, dependency installation, Git
state changes, pushes, merges, publishing, or other actions outside the local
edit.

## Debugging

When facing a bug, test failure, build failure, performance regression,
integration problem, or other unexpected behavior, find the cause before
changing code.

1. Read the complete error, warning, and stack trace.
2. Reproduce the behavior and record exact inputs, steps, and frequency.
3. Inspect the relevant diff, recent commits, configuration, and environment.
4. Compare the failing path with a working example.
5. Trace the bad value or state backward to its earliest incorrect origin.

State one specific hypothesis, test it with the smallest possible change, and
implement one root-cause fix at a time. Add a regression test when the
behavior is repeatable and the project has a suitable test layer. If two
focused fixes fail, return to investigation. If three or more reveal new
coupling or shared-state failures, question the architecture instead of
stacking symptom fixes.

## Verification

Before reporting that a change is complete, fixed, correct, passing, or ready
to deliver:

1. Identify the command or check that proves the specific claim.
2. Run it freshly against the current files and relevant scope.
3. Read the result and inspect the exit code, failures, and warnings.
4. Compare the evidence with the actual requirement.
5. Report the command, result, and any remaining gap.

Tests prove tested behavior, builds prove the exercised target, linters prove
only their configured rules, and manual checks prove only the stated path.
Do not claim success because code changed, an earlier run passed, or another
agent reported success. If a check cannot run, state that limitation.

## Optional Practices

Use test-first development, subagents, isolated worktrees, code review, or
written plans only when the task's risk, scope, or explicit user request
justifies them. A request for lightweight handling takes precedence unless a
concrete risk makes it unsafe.
