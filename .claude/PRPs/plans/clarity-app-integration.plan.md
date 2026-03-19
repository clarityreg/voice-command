# Implementation Plan: Clarity App Integration

**Created**: 2026-03-19
**Status**: Ready for Implementation
**PRD**: `.claude/PRPs/prds/clarity-app-integration.prd.md`

---

## Overview

Connect Command Centre to Clarity App (Django) via an HTTP API bridge. Add 10 new voice intents that call Clarity's REST API (same pattern as existing Plane handlers), a webhook endpoint for receiving Clarity events as notifications, shared parking lot sync, enhanced morning brief, and mobile deployment.

## User Stories

- As a user, I want to ask "What's my schedule status?" and hear a summary from Clarity
- As a user, I want to say "Add to parking lot: call supplier" and have it saved in Clarity's ADHD Bridge
- As a user, I want Clarity events (schedule changes, overdue reviews) to appear in my Command Centre inbox
- As a user, I want my morning brief enriched with Clarity data (overdue reviews, pending actions)

## Success Criteria

- [ ] 10 new voice intents correctly classify and call Clarity API endpoints
- [ ] ClarityClient handles Clarity offline gracefully (friendly error, no crash)
- [ ] Webhook endpoint receives Clarity events and creates NotificationRecords
- [ ] Parking lot voice capture syncs to Clarity's ADHD Bridge
- [ ] Morning brief includes Clarity data with graceful degradation
- [ ] Settings UI allows configuring Clarity API URL and key

---

## Mandatory Reading

Before implementation, read these files to understand patterns:

| File | Purpose | Key Lines |
|------|---------|-----------|
| `backend/src/clarity_backend/integrations/plane.py` | **Template for ClarityClient** — httpx wrapper, auth headers, error handling | All (130 lines) |
| `backend/src/clarity_backend/voice/intent.py` | Intent patterns, `classify()`, `_extract_params()` | 30-151 |
| `backend/src/clarity_backend/voice/commands.py` | Handler pattern — `execute()` dispatch, Plane handlers as template | 289-430 |
| `backend/src/clarity_backend/voice/ai_classifier.py` | AI fallback — needs Clarity intents added to system prompt | 16-32 |
| `backend/src/clarity_backend/webhooks/posthog.py` | Webhook receiver pattern — validation, dedup, DB insert | All (60 lines) |
| `backend/src/clarity_backend/notifications/crud.py` | `save_notification()` — how to persist NotificationRecords | 12-50 |
| `backend/src/clarity_backend/notifications/models.py` | `Source` enum, `Notification` model, `NotificationType` | All (90 lines) |
| `backend/src/clarity_backend/config.py` | `Settings` class — where to add CLARITY_* env vars | 26-79 |
| `backend/src/clarity_backend/settings/manager.py` | `DEFAULT_SETTINGS`, `_read_settings()`, `SECRET_KEYS` | 14-30, 59-71 |
| `backend/src/clarity_backend/brief/morning.py` | Morning brief endpoint — where to merge Clarity data | All (83 lines) |
| `backend/src/clarity_backend/main.py` | Router registration — where to add clarity webhook router | 52-64 |
| `src/app/settings/page.tsx` | Settings form — where to add Clarity fields | 12-24, 42-60 |

## Patterns to Follow

### HTTP Client (from PlaneClient)
- Class wraps `httpx.AsyncClient` with `timeout=30.0`
- Auth via `self._headers` property returning `{"X-API-Key": self.api_key}`
- Each method creates a fresh `async with httpx.AsyncClient()` context
- `response.raise_for_status()` for error propagation
- Constructor cleans up base URL trailing slashes

### Voice Intent (from intent.py)
- Constants at top: `CLARITY_SCHEDULE_STATUS = "clarity_schedule_status"`
- Patterns in `INTENT_PATTERNS` list — order matters (first match wins)
- Clarity patterns should go AFTER Plane patterns, BEFORE generic patterns
- Params extracted in `_extract_params()` with dedicated `elif` branches

