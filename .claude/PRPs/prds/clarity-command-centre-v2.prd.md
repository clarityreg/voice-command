# PRD: Clarity Command Centre v2 — Stabilisation, Validation & Claude Code Integration

**Status**: Draft
**Author**: Claude + Chidi
**Created**: 2026-03-21
**Last Updated**: 2026-03-21

---

## Problem Statement

### The Problem
The Clarity Command Centre is a voice-driven desktop app designed to unify task management (Plane), error monitoring (PostHog), regulatory compliance (Clarity App), and communications (Gmail/Outlook/Slack) into a single command surface. While the architecture is sound and 26 voice intents are implemented, **the app is currently unusable in production** due to broken OAuth flows, disconnected configuration systems, missing validation, and no E2E test coverage. Additionally, new Claude Code features (Channels, Scheduled Tasks, Agent SDK) offer transformative capabilities that aren't yet leveraged.

### Evidence
- OAuth "Add Account" buttons fail silently in Tauri desktop app (redirect callback never reaches frontend)
- Settings UI reads from `~/.clarity/settings.json` while backend services read from `.env` — two disconnected config systems (partially fixed: env seeding added)
- Frontend test coverage at 78% statements but key hooks (useVoice: 43%, settings: 42%) are under-tested
- Zero E2E tests across the full stack
- PostHog poller uses bare `except Exception` — masks auth failures silently
- Agent system requires Claude CLI in PATH but doesn't validate at startup
- Multiple hardcoded `localhost` URLs prevent any non-local deployment
- Voice button clicks and stops in Tauri due to WebView SpeechRecognition limitations

### Impact
- **Users affected**: Solo developer (Chidi) — primary user of both Clarity regulatory platform and this command centre
- **Frequency**: Every session — core features (OAuth, voice, settings) are broken
- **Severity**: Critical — app cannot fulfill its primary purpose

---

## Proposed Solution

### Overview
A phased approach: (1) stabilise existing features with proper validation and E2E tests, (2) integrate Claude Code Channels for Telegram-based mobile voice access and webhook event forwarding, (3) leverage Scheduled Tasks for intelligent error monitoring, and (4) extend the Agent SDK integration for automated error fixing with smarter context.

### Key Hypotheses

| Hypothesis | Test Method | Success Criteria |
|------------|-------------|------------------|
| Telegram channel bridge will provide reliable mobile voice access | Build channel plugin, test 50 voice commands via Telegram | 95%+ intent recognition rate, <3s response time |
| Scheduled PostHog polling with Claude analysis will surface actionable errors faster | Compare current poller vs `/loop`-based analysis over 1 week | 50%+ reduction in noise (false positives / low-value alerts) |
| E2E validation will catch the OAuth/settings/voice regressions before they ship | Build E2E suite covering 10 critical user journeys | Zero broken journeys on `npm run tauri build` |
| Agent auto-fix with PostHog context (screenshots, heatmaps) will resolve simple errors autonomously | Run agent on 10 real PostHog errors with full context | 30%+ auto-resolved without human intervention |
| Regulatory database queries via voice will save time vs manual dashboard navigation | Measure time for 10 common regulatory lookups (voice vs UI) | 60%+ time reduction |

### What We're NOT Building
- Multi-user / team features — this is a single-developer tool
- Custom Tauri native audio pipeline — will use browser-based STT (OpenAI Whisper cloud or Web Speech)
- Full mobile app — Telegram channel is the mobile interface
- Cloud deployment / hosting — runs locally with backend on localhost
- Complete Clarity App feature parity — only voice-accessible endpoints

---

## User Context

### Primary User
**Chidi — Solo Developer & Regulatory Consultant**
- Goal: Manage development tasks, monitor production errors, and answer regulatory questions hands-free via voice
- Pain: Must context-switch between Plane, PostHog, Gmail, Clarity App, and code editor. Voice commands don't work reliably. Can't access from phone.
- Success: "Hey, create a task in Plane for Nutricia to review their novel food dossier" → task created. "What's the vitamin D limit for France?" → instant answer. PostHog error → agent creates fix PR automatically.

