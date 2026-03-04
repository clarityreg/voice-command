---
description: Audit and optimize CLAUDE.md — move reference to docs/, prune unused
argument-hint:
---

# CLAUDE.md Optimizer

Audit the project's CLAUDE.md, separate behavioral directives (which must stay in context) from reference documentation (which can be looked up on-demand), and prune sections for features that aren't installed.

---

## Terminology

- **PROJECT zone**: Everything OUTSIDE the `<!-- PRP-FRAMEWORK-START -->` / `<!-- PRP-FRAMEWORK-END -->` markers. This is the user's own content — **never touch it**.
- **PRP zone**: Everything BETWEEN those markers. This is what we optimize.
- **Behavioral directive**: A rule, constraint, or workflow that Claude MUST follow (contains MUST/NEVER/ALWAYS/DO NOT, or describes a workflow sequence).
- **Reference documentation**: Tables, directory trees, code blocks, API examples, configuration schemas — things Claude can look up from `.claude/docs/` when needed.

---

## Phase 1: SCAN

### 1.1 Read CLAUDE.md

Read the project's `CLAUDE.md` from the repository root.

### 1.2 Locate zones

Look for the PRP markers:

```
<!-- PRP-FRAMEWORK-START -->
...PRP content...
<!-- PRP-FRAMEWORK-END -->
```

- If markers are NOT found, check if this is the PRP framework repo itself (look for `.claude/commands/prp-core/prp-claudemd.md`). If so, report:
  ```
  This appears to be the PRP framework repo itself.
  The framework CLAUDE.md is the source template — it doesn't use PRP markers.
  Run /prp-claudemd on a TARGET project that has PRP installed.
  ```
  Stop here.

- If markers are found, extract the PRP zone content.

### 1.3 Parse sections

Split the PRP zone into sections by `##` headings. Track each section's:
- Heading text
- Line count
- Content type (prose, table, code block, tree, mixed)

---

## Phase 2: CLASSIFY

Label each section using these rules (applied in priority order):

### Classification Rules

| Priority | Condition | Label | Reason |
|----------|-----------|-------|--------|
| 1 | Outside PRP markers | `PROTECTED` | Project zone — never touched |
| 2 | Feature not installed (see Phase 3) | `PRUNE` | Dead weight — feature isn't used |
| 3 | Rule enforced by a hook in settings.json or `.claude/hooks/generated/` | `REMOVE` | Redundant — already mechanically enforced |
| 4 | Content is primarily a table, directory tree, code block, or API example | `MOVE` | Reference material → `.claude/docs/` |
| 5 | Everything else | `KEEP` | Behavioral directive — stays in CLAUDE.md |

### Always KEEP (never move or prune)

These sections contain behavioral directives that Claude needs in-context:

- **Key Principles** — core behavioral rules
- **Fallback Behavior** — graceful degradation rules
- **Task Status Flow** — workflow constraint (only one task "doing" at a time)
- **Quick Start** workflows — step-by-step behavioral sequences
- Any section with `MUST`, `NEVER`, `ALWAYS`, `DO NOT` behavioral overrides
- The framework title and description (first 2-3 lines)

### Always MOVE (reference material)

- **Command Reference** table → `commands-reference.md`
- **Project Settings** JSON block + notes → `project-settings.md`
- **Directory Structure** tree → `directory-structure.md`
- **Pre-commit Hooks** table + skipping instructions → `pre-commit-hooks.md`
- **Auto-Triggered Skills** table + design principles → `skills-reference.md`
- **Archon MCP Integration** API examples → `archon-integration.md` (only if Archon configured)
- **Observability Dashboard** architecture + events → `observability.md` (only if installed)
- **Ralph Loop** usage examples → `ralph-loop.md` (only if installed)

---

## Phase 3: DETECT USAGE

Check the filesystem to determine which features are actually installed. This informs PRUNE decisions.

```bash
# Archon / Plane integration
cat .claude/prp-settings.json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
plane = d.get('plane', {})
has_plane = bool(plane.get('workspace_slug') and plane.get('project_id'))
print(f'archon_configured={has_plane}')
" 2>/dev/null || echo "archon_configured=false"

# Ralph loop
[ -d "ralph" ] && echo "ralph_installed=true" || echo "ralph_installed=false"

# Observability dashboard
[ -d "apps/server" ] && echo "observability_installed=true" || echo "observability_installed=false"

# Pre-commit
[ -f ".pre-commit-config.yaml" ] && echo "precommit_installed=true" || echo "precommit_installed=false"

# Skills
[ -d ".claude/skills" ] && echo "skills_installed=true" || echo "skills_installed=false"

# Generated hooks (from /prp-hookify)
ls .claude/hooks/generated/*.py 2>/dev/null | wc -l | tr -d ' '
```

For each feature NOT installed, mark its documentation sections as `PRUNE`.

---

## Phase 4: PRESENT

Show the user a table of ALL PRP sections with proposed actions:

```
/prp-claudemd — CLAUDE.md Audit
═══════════════════════════════════════════════════════════════

Current CLAUDE.md: {total_lines} lines (PROJECT: {project_lines}, PRP: {prp_lines})

PRP Section Analysis:
┌───┬──────────────────────────────┬───────┬────────┬─────────────────────────────────┐
│ # │ Section                      │ Lines │ Action │ Reason                          │
├───┼──────────────────────────────┼───────┼────────┼─────────────────────────────────┤
│ 1 │ Command Reference            │   28  │ MOVE   │ Table → commands-reference.md    │
│ 2 │ Project Settings             │   25  │ MOVE   │ JSON block → project-settings.md │
│ 3 │ Archon MCP Integration       │   45  │ PRUNE  │ Archon not configured            │
│ 4 │ Ralph Loop                   │   20  │ PRUNE  │ ralph/ not installed             │
│ 5 │ Directory Structure          │   40  │ MOVE   │ Tree → directory-structure.md    │
│ 6 │ Key Principles               │    8  │ KEEP   │ Behavioral directives            │
│ 7 │ Quick Start                  │   20  │ KEEP   │ Workflow sequences               │
│ ...│                              │       │        │                                 │
└───┴──────────────────────────────┴───────┴────────┴─────────────────────────────────┘

Estimated savings: ~{saved_lines} lines removed from CLAUDE.md context

Proceed? You can override specific items (e.g., "keep #3", "move #6").
```

Wait for user confirmation. Apply any overrides they specify.

---

## Phase 5: EXECUTE

### 5.1 Create `.claude/docs/` directory

```bash
mkdir -p .claude/docs
```

### 5.2 Write reference docs

For each section classified as `MOVE`, create the corresponding file in `.claude/docs/`:

| Target File | Source Section |
|-------------|---------------|
| `commands-reference.md` | Command Reference table |
| `project-settings.md` | Project Settings JSON + config notes |
| `directory-structure.md` | Directory Structure tree |
| `pre-commit-hooks.md` | Pre-commit Hooks table + skipping |
| `skills-reference.md` | Skills table + design principles |
| `archon-integration.md` | Archon API examples (if configured) |
| `observability.md` | Observability architecture + events (if installed) |
| `ralph-loop.md` | Ralph usage examples (if installed) |

Each file should have:
```markdown
# {Section Title}

> Moved from CLAUDE.md by `/prp-claudemd`. Reference material — Claude reads this on-demand.

{original section content}
```

### 5.3 Rewrite the PRP zone

Replace the content between `<!-- PRP-FRAMEWORK-START -->` and `<!-- PRP-FRAMEWORK-END -->` with:

1. **Framework title** and description (kept from original)
2. All `KEEP` sections (behavioral directives, workflows, principles)
3. A **Reference Documentation** pointer section at the end:

```markdown
## Reference Documentation

Detailed reference docs are in `.claude/docs/`:

| File | Contents |
|------|----------|
| `commands-reference.md` | Full command table with arguments |
| `project-settings.md` | Settings JSON schema and configuration |
| `directory-structure.md` | Complete directory tree |
| ... | ... |

Use `/prp-primer` to load full project context including these docs.
```

4. Sections classified as `PRUNE` are simply removed (not moved to docs/).
5. Sections classified as `REMOVE` are simply removed (enforced by hooks).

---

## Phase 6: VERIFY (Second Pass)

### 6.1 Re-read optimized CLAUDE.md

Read the file back and check for:
- Orphaned headers (## with no content)
- Dangling references to moved sections (e.g., "see the Command Reference table above")
- Broken markdown (unclosed code blocks, malformed tables)
- Empty PRP zone

Fix any issues found.

### 6.2 Validate docs files

For each file in `.claude/docs/`:
- Confirm it exists and is non-empty
- Check for valid markdown structure

### 6.3 Report metrics

```
/prp-claudemd — Optimization Complete
═══════════════════════════════════════

Before:
  CLAUDE.md total:     {before_total} lines
  PRP zone:            {before_prp} lines

After:
  CLAUDE.md total:     {after_total} lines
  PRP zone:            {after_prp} lines
  Reduction:           {reduction}% ({saved} lines)

Actions taken:
  KEEP (in CLAUDE.md):  {keep_count} sections
  MOVE (to docs/):      {move_count} sections → {file_count} files
  PRUNE (removed):      {prune_count} sections (features not installed)
  REMOVE (hookified):   {remove_count} sections

Reference docs created:
  .claude/docs/commands-reference.md
  .claude/docs/project-settings.md
  .claude/docs/directory-structure.md
  ...

To restore: git checkout CLAUDE.md
To re-optimize after changes: /prp-claudemd
```

---

## Edge Cases

### No PRP markers found (non-PRP project)
Report that this command requires a PRP-installed project with markers. Suggest running `install-prp.sh` first.

### PRP framework repo itself
The framework's own CLAUDE.md is the source template. It doesn't have markers. Report this and stop.

### All sections classified as KEEP
Report that CLAUDE.md is already lean. No changes needed.

### User wants to undo
Point to `git checkout CLAUDE.md` to restore the original.

---

## When to Use

Use `/prp-claudemd` when:
- CLAUDE.md is bloated (300+ lines of PRP content)
- Context window pressure is a concern
- After running `/prp-hookify` (some sections may now be redundant)
- After uninstalling features (Ralph, Observability, etc.)
- Periodically to keep CLAUDE.md lean