### Voice Handler (from commands.py)
- Async function signature: `async def _handler(intent: Intent, session: AsyncSession) -> dict`
- Returns `{"response": str, "data": dict}`
- Template strings in `TEMPLATES` dict
- Registered in `HANDLERS` dict at bottom
- External API handlers (Plane) don't use `session` for queries — they call external APIs directly

### Webhook Receiver (from posthog.py)
- Router with `prefix="/webhooks"`
- Validates payload, creates DB records via session
- Returns counts: `{"ingested": N}`

### Notification Ingestion (from crud.py)
- Use `save_notification()` with a `Notification` model instance
- Deduplicates by `(source, source_id)`
- After saving, broadcast via `ws_manager.send_new(notification_dict)`

### Settings
- New keys added to `DEFAULT_SETTINGS` dict and `SECRET_KEYS` set
- New env vars added to `Settings` class in `config.py`
- Frontend `FormData` type extended with new fields

---

## Implementation Tasks

### Phase 1: Foundation — ClarityClient + Config

#### Task 1.1: Add Clarity env vars to config.py
**Status**: todo

**Description**: Add `CLARITY_API_URL` and `CLARITY_API_KEY` to the `Settings` pydantic model.

**Files**:
- Modify: `backend/src/clarity_backend/config.py:26-79`

**Changes**:
```python
# Add after POSTHOG_HOST line (~line 36):
CLARITY_API_URL: str = "http://localhost:8000"
CLARITY_API_KEY: str = ""
```

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.config import settings; print(settings.CLARITY_API_URL)"
```

**Acceptance Criteria**:
- [ ] `CLARITY_API_URL` defaults to `http://localhost:8000`
- [ ] `CLARITY_API_KEY` defaults to empty string
- [ ] Can be overridden via env vars

---

#### Task 1.2: Add Clarity settings to settings manager
**Status**: todo

**Description**: Add `clarity_api_url` and `clarity_api_key` to `DEFAULT_SETTINGS` and `SECRET_KEYS`. Add fields to `SettingsUpdate` model.

**Files**:
- Modify: `backend/src/clarity_backend/settings/manager.py:14-71`

**Changes**:
- Add `"clarity_api_url": "http://localhost:8000"` and `"clarity_api_key": ""` to `DEFAULT_SETTINGS`
- Add `"clarity_api_key"` to `SECRET_KEYS`
- Add `clarity_api_url: str | None = None` and `clarity_api_key: str | None = None` to `SettingsUpdate`

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.settings.manager import _read_settings; s = _read_settings(); print(s.get('clarity_api_url'))"
```

**Acceptance Criteria**:
- [ ] Settings include Clarity fields with defaults
- [ ] API key is masked in GET responses

---

#### Task 1.3: Create ClarityClient
**Status**: todo

**Description**: Create `integrations/clarity.py` modelled on `PlaneClient`. Wraps all Clarity API calls with auth headers, timeout, and error handling.

**Files**:
- Create: `backend/src/clarity_backend/integrations/clarity.py`

**Design**:
```python
class ClarityClient:
    def __init__(self, base_url: str, api_key: str) -> None: ...

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    # Phase 1 methods:
    async def get_schedule_dashboard(self, client_id: str) -> dict: ...
    async def get_compliance_summary(self, client_id: str) -> dict: ...
    async def get_unified_inbox(self) -> dict: ...
    async def get_upcoming_actions(self) -> dict: ...
    async def create_parking_lot_item(self, content: str) -> dict: ...
    async def start_blitz(self) -> dict: ...
    async def get_gamification_profile(self) -> dict: ...
    async def start_email_review(self) -> dict: ...
    async def check_compliance(self, ingredient: str, market: str | None = None) -> dict: ...
    async def rag_query(self, query: str) -> dict: ...

    # Phase 4 methods:
    async def get_email_analytics(self) -> dict: ...
