# Agent instructions

Before changing any file in this repository, read
[`docs/implementation-workboard.md`](docs/implementation-workboard.md) in full.

The workboard is the source of truth for:

- current implementation stage and approved product direction;
- task dependencies, ownership, and status;
- file boundaries for parallel work;
- required verification and acceptance criteria;
- handoffs, blockers, decisions, and progress history.

Every agent must claim a ready task in the workboard before implementation and
must update the task row and progress log before ending its work. Do not begin a
task whose dependencies are incomplete. Do not silently expand a task's scope.

## graphify

This project has a knowledge graph in `graphify-out/` for token-efficient
navigation across code, documentation, architecture, and file relationships.
The graph is a retrieval map, not a replacement for source files, accepted ADRs,
or the mandatory full workboard read above.

When `graphify-out/graph.json` exists:

- For codebase, architecture, dependency, planning, or review questions, query
  the graph before broad repository searches or loading many files. Start with
  `graphify query "<focused terms>" --budget 1000`; normally keep the budget
  between 800 and 1,500 tokens.
- Prefer exact concepts from the graph's vocabulary. Avoid ambiguous product
  symbols such as `Budget` or `Query` when a more specific concept is available.
  Use `graphify explain "<concept>"` for focused context and
  `graphify path "<A>" "<B>"` to trace a relationship.
- Inspect only the source files and locations returned by the graph, then widen
  the search only when the evidence is incomplete. Treat `INFERRED` and
  `AMBIGUOUS` edges as hypotheses and verify them in the referenced source.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when
  query, path, and explain do not provide enough context. If a generated wiki
  exists, use its index for broad navigation before raw source browsing.
- When delegating work, give each agent the relevant graph slice plus only the
  necessary source files. Do not preload the full repository into every agent's
  context.
- Dirty generated files under `graphify-out/` are expected and are not a reason
  to skip Graphify. Skip it only when the task concerns stale/incorrect graph
  output or the user explicitly asks not to use it.
- After modifying code, run `graphify update .` to refresh AST-derived graph
  data. Documentation and image changes may require a semantic Graphify update;
  record stale graph risk rather than presenting old relationships as current.

When the user explicitly invokes `/graphify`, read and follow the installed
`graphify` skill before taking other task actions.

## Frontend design skill requirement

Every agent whose task changes or reviews frontend UI structure, visual design,
interaction patterns, responsive behavior, accessibility, or user experience
must use the `ui-ux-pro-max` skill. The agent must read that skill's `SKILL.md`
before making design decisions or changing UI files, follow its applicable
design-system/search workflow, and record the skill-guided checks and results in
the workboard verification entry. This requirement applies to implementation,
refactoring, and UI/UX review work; it does not apply to purely non-visual API,
database, infrastructure, or frontend data-client work.

If these instructions conflict with a direct user instruction, follow the user
instruction and record the exception in the workboard progress log.
