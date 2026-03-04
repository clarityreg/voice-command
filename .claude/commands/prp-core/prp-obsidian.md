---
description: Add a note to the Obsidian coding vault
argument-hint: [content or topic]
---

# Add to Obsidian

Add a new note to the Obsidian coding vault at `/Users/chidionyejuruwa/obsidian_vaults/coding/`.

## Phase 1: DISCOVER

List the numbered parent folders and their immediate subfolders:

```bash
find "/Users/chidionyejuruwa/obsidian_vaults/coding/" -maxdepth 2 -type d ! -name '.*' | sort
```

The vault follows a modified PARA structure:

| Folder | Purpose |
|--------|---------|
| `00 - Inbox` | Quick capture — default landing spot |
| `01 - Daily` | One note per day |
| `02 - Projects` | Active work with a deadline (has subfolders per project) |
| `03 - Areas` | Ongoing responsibilities, no end date |
| `04 - Resources` | Reference material and evergreen notes (has subfolders by topic) |
| `05 - System` | Archive, agents, scripts, attachments |

## Phase 2: SELECT DESTINATION

Use `AskUserQuestion` to present the numbered parent folders (00 through 05) as options.

If the user picks a folder that has subfolders (like `02 - Projects` or `04 - Resources`), follow up with a second question listing the subfolders within it.

**Always include "Create new subfolder" as an option** when the selected parent has existing subfolders. If selected, ask for the subfolder name and create it.

If the user doesn't specify and the content doesn't clearly belong somewhere, default to `00 - Inbox`.

## Phase 3: GATHER CONTENT

If `$ARGUMENTS` already contains the note content or topic, use that. Otherwise, ask the user what they want the note to contain. They will write free-form text.

## Phase 4: GENERATE TITLE

From the user's content, generate a concise, descriptive filename:
- Use **Title Case** with spaces (Obsidian handles spaces fine)
- No special characters except hyphens
- Keep it short but descriptive (3-6 words)
- Examples: `Git Rebase Workflow.md`, `JWT Auth Patterns.md`, `Django Signals Guide.md`

## Phase 5: WRITE NOTE

Create the `.md` file with proper Obsidian frontmatter:

```markdown
---
tags: [<relevant-tags>]
created: <YYYY-MM-DD>
parent: "[[<parent-note-if-applicable>]]"
---

# <Title>

<user's content, formatted with proper markdown>
```

**Frontmatter rules:**
- `tags`: 2-4 relevant lowercase tags inferred from the content
- `created`: today's date in `YYYY-MM-DD` format
- `parent`: a `[[wikilink]]` to the parent note if inside a project subfolder (e.g., `"[[PRP Framework]]"` for notes in `02 - Projects/PRP-framework/`). Omit for Inbox or top-level notes.
- Use Obsidian-flavored markdown: `[[wikilinks]]` for internal links, `> [!tip]` / `> [!warning]` for callouts

## Phase 6: CONFIRM

After writing, report:
- Full path of the created file
- The title and tags chosen
- A reminder that the note will appear in Obsidian immediately