```

**Key patterns**:
- Each method: `async with httpx.AsyncClient(timeout=10.0)` (shorter than Plane's 30s — localhost is fast)
- Raise `ClarityOfflineError(httpx.ConnectError)` for connection failures
- Helper: `def _get_clarity_client() -> ClarityClient` that reads settings + env vars (same pattern as `_get_project_resolver()` in commands.py)

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.integrations.clarity import ClarityClient; c = ClarityClient('http://localhost:8000', 'test'); print(c._headers)"
```

**Acceptance Criteria**:
- [ ] ClarityClient has methods for all 10 Clarity API endpoints
- [ ] Uses `X-API-Key` header authentication
- [ ] Raises custom `ClarityOfflineError` on connection failure
- [ ] Timeout set to 10s for localhost calls

---

### Phase 2: Voice Intents + Handlers

#### Task 2.1: Add Clarity intent constants and regex patterns
**Status**: todo

**Description**: Add 10 new intent type constants and regex patterns to `intent.py`. Patterns go AFTER Plane patterns, BEFORE the generic error/vuln/status patterns.

**Files**:
- Modify: `backend/src/clarity_backend/voice/intent.py:10-50`

**New constants**:
```python
CLARITY_SCHEDULE_STATUS = "clarity_schedule_status"
CLARITY_COMPLIANCE = "clarity_compliance"
CLARITY_PARKING_LOT_ADD = "clarity_parking_lot_add"
CLARITY_START_BLITZ = "clarity_start_blitz"
CLARITY_XP_STATUS = "clarity_xp_status"
CLARITY_RUN_EMAIL_REVIEW = "clarity_run_email_review"
CLARITY_UPCOMING_ACTIONS = "clarity_upcoming_actions"
CLARITY_RAG_QUERY = "clarity_rag_query"
CLARITY_INGREDIENT_CHECK = "clarity_ingredient_check"
CLARITY_UNIFIED_INBOX = "clarity_unified_inbox"
```

**New patterns** (insert after PLANE_LIST_TASKS, before QUERY_ERRORS):
```python
# Clarity intents — must come before generic status/email patterns
(r"schedule.*(status|dashboard)|product.*status", CLARITY_SCHEDULE_STATUS),
(r"compliance\s+(for|summary|check)|show\s+compliance", CLARITY_COMPLIANCE),
(r"parking\s+lot|capture|quick\s+note|remember\s+this", CLARITY_PARKING_LOT_ADD),
(r"(start|begin)\s+(a\s+)?blitz|focus\s+session|pomodoro|sprint\s+session", CLARITY_START_BLITZ),
(r"\b(xp|level|streak|points|gamification)\b", CLARITY_XP_STATUS),
(r"review\s+emails?|email\s+review|triage\s+emails?", CLARITY_RUN_EMAIL_REVIEW),
(r"upcoming|due\s+soon|what.s\s+next|action\s+points?", CLARITY_UPCOMING_ACTIONS),
(r"regulation|regulatory|novel\s+food|is\s+\w+\s+allowed", CLARITY_RAG_QUERY),
(r"ingredient|substance|compliant|allowed\s+in", CLARITY_INGREDIENT_CHECK),
(r"unified\s+inbox|what.s\s+urgent|priority\s+items?", CLARITY_UNIFIED_INBOX),
```

**Important ordering note**: `CLARITY_RUN_EMAIL_REVIEW` must come BEFORE the generic `READ_EMAILS` pattern (which matches `email`). `CLARITY_SCHEDULE_STATUS` must come BEFORE `CHECK_STATUS` (which matches `status`).

