---
description: Explain code by tracing control flow, data flow, and design patterns
argument-hint: <file-or-function>
---

# Code Explanation

Explain the target code so the reader **understands** it — not just what it does, but *why* it was written this way.

## Phase 1: LOCATE

Parse `$ARGUMENTS`:
- File path (e.g., `backend/apps/auth/views.py`)
- Function or class name (e.g., `authenticate_user`)
- "this file" (use the most recently discussed file)
- Vague description (e.g., "the auth middleware") — search for it

If the target is ambiguous, list candidates and ask the user to pick one.

Read the target file. If a specific function/class was named, focus on that unit but still read the full file for context.

---

## Phase 2: MAP

Identify the entry point and trace its dependency chain:

1. **Imports** — What does this code pull in? Why those dependencies?
2. **Callers** — What invokes this code? (Search with `Grep` for references)
3. **Callees** — What does this code call? Follow one level deep.

Present a simple **call graph** (text-based, not a diagram):

```
caller_a() -> TARGET_FUNCTION() -> helper_b()
                                -> external_api.fetch()
caller_c() -> TARGET_FUNCTION()
```

---

## Phase 3: WALK THROUGH

Line-by-line explanation of the **control flow**. For each significant block:

- **What** it does (one sentence)
- **Why** it exists — what problem does this block solve?
- **Pattern** — name any design pattern used (e.g., "this is the guard clause pattern", "this uses dependency injection", "this is a decorator / factory / strategy")
- **Trade-off** — if there's an obvious alternative approach, mention why this one was likely chosen

Skip trivial lines (imports, blank lines). Focus on logic.

---

## Phase 4: DATA FLOW

Trace how data transforms through the code:

1. **Input** — What goes in? (parameters, globals, environment, I/O)
2. **Transformations** — What operations are applied? In what order?
3. **Output** — What comes out? (return values, side effects, mutations)
4. **Mutations** — Does this code mutate anything outside its scope? (database writes, global state, file I/O)

Use a simple flow notation:

```
request.body -> validate(body) -> cleaned_data -> db.save(cleaned_data) -> response(201)
                                                                        |
                                                            side effect: audit_log.write()
```

---

## Phase 5: CONTEXT

Zoom out:

1. **Role in the system** — Where does this fit in the overall architecture? (e.g., "this is the authentication middleware that sits between the router and all protected endpoints")
2. **What depends on it** — What would break if you deleted this?
3. **What it depends on** — What external contracts does it rely on? (database schema, API responses, config values)
4. **Change risk** — How safe is this code to modify? (isolated vs. tightly coupled)

---

## Phase 6: LEARNING NOTES

Wrap up with actionable learning pointers:

1. **Key concepts** — List 2-4 concepts worth researching further (e.g., "This uses Python's `__init_subclass__` hook — see PEP 487")
2. **Related files** — Suggest 2-3 files to read next to deepen understanding of this area
3. **Questions to ask** — Pose 1-2 questions the reader should be able to answer after reading (self-test)

---

## Output Format

**Conversational explanation** — write as if you're pair programming and the user asked "walk me through this code." Use code snippets inline to reference specific lines. Do NOT produce a formal artifact or save to a file.

Keep the tone educational but efficient. No fluff, no disclaimers.
