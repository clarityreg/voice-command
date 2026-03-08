# Implementation Plan: Inbox Actioned, Sync & Search

**Created**: 2026-03-07
**Status**: Ready for Implementation

---

## Overview

Add an "Actioned" button to the inbox that applies a label/category to emails in Gmail and Outlook (write-back to source), a manual "Sync" button to pull fresh emails, backend-powered search, and a cache strategy that syncs latest emails live while loading older emails on demand from the DB.

## User Stories

- As a user, I want to mark an email as "Actioned" so it gets a label in Gmail / category in Outlook and is visually distinct in my inbox
- As a user, I want to click "Sync" to immediately pull the latest emails without waiting for the 30s poll
- As a user, I want to search my inbox from the sidebar and get results from all cached emails (not just the in-memory set)
- As a user, I want my inbox to show the latest emails in real-time, and let me scroll to load older cached emails

## Success Criteria

- [ ] Clicking "Actioned" on a Gmail email adds a "Clarity/Actioned" label via Gmail API
- [ ] Clicking "Actioned" on an Outlook email adds a "Clarity - Actioned" category via Graph API
- [ ] "Actioned" sets triage_status to "actioned" locally and the notification moves to an actioned visual state
- [ ] Sync button triggers immediate fetch_recent on all connected email services
- [ ] Backend search endpoint returns results from the DB (title, body, sender_name)
- [ ] Inbox loads latest 50 notifications; scrolling to bottom loads the next page from DB
- [ ] Keyboard shortcut `d` marks selected notification as actioned

---

## Mandatory Reading

Before implementation, read these files to understand patterns:

| File | Purpose | Key Lines |
|------|---------|-----------|
| `backend/src/clarity_backend/services/gmail.py` | Gmail API patterns, executor usage, label handling | 66-93, 161-200 |
| `backend/src/clarity_backend/services/outlook.py` | Graph API patterns, httpx async, category handling | 38-58, 92-110 |
| `backend/src/clarity_backend/services/base.py` | BaseService interface, emit_notification flow | 9-82 |
| `backend/src/clarity_backend/notifications/routes.py` | Action handler pattern (archive/snooze/reply) | 22-71 |
| `backend/src/clarity_backend/notifications/crud.py` | DB read/write patterns, deduplication, load_notifications | 11-106 |
| `backend/src/clarity_backend/notifications/models.py` | TriageStatus enum (actioned already exists!), NotificationAction | 35-67 |
| `src/components/NotificationDetail.tsx` | Action button UI patterns, callback structure | 115-137 |
| `src/components/NotificationCard.tsx` | Card UI, quick-action button pattern | 90-97 |
| `src/hooks/useNotifications.ts` | Reducer, filtering, sorting, unread counts | Full file |
| `src/lib/notificationApi.ts` | API helper patterns (archiveNotification, etc.) | Full file |
| `src/app/inbox/page.tsx` | Page-level handlers, keyboard shortcuts | 30-111 |

## Patterns to Follow

### Backend Actions
- Follow the `archive` action pattern in `routes.py:47-52`: update DB status → broadcast WS update → return status
- Follow the `reply` pattern for service-level write operations: get service from registry → call method → handle errors

### Gmail API Write
- Use `run_in_executor` wrapping `self._gmail_client.users().messages().modify()` — same pattern as `reply()` at `gmail.py:161`
- Label creation: `users().labels().create()` with `{"name": "Clarity/Actioned", "labelListVisibility": "labelShow"}`

### Outlook Graph API Write
- Use `httpx.AsyncClient` PATCH — same pattern as `reply()` at `outlook.py:92`
- Categories: `PATCH /me/messages/{id}` with `{"categories": ["Clarity - Actioned"]}`

### Frontend Actions
- Follow `handleArchive` pattern in `page.tsx:43-53`: optimistic local update → fire API call → handle WS broadcast
- Follow `archiveNotification` API helper pattern in `notificationApi.ts:28-33`

---

## Implementation Tasks

### Phase 1: Gmail & Outlook Write-Back Methods

#### Task 1.1: Gmail — add_label and ensure_label methods
**Status**: todo

**Description**: Add methods to `GmailService` to create a "Clarity/Actioned" label (idempotently) and apply it to a message. Gmail labels are per-account, so we create once and cache the label ID.

