# C++ Coding Standards Reference

Use this reference only for verified C++ work. Generate repository-facing rules from the applicable sections; adapt version-dependent features and tool commands to verified project configuration. The shared policy, correctness basis, and proof/failure strategy in `output-contract.md` govern every rule below.

## Contents

1. Scope and compatibility
2. Compact design
3. Types, conversions, and constness
4. Ownership and lifetime
5. Initialization and special members
6. Classes, interfaces, and ABI
7. Containers and iterators
8. Move semantics and templates
9. Errors and `noexcept`
10. Macros and compile-time configuration
11. Concurrency
12. Numeric code
13. Tensor, image, buffer, and native boundaries
14. I/O, serialization, and security
15. Performance
16. Headers, dependencies, and build integration
17. Logging, comments, and tests

## 1. Scope and compatibility

- Follow the repository's configured C++ standard, compiler support, warnings, formatter, linter, ABI policy, and established naming. Do not introduce a newer language feature without verified support.
- Apply these rules to new code and modified regions. Do not reformat, rename, or modernize unrelated legacy code.
- Preserve public API, ABI, serialized layout, wire format, exception behavior, and ownership contracts unless the task explicitly changes them.
- Before changing public API/ABI, object layout, ownership, thread behavior, persistence/protocol format, dependencies, or established module boundaries, present a short plan and wait for approval.
- A local compatibility exception must be narrower than the rule it relaxes, must state the verified contract, and must not hide undefined behavior.

## 2. Compact design

- Keep short sequential logic at the call site when extraction would only rename an operation or move a few obvious lines elsewhere.
- Add a helper only when it names a real domain operation, is reused, isolates complex branching/resource/error policy, or measurably reduces reasoning complexity.
- Do not create a stateless one-method class merely to hide a free function. Function objects, custom deleters, comparators, visitors, and policy types are allowed when their type identity is part of a real contract.
- Do not introduce interfaces, factories, registries, strategies, builders, or generalized frameworks for hypothetical future variants.
- Prefer the repository's existing abstraction even when another design is fashionable. Do not expand task scope to make surrounding code conform.
- Do not split a file solely because of a fixed line count. Split when responsibilities, ownership, dependencies, or independent testing form a stable boundary.

## 3. Types, conversions, and constness

- Prefer types that encode units, validity, ownership, and optionality when the distinction prevents a demonstrated error; do not create wrapper types for every primitive.
- Do not use C-style casts. Use the narrowest named cast and make its required preconditions visible.
- Before an integral conversion, prove or validate range and signedness when the source can exceed the destination. Do not silence warnings with an unchecked `static_cast`.
- Before a floating/integral conversion, define rounding, truncation, overflow, NaN, and infinity behavior when those states can reach the boundary.
- Use `reinterpret_cast` only at a verified low-level representation boundary. Confirm size, alignment, object lifetime, strict-aliasing, and endianness requirements; prefer `std::bit_cast` or `memcpy` when supported and semantically correct.
- Do not remove constness from storage that may actually be immutable. If a callee can write, provide genuinely mutable storage or change the owning API.
- `const_cast` is prohibited by default. It is allowed only in a minimal wrapper around a verified const-incorrect external API whose contract guarantees no write.
- A `const_cast` exception must document `SAFETY`, `LIFETIME`, and `CONTRACT`, name the external API guarantee, and use the narrowest applicable suppression. If any guarantee is unknown, report the risk instead of casting.
- Apply `const` to observers and immutable inputs where consistent with the repository, but do not perform unrelated const-propagation refactors.

## 4. Ownership and lifetime

