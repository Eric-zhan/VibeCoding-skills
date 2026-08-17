---
name: initialize-repository-context
description: Use when initializing, repairing, or auditing repository instructions and AI coding context such as AGENTS.md, architecture notes, code maps, test guidance, invariants, or repository onboarding documents.
---

# Initialize Repository Context

Create a compact, evidence-backed navigation and coding-policy layer for coding agents. Keep discovery read-only and bounded; write only exact paths the user approves.

## Guardrails

- Resolve the target and Git root first. If the target is a subtree, ask whether the scope is the repository or subtree.
- Read ancestor instructions only to learn applicable rules. Do not browse siblings or unrelated paths.
- Do not install dependencies, execute repository code, run builds/tests, change Git state, or save discovery output in the repository.
- Do not read likely secret files. Report their paths only.
- Merge existing context, especially `AGENTS.md`; never replace it wholesale.
- Apply coding standards only to new code and modified regions. Do not turn initialization into a legacy-code modernization pass.
- Treat language detection as a routing signal, not proof of project policy. Confirm ambiguous language, version, ABI, framework, and typing assumptions before making them mandatory.
- Require separate approval for hooks, CI, PR templates, `CODEOWNERS`, MCP, dependencies, and global settings.

## Workflow

### 1. Inventory

Inspect applicable instructions and existing user changes, then run without redirection:

```bash
python3 <skill-dir>/scripts/inventory_repo.py <target> --pretty
```

The script uses Git metadata, limits detailed output to depth 3 and 500 paths, skips generated/vendor/cache directories, and reads only recognized command configuration. It hashes pre-existing changed files locally without emitting their contents. Increase a limit only when evidence is insufficient, and explain why.

### 2. Confirm high-signal evidence

Read only selected manifests, CI definitions, existing docs, entry points, module boundaries, and representative tests. Use targeted `rg` queries instead of full traversal.

Classify conclusions:

- `[Verified]`: directly supported by inspected code, configuration, CI, or user confirmation.
- `[Inferred]`: supported by signals but not directly confirmed.
- `[Unknown]`: requires a concrete human or runtime check.

Mandatory rules may use only verified facts. A README example, dependency file, entrypoint filename, or plausible convention does not verify a command. Keep such commands `[Inferred]`/`[Unknown]` and out of canonical `AGENTS.md` instructions.

### 3. Select coding-standard profiles

Use `signals.languages_by_file_count`, build configuration, and representative source files to decide which profiles are relevant:

- For verified C++ work, read [references/cpp-coding-standards.md](references/cpp-coding-standards.md) completely.
- For verified Python work, read [references/python-coding-standards.md](references/python-coding-standards.md) completely.
- For a mixed repository, read both. Do not load either reference for an unrelated language.

Inspect the repository's configured language version, formatter, linter, compiler warnings, type checker, tests, public interfaces, and established local style. Distinguish a typed Python module from a legacy untyped area. Distinguish C++ from C or ambiguous headers. Do not infer a third-party mutability, lifetime, thread-safety, or ABI contract from a call signature alone.

### 4. Propose and pause

Before any write, show exact target, create/update action, proposed sections, evidence, and reason. State preserved content, omitted candidates, separate changes, and unknowns. Wait for approval of those exact paths.

Normally propose `AGENTS.md` and:

- `docs/ai/index.md`
- `docs/ai/code-map.md`
- `docs/ai/architecture.md`
- `docs/ai/testing.md`
- `docs/ai/invariants.md`

Add `glossary.md` only for important, evidenced domain terms. Reuse an established equivalent layout.

When verified C++ or Python code is in scope, also propose:

- `docs/ai/coding-standards.md` for shared rule precedence, proof strategy, failure strategy, compact-change policy, and risk-triggered planning.
- `docs/ai/cpp-coding-standards.md` only for verified C++ work.
- `docs/ai/python-coding-standards.md` only for verified Python work.

Reuse existing coding-policy documents instead of creating duplicates. In the proposal, identify the selected profiles and state that approval makes the proposed rules verified project policy. Keep only an always-loaded policy capsule and links in `AGENTS.md`; do not copy full language standards into it.

### 5. Draft approved files

Read [references/output-contract.md](references/output-contract.md). Keep `AGENTS.md` short and operational; place explanations in `docs/ai/`. Use relative Markdown links for repository paths and preserve existing content.

Draft only the approved language profiles. Adapt them to verified project versions, tools, ABI requirements, framework behavior, and typing level. Preserve the safety intent, proof/failure strategy, compact-style constraints, and every core semantic category in the output contract. When a core risk is not currently observed, keep one concise trigger-keyed rule (`When code uses X, require Y`) rather than a broad generic section. Omit only unsupported framework examples, project-specific expansions, and unverified tool commands. Never use the reference alone as evidence that a repository already follows a rule.

### 6. Validate

Before mechanical validation, perform the semantic acceptance audit in `references/output-contract.md`. Check the shared document, every selected language profile, and the `AGENTS.md` policy capsule against its required coverage. Treat a missing required topic, a rule with no trigger/fallback, or a selected profile not linked from `AGENTS.md` as an error. Do not replace this audit with file existence or keyword counts.

Run the validator with every approved output and each `path=fingerprint` pair from inventory `preexisting_changes`:

```bash
python3 <skill-dir>/scripts/validate_context.py <target> \
  --approved-path AGENTS.md \
  --approved-path docs/ai/index.md \
  --allow-existing-change <path>=<fingerprint> \
  --pretty
```

When the approved set includes coding standards, pass every non-`AGENTS.md` output explicitly with repeated `--document`; this replaces the default document set. Pass every output with repeated `--approved-path`.

Never whitelist a pre-existing item whose fingerprint is `null`; preserve it and report that approval-scope verification needs human review. Resolve every semantic-audit and validator error. For each warning, add evidence, weaken the claim, or report the remaining uncertainty. Report changed files, selected language profiles, semantic-audit result, validator result, unknowns, and the smallest maintenance trigger.

Stop if scope expands, an existing instruction would be overwritten, a command lacks evidence, architecture is inferred from names alone, or generated files retain placeholders.