**Files**:
- Modify: `backend/src/clarity_backend/services/gmail.py`

**Implementation**:
```python
# Add to GmailService.__init__:
self._actioned_label_id: str | None = None

# New methods:
async def _ensure_actioned_label(self) -> str | None:
    """Create 'Clarity/Actioned' label if it doesn't exist, return label ID."""
    if self._actioned_label_id:
        return self._actioned_label_id
    # List labels, find existing
    labels = await asyncio.get_event_loop().run_in_executor(
        None, lambda: self._gmail_client.users().labels().list(userId="me").execute()
    )
    for label in labels.get("labels", []):
        if label["name"] == "Clarity/Actioned":
            self._actioned_label_id = label["id"]
            return label["id"]
    # Create it
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: self._gmail_client.users().labels().create(
            userId="me", body={"name": "Clarity/Actioned", "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        ).execute()
    )
    self._actioned_label_id = result["id"]
    return result["id"]

async def add_label(self, message_id: str, label_name: str = "Clarity/Actioned") -> bool:
    """Add a label to a Gmail message."""
    try:
        label_id = await self._ensure_actioned_label()
        if not label_id:
            return False
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._gmail_client.users().messages().modify(
                userId="me", id=message_id, body={"addLabelIds": [label_id]}
            ).execute()
        )
        return True
    except Exception as e:
        print(f"[Gmail] Error adding label: {e}")
        return False
```

**Validation**:
```bash
cd backend && DOTENV_CONFIG=1 uv run pytest tests/test_gmail_service.py -v --tb=short
```

**Acceptance Criteria**:
- [ ] `_ensure_actioned_label()` creates label on first call, returns cached ID on subsequent calls
- [ ] `add_label()` applies the label to the specified message
- [ ] Errors are caught and logged, return False

---

#### Task 1.2: Outlook — add_category method
**Status**: todo

**Description**: Add method to `OutlookService` to apply a "Clarity - Actioned" category to a message via Graph API PATCH.

**Files**:
- Modify: `backend/src/clarity_backend/services/outlook.py`

**Implementation**:
```python
async def add_category(self, message_id: str, category: str = "Clarity - Actioned") -> bool:
    """Add a category to an Outlook message."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get existing categories first to avoid overwriting
            resp = await client.get(
                f"{self.GRAPH_BASE}/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={"$select": "categories"},
            )
            resp.raise_for_status()
            existing = resp.json().get("categories", [])
            if category in existing:
                return True  # Already applied
            # PATCH to add category
            resp = await client.patch(
                f"{self.GRAPH_BASE}/me/messages/{message_id}",
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                },
                json={"categories": [*existing, category]},
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        print(f"[Outlook] Error adding category: {e}")
        return False
```

**Validation**:
```bash
cd backend && DOTENV_CONFIG=1 uv run pytest tests/test_outlook_service.py -v --tb=short
```