- Choose ownership in this order: value/member object, scoped RAII object, `std::unique_ptr` for required dynamic lifetime or polymorphism, then `std::shared_ptr` for real shared ownership.
- Do not heap-allocate an object merely to make ownership look explicit. State the need for indirection: polymorphism, optional large storage, stable address, PImpl, or independent dynamic lifetime.
- Treat raw pointers and references as non-owning unless an established API explicitly says otherwise. Use a reference only when null is not a valid state.
- Do not create an owning raw pointer. Match allocation and deallocation through an RAII owner, including third-party resources with custom deleters.
- A returned pointer, reference, iterator, `std::string_view`, or `std::span` requires an owner whose lifetime is proven to outlive every use.
- Never return a view/reference into a local or temporary object. Do not carry a view into a stack object across an asynchronous boundary. If lifetime cannot be proved, return an owning value.
- Before storing a callback or lambda, prove that reference captures and `this` outlive invocation. Prefer value capture or an explicit ownership/weak-reference protocol when execution is deferred.
- After container mutation, re-establish the validity of retained pointers, references, and iterators according to that container's invalidation rules.

## 5. Initialization and special members

- Every object must have a determinate value before its first read. Initialize members explicitly unless construction guarantees are otherwise visible.
- Prefer initializing local variables at declaration. Omit meaningless pre-initialization only when a verified API completely writes the object before any success-path read and failure paths do not read it.
- Initialize members in declaration order and do not rely on initializer-list order.
- Prefer the Rule of Zero. After customizing any destructor, copy constructor, copy assignment, move constructor, or move assignment, review every other special member and choose implicit generation, `= default`, `= delete`, or a custom implementation according to the type contract.
- Do not mechanically implement all five special members. A resource-owning type must preserve single ownership, valid moved-from state, and exception safety.
- Destructors must not allow exceptions to escape. Cleanup failure requiring handling must occur before destruction through an explicit operation.

## 6. Classes, interfaces, and ABI

- Establish class invariants during construction or factory creation. Do not expose partially initialized objects unless that state is an explicit protocol.
- Prefer a `struct` with public members for simple internal aggregates. Do not add pass-through getters/setters that enforce no invariant and provide no compatibility boundary.
- Exported SDK or ABI-facing interfaces may use nontrivial accessors to preserve encapsulation and compatibility. An inline getter does not by itself provide ABI stability; use a verified strategy such as non-inline exported functions, PImpl, opaque handles, or a C ABI.
- Use `explicit` for a single-argument constructor or conversion operator unless implicit conversion is deliberately part of the API.
- A polymorphic base deleted through the base must have a virtual destructor. Mark overrides with `override`; use `final` only when extension is intentionally prohibited.
- Do not expose ownership through ambiguous pointer-returning APIs. State borrowing, transfer, nullable state, and mutation in types or stable interface documentation.
- Avoid public data layout changes in ABI-stable types. Confirm packing, alignment, enum width, calling convention, and symbol visibility at binary boundaries.

## 7. Containers and iterators

- Select a container for required semantics and measured access patterns, not habit. Default to contiguous value storage when it fits the contract.
- Index, iterator, lookup, and empty-container checks are required only when not already proved by types, local control flow, container operations, or maintained invariants.
- Check `find` results before dereference unless the key's presence has already been established locally. Do not replace a lookup with `operator[]` when insertion is not intended.
- Use unchecked indexing only when the bound is proven in the current path. Validate untrusted indexes at their boundary; do not add duplicate checks inside an already bounded loop.
- Do not retain iterators/references across operations that may invalidate them. Make mutation order explicit when traversing and erasing.
- Reserve capacity only when a meaningful bound is known and allocation behavior matters. Do not guess large capacities as a generic optimization.

## 8. Move semantics and templates

