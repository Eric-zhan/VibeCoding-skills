# Python Coding Standards Reference

Use this reference only for verified Python work. Generate repository-facing rules from applicable sections and adapt them to the verified Python versions, typing level, frameworks, tools, and data boundaries. The shared policy, correctness basis, and proof/failure strategy in `output-contract.md` govern every rule below.

## Contents

1. Scope and compatibility
2. Compact design and formatting
3. Type annotations and runtime contracts
4. Defaults, mutability, and data models
5. Python state semantics
6. Functions, APIs, and dynamic behavior
7. Exceptions and fault boundaries
8. Resources, iterators, and generators
9. Imports, modules, and dependencies
10. Async and concurrency
11. NumPy, OpenCV, Tensor, and third-party I/O
12. I/O, serialization, SQL, processes, and paths
13. Performance, logging, and documentation
14. Tests and tools

## 1. Scope and compatibility

- Follow the repository's supported Python versions, dependency manager, formatter, linter, type checker, test framework, framework conventions, and established naming.
- Apply these rules to new code and modified regions. Do not reformat, rename, annotate, or modernize unrelated legacy code.
- Preserve public behavior, import paths, exception behavior, serialization, plugin contracts, and framework-visible metadata unless the task explicitly changes them.
- Before changing a public API, persisted/schema/protocol format, dependency set, task/thread model, framework lifecycle, or established module boundaries, present a short plan and wait for approval.
- Do not infer runtime validity from a type hint. External input, deserialized data, environment state, and untyped dependencies require boundary handling based on their actual contract.

## 2. Compact design and formatting

- Keep short sequential logic at the call site when extraction would only rename one operation or move a few obvious lines elsewhere.
- Add a helper only when it names a real domain operation, is reused, isolates complex branching/resource/error policy, or measurably reduces reasoning complexity.
- Do not create a one-use wrapper around `cv2.imread`, `json.loads`, a database call, or another API merely to repeat the call. A wrapper must add a stable contract such as normalization, failure policy, resource ownership, instrumentation, or meaningful reuse.
- Do not introduce managers, factories, strategies, registries, base classes, decorators, or generalized plugin layers for hypothetical future variants.
- Do not convert every mapping into a class or every failure into a custom exception. Use the simplest representation that preserves the real contract.
- Let the verified project formatter decide line wrapping. Do not vertically expand short expressions or reflow unrelated code by hand.
- Do not split a module solely because of a fixed line count. Split when responsibilities, state ownership, dependencies, or independent testing form a stable boundary.

## 3. Type annotations and runtime contracts

- New annotations should match the typing level of the surrounding project, its minimum Python version, and the modules actually covered by static checking.
- When the project statically checks the relevant module, a new public interface must have accurate annotations. Public interfaces include exported APIs, framework entry points, plugin hooks, and stable cross-module contracts, not merely names without a leading underscore.
- When modifying an existing untyped function, do not annotate its entire call chain solely because the function was touched. If the data contract changes, update related existing annotations.
- Do not add decorative annotations that collapse to `Any` or fail to express the real contract. Do not expand an unrelated typing refactor to satisfy a local rule.
- Use `Any` only at a genuinely dynamic/untyped boundary and narrow it as soon as evidence permits. Do not allow `Any` to spread through otherwise typed business logic.
- `cast()` changes only static analysis. Use it only when a visible invariant or verified external contract proves the type; validate at runtime when the value can actually violate the claim.
- A type suppression must be local, use a specific error code when supported, and state why the checker cannot express a verified contract. Fix an in-scope cause instead of suppressing it.
- Model `None` and union states accurately and narrow them through control flow. Do not lie in an annotation to avoid handling a valid state.
- Add `Protocol`, `TypeVar`, overloads, or a generic base only for actual polymorphic callers or a stable generic contract, not for one implementation.
- Annotations may be consumed at runtime. Before changing annotations, `Annotated` metadata, forward references, or annotation evaluation (including `from __future__ import annotations`), verify effects on FastAPI, Pydantic, ORMs, dependency injection, serialization, decorators, and project reflection.

