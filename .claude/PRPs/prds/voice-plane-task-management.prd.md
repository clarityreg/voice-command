# PRD: Voice-Driven Plane Task Management

**Status**: Draft
**Author**: Claude + Chidi
**Created**: 2026-03-05
**Last Updated**: 2026-03-05

---

## Problem Statement

### The Problem
Managing work items across multiple Plane projects (clients + internal) requires switching to a browser, navigating to the right project, filling out forms, and updating statuses. This context-switching breaks flow, especially during meetings, commutes, or focused work sessions. The Clarity voice command app already has a working voice pipeline and basic Plane integration (read-only notifications + single-project issue creation), but it can't yet manage tasks across multiple projects or update existing work items by voice.

### Evidence
- Existing `PlaneClient` in `integrations/plane.py` only supports creating issues in a single hardcoded project
- `plane_notifier.py` polls a single project for assigned issues (read-only)
- The voice intent classifier has `CREATE_ISSUE` but it only references local triage items, not arbitrary Plane tasks
- No voice intents exist for completing, updating, or querying Plane work items
- Multiple Plane projects (clients) require project selection, which the current single-project config doesn't support

### Impact
- **Users affected**: Primary user (Chidi) managing multiple client projects
- **Frequency**: Multiple times daily - creating tasks during calls, completing tasks after work, quick status checks
- **Severity**: Medium - workaround exists (manual browser) but it's friction-heavy

---

## Proposed Solution

### Overview
Extend the Clarity voice command system with Plane-aware intents that support multi-project task management. Voice commands will be processed into structured actions, displayed as visual confirmation cards in the UI, and only executed after explicit user approval (click/tap). This creates a safe "voice-to-preview-to-confirm" workflow.

### Architecture Decision: Hybrid - Regex First, AI Fallback

The system uses a **two-tier intent classification** approach:

1. **Tier 1: Regex keyword matching (fast, offline)** - Handles well-structured commands like "create task in acme: update docs". Returns instantly with high confidence.
2. **Tier 2: Local LLM fallback (for ambiguous input)** - When regex returns UNKNOWN or low confidence, a local LLM (Ollama/llama.cpp or Whisper-derived model) interprets the natural language. This handles messy voice transcripts like "uh add something to the acme project about updating the documentation".
3. **Trainable client vocabulary** - Users register project names and aliases (e.g., "Acme Corp" = "acme", "clarity reg" = "clarity-regulatory"). The system learns these names and uses fuzzy matching + the AI layer to resolve spoken client names to projects, even when voice recognition garbles them.
4. **Direct Plane API for execution** - Once intent is resolved, the app calls the Plane REST API directly (not through Claude Code). Claude Code is a dev-time tool; the production app talks to Plane via `httpx`.
5. **Where Claude Code fits** - Claude Code (with the Plane MCP) is useful during *development* to test API calls and explore endpoints. The existing `FIX_ITEM` flow already uses Claude CLI as a subprocess for code patches - that pattern stays separate.

### Key Hypotheses

| Hypothesis | Test Method | Success Criteria |
|------------|-------------|------------------|
| Users can reliably name projects by voice | Test with 5 voice commands using project nicknames | 80%+ correct project resolution |
| Visual confirmation prevents accidental actions | Track confirm vs reject ratio over 2 weeks | <5% rejected actions (indicates high-confidence commands) |
| Voice task creation is faster than browser | Time both workflows for 10 task creations | Voice+confirm <15 seconds vs browser ~45 seconds |
| Multi-project voice commands don't feel complex | User satisfaction after 1 week | No regression to browser for simple tasks |

### What We're NOT Building
- Voice-driven task editing (changing descriptions, adding comments) - v2
- Voice assignment to other team members - v2
- Mobile-optimized touch confirmation - v2 (mouse/desktop first)
- Cloud-only LLM (must work with local models for privacy and speed)
- Batch operations ("complete all tasks in project X") - too risky for voice
- Voice-driven sprint/cycle management - out of scope

---

## User Context

### Primary Users
**Project Manager / Developer (Chidi)**
- Goal: Manage work items across multiple client projects without leaving current context
- Pain: Context-switching to browser, navigating to correct project, form-filling
- Success: "Create task in Acme project: update API documentation" works end-to-end in <15 seconds

### User Stories
- As a user, I want to say "create task in [project]: [title]" so that I can capture work items without opening Plane
- As a user, I want to say "complete task [identifier]" so that I can mark work done immediately
- As a user, I want to see a visual preview card of the action before it executes so that I can catch mistakes
- As a user, I want to say "show my tasks" or "show tasks in [project]" so that I can get a quick overview
- As a user, I want to accept or reject proposed actions with a mouse click so that voice errors don't cause problems
- As a user, I want to use project nicknames (not UUIDs) so that voice commands feel natural

---

## Technical Approach

### Architecture

```
Voice Input (speech-to-text)
    |
Intent Classifier (regex, extended with Plane patterns)
    |
    v
Command Handler (new Plane handlers)
    |
    v
Action Preview (returned to frontend as pending_action)
    |
    v
Frontend Confirmation Card (visual preview with Accept/Reject buttons)
    |
    v (on Accept)
Plane API Call (direct HTTP via extended PlaneClient)
    |
    v
Success/Failure Response (TTS + visual feedback)
```

### Key Technical Components

#### 1. Multi-Project Configuration
- Extend settings to store a project registry: `{ "acme": { "id": "uuid", "slug": "acme-corp" }, ... }`
- Support project aliases/nicknames for voice matching (e.g., "acme" matches "Acme Corp Website Redesign")
- Store in backend config (settings page already exists)