### User Stories

**Stabilisation:**
- As a user, I want OAuth account linking to work reliably in the desktop app so that I can connect Gmail and Outlook without workarounds
- As a user, I want my `.env` API keys to auto-populate in the settings UI so that I don't have to enter them twice
- As a user, I want the voice button to work consistently so that I can issue commands without it silently failing
- As a user, I want to customize the voice shortcut key so that it doesn't conflict with my other tools

**Claude Code Integration:**
- As a user, I want to send voice commands via Telegram from my phone so that I can manage tasks while away from my desk
- As a user, I want PostHog errors to be analyzed and triaged automatically on a schedule so that I wake up to a prioritized error list
- As a user, I want the AI agent to include PostHog screenshots/context when fixing errors so that fixes are more accurate
- As a user, I want to query the regulatory database by voice ("is glucosamine allowed in France?") and get instant answers

**Validation:**
- As a developer, I want E2E tests covering all critical user journeys so that regressions are caught before release
- As a developer, I want full backend + frontend test coverage above 85% so that I can refactor confidently

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │
│  │  Tauri   │  │ Telegram │  │  Claude Code Session   │ │
│  │ Desktop  │  │ Channel  │  │  (headless / -p mode)  │ │
│  └────┬─────┘  └────┬─────┘  └──────────┬────────────┘ │
│       │              │                    │              │
│       ▼              ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────┐│
│  │              FastAPI Backend (:8070)                 ││
│  │                                                     ││
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ││
│  │  │  Voice  │ │  Triage  │ │  Agent   │ │Settings│ ││
│  │  │ Router  │ │ + Brief  │ │ Runner   │ │Manager │ ││
│  │  └────┬────┘ └────┬─────┘ └────┬─────┘ └────┬───┘ ││
│  │       │           │            │             │     ││
│  │  ┌────▼────┐ ┌────▼─────┐ ┌───▼──────┐     │     ││
│  │  │ Intent  │ │ PostHog  │ │ Claude   │     │     ││
│  │  │Classify │ │ Poller   │ │ CLI/-p   │     │     ││
│  │  └────┬────┘ └──────────┘ └──────────┘     │     ││
│  │       │                                     │     ││
│  │  ┌────▼──────────────────────────────┐     │     ││
│  │  │         Integrations              │     │     ││
│  │  │ Plane │ Clarity │ Gmail │ Outlook │     │     ││
│  │  └──────────────────────────────────-┘     │     ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │           Claude Code Extensions                    ││
│  │                                                     ││
│  │  ┌──────────────┐  ┌────────────┐  ┌─────────────┐││
│  │  │   Telegram   │  │  Scheduled │  │   Agent     │││
│  │  │   Channel    │  │   Tasks    │  │   SDK       │││
│  │  │  (plugin)    │  │  (/loop)   │  │  (claude -p)│││
│  │  └──────────────┘  └────────────┘  └─────────────┘││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### Phase 1: Stabilisation & Validation (MVP)

#### 1a. Fix OAuth Flow for Tauri
**Problem**: `<a href="${API_BASE}/auth/google/start" target="_blank">` opens OAuth in the Tauri webview. The callback returns HTML to a popup that the Tauri app can't intercept.

**Solution**: Replace popup-based OAuth with a redirect-back flow:
1. Backend callback endpoint redirects to `http://localhost:3080/auth/callback?provider=google&status=success` instead of returning HTML
2. Frontend catches the redirect on a new `/auth/callback` page, updates account state
3. For Tauri builds: use `tauri-plugin-shell` to open OAuth URL in the system browser, with a deep-link callback (`clarity://auth/callback`)

**Files to modify**:
- `backend/src/clarity_backend/auth/routes.py` — change callback to redirect
- `src/app/auth/callback/page.tsx` — new frontend callback handler
- `src/components/AccountManager.tsx` — add window.open fallback for Tauri

