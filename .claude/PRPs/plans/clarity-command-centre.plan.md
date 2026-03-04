# Implementation Plan: Clarity Command Centre

**Created**: 2026-03-02
**Updated**: 2026-03-03
**Status**: All Phases Complete (1-5) ✅
**Archon Project ID**: Not created (Archon not configured)

---

## Overview

A Tauri 2.0 desktop app with a Python FastAPI sidecar that serves as a unified "air traffic control" for your technical and regulatory operations. It ingests errors from PostHog and vulnerabilities from Aikido via webhooks, presents them in an ADHD-friendly triage queue, creates Plane work items, and supports voice-first interaction via local STT/TTS. All Claude interactions use the CLI subprocess approach (Max subscription, zero incremental cost).

## Current State (Phase 1 Complete)

Phase 1 "The Spine" is **fully implemented and tested**:

| Feature | Status | Tests |
|---------|--------|-------|
| Tauri 2.0 + Next.js scaffold | Done | Build passes |
| Python FastAPI sidecar (SQLite, SQLModel) | Done | 54 backend tests |
| PostHog webhook receiver (dedup, severity) | Done | 13 tests |
| Aikido webhook receiver (HMAC, replay protection) | Done | 9 tests |
| Triage queue UI (one-at-a-time, 3 actions) | Done | 9 tests |
| Dashboard (card-based event list) | Done | 7 tests |
| Focus page (score ring, assistant card) | Done | 7 tests |
| Plane API integration (create issues) | Done | 9 tests |
| Status bar (2x2 metric cards) | Done | 2 tests |
| Navigation (bottom tab bar) | Done | 3 tests |
| API client library (typed) | Done | 7 tests |
| Visual overhaul (warm health-dashboard theme) | Done | — |

**Metrics**: 175 tests (78 frontend + 97 backend).

## User Stories

- ~~As a solo developer, I want a single-task focus view~~ ✅ (Score ring + assistant card)
- ~~As a developer, I want PostHog errors in a triage queue~~ ✅
- ~~As a developer, I want one-at-a-time triage~~ ✅ (Snooze/Dismiss/Create Issue)
- ~~As a developer, I want Plane issues from triage~~ ✅
- ~~As a developer, I want Aikido vulns in the same pipeline~~ ✅
- ~~As a developer, I want an ambient status bar~~ ✅ (2x2 metric cards)
- ~~As a developer, I want voice input to capture thoughts and commands~~ ✅ (Intent router + Web Speech API)
- ~~As a developer, I want keyboard shortcuts for power-user triage~~ ✅ (c/s/d/? shortcuts)
- ~~As a developer, I want a morning brief summarizing overnight activity~~ ✅ (GET /api/brief/morning)
- ~~As a developer, I want a focus timer for Pomodoro sessions~~ ✅ (FocusTimer component)

## Success Criteria (Remaining)

- [x] Tauri 2.0 app launches with Next.js frontend
- [x] Python FastAPI sidecar starts alongside the app
- [x] PostHog webhook events are received, deduplicated, and stored in SQLite
- [x] Aikido webhook events are received with HMAC verification and stored
- [x] Triage queue presents one item at a time with Create/Snooze/Dismiss actions
- [x] "Create Issue" action creates a Plane work item via the API
- [x] Ambient status bar shows error/vuln/task counts
- [x] Keyboard shortcuts for all triage actions
- [x] Focus timer with Pomodoro intervals
- [x] Voice push-to-talk captures speech and executes commands
- [x] Morning brief summarizes errors, vulns, and tasks
- [x] Settings page for API keys and preferences

---

## Mandatory Reading

Before implementation, read these files to understand existing patterns:

