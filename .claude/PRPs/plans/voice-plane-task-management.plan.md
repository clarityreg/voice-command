# Implementation Plan: Voice-Driven Plane Task Management

**Created**: 2026-03-05
**Status**: Ready for Implementation
**PRD**: `.claude/PRPs/prds/voice-plane-task-management.prd.md`
**Archon Project ID**: Not created (Archon not configured)

---

## Overview

Extend the Clarity voice command system to create, complete, and query Plane work items across 32+ projects. Uses a hybrid intent classifier (regex first, local LLM fallback for natural speech) with trainable client name vocabulary. All mutating actions require visual confirmation via a modal overlay card before execution.

## User Stories

- As a user, I want to say "create task in [client name]: [title]" so I can capture work without opening Plane
- As a user, I want to say "complete task [identifier]" to mark work done immediately
- As a user, I want to say "show my tasks" or "show tasks in [project]" for a quick overview
- As a user, I want to train the system with my client names so voice recognition works naturally
- As a user, I want to see a confirmation card before any action executes so I can catch mistakes
- As a user, I want to set priority by voice (e.g., "create urgent task in acme: fix login")

## Success Criteria

- [ ] Can create tasks in any of 32+ Plane projects via voice
- [ ] Can complete/close tasks by identifier via voice
- [ ] Can list tasks filtered by project via voice
- [ ] All mutating actions show confirmation card with Accept/Reject
- [ ] Client name vocabulary is trainable via settings UI
- [ ] Fuzzy + AI matching resolves spoken client names to projects
- [ ] Priority settable via voice ("urgent", "high", "medium", "low")
- [ ] TTS speaks confirmation/success/error responses

---

## Mandatory Reading

Before implementation, read these files to understand patterns:

| File | Purpose | Key Lines |
|------|---------|-----------|
| `backend/src/clarity_backend/voice/intent.py` | Intent classifier pattern (regex + dataclass) | 26-63 |
| `backend/src/clarity_backend/voice/commands.py` | Command handler pattern (HANDLERS dict + templates) | 27-41, 287-301 |
| `backend/src/clarity_backend/voice/router.py` | Voice endpoint (classify -> execute -> response) | 28-36 |
| `backend/src/clarity_backend/integrations/plane.py` | Existing PlaneClient (httpx async) | 15-52 |
| `backend/src/clarity_backend/services/plane_notifier.py` | Plane API usage pattern + create_issue method | 46-121 |
| `backend/src/clarity_backend/settings/manager.py` | Settings persistence pattern (JSON file, masked secrets) | 16-76 |
| `src/hooks/useVoice.ts` | Voice state machine + handleResult flow | 82-95 |
| `src/components/VoiceButton.tsx` | Response toast pattern (lastResponse display) | 17-26 |
| `src/components/VocabularyEditor.tsx` | Custom vocabulary editor UI pattern | 6-66 |
| `src/lib/api.ts` | Frontend API helpers + TypeScript interfaces | 72-114 |
| `src/lib/wsClient.ts` | WebSocket message routing pattern | 63-103 |
| `src/app/settings/page.tsx` | Settings form layout and save pattern | 98-178 |
| `backend/tests/test_voice_intent.py` | Intent test pattern (class-organized, parametric) | 17-129 |

## Patterns to Follow

### Naming
- Backend modules: `snake_case.py` in feature directories
- Frontend components: `PascalCase.tsx` in `src/components/`
- API functions: `camelCase` in `src/lib/api.ts`
- Tests: `test_*.py` (backend), `*.test.ts` (frontend)

### Code Style
- Backend: async functions, `SessionDep` for DB, Pydantic models for request/response
- Frontend: `"use client"` components, `useState`/`useCallback` hooks, Tailwind classes
- API: `apiFetch<T>()` generic wrapper, typed interfaces

### Error Handling
- Backend: return error message in response dict, don't throw (see `commands.py:258`)
- Frontend: try/catch in async handlers, set error state (see `settings/page.tsx:64`)

### Testing
- Backend: `pytest` + `pytest-asyncio`, class-organized, test classification + handlers separately
- Frontend: `vitest` + `@testing-library/react`, mock hooks and APIs

---

## Implementation Tasks

### Phase 1: Backend Foundation - Extended PlaneClient + Project Registry

#### Task 1.1: Extend PlaneClient with Multi-Project API Methods
**Status**: todo

**Description**: Add `list_projects()`, `list_work_items()`, `update_work_item_state()`, and `get_states()` methods to the existing `PlaneClient`. Remove the single-project assumption — methods should accept `project_id` as a parameter.

**Files**:
- Modify: `backend/src/clarity_backend/integrations/plane.py` (extend class, lines 15-52)

