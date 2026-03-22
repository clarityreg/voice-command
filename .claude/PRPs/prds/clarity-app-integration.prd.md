# PRD: Clarity App Integration

**Status**: Draft
**Author**: Claude + Chidi
**Created**: 2026-03-19
**Last Updated**: 2026-03-19

---

## Problem Statement

### The Problem
Clarity Command Centre (voice triage, notifications) and Clarity App (Django regulatory platform with 48 modules) are two powerful tools that don't talk to each other. Using them separately means context-switching between apps for tasks that should flow together — checking schedules, triaging emails, capturing thoughts, reviewing compliance.

### Evidence
- Both apps already integrate with Plane independently — proving shared-backbone connectivity works
- Command Centre already has voice → HTTP API patterns (Plane handlers) that can be reused
- Clarity App already exposes REST endpoints for schedules, ADHD Bridge, email review, RAG, and compliance
- The user manually switches between both apps throughout the day

### Impact
- **Users affected**: 1 (solo user — Chidi)
- **Frequency**: Multiple times daily — every schedule check, email triage, or thought capture
- **Severity**: Medium — functional but fragmented workflow

---

## Proposed Solution

### Overview
Connect Command Centre to Clarity App via HTTP API calls. Command Centre becomes the voice + notification frontend; Clarity App remains the regulatory backend. No merging, no data duplication — just an API bridge.

The pattern already exists: Plane voice handlers in `commands.py` make live `httpx` calls to an external API. Clarity integration follows the same pattern — new intents, new handlers, new HTTP client.

### Key Hypotheses

| Hypothesis | Test Method | Success Criteria |
|------------|-------------|------------------|
| Voice → Clarity API calls feel fast enough for interactive use | Measure round-trip latency for each intent | < 2s end-to-end (voice → response) on local network |
| 10 new voice intents cover the most common Clarity actions | Track which intents are used over 2 weeks | 80%+ of Clarity interactions happen via voice |
| Webhook-driven notifications reduce missed Clarity events | Compare missed events before/after | Zero missed schedule changes or overdue reviews |
| Shared parking lot eliminates duplicate capture | Check for duplicates across both apps | Single source of truth for captured thoughts |

### What We're NOT Building
- Merging the two codebases or databases
- Syncing/replicating Clarity data into Command Centre's SQLite
- A shared authentication system (API key is sufficient for local dev)
- Mobile deployment (Phase 5 is scoped as deployment, not new features)
- New Clarity App features — we only consume existing endpoints

---

## User Context

### Primary User
**Chidi — Solo developer and regulatory professional**
- Goal: Interact with Clarity's regulatory tools without leaving the Command Centre voice/triage workflow
- Pain: Must open Clarity App separately for schedules, compliance checks, email review, parking lot
- Success: "What's my schedule status?" spoken into Command Centre returns the answer in < 2 seconds

### User Stories
- As a user, I want to ask "What's my schedule status?" and hear a summary so I don't have to open Clarity's dashboard
- As a user, I want to say "Add to parking lot: call supplier about formulation" and have it saved in Clarity's ADHD Bridge
- As a user, I want to see "Product X approved in France" appear in my Command Centre notifications when it changes in Clarity
- As a user, I want my morning brief to include overdue reviews and pending email actions from Clarity
- As a user, I want to say "Is retinol compliant in Germany?" and get an answer from Clarity's compliance engine

---

## Technical Approach

### Architecture

```
Command Centre (FastAPI :8070)          Clarity App (Django :8000)
┌─────────────────────────┐             ┌──────────────────────┐
│ voice/intent.py         │             │                      │
│   + 10 new regex intents│             │ api/schedules/       │
│                         │             │ api/adhd/            │
│ voice/commands.py       │  httpx      │ api/email/           │
│   + 10 new handlers ────┼────────────►│ api/reviews/         │
│                         │  X-API-Key  │ api/rag/             │
│ integrations/clarity.py │             │                      │
│   ClarityClient (httpx) │             │ webhook sender ──────┼──┐
│                         │             └──────────────────────┘  │
│ webhooks/clarity.py  ◄──┼──────────────────────────────────────┘
│   POST /webhooks/clarity│  POST + shared secret
│                         │
│ brief/morning.py        │
│   + Clarity data merge  │
└─────────────────────────┘
```