| File | Purpose | Key Lines |
|------|---------|-----------|
| `backend/src/clarity_backend/main.py` | FastAPI app structure, router registration, lifespan | All |
| `backend/src/clarity_backend/triage/routes.py` | Route pattern, SessionDep, response serialization | All |
| `backend/src/clarity_backend/triage/engine.py` | Pure function pattern for business logic | All |
| `backend/tests/conftest.py` | Test fixture pattern (in-memory SQLite, AsyncClient) | All |
| `backend/tests/test_triage_routes.py` | Integration test pattern with _seed_item helper | All |
| `src/components/TriageCard.tsx` | Component pattern: severity config maps, pastel theme | All |
| `src/app/triage/page.tsx` | Page pattern: API mock, loading/error/empty states | All |
| `src/components/StatusBar.test.tsx` | Frontend test pattern: vi.mock, waitFor | All |
| `src/app/globals.css` | Tailwind v4 @theme tokens — all new UI must use these | All |
| `vitest.config.ts` | Frontend test configuration | All |

## Patterns to Follow

### Naming
- Components: PascalCase (`TriageCard.tsx`, `FocusTimer.tsx`)
- Python modules: snake_case (`posthog.py`, `triage_engine.py`)
- API routes: `/api/{resource}` (no kebab-case)
- Tests: colocated `*.test.tsx` (frontend), `tests/test_*.py` (backend)

### Theme
- All colors use `@theme` tokens from `globals.css` (e.g., `bg-cream`, `text-bark`, `bg-sev-critical/20`)
- Cards: `rounded-card bg-card-bg shadow-card` or `bg-sev-*/15` for tinted
- Buttons: primary `rounded-pill bg-nav-bg text-cream`, secondary `rounded-pill bg-cream text-bark`
- Badges: `rounded-pill bg-sev-*/40 text-bark`

### Error Handling
- Backend: FastAPI HTTPException with detail messages
- Frontend: loading → loaded → error states in each page component
- API client: throws on non-2xx, caught in page components

### Testing
- Backend: pytest + httpx AsyncClient, conftest fixtures, `_seed_item` helpers
- Frontend: Vitest + React Testing Library, `vi.mock("@/lib/api")`, `waitFor` for async

---

## Implementation Tasks

### Phase 2: ADHD Power Features (Low Risk, High Value)

These features directly enhance the core triage workflow without new external dependencies.

#### Task 2.1: Keyboard Shortcuts for Triage
**Status**: done ✓

**Description**: Add keyboard shortcuts for all triage actions. When on the `/triage` page, single keypresses trigger actions: `c` = Create Issue, `s` = Snooze, `d` = Dismiss, `n` = Next (if multiple items). Show a `?` shortcut help overlay. Use a `useEffect` with `keydown` listener — no external library needed.

**Files**:
- Modify: `src/app/triage/page.tsx` (add `useEffect` keydown handler, `?` toggle state)
- Create: `src/components/ShortcutHelp.tsx` (modal overlay listing shortcuts)

**Validation**:
```bash
bun run build && bun run test
# Manual: open /triage, press c/s/d/n, press ? for help
```

**Acceptance Criteria**:
- [ ] `c` triggers Create Issue on current item
- [ ] `s` triggers Snooze on current item
- [ ] `d` triggers Dismiss on current item
- [ ] `?` toggles shortcut help overlay
- [ ] Shortcuts only active on /triage page
- [ ] Tests cover keydown handlers

---

#### Task 2.2: Focus Timer (Pomodoro)
**Status**: done ✓

**Description**: Add a configurable Pomodoro timer to the Focus page. Default: 25 min focus / 5 min break. Timer displays as a countdown ring (reuse the ScoreRing SVG pattern). When timer ends, show a gentle notification card. Timer state persists across page navigation using `useRef` + context.

**Files**:
- Create: `src/components/FocusTimer.tsx` (timer ring + controls)
- Modify: `src/app/page.tsx` (integrate FocusTimer below score ring)

**Validation**:
```bash
bun run build && bun run test
# Manual: start timer, navigate away and back, verify timer continues
```

**Acceptance Criteria**:
- [ ] Timer displays as countdown ring with minutes:seconds
- [ ] Start/Pause/Reset controls
- [ ] Gentle notification when timer completes (card, not system notification)
- [ ] Timer persists across page navigation
- [ ] Tests cover timer start/pause/complete states