**Details**:
```python
# New methods to add to PlaneClient:

async def list_projects(self) -> list[dict]:
    """GET /workspaces/{workspace}/projects/ — returns all projects."""

async def get_states(self, project_id: str) -> list[dict]:
    """GET /workspaces/{workspace}/projects/{project_id}/states/ — returns workflow states."""

async def list_work_items(self, project_id: str, assignees: str = "me", limit: int = 20) -> list[dict]:
    """GET /workspaces/{workspace}/projects/{project_id}/issues/ — filterable."""

async def update_work_item_state(self, project_id: str, issue_id: str, state_id: str) -> dict:
    """PATCH /workspaces/{workspace}/projects/{project_id}/issues/{issue_id}/ — update state."""

async def get_work_item_by_sequence(self, project_id: str, sequence_id: int) -> dict | None:
    """Search for issue by sequence_id (the human-readable number like ACME-42)."""
```

Also update `create_work_item()` to accept `project_id` as parameter (currently hardcoded in `__init__`).

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.integrations.plane import PlaneClient; print('OK')"
```

**Acceptance Criteria**:
- [ ] All methods are async, use httpx, handle errors gracefully
- [ ] `project_id` is a parameter, not hardcoded from config
- [ ] Existing `create_work_item` still works (backwards compatible)

---

#### Task 1.2: Project Registry in Settings
**Status**: todo

**Description**: Add a `plane_projects` field to the settings manager that stores a registry of projects with aliases for voice matching. Structure: `{ "alias": { "id": "uuid", "name": "Full Name", "identifier": "ACME" } }`. Also add a `plane_done_state_name` setting (default: "Done").

**Files**:
- Modify: `backend/src/clarity_backend/settings/manager.py` (add to DEFAULT_SETTINGS, lines 16-23)

**Details**:
```python
# Add to DEFAULT_SETTINGS:
"plane_projects": {},        # { alias: { id, name, identifier } }
"plane_done_state_name": "Done",
```

Add endpoint to sync projects from Plane API:
```python
@router.post("/plane/sync-projects")
async def sync_plane_projects() -> dict:
    """Fetch all projects from Plane, merge into settings preserving existing aliases."""
```

**Validation**:
```bash
cd backend && uv run pytest tests/test_config.py -v
```

**Acceptance Criteria**:
- [ ] `plane_projects` persisted in `~/.clarity/settings.json`
- [ ] Sync endpoint fetches from Plane API and merges (doesn't overwrite user aliases)
- [ ] Each project entry has: `id`, `name`, `identifier` (Plane project identifier prefix)

---

#### Task 1.3: Project Name Resolver (Fuzzy + AI)
**Status**: todo

**Description**: Create a project name resolver that takes a spoken project name and resolves it to a project ID. Two-tier approach: (1) exact/fuzzy match against aliases and names, (2) local LLM fallback for ambiguous cases.

**Files**:
- Create: `backend/src/clarity_backend/voice/project_resolver.py`

**Details**:
```python
class ProjectResolver:
    def __init__(self, projects: dict[str, dict]):
        """Initialize with project registry from settings."""

    def resolve(self, spoken_name: str) -> ResolveResult:
        """Try exact match, then fuzzy match (Levenshtein), return best match or ambiguous list."""

    async def resolve_with_ai(self, spoken_name: str, transcript_context: str) -> ResolveResult:
        """Use local LLM (Ollama) to disambiguate when fuzzy match is uncertain."""

@dataclass
class ResolveResult:
    project_id: str | None
    project_name: str | None
    confidence: float
    alternatives: list[dict]  # For disambiguation
    method: str  # "exact", "fuzzy", "ai"
```

**Fuzzy matching approach**:
- Normalize both sides (lowercase, strip whitespace/punctuation)
- Check alias exact match first
- Check substring match (e.g., "acme" in "Acme Corp Website")
- Levenshtein distance with threshold (use `difflib.SequenceMatcher` from stdlib)
- If multiple candidates within threshold, return ambiguous with alternatives

**AI fallback approach**:
- Call Ollama API (`http://localhost:11434/api/generate`) with a short prompt
- Prompt: "Given these projects: [list], which one does '[spoken_name]' refer to? Reply with just the alias."
- Timeout: 3 seconds (fail fast to regex fallback)
- Graceful degradation: if Ollama not running, skip AI tier

**Validation**:
```bash
cd backend && uv run pytest tests/test_project_resolver.py -v
```

**Acceptance Criteria**:
- [ ] Exact alias match works (e.g., "acme" -> Acme project)
- [ ] Fuzzy match handles voice garbling (e.g., "acmee" -> "acme")
- [ ] AI fallback works when Ollama is available, degrades gracefully when not
- [ ] Returns confidence score + alternatives for disambiguation
- [ ] Resolves within <500ms for regex, <3s for AI

