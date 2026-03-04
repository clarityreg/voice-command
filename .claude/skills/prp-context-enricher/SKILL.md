---
name: enriching-session-context
description: "When the user begins working on a specific file or feature area, searches for related context: Obsidian notes in the PRP-framework project folder, recent coverage data, related PRP artifacts (PRDs, plans, investigations), and active Plane tasks. Surfaces a brief context summary once per topic area per session. Triggers when the user opens, reads, or starts discussing a specific area of the codebase."
---

# Session Context Enrichment

When the user starts working on a specific area of the codebase, proactively search for and surface related context from the project's knowledge base.

## When to trigger

Activate when the user **first engages** with a specific area of the codebase in a session. Engagement signals:

- User asks to read, edit, or explain a file in a specific domain area (e.g., auth, payments, API, frontend)
- User starts discussing a feature or module they want to work on
- User references a specific component, service, or system by name

**Extract topic keywords** from the file path and discussion. For example:
- `backend/apps/auth/views.py` -> keywords: `auth`, `authentication`, `login`, `views`
- "I need to fix the payment webhook" -> keywords: `payment`, `webhook`, `billing`
- `frontend/src/components/Dashboard.tsx` -> keywords: `dashboard`, `frontend`, `components`

## What to search for

Search these sources in parallel for matches against the topic keywords:

### 1. Obsidian notes

Search in `/Users/chidionyejuruwa/obsidian_vaults/coding/02 - Projects/PRP-framework/` for notes with matching keywords in their filename or content.

Use Glob to find files, then Grep to check content relevance. Only surface notes that are **clearly related** (keyword in title, or 2+ keyword matches in content).

### 2. PRP artifacts

Search in `.claude/PRPs/` for related artifacts:
- `prds/` — PRD documents mentioning the topic
- `plans/` — Implementation plans for the feature area
- `issues/` — Issue investigations related to the area

Use Glob and Grep to find matching files by name and content.

### 3. Coverage data

Check if `.claude/PRPs/coverage/latest.json` exists. If it does, look for coverage data related to the current file or module area.

### 4. Plane tasks (if configured)

If `.claude/prp-settings.json` has Plane configured (non-empty `workspace_slug` and `project_id`), check for tasks in "doing" or "todo" status related to the topic area. Use the Plane MCP tools if available, otherwise skip silently.

## How to present

After gathering context, present a **brief summary** (3-5 lines max):

> **Related context found:**
> - Obsidian: [[Note Title]] — <one-line summary of relevance>
> - Plan: `<plan-filename>` — <status or key detail>
> - Coverage: `<module>` at <X>% (target: <Y>%)
> - Plane: Task "<title>" in `<status>` status

Only include sections that have actual matches. If nothing is found, say nothing — do not report "no context found."

## Rules

- **Once per topic area per session** — if the user works on auth, surface auth context once. Do not repeat when they edit another auth file.
- **Track surfaced topics** internally — maintain a mental list of topic areas already enriched in this session.
- **Brief, not verbose** — the summary should be scannable in 5 seconds. Link to sources, don't reproduce them.
- **Non-blocking** — present the context and immediately continue with the user's actual request. Do not wait for acknowledgment.
- **Graceful degradation** — if any source is unavailable (no Obsidian notes, no coverage data, Plane not configured), skip it silently. Only surface what's available.
- **Don't trigger on PRP framework files** — when the user is working on the PRP framework itself (`.claude/` directory), this skill adds noise. Skip it for those paths.