#### 1b. Fix Voice Button Reliability
**Problem**: In Tauri WebView (WKWebView on macOS), `SpeechRecognition` API is not available. Detection falls to `sttBackend = "none"`, and clicking the mic shows "Speech recognition not supported" or silently fails.

**Solution**:
1. Default STT backend to `"openai-whisper"` when OpenAI API key is configured (from .env seeding)
2. Add console logging to voice state transitions for debugging
3. Fix `useAudioCapture.ts` line 59: connect processor to `audioContext.createGain()` (silent node) instead of `audioContext.destination` to prevent output-triggered stream closure
4. Add explicit error state with user-visible message in VoiceCommandArea

**Files to modify**:
- `src/hooks/useVoice.ts` — improve backend detection, add error logging
- `src/hooks/useAudioCapture.ts` — fix ScriptProcessorNode connection
- `src/components/VoiceCommandArea.tsx` — show STT backend status + errors

#### 1c. Fix Configuration Consistency
**Status**: PARTIALLY DONE (env seeding implemented this session)

**Remaining work**:
- Verify all 11 env-to-settings mappings work correctly
- Add "Seeded from .env" indicator next to auto-populated fields in settings UI
- Ensure settings saved via UI take precedence over .env values on subsequent reads
- Fix Google/Microsoft redirect URIs to be configurable via .env (currently hardcoded in config.py)

#### 1d. Customizable Voice Shortcut
**Status**: DONE (implemented this session)
- Backend: `voice_shortcut` field in settings manager
- Frontend: ShortcutRecorder component in settings page
- Hook: `matchesShortcut()` dynamic matcher in useVoice.ts

#### 1e. E2E Test Suite
**Approach**: Use Vitest + Playwright (or agent-browser from PRP framework) for full-stack E2E tests.

**Critical User Journeys to Cover**:
1. App loads → dashboard renders with morning brief
2. Settings page → save API keys → keys persist on reload
3. Voice button → click → listen → process → response displayed
4. Triage page → loads items → snooze/dismiss/create-issue actions work
5. Agent page → shows jobs → approve plan → execution completes
6. Inbox page → WebSocket connects → notifications render
7. Stats page → charts render with data
8. OAuth flow → Add Gmail account → account appears in list
9. Voice: "create task in Plane for [project]" → confirmation card → confirm → task created
10. Voice: "what errors do I have?" → error count response

**Files to create**:
- `tests/e2e/` directory with Playwright config
- One test file per journey above

#### 1f. Backend Test Coverage
**Target**: 90%+ on critical paths (voice, agent, auth, triage)

**Gaps to fill**:
- `test_settings_env_seeding.py` — verify env-to-settings mapping
- `test_oauth_callback_redirect.py` — test new redirect-based OAuth
- `test_agent_cli_check.py` — test Claude CLI availability check at startup
- `test_posthog_auth_failure.py` — test proper error handling when API key is invalid

### Phase 2: Claude Code Channel Integration

#### 2a. Telegram Voice Channel
**What**: Build a custom Claude Code channel plugin that bridges Telegram messages to the Clarity Command Centre backend.

**How it works**:
1. User sends text/voice message to Telegram bot
2. Channel plugin receives message, forwards to Claude Code session
3. Claude Code calls `POST /api/voice/process` on the backend
4. Response sent back through Telegram channel

**Architecture**:
```
Phone → Telegram Bot → Channel Plugin → Claude Code Session
                                              ↓
                                    POST /api/voice/process
                                              ↓
                                    Backend processes intent
                                              ↓
                                    Channel reply → Telegram
```

**Files to create**:
- `.claude/plugins/clarity-telegram/` — custom channel plugin (Bun script)
- Plugin reads from `TELEGRAM_BOT_TOKEN` env var
- Forwards text messages as voice commands to backend API
- Returns response text back to Telegram

