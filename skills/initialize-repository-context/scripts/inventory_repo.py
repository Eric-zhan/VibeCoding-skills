#!/usr/bin/env python3
"""Create a bounded, read-only inventory of a Git repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git", ".hg", ".svn", ".cache", ".idea", ".vscode", ".venv", "venv",
    "node_modules", "vendor", "dist", "build", "target", "coverage", "generated",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".next", ".nuxt",
    ".ssh", ".aws", ".gnupg", ".kube",
}
GENERATED_DIRS = {"dist", "build", "target", "coverage", "generated", "vendor", "node_modules"}
MANIFESTS = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "Pipfile", "poetry.lock", "uv.lock", "Cargo.toml", "go.mod", "go.work", "pom.xml",
    "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
    "Makefile", "makefile", "Taskfile.yml", "Taskfile.yaml", "justfile", "Justfile",
    "CMakeLists.txt", "composer.json", "Gemfile", "mix.exs",
}
INSTRUCTION_NAMES = {"AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules"}
CI_NAMES = {".gitlab-ci.yml", ".gitlab-ci.yaml", "Jenkinsfile", "azure-pipelines.yml", "azure-pipelines.yaml"}
ENTRY_NAMES = {
    "main.py", "app.py", "manage.py", "main.go", "main.rs", "index.js", "index.ts",
    "server.js", "server.ts", "cli.py", "Program.cs", "Application.java",
}
TEST_DIRS = {"test", "tests", "spec", "specs", "__tests__", "e2e", "integration"}
LANGUAGE_BY_SUFFIX = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".kts": "Kotlin", ".cs": "C#", ".cpp": "C++", ".cc": "C++", ".c": "C",
    ".h": "C/C++ header", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".scala": "Scala", ".ex": "Elixir", ".exs": "Elixir", ".sh": "Shell",
}
SENSITIVE_RE = re.compile(
    r"^(?:\.env(?:\..*)?|\.netrc|\.npmrc|\.pypirc|id_(?:rsa|dsa|ecdsa|ed25519)|"
    r"kubeconfig|token|.*(?:secret|credential|private[_-]?key|signing[_-]?key).*|.*\.(?:pem|key|p12|pfx))$",
    re.IGNORECASE,
)
SENSITIVE_COMPONENTS = {".ssh", ".aws", ".gnupg", ".kube"}
MAX_FINGERPRINT_BYTES = 64 * 1024 * 1024
COMMAND_CONFIG_NAMES = {"package.json", "Makefile", "makefile", "justfile", "Justfile"}


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def safe_text(path: Path, boundary: Path, limit: int = 1_000_000) -> str | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
            return None
        resolved = path.resolve(strict=True)
        resolved.relative_to(boundary)
        return resolved.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return None


def is_sensitive_path(path: str) -> bool:
    return any(part in SENSITIVE_COMPONENTS or SENSITIVE_RE.match(part) for part in Path(path).parts)


def fingerprint_path(path: Path, boundary: Path) -> str:
    resolved_parent = path.parent.resolve(strict=False)
    resolved_parent.relative_to(boundary)
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


def changed_paths(git_root: Path, target_rel: Path) -> list[str]:
    args = ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--"]
    if target_rel != Path("."):
        args.append(target_rel.as_posix())
    records = run_git(git_root, *args).split("\0")
    repo_paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        state = record[:2]
        repo_paths.append(record[3:])
        if "R" in state or "C" in state:
            if index < len(records) and records[index]:
                repo_paths.append(records[index])
                index += 1
    prefix = "" if target_rel == Path(".") else target_rel.as_posix().rstrip("/") + "/"
    return sorted({item[len(prefix):] for item in repo_paths if not prefix or item.startswith(prefix)})


def classify(paths: list[str]) -> dict[str, Any]:
    groups: dict[str, list[str]] = {
        "instructions": [], "manifests": [], "documentation": [], "ci": [],
        "entrypoints": [], "tests": [], "sensitive_candidates_not_read": [],
    }
    languages: Counter[str] = Counter()
    generated_dirs: set[str] = set()

    for item in paths:
        parts = Path(item).parts
        name = parts[-1]
        suffix = Path(name).suffix.lower()
        if suffix in LANGUAGE_BY_SUFFIX:
            languages[LANGUAGE_BY_SUFFIX[suffix]] += 1
        generated_dirs.update(part for part in parts[:-1] if part in GENERATED_DIRS)
        if name in INSTRUCTION_NAMES:
            groups["instructions"].append(item)
        if name in MANIFESTS or name.endswith((".lock", ".csproj", ".sln")):
            groups["manifests"].append(item)
        if name.lower().startswith(("readme", "contributing")) or "docs" in parts or name.endswith(".md"):
            groups["documentation"].append(item)
        if name in CI_NAMES or (len(parts) >= 3 and parts[0:2] == (".github", "workflows")):
            groups["ci"].append(item)
        if name in ENTRY_NAMES or (parts and parts[0] == "cmd" and suffix in LANGUAGE_BY_SUFFIX):
            groups["entrypoints"].append(item)
        lowered = name.lower()
        if TEST_DIRS.intersection(parts) or lowered.startswith("test_") or lowered.endswith(("_test.py", "_test.go", ".test.ts", ".spec.ts", ".test.js", ".spec.js")):
            groups["tests"].append(item)
        if is_sensitive_path(item):
            groups["sensitive_candidates_not_read"].append(item)

    return {
        **{key: sorted(values) for key, values in groups.items()},
        "generated_or_vendor_directories": sorted(generated_dirs),
        "languages_by_file_count": dict(languages.most_common()),
    }


def package_manager(target: Path, visible_paths: list[str], all_paths: set[str]) -> tuple[str | None, str | None]:
    locks = {
        "pnpm": ("pnpm-lock.yaml",), "yarn": ("yarn.lock",),
        "bun": ("bun.lock", "bun.lockb"), "npm": ("package-lock.json",),
    }
    found = [manager for manager, names in locks.items() if any(name in all_paths for name in names)]
    package_json = "package.json" if "package.json" in visible_paths else None
    declared = ""
    if package_json:
        text = safe_text(target / package_json, target)
        if text:
            try:
                declared = json.loads(text).get("packageManager", "").split("@", 1)[0]
            except (json.JSONDecodeError, AttributeError):
                pass
    if len(found) > 1:
        return None, "Multiple package-manager lockfiles found; package scripts have no canonical invocation"
    if declared in locks and found and declared != found[0]:
        return None, "packageManager conflicts with the lockfile; package scripts have no canonical invocation"
    if declared in locks:
        return declared, None
    if len(found) == 1:
        return found[0], None
    return None, "No unique package manager evidence; package scripts have no canonical invocation"


def command_evidence(target: Path, visible_paths: list[str], all_paths: set[str]) -> tuple[list[dict[str, str]], list[str]]:
    evidence: list[dict[str, str]] = []
    warnings: list[str] = []
    manager, manager_warning = package_manager(target, visible_paths, all_paths)
    if manager_warning and any(Path(path).name == "package.json" for path in visible_paths):
        warnings.append(manager_warning)

    def add(command: str, source: str, kind: str, script: str = "") -> None:
        item = {"command": command, "source": source, "kind": kind}
        if script:
            item["script"] = script
        evidence.append(item)

    for rel in visible_paths:
        name = Path(rel).name
        if name not in COMMAND_CONFIG_NAMES or is_sensitive_path(rel):
            continue
        text = safe_text(target / rel, target)
        if text is None:
            continue
        if name == "package.json":
            try:
                scripts = json.loads(text).get("scripts", {})
                if isinstance(scripts, dict):
                    for script_name in sorted(scripts):
                        if isinstance(script_name, str):
                            invocation = f"{manager} run {script_name}" if manager and rel == "package.json" else ""
                            add(invocation, rel, "package script", script_name)
                            if manager == "npm" and rel == "package.json" and script_name in {"start", "test", "stop", "restart"}:
                                add(f"npm {script_name}", rel, "package script alias", script_name)
            except (json.JSONDecodeError, AttributeError):
                warnings.append(f"Could not parse {rel} as JSON")
        elif name in {"Makefile", "makefile"}:
            for match in re.finditer(r"^(?![.#\t ])([A-Za-z0-9][A-Za-z0-9_.-]*):(?:\s|$)", text, re.MULTILINE):
                if "%" not in match.group(1):
                    add(f"make {match.group(1)}", rel, "declared")
        elif name in {"justfile", "Justfile"}:
            for match in re.finditer(r"^([A-Za-z_][A-Za-z0-9_-]*)(?:\s+[^:=\n]+)?\s*:=?\s*$", text, re.MULTILINE):
                add(f"just {match.group(1)}", rel, "declared")

    conventions = {
        "Cargo.toml": ["cargo build", "cargo check", "cargo test"],
        "go.mod": ["go build ./...", "go test ./..."],
        "pom.xml": ["mvn test", "mvn package"],
        "build.gradle": ["gradle build", "gradle test"],
        "build.gradle.kts": ["gradle build", "gradle test"],
        "tox.ini": ["tox"],
        "noxfile.py": ["nox"],
    }
    for source, commands in conventions.items():
        if source in all_paths:
            for command in commands:
                add(command, source, "tool convention")

    if "gradlew" in all_paths:
        gradle_source = "build.gradle.kts" if "build.gradle.kts" in all_paths else "build.gradle"
        if gradle_source in all_paths:
            add("./gradlew build", gradle_source, "wrapper convention")
            add("./gradlew test", gradle_source, "wrapper convention")

    unique = {
        (item["command"], item["source"], item["kind"], item.get("script", "")): item
        for item in evidence
    }
    return sorted(unique.values(), key=lambda item: (item["command"], item["source"])), warnings


def build_inventory(target_arg: str, max_depth: int, max_files: int) -> dict[str, Any]:
    target = Path(target_arg).expanduser().resolve(strict=True)
    if not target.is_dir():
        raise ValueError(f"Target is not a directory: {target}")
    git_root = Path(run_git(target, "rev-parse", "--show-toplevel").strip()).resolve(strict=True)
    try:
        target_rel = target.relative_to(git_root)
    except ValueError as exc:
        raise ValueError("Resolved target is outside its Git root") from exc
    if target_rel != Path(".") and is_sensitive_path(target_rel.as_posix()):
        raise ValueError("Refusing to inventory a target inside a likely sensitive directory")

    git_args = ["ls-files", "-co", "--exclude-standard", "-z", "--"]
    if target_rel != Path("."):
        git_args.append(target_rel.as_posix())
    raw = run_git(git_root, *git_args)
    repo_paths = [item for item in raw.split("\0") if item]
    prefix = "" if target_rel == Path(".") else target_rel.as_posix().rstrip("/") + "/"
    scoped = [item[len(prefix):] for item in repo_paths if not prefix or item.startswith(prefix)]
    all_paths = set(scoped)
    visible: list[str] = []
    skipped_dirs: set[str] = set()
    depth_omitted = 0
    eligible_files = 0
    for item in sorted(scoped):
        parts = Path(item).parts
        blocked = next((part for part in parts[:-1] if part in SKIP_DIRS), None)
        if blocked:
            skipped_dirs.add(blocked)
            continue
        if len(parts) - 1 > max_depth:
            depth_omitted += 1
            continue
        eligible_files += 1
        if len(visible) < max_files:
            visible.append(item)

    classified = classify(visible)
    full_summary = classify(scoped)
    classified["languages_by_file_count"] = full_summary["languages_by_file_count"]
    classified["generated_or_vendor_directories"] = full_summary["generated_or_vendor_directories"]
    sensitive_paths = full_summary["sensitive_candidates_not_read"]
    classified["sensitive_candidates_not_read"] = sensitive_paths[: min(max_files, 100)]
    commands, parse_warnings = command_evidence(target, visible, all_paths)
    warnings = list(parse_warnings)
    baseline: list[dict[str, str | None]] = []
    changed = changed_paths(git_root, target_rel)
    for rel in changed[: min(max_files, 100)]:
        if is_sensitive_path(rel):
            baseline.append({"path": rel, "fingerprint": None})
            continue
        try:
            baseline.append({"path": rel, "fingerprint": fingerprint_path(target / rel, target)})
        except (OSError, ValueError):
            baseline.append({"path": rel, "fingerprint": None})
    if target != git_root:
        warnings.append("Target is a repository subtree; confirm scope before writing context files")
    if any("/" in item["source"] and item.get("script") for item in commands):
        warnings.append("Nested package scripts are listed without a canonical root invocation")
    if eligible_files > max_files:
        warnings.append(f"Visible inventory reached --max-files={max_files}; increase only if needed")
    if len(sensitive_paths) > len(classified["sensitive_candidates_not_read"]):
        warnings.append("Sensitive path-name list was truncated to preserve the output budget")
    if sensitive_paths:
        warnings.append("Potentially sensitive paths were identified by name and their contents were not read")
    if len(changed) > len(baseline):
        warnings.append("Pre-existing worktree fingerprint list was truncated to preserve the output budget")
    if any(item["fingerprint"] is None for item in baseline):
        warnings.append("Some pre-existing changes could not be fingerprinted; do not modify or auto-whitelist them")

    return {
        "schema_version": 1,
        "target": str(target),
        "git_root": str(git_root),
        "is_git_root": target == git_root,
        "limits": {"max_depth": max_depth, "max_files": max_files},
        "counts": {
            "scoped_files": len(scoped), "visible_files": len(visible),
            "depth_omitted": depth_omitted, "eligible_files": eligible_files,
        },
        "skipped_directory_names": sorted(skipped_dirs),
        "signals": classified,
        "command_evidence": commands,
        "preexisting_changes": baseline,
        "visible_paths": visible,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", default=".", help="Repository root or explicitly scoped subtree")
    parser.add_argument("--max-depth", type=int, default=3, help="Maximum directory depth shown in visible_paths (default: 3)")
    parser.add_argument("--max-files", type=int, default=500, help="Maximum paths shown in visible_paths (default: 500)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    if args.max_depth < 0 or args.max_files < 1:
        parser.error("--max-depth must be >= 0 and --max-files must be >= 1")
    try:
        inventory = build_inventory(args.target, args.max_depth, args.max_files)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(inventory, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