---

#### Task 1.4: Plane API Router (Backend Endpoints)
**Status**: todo

**Description**: Create new FastAPI router for Plane task management endpoints. These are called by the frontend confirmation flow (not directly by voice).

**Files**:
- Create: `backend/src/clarity_backend/plane/routes.py`
- Modify: `backend/src/clarity_backend/main.py` (register router, line 62)

**Details**:
```python
router = APIRouter(prefix="/api/plane", tags=["plane"])

@router.get("/projects")
async def list_projects() -> list[dict]:
    """Return configured projects with aliases from settings."""

@router.get("/projects/{project_id}/tasks")
async def list_tasks(project_id: str, assignees: str = "me") -> list[dict]:
    """Fetch tasks from Plane for a specific project."""

@router.post("/confirm-action")
async def confirm_action(body: ConfirmActionRequest) -> dict:
    """Execute a previously previewed action (create task, complete task, etc.)."""

@router.get("/projects/{project_id}/states")
async def get_project_states(project_id: str) -> list[dict]:
    """Fetch workflow states for a project (needed to find 'Done' state ID)."""
```

**ConfirmActionRequest model**:
```python
class ConfirmActionRequest(BaseModel):
    action_type: str  # "create_task", "complete_task"
    project_id: str
    # For create:
    title: str | None = None
    priority: str | None = None
    # For complete:
    issue_id: str | None = None
    state_id: str | None = None
```

**Validation**:
```bash
cd backend && uv run pytest tests/test_plane_routes.py -v
```

**Acceptance Criteria**:
- [ ] All endpoints use async, proper error handling
- [ ] `confirm-action` validates required fields based on action_type
- [ ] Projects endpoint returns data from settings (cached), not live API on every call
- [ ] Router registered in `main.py`

---

### Phase 2: Voice Intents - Classify + Handle Plane Commands

#### Task 2.1: Add Plane Intent Types and Patterns
**Status**: todo

**Description**: Extend `intent.py` with new Plane-specific intents. These must be placed BEFORE the existing `CREATE_ISSUE` pattern (which matches "create issue" for triage items) to avoid conflicts.

**Files**:
- Modify: `backend/src/clarity_backend/voice/intent.py` (add types lines 11-23, add patterns lines 26-39)

**Details**:
```python
# New intent types (add after line 23):
PLANE_CREATE_TASK = "plane_create_task"
PLANE_COMPLETE_TASK = "plane_complete_task"
PLANE_LIST_TASKS = "plane_list_tasks"

# New patterns (insert BEFORE existing CREATE_ISSUE pattern at line 35):
# "create task in acme: update documentation" / "add task for client-x: fix bug"
(r"(create|add|new)\s+(task|work item|ticket)\s+(in|for)\s+(.+?)(?:\s*[:\-]\s*(.+))?$", PLANE_CREATE_TASK),

# "complete task ACME-42" / "done with task 42 in acme" / "finish ticket acme 15"
(r"(complete|finish|done|close|resolve)\s+(?:with\s+)?(?:task|ticket|item)\s+(.+)", PLANE_COMPLETE_TASK),

# "show my tasks" / "list tasks in acme" / "what are my tickets"
(r"(show|list|what are|check)\s+(?:my\s+)?(tasks|work items|tickets)(?:\s+(?:in|for)\s+(.+))?", PLANE_LIST_TASKS),
```

**Parameter extraction** (extend `_extract_params`):
```python
elif intent_type == PLANE_CREATE_TASK:
    # Extract project name and task title from regex groups
    params["project_name"] = <captured group for project>
    params["task_title"] = <captured group for title>
    # Extract priority from keywords
    for prio in ("urgent", "high", "medium", "low"):
        if prio in text:
            params["priority"] = prio
            break

elif intent_type == PLANE_COMPLETE_TASK:
    # Extract task identifier: "ACME-42" or "42 in acme"
    params["task_ref"] = <captured group>

elif intent_type == PLANE_LIST_TASKS:
    # Extract optional project name
    params["project_name"] = <captured group or None for "my tasks">
```

**Important**: The regex patterns must handle the way speech-to-text formats these commands. Voice often drops punctuation, so "create task in acme update documentation" (no colon) should still work.

**Validation**:
```bash
cd backend && uv run pytest tests/test_voice_intent.py -v
```

**Acceptance Criteria**:
- [ ] "create task in acme: update docs" -> PLANE_CREATE_TASK with project_name="acme", task_title="update docs"
- [ ] "complete task ACME-42" -> PLANE_COMPLETE_TASK with task_ref="ACME-42"
- [ ] "show my tasks" -> PLANE_LIST_TASKS with project_name=None
- [ ] "show tasks in acme" -> PLANE_LIST_TASKS with project_name="acme"
- [ ] "create urgent task in acme: fix login" -> priority="urgent"
- [ ] Existing intents (QUERY_ERRORS, FIX_ITEM, etc.) still work correctly