**Validation**:
```bash
cd backend && uv run python -c "
from clarity_backend.voice.intent import classify
tests = [
    ('what is my schedule status', 'clarity_schedule_status'),
    ('add to parking lot buy milk', 'clarity_parking_lot_add'),
    ('start a blitz session', 'clarity_start_blitz'),
    ('how much xp do I have', 'clarity_xp_status'),
    ('review my emails', 'clarity_run_email_review'),
    ('is retinol allowed in germany', 'clarity_ingredient_check'),
]
for text, expected in tests:
    result = classify(text)
    status = '✓' if result.type == expected else f'✗ got {result.type}'
    print(f'{status}: {text}')
"
```

**Acceptance Criteria**:
- [ ] All 10 Clarity intents correctly classified
- [ ] No collision with existing Plane/error/status intents
- [ ] Parameters extracted (client_id, ingredient, market, content, query)

---

#### Task 2.2: Add `_extract_params` branches for Clarity intents
**Status**: todo

**Description**: Add parameter extraction logic for Clarity intents in `_extract_params()`.

**Files**:
- Modify: `backend/src/clarity_backend/voice/intent.py:77-151`

**Key extractions**:
- `CLARITY_SCHEDULE_STATUS`: extract client name if mentioned
- `CLARITY_COMPLIANCE`: extract client name
- `CLARITY_PARKING_LOT_ADD`: extract content after "parking lot" / "capture" / "remember"
- `CLARITY_INGREDIENT_CHECK`: extract ingredient name and market ("in germany")
- `CLARITY_RAG_QUERY`: extract query text after "about" / "regulation"
- `CLARITY_UNIFIED_INBOX`: no params needed
- Others: no params needed (simple triggers)

**Validation**: Same test script as Task 2.1, checking `params` values.

**Acceptance Criteria**:
- [ ] Parking lot content correctly extracted from "add to parking lot: call supplier"
- [ ] Ingredient and market extracted from "is retinol compliant in germany"
- [ ] RAG query text extracted from "ask about novel food regulation"

---

#### Task 2.3: Add Clarity command handlers
**Status**: todo

**Description**: Add 10 new async handler functions to `commands.py`, plus templates and HANDLERS registration. Handlers call `ClarityClient` methods and format TTS-friendly responses.

**Files**:
- Modify: `backend/src/clarity_backend/voice/commands.py`

**Design pattern** (follow `_handle_plane_list_tasks`):
```python
async def _handle_clarity_schedule_status(intent: Intent, session: AsyncSession) -> dict:
    from clarity_backend.integrations.clarity import ClarityOfflineError, _get_clarity_client
    try:
        client = _get_clarity_client()
        data = await client.get_schedule_dashboard(intent.params.get("client_id", "default"))
        # Format TTS response from data
        return {"response": "...", "data": data}
    except ClarityOfflineError:
        return {"response": "Clarity is not available right now. Is it running?", "data": {}}
    except Exception as e:
        return {"response": f"Failed to reach Clarity: {e}", "data": {}}
```

**All 10 handlers follow this pattern**:
1. Get `ClarityClient` via helper
2. Call the appropriate method with extracted params
3. Format response as TTS-friendly text
4. Catch `ClarityOfflineError` → friendly message
5. Register in `HANDLERS` dict