### New Files (Command Centre)

| File | Purpose |
|------|---------|
| `backend/src/clarity_backend/integrations/clarity.py` | `ClarityClient` — httpx wrapper for all Clarity API calls |
| `backend/src/clarity_backend/webhooks/clarity.py` | `POST /webhooks/clarity` — receives events from Clarity |

### Modified Files (Command Centre)

| File | Change |
|------|--------|
| `backend/src/clarity_backend/voice/intent.py` | Add ~10 new regex patterns for Clarity intents |
| `backend/src/clarity_backend/voice/commands.py` | Add ~10 new handler functions using ClarityClient |
| `backend/src/clarity_backend/config.py` | Add `CLARITY_API_URL`, `CLARITY_API_KEY` env vars |
| `backend/src/clarity_backend/settings/manager.py` | Add Clarity settings to DEFAULT_SETTINGS |
| `backend/src/clarity_backend/brief/morning.py` | Merge Clarity data (overdue reviews, pending actions) |
| `backend/src/clarity_backend/main.py` | Register webhook router |
| `src/app/settings/page.tsx` | Add Clarity API URL + key config fields |

### Auth Approach

**Recommendation: API key authentication**

Add a simple middleware to Clarity's Django backend:

```python
# Clarity side: middleware checks X-API-Key header
COMMAND_CENTRE_API_KEY = env("COMMAND_CENTRE_API_KEY")
```

```python
# Command Centre side: ClarityClient sends header
headers = {"X-API-Key": self.api_key}
```

**Why API key over Supabase service role:**
- Stateless — no token expiry, no refresh logic
- Decoupled — doesn't tie inter-service auth to Supabase
- Simple to rotate — change one env var on each side
- Sufficient for local dev; upgrade to mutual TLS or OAuth2 client credentials if deployed

### Dependencies
- Clarity App must be running locally on `:8000` (or configured URL)
- Clarity must expose the endpoints listed in the voice intent table
- Clarity needs a new API key auth middleware (small change)
- Clarity needs a webhook sender for Phase 2 (Django signals or Celery)

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Clarity not running when voice command fires | Medium | Medium | Return friendly "Clarity is offline" message; don't crash |
| Clarity API changes break Command Centre | Low | Medium | Version the ClarityClient; integration tests |
| Webhook delivery failures (Phase 2) | Medium | Low | Retry with backoff; log failures; notifications are advisory |
| Regex intent collisions with existing intents | Low | Medium | Test new patterns against existing corpus; AI fallback handles edge cases |

---

## Success Metrics

### Primary Metrics
- **Voice → Clarity latency**: target < 2s round-trip on localhost
- **Intent recognition accuracy**: target > 90% for Clarity commands
- **Webhook delivery rate**: target > 99% on local network

### Validation Approach
- Manual testing of each voice intent with varied phrasings
- Integration tests for ClarityClient against Clarity's API
- 2-week usage tracking to see which intents get used

---

## Implementation Phases

### Phase 1: Voice → Clarity Actions (3-5 days) — Highest Value

New voice intents that call Clarity's REST API:

| Voice Command | Intent | Clarity API |
|---|---|---|
| "What's my schedule status?" | `clarity_schedule_status` | `GET api/schedules/{id}/dashboard/` |
| "Show compliance for [client]" | `clarity_compliance` | `GET api/schedules/{id}/compliance/summary/` |
| "Check my emails" | `clarity_unified_inbox` | `GET api/adhd/unified-inbox/` |
| "What's upcoming?" | `clarity_upcoming_actions` | `GET api/email/action-points/upcoming/` |
| "Add to parking lot: [thought]" | `clarity_parking_lot_add` | `POST api/adhd/parking-lot/` |
| "Start a blitz session" | `clarity_start_blitz` | `POST api/adhd/blitz/` |
| "How much XP do I have?" | `clarity_xp_status` | `GET api/adhd/gamification/profile/` |
| "Run email review" | `clarity_run_email_review` | `POST api/email/review/start/` |
| "Is [ingredient] compliant?" | `clarity_ingredient_check` | `POST api/reviews/compliance-check/` |
| "Ask about [regulation]" | `clarity_rag_query` | `POST api/rag/query/` |

Deliverables:
- `ClarityClient` httpx wrapper with error handling and timeout
- 10 new intent regex patterns in `intent.py`
- 10 new handler functions in `commands.py`
- `CLARITY_API_URL` + `CLARITY_API_KEY` in config
- Settings UI for Clarity connection
- API key middleware on Clarity side (small Django change)

### Phase 2: Clarity → Command Centre Notifications (3-5 days)

Webhook-driven notifications from Clarity events:

| Clarity Event | Notification |
|---|---|
| Schedule status change | "Product X changed to Approved in France" |
| Email action point generated | "New action point: respond to [client] by Thursday" |
| Review overdue (SLA) | "Formula review for [product] is 2 days overdue" |
| Registration submitted | "Spain registration submitted for [product]" |
| Compliance check failed | "Ingredient [X] failed compliance for [market]" |

Deliverables:
- `POST /webhooks/clarity` endpoint in Command Centre
- Webhook events ingested as `NotificationRecord` entries (appear in inbox)
- WebSocket broadcast on new Clarity notification
- Webhook sender utility on Clarity side (Django signals / Celery tasks)
- Shared webhook secret for auth

### Phase 3: Shared Parking Lot (1-2 days)

Deliverables:
- Voice "quick capture" also POSTs to Clarity's `api/adhd/parking-lot/`
- Clarity action points trigger Phase 2 webhook → appear in Command Centre inbox
- Parking lot items visible in both apps

### Phase 4: Enhanced Morning Brief (1 day)

Deliverables:
- `brief/morning.py` calls Clarity's `api/email/analytics/` and `api/schedules/*/dashboard/`
- Morning brief response includes: overdue reviews, pending email actions, approaching deadlines
- Graceful degradation if Clarity is offline (brief still works with existing data)

### Phase 5: Mobile Access (2-3 days)

Deliverables:
- Deploy Next.js static export to Vercel/Netlify (quick win)
- Mobile-responsive layout verification (VoiceButton already has mobile layout)
- Optional: Capacitor/Tauri Mobile wrapper for native push notifications

---

## Open Questions
- [ ] Which Clarity client_id to use for testing schedule/compliance voice commands?
- [ ] Does Clarity's Django app already have any API key auth, or does the middleware need to be added from scratch?
- [ ] Are all listed Clarity API endpoints currently functional and returning data?
- [ ] For Phase 2 webhooks — does Clarity use Celery for async tasks, or should webhooks fire from Django signals?
- [ ] For Phase 5 — preferred hosting for mobile access (Vercel, self-hosted, other)?

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-19 | Connect via API bridge, don't merge codebases | Both apps work independently; merging would take months and break features |
| 2026-03-19 | API key auth over Supabase service role | Simpler, stateless, decoupled from Supabase; sufficient for local dev |
| 2026-03-19 | Live API calls (like Plane), not local data sync | Avoids data duplication; Clarity is the source of truth; both run locally so latency is negligible |
| 2026-03-19 | All 5 phases in priority order | Full integration is the goal; phases are ordered by value/effort ratio |

---
*This PRD is ready for planning with `/prp-plan .claude/PRPs/prds/clarity-app-integration.prd.md`*
