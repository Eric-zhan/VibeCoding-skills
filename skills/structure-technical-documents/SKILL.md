---
name: structure-technical-documents
description: Use when turning conversations, source material, code investigations, work logs, or draft Markdown into structured, readable technical documentation, or when auditing an existing document for logic, evidence, terminology, and maintainability.
---

# Structure Technical Documents

Organize knowledge by its subject, evidence, audience, and lifecycle rather than by the order in which the conversation happened. Select the most appropriate document style automatically, announce that choice in Chinese, and continue without blocking for confirmation.

## 1. Classify Before Editing

Use the following evidence, in order:

1. A user-requested style overrides all other signals.
2. An existing document declaration or established structure takes precedence over reclassification.
3. Otherwise infer from source, boundary, and update model:

| Observable evidence | Select | Typical output |
| --- | --- | --- |
| Paper, book, chapter, formula, figure, citation, or source section | 论文阅读笔记 | Source-grounded study notes |
| Repository, entry point, module, call graph, data flow, configuration, or runtime path | 代码流程文档 | Maintainer-facing system or pipeline guide |
| Dates, tasks, questions, decisions, and recurring additions | 持续知识记录 | Topic pages plus append-only work log |
| Other technical explanation or procedure | 通用技术文档 | Audience- and task-oriented guide |

When evidence is mixed, choose the dominant lifecycle and state the ambiguity. Do not stop merely to request confirmation unless the user asks for a choice.

## 2. Announce the Choice in Chinese

Before reading deeply or writing, state:

```text
我将使用“<文档类型>”模式，以“<处理方式>”整理文档。

选择原因：
- <observable evidence>
- <boundary and audience>

本次预计更新：
- <scope>

本次不会：
- <non-goal>
```

Use these user-facing names: `论文阅读笔记`, `代码流程文档`, `持续知识记录`, and `通用技术文档`. Use these processing names: `结构发现`, `增量记录`, `综合整理`, `可读性审查`, and `归纳整理`. Do not expose internal routing fields or raw key-value selectors. Continue immediately after the notice. If the user later requests a different type, switch explicitly and explain what existing content will remain unchanged.

## 3. Choose the Processing Action

- **结构发现**: inspect the source and propose a bounded outline before drafting. Use for codebases and unfamiliar material.
- **增量记录**: capture new evidence, questions, decisions, or events without rewriting the entire document.
- **综合整理**: rebuild the canonical document around concepts, causality, data flow, or reader tasks; never append a conversation transcript.
- **可读性审查**: inspect an existing document and make a concrete reorder/rewrite proposal, then apply only approved paths.
- **归纳整理**: promote durable conclusions from long-running records into topic pages, decisions, glossary entries, and indexes while preserving the raw log.

Do not use a full-document rewrite for every question. During an active investigation, record small evidence items first and synthesize at a natural checkpoint: end of a section, end of a task, before sharing, or when the current draft becomes difficult to navigate.

## 4. Evidence and Annotation Contract

Separate claims by status:

```markdown
> **原文事实**：来源明确陈述的内容。

> **代码证据**：由具体文件、符号或配置直接确认的行为。

> **我的理解**：基于事实的解释或推导。

> **概念补充**：为了理解主线而补充的背景知识。

> **待确认**：当前材料不足以可靠确认的内容。
```

Attach a source anchor when one exists: section/page/figure for publications, or repository-relative path and line/symbol for code. Do not convert a plausible name, example, or assumption into a verified fact. Keep explanatory callouts near the concept they explain; move lengthy background to a dedicated concept section or appendix.

## 5. Capture Without Losing the Main Line

During conversation-driven work:

- Record the question, concise answer, source anchor, and confidence separately from the canonical narrative.
- Place a question into the section it clarifies during synthesis, not where it was asked.
- Keep unresolved questions visible; do not silently fill them with guesses.
- Preserve a raw work log when the material is unbounded. Do not delete it merely because a conclusion was promoted elsewhere.
- Mark superseded conclusions explicitly instead of rewriting history without explanation.

## 6. Synthesis Rules

The canonical document must:

- begin with purpose, scope, audience, and a concise overview;
- introduce prerequisites and terminology before relying on them;
- present claims before details and explain why each section matters;
- follow a stable order such as problem -> inputs/outputs -> mechanism -> evidence -> limits, or entry -> data flow -> modules -> runtime behavior for a pipeline;
- distinguish facts, interpretations, examples, and unresolved items;
- use one concept per section and avoid duplicate explanations;
- link to source locations and related sections;
- end with limitations, open questions, and a compact summary when useful.

Do not preserve conversational phrases such as “刚才我们讨论过” in the canonical document. Do not invent commands, paths, metrics, interfaces, or project-specific facts to make a document look complete.

## 7. Unbounded Documents

Never force an infinite work or learning record into one ever-growing file. Prefer this layout:

```text
knowledge/
├── index.md
├── topics/
├── decisions.md
├── open-questions.md
├── glossary.md
└── worklog/YYYY-MM.md
```

Append events to the dated work log. During `归纳整理`, promote only durable and reusable knowledge to topic pages, decisions, glossary, and the index. Preserve links back to the source log. Tell the user when content has crossed from temporary notes into maintainable knowledge and a compaction pass is warranted.

## 8. Profile-Specific Routing

Read [references/document-profiles.md](references/document-profiles.md) for the selected document type. Keep the main Skill workflow stable; load only the relevant profile details. If a document combines types, choose one primary lifecycle and treat the other as a clearly labeled secondary section or companion document.

## 9. Safe Editing and Completion

Before writing, show exact target paths, preserved content, and the reason for each change. Merge existing documentation; do not replace it wholesale. Do not expand into unrelated code, dependency, CI, or repository refactors. After editing, report the selected document type, processing action, changed paths, source gaps, and validation performed.