---

#### Task 2.3: Morning Brief
**Status**: done ✓

**Description**: On first app launch each day, show a summary card on the Focus page: new errors since yesterday, open vulnerabilities, items actioned yesterday. Backend endpoint aggregates the data. Frontend stores "last brief date" in localStorage to trigger once daily.

**Files**:
- Create: `backend/src/clarity_backend/brief/morning.py` (aggregation queries)
- Create: `backend/src/clarity_backend/brief/__init__.py`
- Modify: `backend/src/clarity_backend/main.py` (register brief router)
- Create: `src/components/MorningBrief.tsx` (brief display card)
- Modify: `src/app/page.tsx` (show brief on first daily visit)

**Validation**:
```bash
cd backend && uv run pytest tests/ -v
bun run build && bun run test
```

**Acceptance Criteria**:
- [ ] `GET /api/brief/morning` returns aggregated metrics
- [ ] Brief card shows on Focus page once per day
- [ ] Card is dismissible
- [ ] Brief includes: new errors (24h), open vulns, actioned yesterday
- [ ] Tests cover the aggregation endpoint and brief component

---

#### Task 2.4: Settings Page
**Status**: done ✓

**Description**: Build a settings page for configuring Plane API credentials, webhook secrets, and timer preferences. Settings stored in a local JSON file (`~/.clarity/settings.json`) via a backend settings API. Frontend form with save/reset.

**Files**:
- Create: `backend/src/clarity_backend/settings/manager.py` (read/write JSON settings)
- Create: `backend/src/clarity_backend/settings/__init__.py`
- Modify: `backend/src/clarity_backend/main.py` (register settings router)
- Create: `src/app/settings/page.tsx` (settings form)

**Validation**:
```bash
cd backend && uv run pytest tests/ -v
bun run build && bun run test
```

**Acceptance Criteria**:
- [ ] `GET /api/settings` returns current settings (secrets masked)
- [ ] `PUT /api/settings` saves updated settings
- [ ] Settings page shows form with current values
- [ ] Plane API key, workspace slug configurable
- [ ] Timer duration configurable (focus/break minutes)
- [ ] Tests cover settings CRUD

---

### Phase 3: Voice Layer (Higher Risk)

These features depend on Tauri native plugins. Start with the intent router (pure Python, no plugin risk) before wiring up STT/TTS.

#### Task 3.1: Intent Router (Backend)
**Status**: done ✓

**Description**: Build the Python intent classification system. Parse natural language commands into structured intents with parameters. Use Claude Code CLI subprocess for classification. Support intents: query_errors, create_issue, check_status, snooze_item, morning_brief.

**Files**:
- Create: `backend/src/clarity_backend/voice/intent.py` (intent classifier)
- Create: `backend/src/clarity_backend/voice/commands.py` (command executors)
- Create: `backend/src/clarity_backend/voice/__init__.py`
- Create: `backend/src/clarity_backend/integrations/claude.py` (CLI subprocess wrapper)
- Modify: `backend/src/clarity_backend/main.py` (register voice router)

**Validation**:
```bash
curl -X POST http://localhost:8001/api/voice/process \
  -H "Content-Type: application/json" \
  -d '{"text": "What errors came in today?"}'
```

**Acceptance Criteria**:
- [ ] `POST /api/voice/process` accepts text, returns intent + response
- [ ] Claude CLI called via subprocess (graceful fallback if unavailable)
- [ ] 5+ intents recognized: query, create, status, snooze, brief
- [ ] Response text suitable for TTS output
- [ ] Tests cover intent classification with mocked Claude CLI

---

#### Task 3.2: STT Integration
**Status**: done ✓ (Resolved via Wispr — system-level STT replaces Tauri plugin)

**Description**: Speech-to-text is handled by Wispr, a system-level dictation tool, eliminating the need for `tauri-plugin-stt` or Vosk. Wispr provides high-quality STT across all applications including Clarity.