#### 2. New Voice Intents
```python
# New intent types
PLANE_CREATE_TASK = "plane_create_task"      # "create task in acme: update docs"
PLANE_COMPLETE_TASK = "plane_complete_task"   # "complete task ACME-42"
PLANE_LIST_TASKS = "plane_list_tasks"        # "show my tasks" / "show tasks in acme"
PLANE_TASK_STATUS = "plane_task_status"       # "what's the status of ACME-42"

# New patterns
(r"(create|add|new)\s+(task|work item|ticket)\s+(in|for)\s+(\w+)", PLANE_CREATE_TASK),
(r"(complete|finish|done|close|resolve)\s+(task|ticket|item)\s+(\w+-\d+|\d+)", PLANE_COMPLETE_TASK),
(r"(show|list|what are)\s+(my\s+)?(tasks|work items|tickets)(\s+in\s+\w+)?", PLANE_LIST_TASKS),
```

#### 3. Confirmation Card System (Frontend)
```
+------------------------------------------+
| [Plane Icon] Create Task                 |
|                                          |
| Project: Acme Corp                       |
| Title: "Update API documentation"        |
| Priority: None (default)                 |
| State: Backlog                           |
|                                          |
|     [ Reject ]          [ Confirm ]      |
+------------------------------------------+
```
- Card appears in a fixed overlay area (like the existing `lastResponse` toast but richer)
- Auto-dismiss after 30 seconds (defaults to reject)
- Keyboard shortcut: Enter to confirm, Esc to reject

#### 4. Extended PlaneClient
- Add methods: `list_projects()`, `list_work_items()`, `update_work_item()`, `get_states()`
- Support multiple projects (remove single-project assumption)
- Cache project list and states to avoid repeated API calls

#### 5. Backend API Endpoints
```
POST /api/voice/process          (existing - returns pending_action for Plane commands)
POST /api/plane/confirm-action   (new - executes a previewed action)
GET  /api/plane/projects         (new - returns configured projects with aliases)
GET  /api/plane/tasks            (new - returns tasks, filterable by project)
```

### Dependencies
- Plane API v1 (already integrated)
- Existing voice pipeline (VoiceButton, useVoice, intent classifier)
- Existing WebSocket for real-time feedback
- Existing settings page for project configuration

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Voice misrecognizes project name | High | Medium | Fuzzy matching + confirmation card prevents wrong-project actions |
| Voice misrecognizes task title | Medium | Low | Confirmation card shows exact text; user can reject |
| Plane API rate limiting | Low | Medium | Cache project/state lists; batch where possible |
| User skips confirmation (habit) | Low | High | Auto-dismiss defaults to reject (safe default) |
| Task identifier ambiguity (numbers vs project-IDs) | Medium | Medium | Require project prefix format (e.g., "ACME-42") |

---

## Success Metrics

### Primary Metrics
- Task creation time: ~45s (browser) -> <15s (voice + confirm)
- Daily voice-created tasks: 0 -> 3+ per day
- Confirmation acceptance rate: >90% (indicates voice accuracy)

### Validation Approach
- Track confirm/reject ratio in backend logs
- Compare task creation timestamps (voice vs manual) over 2 weeks
- User feedback after 1 week of usage

---

## Implementation Phases

### Phase 1: Foundation - Multi-Project PlaneClient + Confirmation UI (MVP)
- Extend `PlaneClient` with `list_projects()`, `list_work_items()`, `update_work_item()`, `get_states()`
- Add project registry to settings (settings page UI for adding projects with aliases)
- Build confirmation card component in frontend
- Add `POST /api/plane/confirm-action` endpoint
- Wire confirmation flow: voice -> preview -> confirm -> execute

### Phase 2: Voice Intents - Create & Complete Tasks
- Add `PLANE_CREATE_TASK`, `PLANE_COMPLETE_TASK`, `PLANE_LIST_TASKS` intent patterns
- Add parameter extraction (project name, task title, task identifier)
- Implement fuzzy project name matching (voice says "acme", matches "Acme Corp")
- Add command handlers that return `pending_action` payloads
- TTS responses for success/failure/ambiguity

### Phase 3: Task Querying & Status
- "Show my tasks" / "Show tasks in [project]" - returns spoken summary + visual list
- "What's the status of ACME-42" - returns task details via TTS
- Task list view in UI (lightweight, not replacing Plane UI)

### Phase 4: Polish & Safety
- Add undo support ("undo last action" within 30-second window)
- Improve fuzzy matching with Levenshtein distance for project names
- Add voice feedback for ambiguous commands ("Did you mean project Acme or project Alpha?")
- Keyboard shortcuts for confirmation cards (Enter/Esc)
- Desktop notification when confirmation card is waiting

---

## Open Questions
- [ ] How many Plane projects are actively managed? (determines if a flat list or search is needed) 32
- [ ] Are there preferred project aliases already in use? (e.g., do you call "Acme Corp" just "acme"?) no aliases
- [ ] Should completed tasks update the state to a specific state name, or always the "Done" equivalent? done
- [ ] Is there a need for priority setting via voice? (e.g., "create urgent task in acme: fix login") yes
- [ ] Should the confirmation card show on desktop sidebar or as a modal overlay? modal overlay

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-05 | Direct Plane API, not Claude Code at runtime | Claude Code is a CLI for code editing; Plane API is simpler, faster, more reliable for CRUD ops |
| 2026-03-05 | Confirmation card required for all mutating actions | Safety-first: voice recognition errors must not cause unintended side effects |
| 2026-03-05 | Hybrid classifier: regex first, local LLM fallback | Fast for structured commands, AI handles natural speech and client name resolution |
| 2026-03-05 | Desktop/mouse first, mobile later | Per user request; touch confirmation is v2 |
| 2026-03-05 | Project aliases for voice matching | UUIDs and long project names are not voice-friendly |

---
*This PRD is ready for planning with `/prp-plan`*