## 4. Defaults, mutability, and data models

- Do not use a mutable default argument. Create the value at call time.
- Use `None` as an omitted-value sentinel only when `None` is not a valid input state. Otherwise use a unique private sentinel and test identity.
- Default expressions are evaluated when the function is defined. Time, randomness, environment state, mutable state, or any value that must be refreshed per call must be computed inside the function or by an explicit factory.
- For dataclasses and similar models, use the framework's default factory for mutable or per-instance values.
- Distinguish shared references, shallow copies, and deep copies. Copy only when isolation is part of the contract; do not defensively copy every large object.
- Do not introduce accidental shared class-level mutable state. Use class state only when sharing and synchronization/lifecycle are explicit.
- Avoid aliasing constructions such as repeating one mutable object with sequence multiplication. Build independent objects when independent mutation is required.
- Use a simple mapping, tuple, named tuple, dataclass, validated model, or ordinary class according to required invariants and project conventions. Do not add a new modeling dependency without approval.
- If equality is customized, review hashing and mutability. Only objects with stable hash/equality semantics may be used as persistent mapping keys or set members.

## 5. Python state semantics

- Distinguish `None`, missing, and other falsy values according to domain semantics. When `0`, `False`, `""`, or an empty collection is valid, do not use a truthiness check as a substitute for an explicit missing/`None` test.
- When a missing mapping key differs from a key whose value is `None`, do not use `dict.get()` in a way that merges the states. Use membership testing or a unique sentinel.
- Use identity comparison for `None`, a verified singleton, or genuine object-identity semantics. Use equality for ordinary values.
- When creating callbacks, closures, comprehensions, or deferred work in a loop, verify whether late binding of loop variables is intended. Bind a per-iteration value explicitly when needed.
- Do not structurally modify a container during iteration unless the specific container/API documents that operation as valid. Iterate over a deliberate snapshot or collect changes when necessary.
- Do not assume an iterator can be restarted or consumed twice. If repeated traversal is required, choose a reusable collection or explicitly materialize with an understood memory bound.

## 6. Functions, APIs, and dynamic behavior

- Give a function one clear purpose, but do not interpret that as one function per statement or library call.
- Keep return shape, error semantics, and mutation behavior consistent across branches. Do not make callers guess whether a function returns a value, `None`, a sentinel, or raises for the same condition.
- Do not mutate a caller-provided object unless the API name, framework convention, or documentation makes in-place mutation explicit.
- Avoid `*args` and `**kwargs` when a stable interface can name its parameters. They are appropriate for genuine forwarding, decorators, compatibility layers, or framework protocols.
- Do not stack boolean switches that create unrelated modes. Use a small enum or separate operation only when distinct semantics justify it; do not create extra types mechanically.
- Limit monkey patching, descriptor/metaclass machinery, dynamic attribute injection, reflection, and code generation to verified framework requirements or cases where simpler mechanisms cannot satisfy the contract.
- Do not use dynamic behavior to bypass typing, validation, access boundaries, or dependency ownership.

## 7. Exceptions and fault boundaries

- In business logic, catch the narrowest exception that the current layer can handle, enrich, translate, retry, or clean up from.
- Do not use bare `except:`. Do not silently swallow an exception. If a specific failure is intentionally ignored, constrain the exception and state why continuing is safe.
- Keep the `try` region around the operation expected to fail so unrelated programming errors are not misclassified.
- When translating an exception, preserve causality with `raise ... from exc`. When propagating the same exception, use bare `raise`.
- At an explicit process, request, worker, task, job, or plugin fault-isolation boundary, catching `Exception` is allowed to log, translate, or isolate an unknown failure. Do not continue with state that may be inconsistent.
- Do not catch `BaseException` as a general failure policy. Preserve `SystemExit`, `KeyboardInterrupt`, and framework control-flow exceptions unless that exact boundary owns them.
- Cancellation is control flow, not an ordinary business failure. If cancellation is caught for cleanup, propagate it by default; consume it only at the scheduler/task boundary responsible for doing so.
- Follow the async framework's cancellation hierarchy rather than assuming every cancellation exception is or is not an `Exception` subclass.
- Do not create a custom exception for every message. Add a type when callers need stable programmatic distinction or an established domain hierarchy requires it.