- Use `std::move` only when the source may be consumed and is not subsequently relied on except for valid operations on a moved-from object.
- Do not move from `const` expecting a move; this normally selects a copy. Do not add `std::move` to return statements when copy elision applies unless verified measurement or semantics require it.
- Use ordinary rvalue-reference parameters only for consuming APIs. Use forwarding references and `std::forward` only for genuine generic forwarding.
- For a normal business function, prefer value-then-move or `const&` according to object size, ownership, and call patterns; do not use unconstrained `T&&` to avoid deciding the contract.
- Introduce a template only when behavior is genuinely type-generic or the established API requires it. Prefer a concrete function when only one or two fixed types exist.
- Constrain templates with the project's supported mechanism when unconstrained substitution would produce ambiguous or unsafe usage. Keep template definitions out of public headers when no instantiation requirement exists.

## 9. Errors and `noexcept`

- Follow the repository's established exception/status/result policy. Do not mix error models within one path without an explicit boundary adapter.
- Check status values when failure is possible and not already made impossible by contract. Do not ignore a result merely to silence a warning.
- Catch only exceptions that the current layer can handle, enrich, translate, or clean up from. Preserve diagnostic context when translating.
- Provide at least the exception guarantee required by the operation. Commit externally visible state only after failure-prone preparation when partial update is invalid.
- Mark a function `noexcept` only when all reachable operations satisfy that promise or termination is the intended contract.
- Move operations and `swap` should be `noexcept` when their implementations truly cannot throw; do not add it mechanically. Destructors should remain non-throwing.

## 10. Macros and compile-time configuration

- Do not use a macro for a constant, function, or type alias when `constexpr`, an inline function, a template, or `using` expresses the same contract.
- Macros are acceptable for include guards, platform/configuration selection, feature detection, attributes, logging/assertion call-site metadata, and integration with an existing framework that requires them.
- Keep conditional compilation narrow and test each supported branch. Do not duplicate whole implementations behind platform macros when a small adapter isolates the difference.
- Parenthesize macro parameters and expansions where applicable, prevent repeated evaluation of arguments, and use the standard single-statement pattern for statement-like macros.
- Do not use macros to bypass type checking, access control, or ordinary scoping without a verified framework requirement.

## 11. Concurrency

- Every shared mutable object requires a documented synchronization or ownership rule. Thread safety must come from immutability, confinement/message passing, locks/atomics, or a verified API contract.
- Prefer mutexes, condition variables, queues, and existing project primitives. Do not implement a custom lock-free protocol if the happens-before relationship cannot be explained.
- When using a non-default `std::memory_order`, explain the synchronizes-with/happens-before relationship in code or design documentation. Do not strengthen ordering blindly as a substitute for correctness reasoning.
- Do not use `volatile` for inter-thread synchronization.
- Acquire and release locks through RAII. Define lock order when multiple locks may be held, and do not call unknown or re-entrant code while holding a lock unless the contract requires it.
- Make thread/task lifetime explicit. Join, stop, cancel, or transfer ownership; do not leave callbacks referring to destroyed state.
- Predicate condition-variable waits and re-check state after wakeup. Do not treat notification as proof that the condition holds.

## 12. Numeric code

- Make units, coordinate frames, dimensions, signedness, and size units explicit at boundaries where confusion is possible.
- Before arithmetic that can exceed its type for reachable input, validate bounds or use a representation/operation with defined behavior. Do not rely on signed overflow.
- Define integer division, rounding, saturation, and narrowing behavior when results cross an API or storage boundary.
- Use exact floating comparison only when exact representation is part of the contract. Otherwise choose tolerance from domain scale; do not insert a universal epsilon.
- Check NaN, infinity, domain, or range only where invalid values can enter or materially affect behavior and the property is not already proved.

## 13. Tensor, image, buffer, and native boundaries

- At a framework, device, native API, serialization, or asynchronous boundary, confirm the relevant shape, element type, layout, stride/contiguity, size units, device, mutability, ownership/aliasing, alignment, and lifetime.
- Do not mechanically copy, clone, detach, cast, or make a buffer contiguous. Perform only transformations required by the destination contract and preserve algorithm semantics.
- Distinguish element count from byte count and check multiplication overflow before allocating or passing a byte size.
- A data pointer borrowed from a tensor/image/container is valid only while the owner, storage, and required layout remain unchanged. Do not retain it past reallocation, mutation, device transfer, or asynchronous completion without a verified contract.
- If a native API accepts `void*`, determine whether it writes. For a read-only source, prefer a `const void*` path; a const-incorrect API may use only the documented wrapper exception from Section 3.
- Confirm channel order, color space, coordinate convention, and numeric range when images cross library boundaries. Do not infer these from type alone.