**Templates to add**:
```python
CLARITY_SCHEDULE_STATUS: "Schedule status: {summary}",
CLARITY_COMPLIANCE: "Compliance summary for {client}: {summary}",
CLARITY_PARKING_LOT_ADD: "Added to parking lot: {content}",
CLARITY_START_BLITZ: "Blitz session started. {duration} minutes. Go!",
CLARITY_XP_STATUS: "You have {xp} XP, level {level}. Current streak: {streak} days.",
CLARITY_RUN_EMAIL_REVIEW: "Email review started. {count} emails queued for AI review.",
CLARITY_UPCOMING_ACTIONS: "You have {count} upcoming action{s}. {summary}",
CLARITY_RAG_QUERY: "{answer}",
CLARITY_INGREDIENT_CHECK: "{ingredient} is {status} in {market}. {detail}",
CLARITY_UNIFIED_INBOX: "Your Clarity inbox has {count} item{s}. {summary}",
```

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.voice.commands import HANDLERS; print([k for k in HANDLERS if k.startswith('clarity')])"
```

**Acceptance Criteria**:
- [ ] All 10 handlers registered in HANDLERS dict
- [ ] Each handler catches ClarityOfflineError gracefully
- [ ] TTS responses are concise and natural-sounding
- [ ] No handler uses the local SQLite session (all call ClarityClient)

---

#### Task 2.4: Update AI classifier with Clarity intents
**Status**: todo

**Description**: Add Clarity intent types to the Ollama system prompt in `ai_classifier.py` so the AI fallback can classify Clarity commands.

**Files**:
- Modify: `backend/src/clarity_backend/voice/ai_classifier.py:16-32`

**Changes**: Add Clarity intent types to the `SYSTEM_PROMPT` intent list:
```
- clarity_schedule_status: user asks about schedule/product status in Clarity
- clarity_compliance: user asks about compliance for a client
- clarity_parking_lot_add: user wants to capture/remember something
- clarity_start_blitz: user wants to start a focus/blitz session
- clarity_xp_status: user asks about XP/level/streak/gamification
- clarity_run_email_review: user wants to run AI email review
- clarity_upcoming_actions: user asks about upcoming actions/deadlines
- clarity_rag_query: user asks about regulations
- clarity_ingredient_check: user asks if an ingredient is compliant
- clarity_unified_inbox: user asks about priority/urgent items in Clarity
```

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.voice.ai_classifier import SYSTEM_PROMPT; print('clarity_schedule_status' in SYSTEM_PROMPT)"
```

**Acceptance Criteria**:
- [ ] All 10 Clarity intent types in AI classifier prompt
- [ ] AI can classify ambiguous Clarity commands as fallback

---

### Phase 3: Settings UI

#### Task 3.1: Add Clarity settings to frontend
**Status**: todo

**Description**: Add Clarity API URL and API Key fields to the Settings page. Add a "Test Connection" button.

**Files**:
- Modify: `src/app/settings/page.tsx`
- Modify: `src/lib/api.ts` (add `clarity_api_url` and `clarity_api_key` to `AppSettings` type)

**Changes**:
- Add `clarity_api_url` and `clarity_api_key` to `FormData` type and `toForm()`
- Add a "Clarity App" section in the settings form with URL + API key inputs
- Optional: "Test Connection" button that calls `GET /health` on the Clarity URL

**Validation**:
```bash
cd /Users/chidionyejuruwa/Development/voice-command && npm run build
```

**Acceptance Criteria**:
- [ ] Clarity API URL and Key fields visible in Settings
- [ ] Values save and load correctly
- [ ] API key is masked like other secrets

---

### Phase 4: Webhook Receiver (Clarity → Command Centre)

#### Task 4.1: Add "clarity" to Source enum
**Status**: todo

**Description**: Add `CLARITY = "clarity"` to the `Source` enum and a new `NotificationType` if needed.

**Files**:
- Modify: `backend/src/clarity_backend/notifications/models.py:9-27`

**Changes**:
```python
class Source(StrEnum):
    ...
    CLARITY = "clarity"

class NotificationType(StrEnum):
    ...
    SCHEDULE_UPDATE = "schedule_update"
    COMPLIANCE_ALERT = "compliance_alert"
    ACTION_POINT = "action_point"
```

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.notifications.models import Source; print(Source.CLARITY)"
```

**Acceptance Criteria**:
- [ ] Source.CLARITY available
- [ ] New NotificationType values available

---

#### Task 4.2: Create webhook endpoint
**Status**: todo

**Description**: Create `webhooks/clarity.py` with a `POST /webhooks/clarity` endpoint. Validates webhook secret, maps event types to NotificationRecords, saves via `save_notification()`, and broadcasts via WebSocket.

**Files**:
- Create: `backend/src/clarity_backend/webhooks/clarity.py`

**Design** (follow posthog.py pattern):
```python
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/clarity")
async def clarity_webhook(payload: dict, session: AsyncSession = Depends(get_session)) -> dict:
    # 1. Validate X-Webhook-Secret header
    # 2. Map event_type to NotificationType
    # 3. Create Notification model instance
    # 4. save_notification(session, notification)
    # 5. Broadcast via ws_manager
    # 6. Return {"ingested": 1}