---

#### Task 2.2: Add Plane Command Handlers
**Status**: todo

**Description**: Create handler functions for the three new Plane intents. These handlers return `pending_action` payloads (not executed immediately) that the frontend will display as confirmation cards.

**Files**:
- Modify: `backend/src/clarity_backend/voice/commands.py` (add handlers, add to HANDLERS dict)

**Details**:
```python
# New response templates:
PLANE_CREATE_TASK: "I'll create a task in {project_name}: \"{title}\". Priority: {priority}. Please confirm.",
PLANE_COMPLETE_TASK: "I'll mark {task_ref} as done in {project_name}. Please confirm.",
PLANE_LIST_TASKS: "You have {count} task{s} in {project_name}. {summary}",

# Handler returns pending_action instead of executing:
async def _handle_plane_create_task(intent: Intent, session: AsyncSession) -> dict:
    project_name = intent.params.get("project_name", "")
    task_title = intent.params.get("task_title", "")
    priority = intent.params.get("priority", "none")

    if not project_name:
        return {"response": "Which project should I create the task in?", "data": {}}
    if not task_title:
        return {"response": f"What should the task be called in {project_name}?", "data": {}}

    # Resolve project name to ID
    resolver = _get_project_resolver()
    result = resolver.resolve(project_name)

    if not result.project_id:
        if result.alternatives:
            names = ", ".join(a["name"] for a in result.alternatives[:3])
            return {"response": f"Did you mean {names}?", "data": {"alternatives": result.alternatives}}
        return {"response": f"I don't know a project called {project_name}.", "data": {}}

    return {
        "response": TEMPLATES[PLANE_CREATE_TASK].format(
            project_name=result.project_name, title=task_title, priority=priority
        ),
        "data": {
            "pending_action": {
                "action_type": "create_task",
                "project_id": result.project_id,
                "project_name": result.project_name,
                "title": task_title,
                "priority": priority,
            }
        },
    }
```

Similar pattern for `_handle_plane_complete_task` and `_handle_plane_list_tasks`.

The `_handle_plane_list_tasks` handler is different — it executes immediately (read-only, no confirmation needed) and returns task count + top 3 task titles via TTS.

**Validation**:
```bash
cd backend && uv run pytest tests/test_voice_commands.py tests/test_plane_commands.py -v
```

**Acceptance Criteria**:
- [ ] Create and complete handlers return `pending_action` in data dict
- [ ] List handler returns immediately with task count and summary
- [ ] Missing parameters prompt user for clarification
- [ ] Project name resolution uses fuzzy matching
- [ ] Priority extracted from voice command

---

#### Task 2.3: Hybrid Intent Classifier (AI Fallback)
**Status**: todo

**Description**: When the regex classifier returns `UNKNOWN` (confidence=0), attempt to classify using a local LLM via Ollama. This handles natural/messy speech that doesn't match rigid regex patterns.

**Files**:
- Create: `backend/src/clarity_backend/voice/ai_classifier.py`
- Modify: `backend/src/clarity_backend/voice/intent.py` (add fallback call in `classify()`, line 62)

**Details**:
```python
# ai_classifier.py
import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"  # Small, fast model for classification

SYSTEM_PROMPT = """You are a voice command classifier. Given a transcript, output JSON:
{"intent": "<type>", "params": {"project_name": "...", "task_title": "...", "priority": "...", "task_ref": "..."}}

Intent types: plane_create_task, plane_complete_task, plane_list_tasks, query_errors, query_vulns, check_status, morning_brief, unknown

Available projects: {project_list}
"""

async def classify_with_ai(text: str, project_names: list[str]) -> Intent | None:
    """Attempt classification via local Ollama. Returns None if unavailable."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(OLLAMA_URL, json={
                "model": MODEL,
                "prompt": text,
                "system": SYSTEM_PROMPT.format(project_list=", ".join(project_names)),
                "stream": False,
                "format": "json",
            })
            if resp.status_code == 200:
                # Parse response, construct Intent
                ...
    except (httpx.ConnectError, httpx.TimeoutException):
        return None  # Ollama not running, graceful degradation
```

**Modification to `intent.py:classify()`**:
```python
def classify(text: str) -> Intent:
    # ... existing regex matching ...

    # If regex returns UNKNOWN, try AI fallback (async)
    # Note: classify() is sync, so we need to make it async or
    # handle this in the router layer instead
    return Intent(type=UNKNOWN, confidence=0.0, params={"original_text": text})
```