---

#### Task 3.3: TTS Integration
**Status**: done ✓ (Resolved via Wispr — system-level TTS replaces Tauri plugin)

**Description**: Text-to-speech is handled at the system level via Wispr/macOS native TTS, eliminating the need for `tauri-plugin-tts`.

---

#### Task 3.4: Push-to-Talk UI + Wiring
**Status**: done ✓ (Web Speech API — Tauri plugins deferred)

**Description**: Build the frontend voice interaction layer. Global hotkey (Cmd+Shift+Space) activates listening. Visual indicator shows listening state. Transcribed text sent to intent router, response spoken via TTS.

**Files**:
- Create: `src/components/VoiceButton.tsx` (visual push-to-talk indicator)
- Create: `src/lib/voice.ts` (Tauri event listeners for STT/TTS)
- Modify: `src/app/layout.tsx` (render VoiceButton globally)

**Acceptance Criteria**:
- [ ] Hotkey activates listening globally
- [ ] Pulsing mic indicator during listening
- [ ] Text → intent router → response → TTS pipeline works end-to-end

---

### Phase 4: Intelligence Layer

#### Task 4.1: Claude Error Investigation
**Status**: done ✓

**Description**: When user clicks "Investigate" in triage (currently removed button), spawn a Claude Code CLI process that analyzes the error context and returns a diagnosis. Results displayed in an expandable panel below the triage card.

**Files**:
- Create: `backend/src/clarity_backend/triage/investigator.py`
- Create: `src/components/InvestigationResult.tsx`
- Modify: `src/components/TriageCard.tsx` (re-add Investigate button)
- Modify: `src/app/triage/page.tsx` (show investigation results)

**Acceptance Criteria**:
- [ ] `POST /api/triage/{id}/investigate` triggers Claude CLI analysis
- [ ] Results include: root cause, affected files, suggested fix
- [ ] Results displayed in expandable panel
- [ ] 5-minute timeout with progress indicator
- [ ] Graceful fallback if Claude CLI unavailable

---

#### Task 4.2: Pattern Detection
**Status**: done ✓

**Description**: Track error patterns over time. When the same fingerprint appears 3+ times in a week, surface a "recurring pattern" badge on the triage card.

**Files**:
- Create: `backend/src/clarity_backend/triage/patterns.py`
- Modify: `src/components/TriageCard.tsx` (pattern badge)

**Acceptance Criteria**:
- [ ] Errors grouped by fingerprint
- [ ] Pattern badge after 3 occurrences within 7 days
- [ ] Triage card shows occurrence history

---

### Phase 5: Statistics & Polish

#### Task 5.1: Statistics Page
**Status**: done ✓

**Description**: Weekly error resolution count, average time-to-triage, task completion trend.

**Files**:
- Created: `src/app/stats/page.tsx` (summary cards, severity breakdown, 14-day trend bar chart)
- Created: `backend/src/clarity_backend/stats/queries.py` (4 query functions)
- Created: `backend/src/clarity_backend/stats/routes.py` (GET /api/stats)
- Modified: `src/components/Navigation.tsx` (Stats tab added)

**Tests**: 8 backend tests in `test_stats.py` (queries + endpoint)

---

#### Task 5.2: Notification System
**Status**: done ✓

**Description**: Full notification system with CRUD, WebSocket real-time broadcasting, reply/archive/snooze/mark_read actions, multi-service integration (Gmail, Outlook, Slack), and task creation via Plane/Asana.

**Files**:
- Created: `backend/src/clarity_backend/notifications/routes.py` (REST + WebSocket endpoints)
- Created: `backend/src/clarity_backend/notifications/crud.py` (notification CRUD)
- Created: `backend/src/clarity_backend/notifications/models.py` (Pydantic models)
- Created: `backend/src/clarity_backend/notifications/ws.py` (WebSocket connection manager)

---

## Edge Cases

