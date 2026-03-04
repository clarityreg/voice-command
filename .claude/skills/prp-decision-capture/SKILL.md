---
name: capturing-architecture-decisions
description: "Detects significant architectural decisions — new API endpoints, database schema changes, dependency additions, new services/models/middleware — and offers to capture them as Architecture Decision Records in Obsidian. Triggers after implementation of routes, migrations, new dependencies in package.json/pyproject.toml, or new structural files (services, models, middleware, schemas)."
---

# Architecture Decision Capture

After the user makes a significant architectural decision during implementation, offer to capture it as an Architecture Decision Record (ADR) in the Obsidian vault.

## When to trigger

Activate when the user has **finished implementing** (not just started) something that involves ANY of these signals:

### Strong signals (always offer)
- **New API endpoint/route**: Created a new route file, added a new path in `urls.py`, `router.*`, or route handler
- **Database schema change**: Created or modified a migration file, added a new model/entity
- **New dependency**: Added a package to `package.json`, `pyproject.toml`, `Cargo.toml`, `requirements.txt`, or `go.mod`
- **New service/middleware**: Created a new file in a `services/`, `middleware/`, or `providers/` directory

### Weak signals (only offer if combined with other changes)
- New utility/helper file
- Configuration changes (`settings.py`, environment variables)
- New test fixtures or factories

### Do NOT trigger on
- Bug fixes that don't change architecture
- Refactoring that preserves behavior
- Documentation changes
- Test-only changes
- Style/formatting changes
- Dependency version bumps (patch/minor)

## How to offer

After the implementation is complete and validated, say:

> You just added **[concise description of what was added]**. Want to capture this decision in Obsidian? I'll document the context, alternatives considered, and trade-offs.

If the user says **yes** (or equivalent):

1. Write an ADR note to the Obsidian vault at:
   `/Users/chidionyejuruwa/obsidian_vaults/coding/02 - Projects/PRP-framework/`

2. Use this ADR format:

```markdown
---
tags: [adr, <topic-tags>]
created: <YYYY-MM-DD>
parent: "[[PRP Framework]]"
status: accepted
---

# ADR: <Title of Decision>

## Context

<What problem or requirement led to this decision? 2-3 sentences.>

## Decision

<What was decided and implemented? Be specific — mention files, patterns, libraries.>

## Alternatives Considered

<What other approaches were evaluated? Why were they rejected? Use a bullet list.>

## Consequences

### Positive
- <benefit 1>
- <benefit 2>

### Negative / Trade-offs
- <trade-off 1>
- <risk or limitation>

### Follow-up
- <anything that should be done next as a result of this decision>
```

3. Generate the filename in Title Case (e.g., `ADR JWT Authentication Strategy.md`)

4. Confirm with the file path after writing.

If the user says **no**: Do nothing. Do not nag or ask again for the same decision.

## Rules

- **Once per decision** — do not re-offer for the same architectural change in the same session.
- **After implementation, not during** — wait until the code is written and working before offering.
- **Be specific** — name the actual thing that was added, not a vague "architectural change."
- **Infer from conversation** — you have the full context of what was discussed and why. Use it to pre-fill the ADR content, especially the "Alternatives Considered" section from any discussion that happened.
- **Brief prompt** — the offer itself should be one sentence. The detail goes into the ADR.