## 8. Resources, iterators, and generators

- Acquire and release files, locks, connections, transactions, temporary resources, and async resources with the appropriate context manager when deterministic cleanup is required.
- Do not rely on garbage collection or object finalization timing for critical cleanup. A finalizer may be a fallback, not the primary ownership protocol.
- A generator must not implicitly hold a scarce resource requiring prompt deterministic release unless that lifetime is an explicit public contract of the generator.
- If partial consumption can leave a file, connection, transaction, lock, or native handle open, expose a context manager/visible close contract or redesign ownership.
- A generator's `finally` is useful cleanup but does not prove prompt release while a caller retains a partially consumed generator.
- Do not materialize every iterable into a list. Materialize only for bounded repeated traversal, random access, isolation from mutation, or an explicit snapshot.
- Ensure cleanup and transaction semantics remain correct on success, failure, cancellation, and partial iteration.

## 9. Imports, modules, and dependencies

- Importing a module must not start threads/tasks, access the network, mutate process-level environment, or perform expensive initialization.
- When an established framework depends on import-time registration, allow only local, deterministic, idempotent registration. Do not use that exception for I/O, background work, or irreversible global-state changes.
- Do not use wildcard imports. Keep imports at module scope unless optional dependencies, verified cycle avoidance, framework behavior, or delayed heavy loading provides a concrete reason.
- Do not shuffle imports or add local imports merely to hide a circular dependency. Correct the responsibility boundary when that change is in scope and compatible.
- Do not add, replace, or upgrade a dependency without approval. Reuse verified project dependencies and standard-library facilities when they satisfy the contract.
- Use the project's established package layout and entrypoint mechanism. For a standalone executable module, guard direct execution when required by multiprocessing or import safety.

## 10. Async and concurrency

- Do not run blocking I/O or long CPU work directly on an event-loop thread. Use the project's verified executor, worker, process, or async API.
- Every created task requires an owner responsible for awaiting, cancellation, exception observation, and lifetime. Fire-and-forget is allowed only under an explicit supervisor that records failures.
- Do not hold a synchronous thread lock across an `await`. Select a synchronization primitive that matches the execution model.
- Do not treat the GIL as proof of application-level synchronization correctness.
- Thread safety must come from immutable state, a lock or synchronization primitive, message passing/task ownership, or an API with an explicit thread-safety contract.
- Do not build a shared-state protocol around an operation that happens to be atomic in one Python implementation. Preserve correctness across supported implementations and versions.
- Make shutdown ordering explicit for threads, processes, executors, queues, and tasks. Do not leave work referring to state whose owner has exited.
- With multiprocessing, account for serialization, process start method, import behavior, and platform support; do not assume fork semantics.

## 11. NumPy, OpenCV, Tensor, and third-party I/O

- At a framework, device, native API, serialization, or asynchronous boundary, confirm the relevant device, dtype, shape/layout, stride/contiguity, ownership/aliasing, writability, lifetime, and autograd semantics.
- Check only properties relevant to the destination contract and not already proved by local control flow or a maintained invariant.
- Move to CPU only when the target requires host memory. Detach only when severing autograd is intended. Clone/copy only for required ownership isolation. Make contiguous only when the target layout requires it.
- Do not mechanically apply `detach()`, `clone()`, `cpu()`, `contiguous()`, or dtype conversion as generic safety steps; each can change semantics or cost materially.
- Before in-place mutation, determine whether an array/tensor is a view, shared, broadcast, read-only, gradient-tracked, or concurrently visible.
- When crossing image-library boundaries, confirm channel order, color space, dimensional order, and value range when relevant.
- When a third-party I/O API documents a failure sentinel, handle it at the input boundary. For example, an image read may return `None`; do not assume the returned object is valid.
- Do not create a one-use thin wrapper solely to perform that sentinel check. Keep it at the boundary unless a reusable error/normalization contract justifies abstraction.
- Check NaN, infinity, shape, and range only where invalid values can enter or materially affect behavior. Do not add checks after every numeric operation.