```

**Event types to handle**:
- `schedule_status_change` → "Product X changed to Approved in France"
- `action_point_created` → "New action point: respond to [client] by Thursday"
- `review_overdue` → "Formula review for [product] is 2 days overdue"
- `registration_submitted` → "Spain registration submitted for [product]"
- `compliance_failed` → "Ingredient [X] failed compliance for [market]"

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.webhooks.clarity import router; print([r.path for r in router.routes])"
```

**Acceptance Criteria**:
- [ ] Endpoint validates webhook secret
- [ ] Maps all 5 event types to notifications
- [ ] Notifications appear in inbox via WebSocket broadcast
- [ ] Unknown event types are logged but don't error

---

#### Task 4.3: Register webhook router in main.py
**Status**: todo

**Description**: Import and register the clarity webhook router.

**Files**:
- Modify: `backend/src/clarity_backend/main.py:19-64`

**Changes**:
```python
from clarity_backend.webhooks.clarity import router as clarity_webhook_router
# ...
app.include_router(clarity_webhook_router)
```

**Validation**:
```bash
cd backend && uv run python -c "from clarity_backend.main import app; print([r.path for r in app.routes if 'clarity' in str(r.path)])"
```

**Acceptance Criteria**:
- [ ] `/webhooks/clarity` endpoint accessible
- [ ] App starts without errors

---

#### Task 4.4: Add clarity_webhook_secret to settings
**Status**: todo

**Description**: Add `clarity_webhook_secret` to config, settings manager, and frontend.

**Files**:
- Modify: `backend/src/clarity_backend/config.py`
- Modify: `backend/src/clarity_backend/settings/manager.py`

**Changes**:
- Add `CLARITY_WEBHOOK_SECRET: str = ""` to Settings
- Add `"clarity_webhook_secret": ""` to DEFAULT_SETTINGS
- Add to SECRET_KEYS set

**Acceptance Criteria**:
- [ ] Webhook secret configurable via env var or settings UI

---

### Phase 5: Shared Parking Lot

#### Task 5.1: Dual-write parking lot captures
**Status**: todo

**Description**: Modify the parking lot voice handler (from Task 2.3) to also POST to Clarity's `api/adhd/parking-lot/` endpoint. If Clarity is offline, the local capture still succeeds.

**Files**:
- Modify: `backend/src/clarity_backend/voice/commands.py` (the `_handle_clarity_parking_lot_add` handler)

**Design**:
The handler from Task 2.3 already calls Clarity. This task adds a **local fallback**: if Clarity is offline, store the item locally (e.g., as a NotificationRecord with source="clarity" and type="reminder") so it's not lost. On next Clarity connection, could optionally sync.

For MVP: just call Clarity. If offline, return "Saved locally — will sync when Clarity is available." and store as a local notification.

**Validation**:
```bash
# Manual: say "add to parking lot: test item" with Clarity running and stopped
```

**Acceptance Criteria**:
- [ ] Parking lot item created in Clarity when online
- [ ] Friendly message when Clarity is offline
- [ ] Item not lost if Clarity is down

---

### Phase 6: Enhanced Morning Brief

#### Task 6.1: Enrich morning brief with Clarity data
**Status**: todo

**Description**: Modify `brief/morning.py` to call Clarity's API for additional data and merge into the response.