| Case | Expected Behavior | Test Coverage |
|------|-------------------|---------------|
| ~~PostHog webhook with invalid signature~~ | ~~Return 401~~ | ✅ `test_posthog_webhook.py` |
| ~~Aikido webhook older than 30 seconds~~ | ~~Return 401, reject replay~~ | ✅ `test_aikido_webhook.py` |
| ~~Duplicate error within 24h~~ | ~~Merge, increment count~~ | ✅ `test_posthog_webhook.py` |
| ~~Empty triage queue~~ | ~~"All clear" message~~ | ✅ `test_triage_page.test.tsx` |
| ~~Plane API creates issue~~ | ~~Returns Plane issue URL~~ | ✅ `test_plane_integration.py` |
| Claude CLI not installed | Skip AI features, manual-only triage | `test_claude_unavailable` |
| Voice input with no recognized intent | "I didn't understand" response via TTS | `test_unknown_intent` |
| Very long error messages (>10KB) | Truncate to 2KB | `test_long_error_truncation` |
| Keyboard shortcut on non-triage page | No effect (shortcuts scoped to /triage) | `test_shortcuts_scoped` |
| Timer navigation away | Timer continues (ref-based state) | `test_timer_persistence` |

---

## Validation Approach

### Level 1: Static Analysis
```bash
cd backend && ruff check . && ruff format --check .
bun run build  # includes TypeScript check
```

### Level 2: Unit Tests
```bash
cd backend && uv run pytest tests/ --cov=src/clarity_backend --cov-report=term-missing
bun run test:coverage
```

### Level 3: Build Verification
```bash
bun run build
cargo tauri build  # when Tauri features are added
```

### Level 4: Manual Testing
- [ ] Keyboard shortcuts on /triage page
- [ ] Focus timer completes a full cycle
- [ ] Morning brief shows on first daily launch
- [ ] Settings persist across app restarts
- [ ] Voice: speak command → correct action executed

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `tauri-plugin-stt` doesn't work on macOS ARM | Medium | High | Fallback: Whisper.cpp via Rust FFI or Web Speech API |
| Claude CLI rate limits during heavy investigation | Medium | Medium | Queue requests, timeout at 5 min |
| Timer state lost on page navigation | Low | Medium | Use React context or ref-based persistence |
| Settings file corruption | Low | Medium | JSON schema validation + backup on write |
| Keyboard shortcuts conflict with browser | Low | Medium | Use non-conflicting keys (c/s/d/n/?), no modifier keys |

---

## Technology Stack

| Layer | Technology | Status |
|-------|-----------|--------|
| Desktop Shell | Tauri 2.0 | ✅ Configured |
| Frontend | Next.js 16 + Tailwind v4 | ✅ Complete |
| Backend | Python 3.12 + FastAPI + SQLModel | ✅ Complete |
| Database | SQLite (WAL mode) | ✅ Running |
| STT | Wispr (system-level) | ✅ Resolved |
| TTS | Wispr / macOS native | ✅ Resolved |
| AI | Claude Code CLI (subprocess) | ✅ Integrated |
| Project Mgmt | Plane API (REST) | ✅ Integrated |
| Error Tracking | PostHog webhooks | ✅ Integrated |
| Security | Aikido webhooks (HMAC) | ✅ Integrated |

---

## Recommended Implementation Order

1. **Task 2.1** — Keyboard shortcuts (smallest, immediate UX win)
2. **Task 2.2** — Focus timer (self-contained, uses existing SVG pattern)
3. **Task 2.3** — Morning brief (new backend endpoint + frontend card)
4. **Task 2.4** — Settings page (needed before voice config)
5. **Task 3.1** — Intent router (pure Python, no plugin risk)
6. **Task 3.2-3.4** — STT/TTS/Voice UI (highest risk, do together)
7. **Task 4.1-4.2** — Intelligence layer (depends on Claude CLI)
8. **Task 5.1-5.2** — Statistics + notifications (polish)

---

*Ready for implementation with `/prp-implement .claude/PRPs/plans/clarity-command-centre.plan.md`*