**Configuration**:
```bash
# Install and configure
/plugin install clarity-telegram

# Start Claude Code with channel
claude --channels plugin:clarity-telegram
```

#### 2b. Webhook Receiver Channel
**What**: Build a channel that receives PostHog webhooks and pushes them into the Claude Code session for intelligent analysis.

**How it works**:
1. PostHog configured to send webhooks to `http://localhost:8787/webhook/posthog`
2. Channel receives webhook, pushes event into Claude Code session
3. Claude analyzes the error with full codebase context
4. Claude creates a triage item or triggers agent fix

**Benefits over current Python poller**:
- Claude has full codebase context when analyzing errors
- Can immediately correlate errors with recent code changes
- Can trigger agent fix without round-trip through REST API

### Phase 3: Scheduled Tasks Integration

#### 3a. Intelligent PostHog Monitoring
**What**: Replace/complement the Python-based PostHog poller with Claude Code scheduled tasks that provide AI-driven analysis.

```bash
# In Claude Code session:
/loop 15m check PostHog for new errors, correlate with recent commits, and update triage queue
```

**Benefits**:
- Claude can read git log to correlate errors with commits
- Can check if an error is already being fixed by an agent job
- Can classify severity more accurately with codebase context
- Can auto-create Plane tasks for critical errors

#### 3b. Deployment Watch
```bash
/loop 5m check if the Vercel deployment finished and report any preview URL changes
```

#### 3c. Morning Brief Automation
```bash
# One-shot scheduled task
remind me at 9am to run the morning brief and summarize overnight PostHog errors
```

### Phase 4: Extended Voice Capabilities

#### 4a. Regulatory Database Queries
**What**: Extend voice commands to query Clarity App's RAG system for regulatory answers.

**New intents**:
- "What's the limit for [substance] in [country]?" → `CLARITY_REGULATION_LIMIT`
- "Is [ingredient] allowed in [market]?" → already exists (`CLARITY_INGREDIENT_CHECK`)
- "Show me the [country] regulations for [category]" → `CLARITY_REGULATION_SEARCH`
- "Check the database for [query]" → `CLARITY_RAG_QUERY` (exists)

**Enhancement**: Add RAG context to agent fixes — when fixing a compliance-related error, include relevant regulatory data.

#### 4b. Client-Aware Task Management
**What**: Extend Plane voice commands to support client-specific task creation with project resolution.

**New patterns**:
- "Create a task for [client name] to [description]" → resolves client → Plane project → creates task
- "What's the status of [client name]'s tasks?" → lists filtered tasks
- "Complete the [task ref] for [client name]" → marks done

**Enhancement**: Train vocabulary with client names via existing VocabularyEditor component.

#### 4c. PostHog Error → Agent Fix Pipeline
**What**: Automated pipeline from PostHog error detection to agent-driven code fix.

**Flow**:
```
PostHog Error Detected (via poller or webhook channel)
    ↓
Claude analyzes error with codebase context
    ↓
Checks for PostHog session replay / screenshots (via API)
    ↓
Creates AgentJob with enriched context
    ↓
Agent plans fix using claude -p with Read/Glob/Grep
    ↓
Plan posted to triage queue for approval
    ↓
On approve: Agent executes fix in git worktree
    ↓
Result: branch with fix ready for review
```

**PostHog Context Enrichment**:
- Session replay URL
- User actions leading to error
- Heatmap data for affected page
- Error frequency and trend

---

## Success Metrics

### Primary Metrics
- **OAuth success rate**: 0% (broken) → 100% (working in Tauri)
- **Voice command success rate**: ~50% (unreliable) → 95%+ (reliable STT + intent)
- **E2E test coverage**: 0 journeys → 10 critical journeys
- **Backend test coverage**: ~70% → 90%+ on critical paths
- **Frontend test coverage**: 78% → 85%+ overall, 80%+ on hooks
- **Mean time to error awareness**: ~60s (poller) → <5s (webhook channel)
- **Agent auto-fix rate**: 0% → 30%+ of simple errors