**Better approach**: Make the fallback happen in `router.py` where we're already async:
```python
@router.post("/process")
async def process_voice(body: VoiceRequest, session: SessionDep) -> VoiceResponse:
    intent = classify(body.text)

    # AI fallback for unknown intents
    if intent.type == UNKNOWN and intent.confidence == 0.0:
        ai_intent = await classify_with_ai(body.text, _get_project_names())
        if ai_intent and ai_intent.confidence > 0.5:
            intent = ai_intent

    result = await execute(intent, session)
    return VoiceResponse(...)
```

**Validation**:
```bash
cd backend && uv run pytest tests/test_ai_classifier.py -v
```

**Acceptance Criteria**:
- [ ] AI classifier calls Ollama with structured prompt
- [ ] 3-second timeout — never blocks the voice pipeline
- [ ] Returns None when Ollama is not running (graceful degradation)
- [ ] Injects project names into prompt for context
- [ ] Returns Intent with confidence score from AI response
- [ ] Router falls back to AI only when regex returns UNKNOWN

---

### Phase 3: Frontend - Confirmation Card + Voice Response Enhancement

#### Task 3.1: Confirmation Card Component
**Status**: todo

**Description**: Build a modal overlay component that displays pending actions from voice commands. Shows action details (project, title, priority) with Accept/Reject buttons. Auto-dismisses after 30 seconds (defaults to reject).

**Files**:
- Create: `src/components/ConfirmationCard.tsx`

**Details**:
```tsx
interface PendingAction {
  action_type: "create_task" | "complete_task";
  project_id: string;
  project_name: string;
  title?: string;
  priority?: string;
  task_ref?: string;
  issue_id?: string;
}

interface ConfirmationCardProps {
  action: PendingAction;
  onConfirm: () => void;
  onReject: () => void;
}
```

**UI Layout** (modal overlay, centered, follows existing card pattern from `settings/page.tsx`):
```
Fixed overlay (z-50, backdrop blur)
├── Card (rounded-card bg-card-bg shadow-card, max-w-sm)
│   ├── Header: icon + action type name
│   ├── Body: key-value pairs (Project, Title, Priority)
│   ├── Countdown timer bar (30s, visual progress)
│   └── Footer: [Reject] button + [Confirm] button
```

**Keyboard shortcuts**: Enter = confirm, Escape = reject
**Auto-dismiss**: 30s countdown, defaults to reject, visual timer bar

**Styling**: Use existing Tailwind classes from the codebase:
- `rounded-card`, `bg-card-bg`, `shadow-card` (from settings page)
- `bg-nav-bg text-cream` for confirm button (from save button pattern)
- `bg-cream-dark text-bark` for reject button (from reset button pattern)
- `text-bark`, `text-bark-muted`, `text-xs` for labels

**Validation**:
```bash
bun run test -- src/components/ConfirmationCard.test.tsx
```

**Acceptance Criteria**:
- [ ] Displays action details in readable format
- [ ] Enter/Escape keyboard shortcuts work
- [ ] 30-second auto-dismiss with visual countdown
- [ ] Accessible: focus management, aria labels
- [ ] Responsive (works at md+ desktop widths)

---

#### Task 3.2: Extend useVoice Hook for Pending Actions
**Status**: todo

**Description**: Modify the `useVoice` hook to detect `pending_action` in voice responses and expose it as state. The hook should manage the confirm/reject flow.

**Files**:
- Modify: `src/hooks/useVoice.ts` (extend state and handleResult, lines 15-95)
- Modify: `src/lib/api.ts` (add `confirmPlaneAction()` function)

**Details**:

In `useVoice.ts`:
```typescript
// Add to state:
const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);

// Modify handleResult (line 82-95):
const handleResult = useCallback(async (transcript: string) => {
    setState("processing");
    try {
        const result = await processVoice(transcript);
        setLastResponse(result.response);
        speak(result.response);

        // Check for pending action
        if (result.data?.pending_action) {
            setPendingAction(result.data.pending_action as PendingAction);
        }
    } catch { ... }
}, [speak]);

// Add confirm/reject handlers:
const confirmAction = useCallback(async () => {
    if (!pendingAction) return;
    try {
        const result = await confirmPlaneAction(pendingAction);
        setLastResponse(result.response);
        speak(result.response);
    } catch {
        setLastResponse("Action failed. Please try again.");
    } finally {
        setPendingAction(null);
    }
}, [pendingAction, speak]);

const rejectAction = useCallback(() => {
    setPendingAction(null);
    setLastResponse("Action cancelled.");
    speak("Cancelled.");
}, [speak]);
```