**Files**:
- Modify: `backend/src/clarity_backend/brief/morning.py`

**Changes**:
- Add new fields to `MorningBriefResponse`: `overdue_reviews`, `pending_email_actions`, `approaching_deadlines`
- In `morning_brief()`, call `ClarityClient.get_email_analytics()` and schedule dashboard
- Wrap Clarity calls in try/except — if offline, return `None` for Clarity fields
- Existing local data always returned regardless

**New response fields**:
```python
class MorningBriefResponse(BaseModel):
    # Existing
    new_errors_24h: int
    new_vulns_24h: int
    actioned_yesterday: int
    pending_total: int
    top_severity: str | None
    # New — Clarity data (None if offline)
    overdue_reviews: int | None = None
    pending_email_actions: int | None = None
    approaching_deadlines: list[str] | None = None
    clarity_available: bool = False
```

**Validation**:
```bash
cd backend && uv run pytest tests/ -k "brief" -v
```

**Acceptance Criteria**:
- [ ] Brief returns Clarity data when available
- [ ] Brief works normally when Clarity is offline (fields are None)
- [ ] Frontend morning brief component handles new fields

---

#### Task 6.2: Update frontend MorningBrief component
**Status**: todo

**Description**: Display Clarity data in the MorningBrief component on the home page.

**Files**:
- Modify: `src/components/MorningBrief.tsx` (or wherever the component lives)

**Changes**:
- Show overdue reviews count, pending email actions, approaching deadlines
- Show "Clarity offline" indicator if `clarity_available` is false
- Keep existing data display unchanged

**Validation**:
```bash
npm run build
```

**Acceptance Criteria**:
- [ ] Clarity data displayed when available
- [ ] Graceful display when Clarity is offline

---

### Phase 7: Mobile Access

#### Task 7.1: Verify mobile-responsive layout
**Status**: todo

**Description**: Test the existing responsive layout on mobile screen sizes. Fix any issues with the voice button, inbox, and triage views.

**Files**:
- Potentially modify: `src/components/VoiceButton.tsx`, `src/app/inbox/page.tsx`, `src/components/Navigation.tsx`

**Validation**:
```bash
# Manual: test in Chrome DevTools mobile view (iPhone 14, Pixel 7)
```

**Acceptance Criteria**:
- [ ] Voice button accessible and functional on mobile
- [ ] Inbox readable with proper card layout
- [ ] Navigation works (bottom bar visible)

---

#### Task 7.2: Deploy static export
**Status**: todo

**Description**: Deploy the Next.js static export to a hosting service for mobile browser access.

**Changes**:
- Verify `next.config.js` has `output: "export"` for static generation
- Deploy to Vercel or preferred host
- Configure API URL env var for production backend

**Validation**:
```bash
npm run build && ls out/
```

**Acceptance Criteria**:
- [ ] Static export builds successfully
- [ ] Deployed and accessible from mobile browser
- [ ] Voice commands work from mobile (Whisper API)

---

### Phase 8: Testing

#### Task 8.1: Unit tests for ClarityClient
**Status**: todo

**Description**: Test ClarityClient methods with mocked httpx responses.

**Files**:
- Create: `backend/tests/test_clarity_client.py`

**Test cases**:
- Successful API calls return expected data
- Connection errors raise ClarityOfflineError
- Timeout errors raise ClarityOfflineError
- Auth header is correct

---

#### Task 8.2: Unit tests for Clarity voice intents
**Status**: todo

**Description**: Test intent classification for all 10 new Clarity patterns.

**Files**:
- Modify: `backend/tests/test_intent.py` (or create if not exists)

**Test cases**:
- Each intent matches expected phrases
- No collision with existing intents (test existing phrases still work)
- Parameter extraction correct for parking lot, ingredient check, RAG query

---

#### Task 8.3: Unit tests for Clarity command handlers
**Status**: todo

