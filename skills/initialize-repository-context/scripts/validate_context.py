#!/usr/bin/env python3
"""Validate repository AI context documents without executing repository code."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


DEFAULT_DOCS = ("index.md", "code-map.md", "architecture.md", "testing.md", "invariants.md")
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME|XXX|YOUR_[A-Z0-9_]*_HERE)\b|\{\{[^}\n]+\}\}|"
    r"\$\{[A-Z][A-Z0-9_]*\}|<[A-Z][A-Z0-9_-]{2,}>|\[replace\s+me\]",
    re.IGNORECASE,
)
REFERENCE_LINK_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)
REFERENCE_DEFINITION_RE = re.compile(r"^\s{0,3}\[([^\]]+)\]:", re.MULTILINE)
REFERENCE_USE_RE = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
EVIDENCE_LABEL_RE = re.compile(r"\[(?:Verified|Inferred|Unknown)\]")
COMMAND_RE = re.compile(
    r"^(?:npm|pnpm|yarn|bun|deno|make|just|task|cargo|go\s+(?:test|build|run|generate|vet|fmt)|"
    r"pytest|python(?:3)?(?:\s+-m)?|tox|nox|ruff|black|mypy|uv|poetry|pipenv|hatch|pdm|"
    r"mvn|gradle|\./gradlew|dotnet|cmake|ctest|ninja|bazel|buck2?|composer|phpunit|"
    r"bundle|rake|rspec|mix|swift|xcodebuild|pre-commit|docker\s+compose)(?:\s|$)",
    re.IGNORECASE,
)
SHELL_FENCE_LANGUAGES = {"bash", "sh", "shell", "console", "zsh", "powershell", "pwsh"}
MAX_FINGERPRINT_BYTES = 64 * 1024 * 1024


def issue(level: str, code: str, path: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "path": path, "message": message}


def normalize_link(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        raw = raw[1:raw.index(">")]
    else:
        raw = raw.split(maxsplit=1)[0]
    if not raw or raw.startswith(("http://", "https://", "mailto:", "#")):
        return None
    raw = re.sub(r"\\([\\() ])", r"\1", raw)
    return unquote(raw.split("#", 1)[0]) or None


def local_links(text: str) -> list[str]:
    """Extract inline and reference-definition Markdown links with balanced parentheses."""
    links: list[str] = []
    cursor = 0
    while True:
        marker = text.find("](", cursor)
        if marker < 0:
            break
        index = marker + 2
        start = index
        depth = 1
        escaped = False
        while index < len(text):
            char = text[index]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    link = normalize_link(text[start:index])
                    if link:
                        links.append(link)
                    index += 1
                    break
            index += 1
        cursor = max(index, marker + 2)
    for raw in REFERENCE_LINK_RE.findall(text):
        link = normalize_link(raw)
        if link:
            links.append(link)
    return links


def commands_in(text: str) -> list[str]:
    candidates = list(INLINE_CODE_RE.findall(text))
    for language, block in FENCE_RE.findall(text):
        label = language.strip().lower()
        first = label.split(maxsplit=1)[0] if label else ""
        if first.startswith("{.") and first.endswith("}"):
            first = first[2:-1]
        if first not in SHELL_FENCE_LANGUAGES:
            continue
        candidates.extend(line.strip() for line in block.splitlines())
    commands: set[str] = set()
    for candidate in candidates:
        command = candidate.strip()
        if command.startswith(("$ ", "> ")):
            command = command[2:].strip()
        if command and not command.startswith("#") and COMMAND_RE.match(command):
            commands.add(command)
    return sorted(commands)


def inventory_commands(root: Path) -> tuple[list[dict[str, str]], str | None]:
    script = Path(__file__).with_name("inventory_repo.py")
    result = subprocess.run(
        [sys.executable, "-B", str(script), str(root)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        return [], result.stderr.strip() or "inventory failed"
    try:
        return json.loads(result.stdout).get("command_evidence", []), None
    except (json.JSONDecodeError, AttributeError):
        return [], "inventory returned invalid JSON"


def command_supported(command: str, evidence: list[dict[str, str]]) -> bool:
    for item in evidence:
        known = str(item.get("command", "")).strip()
        if known and (command == known or command.startswith(known + " ")):
            return True
    return False


def resolve_inside(root: Path, rel: Path) -> Path:
    if rel.is_absolute() or not rel.parts:
        raise ValueError(f"Path must be repository-relative: {rel}")
    candidate = root / rel
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes repository: {rel}") from exc
    return resolved


def unresolved_leaf_inside(root: Path, rel: Path) -> Path:
    """Keep the final symlink unresolved while normalizing and bounding its parent."""
    if rel.is_absolute() or not rel.parts:
        raise ValueError(f"Path must be repository-relative: {rel}")
    candidate = root / rel
    parent = candidate.parent.resolve(strict=False)
    try:
        parent.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes repository: {rel}") from exc
    return parent / candidate.name


def fingerprint_path(path: Path, root: Path) -> str:
    path.parent.resolve(strict=False).relative_to(root)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return "missing"
    mode = stat.S_IMODE(metadata.st_mode)
    if stat.S_ISLNK(metadata.st_mode):
        payload = (f"mode:{mode:o}\0symlink\0" + str(path.readlink())).encode()
        return "sha256:" + hashlib.sha256(payload).hexdigest()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("Only regular files and symlinks can be fingerprinted")
    if metadata.st_size > MAX_FINGERPRINT_BYTES:
        raise ValueError(f"File exceeds fingerprint limit of {MAX_FINGERPRINT_BYTES} bytes")
    digest = hashlib.sha256()
    digest.update(f"mode:{mode:o}\0size:{metadata.st_size}\0".encode())
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def git_status_paths(root: Path) -> tuple[set[str], str | None]:
    top = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if top.returncode:
        return set(), top.stderr.strip() or "not a Git repository"
    git_root = Path(top.stdout.strip()).resolve()
    try:
        target_rel = root.relative_to(git_root)
    except ValueError:
        return set(), "target is outside the reported Git root"
    args = ["git", "-C", str(git_root), "status", "--porcelain=v1", "-z", "--untracked-files=all", "--"]
    if target_rel != Path("."):
        args.append(target_rel.as_posix())
    status = subprocess.run(
        args,
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if status.returncode:
        return set(), status.stderr.strip() or "git status failed"
    records = status.stdout.split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        state = record[:2]
        paths.add(record[3:])
        if "R" in state or "C" in state:
            if index < len(records) and records[index]:
                paths.add(records[index])
                index += 1
    prefix = "" if target_rel == Path(".") else target_rel.as_posix().rstrip("/") + "/"
    scoped = {item[len(prefix):] for item in paths if not prefix or item.startswith(prefix)}
    return scoped, None


def validate(
    root_arg: str,
    agents_name: str,
    context_dir: str,
    max_agents_bytes: int,
    allow_missing: bool,
    documents: list[str] | None = None,
    approved_paths: list[str] | None = None,
    existing_changes: list[str] | None = None,
) -> dict[str, object]:
    root = Path(root_arg).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Target is not a directory: {root}")
    issues: list[dict[str, str]] = []
    doc_paths = [Path(item) for item in documents] if documents else [Path(context_dir) / name for name in DEFAULT_DOCS]
    required = [Path(agents_name), *doc_paths]
    existing: list[Path] = []

    for rel in required:
        try:
            path = resolve_inside(root, rel)
        except ValueError as exc:
            issues.append(issue("error", "invalid-required-path", rel.as_posix(), str(exc)))
            continue
        if not path.is_file():
            level = "warning" if allow_missing else "error"
            issues.append(issue(level, "missing-file", rel.as_posix(), "Expected context document does not exist"))
        else:
            existing.append(path)

    try:
        agents_path = resolve_inside(root, Path(agents_name))
    except ValueError:
        agents_path = root / "__invalid_agents_path__"
    if agents_path.is_file() and agents_path.stat().st_size > max_agents_bytes:
        issues.append(issue("error", "agents-too-large", agents_name, f"File exceeds {max_agents_bytes} bytes"))

    evidence, inventory_error = inventory_commands(root)
    if inventory_error:
        issues.append(issue("warning", "inventory-failed", ".", inventory_error))

    checked_links = 0
    checked_commands = 0
    for path in existing:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        match = PLACEHOLDER_RE.search(text)
        if match:
            issues.append(issue("error", "placeholder", rel, f"Placeholder marker remains: {match.group(0)}"))

        definitions = {re.sub(r"\s+", " ", item.strip().lower()) for item in REFERENCE_DEFINITION_RE.findall(text)}
        for label, identifier in REFERENCE_USE_RE.findall(text):
            key = re.sub(r"\s+", " ", (identifier or label).strip().lower())
            if key not in definitions:
                issues.append(issue("error", "undefined-reference-link", rel, f"Reference link has no definition: [{label}][{identifier}]"))

        if path != agents_path:
            if not EVIDENCE_LABEL_RE.search(text):
                issues.append(issue("warning", "missing-evidence-label", rel, "Document has no evidence-status label"))
            section_labeled = False
            in_fence = False
            unlabeled = 0
            for line_number, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence or not stripped:
                    continue
                heading = re.match(r"^(#{2,6})\s+", stripped)
                if heading:
                    section_labeled = bool(EVIDENCE_LABEL_RE.search(line))
                    continue
                if stripped.startswith("# ") or REFERENCE_LINK_RE.match(line):
                    continue
                if re.match(r"^\|?\s*:?-{3,}", stripped):
                    continue
                if not section_labeled and not EVIDENCE_LABEL_RE.search(line):
                    unlabeled += 1
                    if unlabeled <= 10:
                        issues.append(issue("warning", "unlabeled-factual-item", rel, f"Line {line_number} is outside a labeled section and has no evidence label"))
            if unlabeled > 10:
                issues.append(issue("warning", "unlabeled-factual-item", rel, f"{unlabeled - 10} additional unlabeled factual items omitted"))

        for link in local_links(text):
            checked_links += 1
            candidate = (root / link.lstrip("/")) if link.startswith("/") else (path.parent / link)
            resolved = candidate.resolve(strict=False)
            try:
                resolved.relative_to(root)
            except ValueError:
                issues.append(issue("error", "link-outside-root", rel, f"Link escapes repository: {link}"))
                continue
            if not resolved.exists():
                issues.append(issue("error", "broken-local-link", rel, f"Linked path does not exist: {link}"))

        for command in commands_in(text):
            checked_commands += 1
            if not command_supported(command, evidence):
                issues.append(issue("warning", "unverified-command", rel, f"No declared or conventional evidence found for: {command}"))

    approved_paths = approved_paths or []
    existing_changes = existing_changes or []
    if approved_paths:
        allowed: set[str] = set()
        for raw in approved_paths:
            try:
                allowed.add(resolve_inside(root, Path(raw)).relative_to(root).as_posix())
            except ValueError as exc:
                issues.append(issue("error", "invalid-approved-path", raw, str(exc)))
        for spec in existing_changes:
            if "=" not in spec:
                issues.append(issue("error", "invalid-existing-change", spec, "Expected PATH=FINGERPRINT from inventory output"))
                continue
            raw, expected = spec.rsplit("=", 1)
            try:
                current_path = unresolved_leaf_inside(root, Path(raw))
                rel_path = current_path.relative_to(root).as_posix()
                allowed.add(rel_path)
                actual = fingerprint_path(current_path, root)
                if actual != expected:
                    issues.append(issue("error", "preexisting-change-modified", rel_path, f"Expected {expected}, found {actual}"))
            except (OSError, ValueError) as exc:
                issues.append(issue("error", "invalid-existing-change", spec, str(exc)))
        changed, status_error = git_status_paths(root)
        if status_error:
            issues.append(issue("error", "approval-scope-unchecked", ".", status_error))
        else:
            for changed_path in sorted(changed - allowed):
                issues.append(issue("error", "unapproved-worktree-change", changed_path, "Changed path is neither approved nor declared pre-existing"))
    else:
        issues.append(issue("error", "approval-scope-unchecked", ".", "Pass --approved-path for every approved output and PATH=FINGERPRINT for every pre-existing user change"))

    errors = sum(item["level"] == "error" for item in issues)
    warnings = sum(item["level"] == "warning" for item in issues)
    return {
        "schema_version": 1,
        "root": str(root),
        "valid": errors == 0,
        "summary": {
            "required_files": len(required), "existing_files": len(existing),
            "checked_links": checked_links, "checked_commands": checked_commands,
            "errors": errors, "warnings": warnings,
        },
        "command_evidence": evidence,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", default=".", help="Repository root")
    parser.add_argument("--agents", default="AGENTS.md", help="Instruction file relative to target")
    parser.add_argument("--context-dir", default="docs/ai", help="Default context directory relative to target")
    parser.add_argument("--document", action="append", help="Exact context document path; repeat to replace the default document set")
    parser.add_argument("--approved-path", action="append", default=[], help="Approved output path; repeat for each path")
    parser.add_argument("--allow-existing-change", action="append", default=[], metavar="PATH=FINGERPRINT", help="Pre-existing path and inventory fingerprint; repeat for each path")
    parser.add_argument("--max-agents-bytes", type=int, default=32768, help="Maximum AGENTS.md size")
    parser.add_argument("--allow-missing", action="store_true", help="Report missing expected files as warnings")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    try:
        report = validate(
            args.target, args.agents, args.context_dir, args.max_agents_bytes, args.allow_missing,
            args.document, args.approved_path, args.allow_existing_change,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