In `api.ts`:
```typescript
export interface PendingAction {
    action_type: "create_task" | "complete_task";
    project_id: string;
    project_name: string;
    title?: string;
    priority?: string;
    task_ref?: string;
    issue_id?: string;
    state_id?: string;
}

export function confirmPlaneAction(action: PendingAction): Promise<{ response: string }> {
    return apiFetch("/api/plane/confirm-action", {
        method: "POST",
        body: JSON.stringify(action),
    });
}
```

**Validation**:
```bash
bun run test -- src/hooks/useVoice.test.ts
```

**Acceptance Criteria**:
- [ ] `pendingAction` state exposed from hook
- [ ] `confirmAction` and `rejectAction` callbacks exposed
- [ ] Pending action auto-clears on confirm/reject
- [ ] TTS speaks confirmation result
- [ ] Existing voice flow unchanged when no pending_action in response

---

#### Task 3.3: Wire Confirmation Card into Layout
**Status**: todo

**Description**: Render the ConfirmationCard as a modal overlay in the app layout, driven by `useVoice` state. Show it on desktop when `pendingAction` is non-null.

**Files**:
- Modify: `src/components/DesktopSidebar.tsx` (add ConfirmationCard rendering)
- OR create: `src/components/VoiceOverlay.tsx` (a dedicated overlay wrapper)

**Details**:

Option A (simpler): Add to `DesktopSidebar.tsx` since it already uses `useVoice()`:
```tsx
// After the voice button (line 53):
{pendingAction && (
    <ConfirmationCard
        action={pendingAction}
        onConfirm={confirmAction}
        onReject={rejectAction}
    />
)}
```

Option B (cleaner): Create `VoiceOverlay.tsx` that renders as a portal/fixed overlay and include it in `layout.tsx`. This keeps the sidebar simple and makes the overlay work regardless of page.

**Recommendation**: Option B — a separate `VoiceOverlay.tsx` rendered in `layout.tsx` is more robust. The confirmation card should be visible from any page, not just when the sidebar is visible.

**Validation**:
```bash
bun run build  # Ensure no TypeScript errors
```

**Acceptance Criteria**:
- [ ] Confirmation card appears as modal overlay on any page
- [ ] Card dismisses on confirm/reject/timeout
- [ ] Voice button + sidebar not affected
- [ ] No layout shift when card appears

---

### Phase 4: Settings UI - Project Management + Client Name Training

#### Task 4.1: Project Registry UI in Settings
**Status**: todo

**Description**: Add a "Plane Projects" section to the settings page that shows synced projects and allows editing aliases. Includes a "Sync from Plane" button that fetches all projects.

**Files**:
- Create: `src/components/PlaneProjectsEditor.tsx`
- Modify: `src/app/settings/page.tsx` (add section after Plane Integration, line 114)
- Modify: `src/lib/api.ts` (add project API functions)

**Details**:

UI layout:
```
+------------------------------------------+
| Plane Projects                           |
|                                          |
| [Sync from Plane] button                 |
|                                          |
| Project: Acme Corp (ACME)               |
| Voice alias: [acme________]              |
|                                          |
| Project: Clarity Regulatory (CR)         |
| Voice alias: [clarity______]             |
|                                          |
| ... (scrollable list of 32+ projects)    |
+------------------------------------------+
```

Each project row shows:
- Project name + identifier from Plane
- Editable alias field (what you say by voice)
- Auto-suggested alias (lowercase first word of project name)

API functions to add:
```typescript
export function getPlaneProjects(): Promise<Record<string, ProjectEntry>> {
    return apiFetch("/api/plane/projects");
}
export function syncPlaneProjects(): Promise<Record<string, ProjectEntry>> {
    return apiFetch("/api/settings/plane/sync-projects", { method: "POST" });
}
```

**Validation**:
```bash
bun run test -- src/components/PlaneProjectsEditor.test.tsx
```

**Acceptance Criteria**:
- [ ] Sync button fetches all projects from Plane API
- [ ] Each project has an editable voice alias field
- [ ] Aliases auto-saved when edited (debounced)
- [ ] Shows project identifier prefix (e.g., "ACME")
- [ ] Handles 32+ projects without performance issues (virtual scroll if needed)

---

### Phase 5: Integration Testing + Polish

#### Task 5.1: End-to-End Voice Flow Tests
**Status**: todo

**Description**: Write integration tests that verify the full flow: voice text -> intent classification -> command handler -> pending_action response -> confirm -> Plane API call.

**Files**:
- Create: `backend/tests/test_plane_commands.py`
- Create: `backend/tests/test_project_resolver.py`
- Modify: `backend/tests/test_voice_intent.py` (add Plane intent tests)