## 14. I/O, serialization, and security

- Validate untrusted lengths, indexes, enum values, offsets, and allocation sizes before use. Bound total resource consumption when input controls repetition or nesting.
- Define versioning, endianness, encoding, field presence, and unknown-field behavior for persisted or transmitted data. Preserve compatibility unless change is approved.
- Do not reinterpret arbitrary bytes as an object unless the type and lifetime rules permit it. Prefer explicit decoding, `memcpy`, or supported bit conversion.
- Use parameterized database APIs and argument-vector process APIs. Do not construct commands or queries by concatenating untrusted input.
- When input is restricted to a filesystem boundary, validate the final resource according to the threat model; do not rely only on textual prefix checks.
- Do not log secrets, credentials, tokens, or unrestricted sensitive payloads. Preserve error context without exposing protected data.

## 15. Performance

- Optimize from measured evidence, a demonstrated scale bound, or a clear complexity defect. Do not trade correctness or clarity for speculative micro-optimization.
- Prefer value semantics, stack/scoped storage, and contiguous containers when appropriate, but do not copy large objects unintentionally.
- Make expensive copies and allocations visible at hot boundaries. Pass by value when consumption enables efficient move; otherwise use the appropriate non-owning view/reference with proven lifetime.
- Avoid repeated allocation in a measured loop by reusing capacity or storage only when reset semantics and aliasing remain correct.
- Do not add caching without defining invalidation, ownership, concurrency, memory limits, and evidence that caching is needed.

## 16. Headers, dependencies, and build integration

- Headers must be self-contained and include what they directly use. Follow the repository's include-order and guard convention.
- Do not place `using namespace` in a header. Keep symbols in the narrowest practical namespace and avoid collision-prone global names.
- Use forward declarations only when legal and useful; include the complete definition when layout, inheritance, deletion, or inline behavior requires it.
- Avoid non-inline definitions and mutable global objects in headers that violate the one-definition rule or create initialization-order hazards.
- Do not add a dependency, compiler flag, warning suppression, generated step, or platform branch without approval and verified build integration.
- Keep suppressions local and name the exact diagnostic. Fix the cause when it is in scope and compatible.

## 17. Logging, comments, and tests

- Use the project's logging facility and levels. Do not add stdout/stderr debugging to library code unless that is the established interface.
- Comments explain contracts, safety proofs, units, non-obvious invariants, and reasons. Do not narrate syntax or claim a property the code does not enforce.
- Test observable behavior, boundaries, failure paths, ownership/lifetime-sensitive behavior, and compatibility affected by the change.
- Add a regression test for a fixed defect when a stable test can reproduce it. Do not expose private internals solely to test them.
- Run the smallest verified relevant tests first, then the repository-required broader compiler, formatter, linter/static-analysis, sanitizer, and test checks.
- Do not claim sanitizer, race-detector, static-analysis, or test success unless the command ran in the current task and its result was observed.

## AGENTS.md policy capsule

Keep only a compact form in `AGENTS.md`:

- Apply the repository's C++ standard and detailed C++ rules to new and modified code; do not modernize unrelated code.
- Prefer value semantics and RAII; do not remove constness or rely on an unproved lifetime/ownership contract.
- Keep simple logic local; do not add thin wrappers or speculative abstractions.
- Pause before public API/ABI, persistence/protocol, dependency, ownership, thread-model, or cross-module changes.
- Run the verified C++ checks relevant to the modified area and link the detailed standard.