### Validation Approach
- Run E2E suite on every `npm run tauri build`
- Track voice command success/failure rates via PostHog events
- Monitor agent job completion rates in the agent dashboard
- Weekly review of Telegram channel usage patterns

---

## Implementation Phases

### Phase 1: Stabilisation & Validation (Week 1-2)
- [ ] Fix OAuth flow for Tauri desktop (redirect-based)
- [ ] Fix voice button reliability (STT backend detection, audio capture)
- [ ] Verify settings env seeding (11 mappings)
- [ ] Add "seeded from .env" UI indicators
- [ ] Make Google/Microsoft redirect URIs configurable
- [ ] Build E2E test suite (10 journeys)
- [ ] Increase backend test coverage to 90%
- [ ] Fix PostHog poller error handling (replace bare except)
- [ ] Add Claude CLI availability check at backend startup
- [ ] Fix hardcoded port references (triage `:8001` → `:8070` — done)

### Phase 2: Claude Code Integration (Week 3-4)
- [ ] Build Telegram channel plugin for voice relay
- [ ] Build webhook receiver channel for PostHog
- [ ] Set up `/loop` scheduled tasks for error monitoring
- [ ] Configure morning brief automation
- [ ] Test Telegram voice flow end-to-end

### Phase 3: Extended Capabilities (Week 5-6)
- [ ] Add regulatory database query voice intents
- [ ] Enhance client-aware Plane task management
- [ ] Enrich PostHog errors with session replay context
- [ ] Build PostHog → Agent auto-fix pipeline
- [ ] Add deployment monitoring via scheduled tasks

### Phase 4: Polish & Documentation (Week 7)
- [ ] Performance optimization (API response times)
- [ ] Error handling improvements (circuit breakers, retries)
- [ ] User documentation / setup guide
- [ ] Production deployment story (if applicable)

---

## Dependencies

| Dependency | Required For | Status |
|------------|-------------|--------|
| Claude Code v2.1.80+ | Channels feature | Available |
| Bun runtime | Channel plugins | Installed |
| OpenAI API key | Cloud Whisper STT | In .env |
| Plane API key | Task management | In .env |
| PostHog API key | Error monitoring | In .env |
| Clarity App API | Regulatory queries | In .env |
| Claude CLI | Agent auto-fix | Available |
| Telegram Bot Token | Mobile voice access | [TBD - create bot] |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Channels feature changes (research preview) | Medium | High | Abstract channel interface; fallback to direct API polling |
| Telegram bot rate limits | Low | Medium | Batch messages; respect Telegram API limits |
| PostHog API changes break poller | Low | High | Version pin PostHog client; add integration tests |
| OAuth popup blocked by macOS security | Medium | High | Use system browser via tauri-plugin-shell |
| Claude CLI not installed on user machine | Low | High | Check at startup; show setup instructions in UI |
| WebView audio capture limitations | High | Medium | Default to OpenAI Whisper (cloud); bypass WebView audio |

---

## Open Questions
- [ ] Should Telegram channel run as part of the Tauri app or as a separate Claude Code session?
- [ ] Can PostHog session replay data be fetched via API for agent context enrichment?
- [ ] Should the webhook channel listen on a separate port or reuse the FastAPI backend?
- [ ] Is the current single-process Uvicorn deployment sufficient, or do we need workers?
- [ ] Should regulatory RAG queries go through Clarity App API or direct database access?

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-21 | Settings seed from .env | Users shouldn't enter API keys twice |
| 2026-03-21 | Customizable voice shortcut | Cmd+Shift+Space conflicts with other tools |
| 2026-03-21 | Use OpenAI Whisper as default STT | Web Speech API unavailable in Tauri WKWebView |
| 2026-03-21 | Telegram as mobile interface | Faster than building native mobile app; leverages Claude Code Channels |
| 2026-03-21 | E2E tests before new features | Current state is too fragile to extend without validation |

---
*This PRD is ready for planning with `/prp-plan`*