**Acceptance Criteria**:
- [ ] `add_category()` PATCHes the message with the category
- [ ] Preserves existing categories (appends, doesn't overwrite)
- [ ] Idempotent — skips if category already present
- [ ] Errors caught, returns False

---

### Phase 2: "Actioned" Action Handler

#### Task 2.1: Backend action route for "actioned"
**Status**: todo

**Description**: Add "actioned" to the `NotificationAction` literal and handle it in the action endpoint. The handler should: (1) update local triage_status to "actioned", (2) call the source service to write-back the label/category, (3) broadcast WS update.

**Files**:
- Modify: `backend/src/clarity_backend/notifications/models.py` — add "actioned" to NotificationAction.action literal
- Modify: `backend/src/clarity_backend/notifications/routes.py` — add actioned handler block
- Modify: `backend/src/clarity_backend/notifications/crud.py` — add helper to get notification record by ID

**Implementation in routes.py** (new elif block after snooze):
```python
elif action.action == "actioned":
    # 1. Update local status
    updated = await update_triage_status(session, notification_id, "actioned")
    if not updated:
        raise HTTPException(404, f"Notification {notification_id} not found")

    # 2. Write back label/category to source email
    record = await get_notification_by_id(session, notification_id)
    if record and record["source"] in ("gmail", "outlook"):
        from clarity_backend.notifications.models import Source
        from clarity_backend.services.registry import registry
        source_enum = Source(record["source"])
        service = registry.get_service_for_reply(source_enum, record["source_account"])
        if service:
            if source_enum == Source.GMAIL:
                await service.add_label(record["source_id"])
            elif source_enum == Source.OUTLOOK:
                await service.add_category(record["source_id"])

    # 3. Broadcast
    await ws_manager.send_update(notification_id, {"triage_status": "actioned"})
    return {"status": "actioned"}
```

**Validation**:
```bash
cd backend && DOTENV_CONFIG=1 uv run pytest tests/ -v --tb=short -k "action"
```

**Acceptance Criteria**:
- [ ] POST `/api/notifications/{id}/action` with `{"action": "actioned"}` updates DB and returns 200
- [ ] Gmail emails get "Clarity/Actioned" label applied
- [ ] Outlook emails get "Clarity - Actioned" category applied
- [ ] Non-email notifications (slack, posthog) still get status updated without write-back
- [ ] WS broadcast sent so other clients update

---

#### Task 2.2: CRUD helper — get_notification_by_id
**Status**: todo

**Description**: Add a helper function to `crud.py` that fetches a single notification record by ID (needed by actioned handler to get source/source_id/source_account for write-back).

**Files**:
- Modify: `backend/src/clarity_backend/notifications/crud.py`

**Implementation**:
```python
async def get_notification_by_id(session: AsyncSession, notification_id: str) -> dict | None:
    record = await session.get(NotificationRecord, notification_id)
    if not record:
        return None
    return _record_to_dict(record)
```

**Validation**:
```bash
cd backend && DOTENV_CONFIG=1 uv run pytest tests/ -v --tb=short
```

**Acceptance Criteria**:
- [ ] Returns dict or None
- [ ] Used by actioned handler to resolve source details

---

### Phase 3: Manual Sync Endpoint

#### Task 3.1: Backend sync endpoint
**Status**: todo

**Description**: Add `POST /api/sync` endpoint that triggers `fetch_recent()` on all connected email services (Gmail + Outlook) and saves results to DB. Returns the count of new/updated notifications.

**Files**:
- Modify: `backend/src/clarity_backend/notifications/routes.py`

**Implementation**:
```python
@router.post("/sync")
async def sync_emails(session: SessionDep):
    """Trigger immediate sync of all connected email services."""
    from clarity_backend.services.registry import registry

    total_synced = 0
    errors = []
    for svc in [*registry.gmail_services, *registry.outlook_services]:
        if not svc.is_connected:
            continue
        try:
            notifications = await svc.fetch_recent(limit=50)
            for n in notifications:
                await svc.emit_notification(n)
            total_synced += len(notifications)
        except Exception as e:
            errors.append(f"{svc.source.value}:{svc.account}: {e}")

    return {"synced": total_synced, "errors": errors}
```

**Validation**:
```bash
cd backend && DOTENV_CONFIG=1 uv run pytest tests/ -v --tb=short
```

**Acceptance Criteria**:
- [ ] POST `/api/sync` triggers fetch on all email services
- [ ] New notifications are persisted and broadcast via WS
- [ ] Returns count of synced notifications
- [ ] Errors from individual services don't crash the endpoint

---

#### Task 3.2: Frontend sync API helper
**Status**: todo

**Description**: Add `syncEmails()` function to `notificationApi.ts`.

**Files**:
- Modify: `src/lib/notificationApi.ts`

**Implementation**:
```typescript
export function syncEmails() {
  return apiFetch<{ synced: number; errors: string[] }>("/api/sync", {
    method: "POST",
  });
}
```

**Acceptance Criteria**:
- [ ] Function exists and returns typed response

---

### Phase 4: Backend Search Endpoint

#### Task 4.1: Backend search with DB query
**Status**: todo

**Description**: Add `GET /api/notifications/search?q=term&limit=50&offset=0` endpoint that searches the `notifications` table using SQL LIKE on title, body, and sender_name. This complements the frontend in-memory search by searching all cached emails in the DB, not just the current in-memory set.

**Files**:
- Modify: `backend/src/clarity_backend/notifications/crud.py` — add `search_notifications()` function
- Modify: `backend/src/clarity_backend/notifications/routes.py` — add search endpoint

**Implementation (crud.py)**:
```python
async def search_notifications(
    session: AsyncSession, query: str, limit: int = 50, offset: int = 0
) -> list[dict]:
    """Search notifications by title, body, or sender_name."""
    like_q = f"%{query}%"
    stmt = (
        select(NotificationRecord)
        .where(
            NotificationRecord.triage_status != "archived",
            (NotificationRecord.title.contains(query))
            | (NotificationRecord.body.contains(query))
            | (NotificationRecord.sender_name.contains(query)),
        )
        .order_by(NotificationRecord.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.exec(stmt)
    return [_record_to_dict(r) for r in result.all()]
```

**Implementation (routes.py)**:
```python
@router.get("/notifications/search")
async def search_notifications_endpoint(
    session: SessionDep, q: str = "", limit: int = 50, offset: int = 0
):
    if not q.strip():
        return {"notifications": [], "query": q}
    from clarity_backend.notifications.crud import search_notifications
    results = await search_notifications(session, q.strip(), limit=limit, offset=offset)
    return {"notifications": results, "query": q}
```

**Validation**:
```bash
cd backend && DOTENV_CONFIG=1 uv run pytest tests/ -v --tb=short
```

**Acceptance Criteria**:
- [ ] Search returns matching notifications from DB
- [ ] Case-insensitive matching on title, body, sender_name
- [ ] Supports pagination (limit + offset)
- [ ] Empty query returns empty results

---

### Phase 5: Frontend UI

#### Task 5.1: "Actioned" button in NotificationDetail
**Status**: todo

**Description**: Add an "Actioned" button next to Archive in the detail panel. Only shown for email notifications (gmail/outlook). Styled distinctly (e.g., green tint) to indicate positive completion.

**Files**:
- Modify: `src/components/NotificationDetail.tsx`
- Modify: `src/lib/notificationApi.ts` — add `actionNotification()` helper

**Implementation** (notificationApi.ts):
```typescript
export function actionNotification(notificationId: string) {
  return apiFetch(`/api/notifications/${notificationId}/action`, {
    method: "POST",
    body: JSON.stringify({ notification_id: notificationId, action: "actioned" }),
  });
}
```

**Implementation** (NotificationDetail.tsx):
- Add `onActioned: (id: string) => void` prop
- Add "Actioned" button in actions bar, before Archive
- Keyboard hint: `d` key (consistent with "done")

**Acceptance Criteria**:
- [ ] "Actioned" button visible for gmail/outlook notifications
- [ ] Button calls API and closes detail panel
- [ ] Visual feedback (button shows checkmark or "Done" briefly)

---

#### Task 5.2: "Actioned" quick-action on NotificationCard
**Status**: todo

**Description**: Add a quick "Actioned" button that appears on hover alongside the existing Archive button, but only for email notifications.

**Files**:
- Modify: `src/components/NotificationCard.tsx`

**Acceptance Criteria**:
- [ ] Quick-actioned button on hover for email sources
- [ ] Calls parent handler on click

---

#### Task 5.3: Actioned state in useNotifications hook
**Status**: todo

**Description**: Add `actioned()` mutation to `useNotifications` that sets triage_status to "actioned". Actioned notifications should still appear in the list but with a visual "done" indicator (not filtered out like archived). Add `d` keyboard shortcut in inbox page.

**Files**:
- Modify: `src/hooks/useNotifications.ts` — add `actioned()` function
- Modify: `src/app/inbox/page.tsx` — add `handleActioned` + keyboard shortcut `d`

**Implementation** (useNotifications.ts):
```typescript
const actioned = useCallback((id: string) => {
  dispatch({ type: "UPDATE_ONE", payload: { id, updates: { triage_status: "actioned" } } });
}, []);
```

**Acceptance Criteria**:
- [ ] `actioned()` sets local state immediately (optimistic update)
- [ ] `d` key marks selected notification as actioned
- [ ] Actioned notifications show a visual indicator (e.g., checkmark, muted styling)

---

#### Task 5.4: Sync button in InboxSidebar
**Status**: todo

**Description**: Add a "Sync" button below the search box in InboxSidebar. Shows a loading spinner while syncing. Fires `syncEmails()` and reports result.

**Files**:
- Modify: `src/components/InboxSidebar.tsx`
- Modify: `src/app/inbox/page.tsx` — pass sync handler as prop

**Acceptance Criteria**:
- [ ] Sync button visible in sidebar
- [ ] Loading state while request is in-flight
- [ ] Shows count of synced emails briefly after completion

---

#### Task 5.5: Backend-powered search in sidebar
**Status**: todo

**Description**: When the user types in the search box and the query is >=3 chars, debounce (300ms) and call `GET /api/notifications/search?q=...`. Replace the in-memory filter results with backend results. Fall back to in-memory filter for <3 chars.

**Files**:
- Modify: `src/lib/notificationApi.ts` — add `searchNotifications()` helper
- Modify: `src/hooks/useNotifications.ts` — add backend search state
- Modify: `src/app/inbox/page.tsx` — wire up search results

**Implementation** (notificationApi.ts):
```typescript
export function searchNotifications(query: string, limit = 50, offset = 0) {
  const params = new URLSearchParams({ q: query, limit: String(limit), offset: String(offset) });
  return apiFetch<{ notifications: Notification[]; query: string }>(`/api/notifications/search?${params}`);
}
```

**Acceptance Criteria**:
- [ ] Typing 3+ chars triggers backend search after 300ms debounce
- [ ] Results replace in-memory filter
- [ ] Clearing search restores normal notification list
- [ ] Loading indicator while searching

---

### Phase 6: Pagination & Cache Strategy

#### Task 6.1: Backend — paginated notifications endpoint
**Status**: todo

**Description**: Extend `GET /api/notifications` with `offset` parameter for cursor-based pagination. The frontend will load the first page via WS initial_load, then fetch older pages via REST.

**Files**:
- Modify: `backend/src/clarity_backend/notifications/crud.py` — add offset to `load_notifications()`
- Modify: `backend/src/clarity_backend/notifications/routes.py` — add offset param

**Implementation**:
```python
# crud.py — add offset parameter
async def load_notifications(
    session: AsyncSession, limit: int = 50, offset: int = 0, status_filter: str | None = None
) -> list[dict]:
    query = select(NotificationRecord).order_by(NotificationRecord.timestamp.desc())
    if status_filter:
        query = query.where(NotificationRecord.triage_status == status_filter)
    else:
        query = query.where(NotificationRecord.triage_status != "archived")
    query = query.offset(offset).limit(limit)
    ...
```

```python
# routes.py
@router.get("/notifications")
async def get_notifications(session: SessionDep, limit: int = 50, offset: int = 0, status: str | None = None):
    notifications = await load_notifications(session, limit=limit, offset=offset, status_filter=status)
    return {"notifications": notifications, "offset": offset, "has_more": len(notifications) == limit}
```

**Acceptance Criteria**:
- [ ] `offset` param skips N records
- [ ] `has_more` flag indicates if more pages exist
- [ ] Default behaviour unchanged (offset=0)

---

#### Task 6.2: Frontend — infinite scroll / load more
**Status**: todo

**Description**: Add a "Load More" button or intersection observer at the bottom of the notification list. When triggered, fetch the next page from `GET /api/notifications?offset=N&limit=50` and append to the current list.

**Files**:
- Modify: `src/hooks/useNotifications.ts` — add `loadMore()` and `hasMore` state
- Modify: `src/app/inbox/page.tsx` — render load-more trigger

**Implementation**:
```typescript
// In useNotifications, add:
const [hasMore, setHasMore] = useState(true);

const loadMore = useCallback(async () => {
  const offset = state.notifications.length;
  const { notifications: older, has_more } = await getNotifications(50, undefined, offset);
  dispatch({ type: "APPEND_OLDER", payload: older });
  setHasMore(has_more);
}, [state.notifications.length]);
```

**Acceptance Criteria**:
- [ ] Scrolling to bottom triggers load of older notifications
- [ ] Older notifications append to list (don't replace)
- [ ] "Load More" button disappears when no more results
- [ ] Deduplication prevents double-loading

---

## Edge Cases

| Case | Expected Behavior | Test Coverage |
|------|-------------------|---------------|
| Gmail label already exists | `_ensure_actioned_label()` returns existing ID, skips create | Unit test |
| Outlook category already on message | `add_category()` returns True immediately | Unit test |
| Actioned on non-email (slack/posthog) | Status updated locally, no write-back attempted | Unit test |
| Service disconnected when actioning | Status still updated in DB, write-back fails silently | Unit test |
| Sync when no services connected | Returns `{synced: 0, errors: []}` | Unit test |
| Search with empty query | Returns empty array, no DB query | Unit test |
| Search with SQL injection attempt | SQLModel parameterized queries prevent injection | Framework |
| Pagination beyond available records | Returns empty array with `has_more: false` | Unit test |
| Concurrent sync requests | Each runs independently, dedup handles overlap | Integration |

---

## Validation Approach

### Level 1: Static Analysis
```bash
cd backend && uv run ruff check src/
cd .. && npx tsc --noEmit
```

### Level 2: Unit Tests
```bash
cd backend && DOTENV_CONFIG=1 uv run pytest tests/ -v --tb=short
npm test
```

### Level 3: Integration Testing
```bash
# Test actioned flow end-to-end
curl -X POST http://localhost:8070/api/notifications/{id}/action \
  -H "Content-Type: application/json" \
  -d '{"notification_id": "{id}", "action": "actioned"}'

# Test sync
curl -X POST http://localhost:8070/api/sync

# Test search
curl "http://localhost:8070/api/notifications/search?q=invoice&limit=10"
```

### Level 4: Manual Testing
- [ ] Mark a Gmail email as actioned → verify label appears in Gmail web UI
- [ ] Mark an Outlook email as actioned → verify category appears in Outlook
- [ ] Click Sync → verify new emails appear immediately
- [ ] Search for a sender name → verify results include old cached emails
- [ ] Scroll to bottom of inbox → verify older emails load

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gmail API quota limits on label operations | Low | Medium | Batch label operations, cache label ID |
| Outlook token expiry during write | Medium | Low | Existing 401 → reconnect pattern in listen() |
| Gmail OAuth scopes insufficient for modify | Medium | High | Need `gmail.modify` scope — check existing OAuth consent screen |
| Outlook OAuth scopes insufficient for write | Medium | High | Need `Mail.ReadWrite` scope — check existing OAuth consent screen |
| Large DB search slow without FTS | Low | Medium | SQLite LIKE is fast for <100k rows; add FTS later if needed |
| Race condition between sync and poll | Low | Low | Deduplication by (source, source_id) in save_notification |

**Critical Note on OAuth Scopes**:
- **Gmail**: The OAuth flow must request `gmail.modify` scope (not just `gmail.readonly`). Check `backend/src/clarity_backend/auth/google.py` for current scopes. If only readonly, the scope needs upgrading and users will need to re-authorize.
- **Outlook**: The OAuth flow must request `Mail.ReadWrite` scope (not just `Mail.Read`). Check `backend/src/clarity_backend/auth/microsoft.py` for current scopes. Same re-authorization requirement applies.

---

## Architecture Notes

### Gmail Label Strategy
- Label path: `Clarity/Actioned` (nested under "Clarity" in Gmail sidebar)
- Created per-account on first use, ID cached in `GmailService._actioned_label_id`
- Uses `users().messages().modify()` — requires `gmail.modify` scope

### Outlook Category Strategy
- Category name: `Clarity - Actioned`
- Categories in Outlook are strings, no pre-creation needed
- Uses `PATCH /me/messages/{id}` with `categories` array — requires `Mail.ReadWrite` scope

### Cache & Sync Strategy
- **Live sync**: Polling loop (30s) handles new emails → DB + WS push
- **Manual sync**: POST `/api/sync` triggers immediate `fetch_recent(limit=50)` on all services
- **DB is the cache**: All fetched notifications persist in `notifications` table
- **Pagination**: Frontend loads page 1 via WS `initial_load`, subsequent pages via REST `GET /api/notifications?offset=N`
- **No separate cache layer needed**: SQLite is fast enough for the expected volume (<100k notifications)

---

*Ready for implementation with `/prp-implement`*