## 12. I/O, serialization, SQL, processes, and paths

- Validate untrusted data at the nearest decoding/input boundary and convert it into an internal representation with explicit states. Do not scatter repeated validation through downstream logic.
- Do not deserialize untrusted data with `pickle`, unsafe YAML loaders, `eval`, or `exec`. Use a safe parser and validate the resulting structure.
- Use an explicit text encoding for stable interchange. Preserve newline, atomic-write, and replacement semantics required by the existing format.
- SQL data values must use parameter binding. Do not interpolate values into query text.
- Table names, column names, sort fields, and directions cannot normally use value placeholders. Map finite choices through an allowlist; for genuinely dynamic identifiers, use the driver's identifier-composition API and validate authorization separately.
- Invoke subprocesses with an argument list and `shell=False` by default. Use a shell only when pipes, redirection, shell builtins, or other shell semantics are genuinely required.
- Do not insert untrusted input into shell command text through concatenation, formatting, or templates. Escaping alone is not permission to place arbitrary external input in a command.
- When a subprocess argument can be interpreted as an option, use the called program's safe option delimiter or validate the argument according to that program's contract.
- When external input is restricted to a directory or resource boundary, prove the final operation remains within that boundary. Do not rely only on textual path-prefix checks.
- Symlink policy depends on the interface and threat model; a symlink must not bypass the authorized target boundary.
- In an adversarial filesystem, avoid a check-then-open design whose path can change between operations. Use project/OS facilities for directory-relative or atomic safe opening when required.
- Do not log secrets, credentials, tokens, or unrestricted sensitive payloads. Preserve useful diagnostics with redaction.

## 13. Performance, logging, and documentation

- Optimize from profiling, a demonstrated data-size bound, or a clear complexity defect. Do not trade correctness and clarity for speculative micro-optimization.
- Do not vectorize into an opaque expression merely because NumPy can. Use a clear loop or staged expression when it is easier to verify and performance is adequate.
- Avoid accidental repeated materialization, quadratic concatenation, unbounded caches, and large hidden copies at measured or obviously scaled paths.
- Do not add caching without defining invalidation, ownership, concurrency, memory bounds, and evidence that caching is needed.
- Use the project's logging facility and levels. Do not add `print()` debugging to library code unless stdout is the established interface.
- Prefer logging APIs that defer formatting when that is the project convention. Do not compute expensive log values when the level is disabled.
- Comments explain contracts, safety reasoning, non-obvious state, units, and reasons. Do not narrate syntax or claim enforcement that does not exist.
- Follow the project's docstring convention. Document public/non-obvious contracts, but do not generate template docstrings for every private helper or obvious accessor.

## 14. Tests and tools

- Test observable behavior, boundaries, failure sentinels, state distinctions, cancellation/resource cleanup, and compatibility affected by the change.
- Add a regression test for a fixed defect when a stable test can reproduce it. Do not expose private internals or add wrappers solely to make mocking easier.
- Mock real external boundaries, not simple value objects or the behavior under test. Understand dependency side effects before replacing them.
- Control randomness, time, locale, concurrency, process behavior, and external services when deterministic results matter.
- Run the smallest verified relevant tests first, then the repository-required formatter, linter, type checker, security checks, and broader test suite.
- Do not add or relax formatter/linter/type-checker configuration, skip a test, or add a broad suppression without approval and a concrete compatibility reason.
- Do not claim a check passed unless it ran in the current task and its result was observed.

## AGENTS.md policy capsule

Keep only a compact form in `AGENTS.md`:

- Match the surrounding Python version, typing level, frameworks, and tools; apply detailed Python rules only to new and modified code.
- Keep simple logic local; do not add thin wrappers, decorative typing, or speculative abstractions.
- Distinguish missing/`None`/falsy states, validate dynamic input at its boundary, and make resource/task ownership explicit.
- Pause before public API, persistence/schema/protocol, dependency, concurrency/lifecycle, or cross-module changes.
- Run the verified Python checks relevant to the modified area and link the detailed standard.