**Details**:
```python
# test_voice_intent.py — add new test class:
class TestClassifyPlaneActions:
    def test_create_task_in_project(self):
        intent = classify("create task in acme: update API docs")
        assert intent.type == PLANE_CREATE_TASK
        assert intent.params["project_name"] == "acme"
        assert intent.params["task_title"] == "update API docs"

    def test_create_urgent_task(self):
        intent = classify("create urgent task in acme: fix login")
        assert intent.type == PLANE_CREATE_TASK
        assert intent.params["priority"] == "urgent"

    def test_complete_task_with_identifier(self):
        intent = classify("complete task ACME-42")
        assert intent.type == PLANE_COMPLETE_TASK
        assert intent.params["task_ref"] == "ACME-42"

    def test_show_my_tasks(self):
        intent = classify("show my tasks")
        assert intent.type == PLANE_LIST_TASKS

    def test_show_tasks_in_project(self):
        intent = classify("show tasks in acme")
        assert intent.type == PLANE_LIST_TASKS
        assert intent.params["project_name"] == "acme"

    def test_natural_speech_no_colon(self):
        """Voice often drops punctuation."""
        intent = classify("create task in acme update the documentation")
        assert intent.type == PLANE_CREATE_TASK

# test_project_resolver.py:
class TestProjectResolver:
    def test_exact_alias_match(self): ...
    def test_fuzzy_match_typo(self): ...
    def test_substring_match(self): ...
    def test_no_match_returns_none(self): ...
    def test_ambiguous_returns_alternatives(self): ...
    def test_case_insensitive(self): ...
```

**Validation**:
```bash
cd backend && uv run pytest tests/ -v --tb=short
```

**Acceptance Criteria**:
- [ ] All existing intent tests still pass
- [ ] New Plane intent tests cover create/complete/list
- [ ] Project resolver tests cover exact/fuzzy/ambiguous/no-match
- [ ] Edge cases: empty project name, no title, voice without punctuation

---

#### Task 5.2: Frontend Component Tests
**Status**: todo

**Description**: Test the ConfirmationCard component and the extended useVoice hook.

**Files**:
- Create: `src/components/ConfirmationCard.test.tsx`
- Modify: `src/hooks/useVoice.test.ts` (add pending action tests)

**Details**:
```typescript
// ConfirmationCard.test.tsx:
- Renders action details correctly
- Confirm button calls onConfirm
- Reject button calls onReject
- Enter key triggers confirm
- Escape key triggers reject
- Auto-dismisses after 30 seconds (mocked timer)

// useVoice.test.ts additions:
- When response has pending_action, pendingAction state is set
- confirmAction calls API and clears pendingAction
- rejectAction clears pendingAction without API call
```

**Validation**:
```bash
bun run test
```

**Acceptance Criteria**:
- [ ] All existing frontend tests pass
- [ ] ConfirmationCard renders and handles interactions
- [ ] useVoice pending action flow tested

---

#### Task 5.3: Client Vocabulary Integration with Whisper
**Status**: todo

**Description**: Extend the existing `VocabularyEditor` to also include project aliases as custom vocabulary terms. When project aliases are configured, they should automatically be added to the Whisper custom vocabulary to improve recognition accuracy.

**Files**:
- Modify: `src/components/VocabularyEditor.tsx` (auto-include project aliases)
- Modify: `src/lib/api.ts` (if needed for fetching project aliases)

**Details**:
The existing `VocabularyEditor` saves terms to Whisper's custom vocabulary via Tauri API. Extend it to:
1. Fetch project aliases from `getPlaneProjects()`
2. Display them as "auto-included" terms (visually distinct, not editable in the vocabulary textarea)
3. Include them in the `saveCustomVocab()` call alongside user-defined terms

This ensures Whisper's speech recognition model is primed with client names.

**Validation**:
```bash
bun run test -- src/components/VocabularyEditor.test.tsx
```

**Acceptance Criteria**:
- [ ] Project aliases appear in vocabulary list automatically
- [ ] User can still add custom terms alongside
- [ ] Whisper receives combined vocabulary on save
- [ ] Non-Tauri (web speech) path unaffected

---

## Edge Cases

| Case | Expected Behavior | Test Coverage |
|------|-------------------|---------------|
| No projects synced yet | "No projects configured. Go to Settings > Plane Projects to sync." | `test_plane_commands.py` |
| Ambiguous project name (2+ matches) | "Did you mean Acme Corp or Acme Internal?" + alternatives in data | `test_project_resolver.py` |
| Voice drops punctuation | "create task in acme update docs" still works (flexible regex) | `test_voice_intent.py` |
| Ollama not running | AI fallback silently skipped, regex result used | `test_ai_classifier.py` |
| Plane API error on confirm | Error message spoken via TTS, action card dismisses | `test_plane_routes.py` |
| Confirm timeout (30s) | Card auto-dismisses, action NOT executed (safe default) | `ConfirmationCard.test.tsx` |
| Task identifier not found | "Task ACME-42 not found" spoken via TTS | `test_plane_commands.py` |
| User says "cancel" during confirm | Treat as reject | `useVoice.test.ts` |
| Project alias contains spaces | Normalize: "acme corp" stored as "acme-corp" alias | `test_project_resolver.py` |
| 32+ projects in list | Virtual scroll in settings UI, search filter in project editor | `PlaneProjectsEditor.test.tsx` |