**Description**: Test handlers with mocked ClarityClient.

**Files**:
- Create: `backend/tests/test_clarity_commands.py`

**Test cases**:
- Each handler returns correct response format
- ClarityOfflineError produces friendly message
- Params are correctly passed to ClarityClient methods

---

#### Task 8.4: Integration test for webhook endpoint
**Status**: todo

**Description**: Test `/webhooks/clarity` with sample payloads.

**Files**:
- Create: `backend/tests/test_clarity_webhook.py`

**Test cases**:
- Valid payload creates NotificationRecord
- Invalid secret returns 401
- Unknown event type returns 200 (logged, not errored)
- Notification appears in inbox query

---

## Edge Cases

| Case | Expected Behavior | Test Coverage |
|------|-------------------|---------------|
| Clarity not running | Handler returns "Clarity is not available right now" | test_clarity_commands.py |
| Clarity returns 401 (bad API key) | Handler returns "Authentication failed — check your API key" | test_clarity_client.py |
| Clarity returns 500 | Handler returns "Clarity encountered an error" | test_clarity_client.py |
| Webhook with unknown event_type | Log warning, return 200, don't create notification | test_clarity_webhook.py |
| Webhook with missing secret header | Return 401 | test_clarity_webhook.py |
| Voice "check emails" vs "review emails" | "check emails" → READ_EMAILS (local), "review emails" → CLARITY_RUN_EMAIL_REVIEW | test_intent.py |
| Voice "status" vs "schedule status" | "status" → CHECK_STATUS, "schedule status" → CLARITY_SCHEDULE_STATUS | test_intent.py |
| Morning brief with Clarity offline | Returns local data + None for Clarity fields | test_brief.py |

---

## Validation Approach

### Level 1: Static Analysis
```bash
cd backend && uv run ruff check . && uv run ruff format --check .
```

### Level 2: Unit Tests
```bash
cd backend && uv run pytest tests/ -v --tb=short
```

### Level 3: Integration Tests
```bash
cd backend && uv run pytest tests/ -v -k "integration"
```

### Level 4: Build Verification
```bash
npm run build
cd backend && uv run python -c "from clarity_backend.main import app; print('App OK')"
```

### Level 5: Manual Voice Testing
- [ ] "What's my schedule status?" → Clarity response or offline message
- [ ] "Add to parking lot: call supplier" → Saved in Clarity
- [ ] "Start a blitz session" → Blitz started
- [ ] "How much XP do I have?" → XP stats
- [ ] "Is retinol compliant in Germany?" → Compliance result
- [ ] "Review my emails" → Email review started (not confused with "check emails")

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Clarity not running during voice command | Medium | Medium | ClarityOfflineError → friendly message |
| Regex collisions with existing intents | Low | High | Order Clarity patterns carefully; comprehensive intent tests |
| Clarity API response format changes | Low | Medium | ClarityClient methods handle missing fields with defaults |
| Webhook delivery failures | Medium | Low | Retry logic in Clarity sender; log failures |
| Mobile audio capture issues | Medium | Medium | Test on actual devices; fallback to text input |

---

## Research Findings

### From Codebase
- **PlaneClient** (`integrations/plane.py`) is the exact template for ClarityClient — same httpx pattern, same auth header style
- **Voice commands.py** already has two tiers: local DB handlers and external API handlers (Plane). Clarity handlers follow the Plane tier.
- **Webhook pattern** (`webhooks/posthog.py`) shows how to receive, validate, and ingest external events
- **Notification crud** (`save_notification()`) handles deduplication — reuse for Clarity webhook events
- **AI classifier** (`ai_classifier.py`) needs intent list updated or Clarity commands will never be AI-classified
- **Source enum** needs `CLARITY` added for webhook notifications to render correctly in the inbox UI

---

*Ready for implementation with `/prp-implement .claude/PRPs/plans/clarity-app-integration.plan.md`*
