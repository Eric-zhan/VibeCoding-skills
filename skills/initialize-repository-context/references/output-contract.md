# Repository Context Output Contract

Use this contract after discovery and before drafting. It defines the normal output shape; adapt filenames only when the repository already has an equivalent convention.

## Evidence rules

1. Prefix factual sections or list items with `[Verified]`, `[Inferred]`, or `[Unknown]`.
2. Link verified repository paths with Markdown links relative to the current document.
3. For every canonical runnable command, name its evidence source: manifest script, task target, tool convention, or CI job. README examples, dependency files, and entrypoint filenames are candidate commands, not proof.
4. Put only verified instructions in `AGENTS.md`. Put uncertain findings in `docs/ai/`.
5. Do not include secret values, machine-specific absolute paths, chat history, temporary observations, or generic advice.
6. Do not leave `TODO`, `TBD`, `FIXME`, `XXX`, `{{placeholder}}`, or fill-in-the-blank text.

## Coding-policy construction

### Rule authoring principle

Write executable decisions instead of aspirations. Before making a rule `MUST`, answer:

1. What observable code shape, boundary, or risk triggers the rule?
2. How can an agent determine that the requirement is already satisfied?
3. What should the agent do when it cannot prove the property?
4. Could the wording induce duplicate checks, meaningless initialization, thin wrappers, heap allocation, or other defensive noise?

If these questions have no concrete answers, state the item as rationale or review guidance rather than `MUST`.

### Correctness basis

Use the strongest applicable correctness basis, roughly in this order:

1. Type-system and language guarantees
2. Current local control flow
3. An invariant verified at construction or a trusted boundary and maintained afterward
4. An explicit, stable API contract applicable to the current call
5. Supporting evidence from static analysis, compiler diagnostics, tests, and runtime tools
6. Comments, documentation, names, or caller assumptions

Lower-strength evidence cannot override a stronger guarantee. Tests and dynamic tools cover only exercised cases. External input, cross-module data, and untrusted state cannot rely only on comments, naming, or unverified caller assumptions. A removable assertion is not production validation.

### Proof and failure strategy

When a rule requires a property to hold:

1. If code, types, local control flow, a maintained invariant, or an explicit contract proves it, do not add a duplicate check.
2. If it can fail at runtime, validate once at the nearest appropriate untrusted-input or state-transition boundary and handle failure explicitly.
3. If it cannot be validated reliably, prefer a design with unrepresentable invalid states, simpler ownership, or a shorter lifetime.
4. If it still cannot be proved and a sound fix would change a public API, ownership model, thread model, or task scope, report the concrete risk instead of implementing from assumption.

Do not substitute comments, assertions, passing tests, unconditional defaults, stronger atomic ordering, copies, or repeated defensive checks for correctness reasoning.

### Shared policy

- Follow verified repository language versions, formatters, linters, type checkers, compiler settings, APIs, ABI, and local conventions. Do not modernize unrelated legacy code.
- Apply strict rules to new code and modified regions. Report serious problems in untouched code without expanding the change unless they directly block safe implementation.
- Keep simple sequential logic at the call site. Add a function, class, module, or file only for a real semantic boundary, reusable behavior, isolated resource/error policy, or demonstrated complexity reduction.
- Do not add pass-through wrappers, speculative extension frameworks, or abstractions that merely rename one operation.
- Before changing a public API or ABI, persistence format, protocol, schema, dependency set, ownership model, thread model, or multiple established module boundaries, present a short plan and wait for approval. File count or line count alone does not trigger a pause.
- Use project tools for mechanical formatting and checks. Do not encode tool-enforceable details as long prose when the repository configuration is authoritative.

## File responsibilities

### `AGENTS.md`

Purpose: the small operational contract loaded frequently by coding agents.

Include only sections that have evidence:

- Scope and applicable subtrees
- Fast navigation links into `docs/ai/`
- Canonical build, test, lint, format, and run commands with evidence links
- Non-obvious modification boundaries and generated/vendor paths
- Repository-specific completion checks
- Nested instruction-file map when local rules exist
- For C++ or Python repositories, a compact policy capsule and links to the approved coding-standard documents

Keep it below 32 KiB. Do not duplicate architecture prose or broad onboarding material.

The policy capsule should remain operational: apply standards to changed code, avoid unrelated refactors and thin abstractions, use the proof/failure strategy, pause for high-risk contract changes, and run verified checks. Add a language-specific red flag only when that profile is approved; link the detailed rule instead of restating it.

### `docs/ai/index.md`

Purpose: entry point and ownership map for the AI context set.

Include:

- One-line purpose for every context document
- Evidence-status legend
- Scope and last verification basis, such as the commit or working tree state
- Update triggers: structural changes, command changes, invariant changes
- Known unknowns requiring human confirmation

### `docs/ai/code-map.md`

Purpose: route an agent to the smallest relevant part of the repository.

Include:

- Entrypoints and their roles
- Major modules/packages with responsibilities
- Important interfaces and data-flow links
- Test locations paired with implementation locations
- Generated, vendored, migration, fixture, or schema locations

Prefer a compact table: path, responsibility, dependents, evidence status. Do not inventory every file.

### `docs/ai/architecture.md`

Purpose: explain stable runtime and dependency boundaries.

Include:

- System/component boundaries
- Dependency direction
- Runtime request/event/data flow
- External systems and persistence boundaries
- Important design decisions that are visible in code or ADRs

Separate confirmed behavior from interpretation. A directory name alone is not architecture evidence.

### `docs/ai/testing.md`

Purpose: make verification selection fast and reliable.

Include:

- Test layers and locations
- Canonical commands and their configuration/CI evidence
- Mapping from changed area to minimum relevant checks
- Required services, fixtures, environment variables by name only, and side effects
- Known slow, flaky, destructive, or externally connected checks

Never claim a command passed unless it was run in the current task and its output was observed.

### `docs/ai/invariants.md`

Purpose: record constraints that must survive implementation changes.

Include only repository-specific invariants supported by code, schema, tests, ADRs, or explicit user confirmation:

- API and compatibility guarantees
- Data integrity and ordering rules
- Security and authorization boundaries
- Cross-module dependency restrictions
- Generated-source ownership
- Failure and rollback expectations

For each invariant, link its enforcement point or mark it `[Unknown]` with a concrete verification question.

### `docs/ai/coding-standards.md` (conditional)

Create for approved C++ or Python profiles. Include rule precedence, the rule-authoring principle, correctness basis, proof/failure strategy, shared compact-change policy, risk-triggered planning, and links to each selected language document.

Treat explicit user approval of the proposed profile as policy evidence and state that basis. Do not present generic reference text as an observed repository convention.

### `docs/ai/cpp-coding-standards.md` (conditional)

Create only for verified, approved C++ work. Adapt [cpp-coding-standards.md](cpp-coding-standards.md) to the repository's C++ version, build configuration, ABI surface, third-party boundaries, and tools. Preserve actionable lifetime, ownership, conversion, concurrency, macro, numerical, Tensor/CV, testing, and compact-style rules. Omit sections that cannot apply.

### `docs/ai/python-coding-standards.md` (conditional)

Create only for verified, approved Python work. Adapt [python-coding-standards.md](python-coding-standards.md) to the repository's Python versions, typing level, frameworks, data boundaries, async model, numerical libraries, and tools. Preserve actionable state, typing, exception, resource, import, concurrency, Tensor/array, security, testing, and compact-style rules. Omit sections that cannot apply.

### `docs/ai/glossary.md` (conditional)

Create only when domain terms materially affect code navigation or correctness. Include term, repository meaning, evidence link, and common ambiguity. Do not copy generic industry definitions.

## Proposal contract

Before writing, present one row per target file:

| Target | Action | Proposed content | Evidence | Reason |
|---|---|---|---|---|

Then state:

- Existing content that will be preserved
- Candidate files intentionally omitted and why
- Any separate changes that would need another approval
- Unknowns that affect the draft

Approval must cover exact paths. A broad request to “set up the repository” is not approval for hooks, CI, dependencies, MCP, editor settings, or global configuration.

## Validation contract

### Semantic acceptance

File existence and keyword matching do not prove policy quality. Read each generated document and verify the following core coverage before running the mechanical validator. A core topic needs at least one actionable rule with an observable trigger, a way to recognize satisfaction, and a safe fallback or escalation path where proof can fail.

Core topics remain in every selected language profile because they constrain future changes as well as current code. If the repository does not currently use a core facility, express its rule compactly and conditionally, such as `When code uses dynamic SQL identifiers, ...`; do not claim the facility is currently present. Expand a core topic with repository-specific detail only when evidence supports it.

The shared profile must cover:

- Rule precedence and incremental/project-compatible scope
- Correctness basis and proof/failure strategy
- Compact-change policy that rejects thin wrappers and speculative abstractions
- Risk-triggered planning based on contract impact rather than file/line count
- Links to every selected language profile

The C++ profile, when selected, must cover these core categories:

- Verified language/tool/ABI compatibility and incremental scope
- Compact design and value-semantics-first ownership
- Named conversions, const-removal prohibition, and the documented third-party exception
- Borrowed view/pointer/reference lifetime and invalidation
- RAII, Rule of Zero/special-member review, and truthful `noexcept`
- API/ABI boundaries, macros, concurrency/happens-before, numerical and native buffer/Tensor/image boundaries
- Focused testing and verified project tools

The Python profile, when selected, must cover these core categories:

- Verified version/framework/tool compatibility, legacy typing scope, and runtime annotation consumers
- Compact design without thin wrappers, decorative typing, or speculative abstractions
- Definition-time defaults, mutability/aliasing, and missing/`None`/falsy state distinctions
- Narrow business exceptions, explicit outer fault boundaries, cancellation propagation, and deterministic resource ownership
- Generator lifetime, import-time behavior, task ownership, and GIL-independent synchronization
- Array/Tensor/native and third-party failure-sentinel boundaries without mechanical copy/detach/CPU/contiguous operations
- Safe deserialization, SQL values/identifiers, subprocess shell rules, filesystem resource boundaries, testing, and verified tools

The `AGENTS.md` policy capsule must preserve existing instructions, link the shared and every selected language profile, state incremental scope and compact-change behavior, identify high-risk plan triggers, and route verification to documented project checks. If a pre-existing changed `AGENTS.md` cannot be safely merged under fingerprint protection, report partial installation rather than claiming the policy is active.

Optional material is limited to framework-specific examples, repository-specific expansions, and concrete tool commands/configuration not supported by evidence. Omit that material without removing a core category. Resolve semantic gaps before mechanical validation.

### Mechanical acceptance

The generated set passes when:

- Required files exist at the approved paths
- `AGENTS.md` is at most 32 KiB
- No placeholder markers remain
- Local Markdown path links resolve inside the repository
- Canonical commands are supported by discovered repository evidence; candidate commands remain `[Inferred]`/`[Unknown]` and are reported as warnings
- AI context documents use evidence-status labels
- Validation receives every approved output via `--approved-path` and each inventory `path=fingerprint` pair via `--allow-existing-change`; fingerprints remain unchanged and no other changed path exists

Warnings are review items, not automatic failures. Resolve them by adding evidence, weakening a claim, or documenting the remaining uncertainty.