---

## Validation Approach

### Level 1: Static Analysis
```bash
cd backend && uv run ruff check src/ tests/
bun run typecheck  # or npx tsc --noEmit
```

### Level 2: Unit Tests
```bash
cd backend && uv run pytest tests/ -v --tb=short
bun run test
```

### Level 3: Integration Tests
```bash
cd backend && uv run pytest tests/test_plane_commands.py tests/test_plane_routes.py -v
```

### Level 4: Build Verification
```bash
bun run build
```

### Level 5: Manual Testing
- [ ] Say "create task in [real project]: test task" — verify confirmation card appears
- [ ] Click Confirm — verify task created in Plane
- [ ] Click Reject — verify no task created
- [ ] Say "complete task [real identifier]" — verify confirmation + completion
- [ ] Say "show my tasks" — verify TTS reads task count
- [ ] Say "show tasks in [project]" — verify filtered list
- [ ] Test with Ollama running — verify AI fallback works for messy speech
- [ ] Test with Ollama stopped — verify graceful degradation
- [ ] Sync 32+ projects in settings — verify UI handles it
- [ ] Edit project aliases — verify voice recognition uses them

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Regex patterns conflict with existing intents | Medium | High | Insert Plane patterns before existing ones; comprehensive tests |
| Voice garbles client names beyond recognition | High | Medium | Fuzzy matching + AI fallback + trainable vocabulary |
| Ollama adds too much latency (>3s) | Medium | Medium | Hard 3s timeout; skip if slow; use small model (3b) |
| 32 projects overwhelm settings UI | Low | Low | Virtual scroll or search filter in project editor |
| Plane API changes break client | Low | High | Pin to API v1; error handling returns user-friendly messages |
| Confirmation card UX feels slow/clunky | Medium | Medium | 30s timeout; keyboard shortcuts (Enter/Esc); clear visual design |

---

## Architecture Diagram

```
Voice Input (Whisper / Web Speech)
    |
    v
[useVoice.ts] handleResult()
    |
    v
POST /api/voice/process
    |
    v
[router.py] ──> classify(text)
    |               |
    |    ┌──────────┴──────────┐
    |    │ Tier 1: Regex       │ ──> Intent found? ──> execute()
    |    │ (instant, offline)  │         |
    |    └─────────────────────┘         |
    |               |                    |
    |    ┌──────────┴──────────┐         |
    |    │ Tier 2: Ollama LLM  │         |
    |    │ (3s timeout, local)  │ ──> Intent found? ──> execute()
    |    └─────────────────────┘         |
    |                                    |
    v                                    v
VoiceResponse { response, data: { pending_action? } }
    |
    v
[useVoice.ts] ──> pendingAction state
    |
    v
[ConfirmationCard.tsx] ──> User clicks Accept/Reject
    |                           |
    |  ┌────────────────────────┘
    |  v (Accept)
POST /api/plane/confirm-action
    |
    v
[PlaneClient] ──> Plane REST API
    |
    v
{ response: "Created task ACME-43: update docs" }
    |
    v
TTS speaks result
```

---

## Research Findings

### From Codebase
- **Voice pipeline is clean and extensible**: `classify()` -> `execute()` -> response dict. Adding new intents requires: (1) intent type constant, (2) regex pattern, (3) handler function, (4) HANDLERS dict entry
- **PlaneClient already works**: `integrations/plane.py` has the HTTP pattern. Just needs more methods.
- **PlaneNotifierService has `create_issue()`** that already accepts optional `project_id` (line 103) — this is the multi-project pattern we can extend
- **VocabularyEditor exists**: Custom vocabulary for Whisper is already implemented — perfect for training client names
- **WebSocket infrastructure ready**: `wsClient.ts` routes agent events; can add `plane_action_confirmed` events if needed
- **Settings persist to `~/.clarity/settings.json`**: JSON-based, no migration needed — just add new keys

### From Web Research
- Ollama's `/api/generate` supports `format: "json"` for structured output — ideal for intent classification
- `llama3.2:3b` model runs well on Apple Silicon with <1s response time for short prompts
- `difflib.SequenceMatcher` from Python stdlib provides decent fuzzy matching without external deps

---

*Ready for implementation with `/prp-implement`*
