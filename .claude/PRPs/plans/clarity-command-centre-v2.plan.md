# Implementation Plan: Clarity Command Centre v2

**Created**: 2026-03-21
**Status**: Ready for Implementation
**PRD**: `.claude/PRPs/prds/clarity-command-centre-v2.prd.md`

---

## Overview

Stabilise the Clarity Command Centre desktop app by fixing broken OAuth, unreliable voice, and disconnected settings, then layer on Claude Code Channels (Telegram), Scheduled Tasks (PostHog monitoring), and extended voice capabilities (regulatory queries, client-aware tasks). Four phases over ~7 weeks.

## Success Criteria

- [ ] OAuth "Add Account" works in Tauri desktop app for Gmail and Outlook
- [ ] Voice button works reliably (OpenAI Whisper as default STT)
- [ ] Settings auto-populate from `.env` (11 mappings verified)
- [ ] Voice shortcut is customizable via settings UI
- [ ] 10 E2E user journeys pass
- [ ] Backend test coverage ≥ 90% on critical paths
- [ ] Frontend test coverage ≥ 85% overall
- [ ] Telegram channel bridges voice commands from phone
- [ ] PostHog errors trigger intelligent `/loop` analysis
- [ ] Regulatory queries work via voice ("What's the limit for X in Y?")

---

## Mandatory Reading

Before implementation, read these files to understand patterns:

| File | Purpose | Key Lines |
|------|---------|-----------|
| `backend/src/clarity_backend/auth/routes.py` | OAuth callback flow returning HTML | 14-32 (template), 44-65 (Google callback) |
| `backend/src/clarity_backend/auth/google.py` | PKCE OAuth implementation | 51-95 (build_auth_url, exchange_code) |
| `backend/src/clarity_backend/services/posthog.py` | PostHog poller with bare exceptions | 98, 123, 145 (except Exception) |
| `backend/src/clarity_backend/agent/runner.py` | Agent CLI spawn pattern | 114-124 (subprocess_exec), 94-107 (CLI check) |
| `backend/src/clarity_backend/voice/intent.py` | Intent classification patterns | 45-80 (regex patterns), 93-106 (classify) |
| `backend/src/clarity_backend/settings/manager.py` | Settings manager with env seeding | 61-81 (_seed_from_env) |
| `backend/tests/conftest.py` | Test fixture pattern | 1-39 (async session, FastAPI test client) |
| `src/hooks/useVoice.ts` | Voice hook with STT detection | 87-130 (detectBackend), 336-361 (shortcut) |
| `src/hooks/useAudioCapture.ts` | Audio capture with ScriptProcessor | 26-64 (startCapture), 59 (destination issue) |
| `src/components/AccountManager.tsx` | OAuth link elements | 64, 91 (anchor tags) |
| `src-tauri/src/lib.rs` | Tauri plugin registrations | 17-43 |
| `src-tauri/Cargo.toml` | Tauri dependencies (no shell plugin) | 20-30 |

## Patterns to Follow

### Naming
- Backend tests: `test_{module_name}.py` in `backend/tests/`
- Frontend tests: `{Component}.test.tsx` or `{hook}.test.ts` colocated with source
- E2E tests: `tests/e2e/{journey-name}.spec.ts`

### Code Style
- Backend: FastAPI + SQLModel, async handlers, pydantic models for request/response
- Frontend: React hooks with useCallback/useEffect, Tailwind CSS with project tokens (bark, cream, sev-*)
- Tests: pytest-asyncio for backend, Vitest + Testing Library for frontend

### Error Handling
- Backend services: `except Exception as e` → log + continue (but should be more specific)
- Frontend: try/catch with setError state, user-visible messages

---

## Implementation Tasks

### Phase 1: Stabilisation & Validation

#### Task 1.1: Fix OAuth Flow for Tauri — Backend Redirect
**Status**: todo

**Description**: Replace the HTML success page in OAuth callbacks with a redirect to the frontend. This lets the Tauri webview receive the callback result.

**Files**:
- Modify: `backend/src/clarity_backend/auth/routes.py:44-65` (Google callback)
- Modify: `backend/src/clarity_backend/auth/routes.py:91-110` (Microsoft callback)
- Modify: `backend/src/clarity_backend/auth/routes.py:14-32` (remove HTML template)
- Modify: `backend/src/clarity_backend/config.py` — add `OAUTH_REDIRECT_BASE` field (default `http://localhost:3080`)

**Implementation**:
1. Add `OAUTH_REDIRECT_BASE: str = "http://localhost:3080"` to Settings in config.py
2. In Google callback (line 62): Replace `HTMLResponse(_OAUTH_SUCCESS_HTML.format(...))` with `RedirectResponse(f"{settings.OAUTH_REDIRECT_BASE}/auth/callback?provider=gmail&email={email}&status=success")`
3. In Microsoft callback (line 108): Same redirect pattern with `provider=outlook`
4. On error: redirect with `status=error&message=...`

**Validation**:
```bash
cd backend && uv run pytest tests/test_auth_routes.py -v
```

**Acceptance Criteria**:
- [ ] Google callback returns 302 redirect to frontend URL
- [ ] Microsoft callback returns 302 redirect to frontend URL
- [ ] Error cases redirect with error status

---

#### Task 1.2: Fix OAuth Flow for Tauri — Frontend Callback Page
**Status**: todo

**Description**: Create a new `/auth/callback` page that receives the OAuth redirect, displays status, and triggers account list refresh.

**Files**:
- Create: `src/app/auth/callback/page.tsx`

**Implementation**:
1. Read `provider`, `email`, `status` from URL search params
2. If `status=success`: show success message, call `getAuthStatus()` to refresh, auto-navigate to `/settings` after 2s
3. If `status=error`: show error message with retry button
4. Use existing card styling (`rounded-card bg-card-bg p-5 shadow-card`)

**Validation**:
```bash
npx vitest run src/app/auth/callback
```

**Acceptance Criteria**:
- [ ] Page renders success state with provider name and email
- [ ] Page renders error state with message
- [ ] Navigates back to settings after success

---

#### Task 1.3: Fix OAuth — Open in System Browser for Tauri
**Status**: todo

**Description**: In the Tauri desktop app, OAuth links should open in the system browser (Safari/Chrome) instead of within the webview, because external OAuth providers often block embedded webviews.

**Files**:
- Modify: `src-tauri/Cargo.toml` — add `tauri-plugin-shell` dependency
- Modify: `src-tauri/src/lib.rs` — register shell plugin
- Modify: `src/components/AccountManager.tsx:64,91` — detect Tauri + use shell.open()

**Implementation**:
1. Add `tauri-plugin-shell = "2"` to `[dependencies]` in Cargo.toml
2. Add `.plugin(tauri_plugin_shell::init())` to builder in lib.rs (after log plugin)
3. In AccountManager.tsx: import `isTauri` from whisper.ts, if Tauri use `@tauri-apps/plugin-shell` `open()` instead of `<a>` tag
4. Add `@tauri-apps/plugin-shell` to npm dependencies

**Validation**:
```bash
npm run tauri build
# Then click "Add Gmail Account" — should open system browser
```

**Acceptance Criteria**:
- [ ] Tauri builds with shell plugin
- [ ] "Add Gmail Account" opens system browser, not webview
- [ ] OAuth callback redirects back to frontend after auth

---

#### Task 1.4: Fix Voice Button — Improve STT Backend Detection
**Status**: todo

**Description**: When OpenAI API key is available (seeded from .env), default to `openai-whisper` backend. Add explicit error logging for voice state transitions. Fix the "clicks and stops" issue.

**Files**:
- Modify: `src/hooks/useVoice.ts:101-130` — improve detectBackend logic
- Modify: `src/hooks/useAudioCapture.ts:59` — fix ScriptProcessor connection

**Implementation**:
1. In `detectBackend()`: After fetching settings, if `settings.openai_api_key` is set and `stt_backend` is still `"web-speech"`, auto-upgrade to `"openai-whisper"`
2. Add `console.info("[Voice]", state)` logging to all state transitions
3. In `useAudioCapture.ts:59`: Replace `processor.connect(audioContext.destination)` with:
   ```ts
   const silentGain = audioContext.createGain();
   silentGain.gain.value = 0;
   processor.connect(silentGain);
   silentGain.connect(audioContext.destination);
   ```
4. Add error boundary around `startCapture` with user-visible message

**Validation**:
```bash
npx vitest run src/hooks/useVoice.test.ts src/hooks/useAudioCapture.test.ts
```

**Acceptance Criteria**:
- [ ] With OpenAI key present, STT defaults to openai-whisper
- [ ] Without any key, falls back to web-speech (Chrome) or shows error (Tauri)
- [ ] Audio capture doesn't trigger output-based stream closure
- [ ] Voice state transitions are logged to console

---

#### Task 1.5: Fix Configuration — Verify Env Seeding & Add UI Indicators
**Status**: todo (seeding logic done, verification needed)

**Description**: Verify all 11 env-to-settings mappings work. Add visual indicator in settings UI when a value was seeded from .env. Make OAuth redirect URIs configurable.

**Files**:
- Modify: `backend/src/clarity_backend/settings/manager.py:87-89` — return metadata about seeded fields
- Modify: `backend/src/clarity_backend/config.py:63,70` — make redirect URIs use env vars properly
- Modify: `src/app/settings/page.tsx` — show "from .env" badge on seeded fields
- Create: `backend/tests/test_settings_env_seeding.py`

**Implementation**:
1. In GET `/api/settings`: Return `_seeded_keys` list alongside masked settings
2. In settings page: Show small "(from .env)" text next to fields that were seeded
3. Test all 11 mappings: `plane_api_key`, `plane_workspace_slug`, `plane_project_id`, `openai_api_key`, `aikido_webhook_secret`, `posthog_api_key`, `posthog_project_id`, `posthog_host`, `clarity_api_url`, `clarity_api_key`, `clarity_webhook_secret`

**Validation**:
```bash
cd backend && uv run pytest tests/test_settings_env_seeding.py -v
```

**Acceptance Criteria**:
- [ ] All 11 env vars seed into settings when JSON file is empty/missing
- [ ] User-saved values take precedence over env vars
- [ ] Settings UI shows which values came from .env
- [ ] OAuth redirect URIs configurable via env

---

#### Task 1.6: Fix PostHog Poller — Specific Exception Handling
**Status**: todo

**Description**: Replace bare `except Exception` handlers in PostHog service with specific exception types. Log auth failures distinctly.

**Files**:
- Modify: `backend/src/clarity_backend/services/posthog.py:98,123,145`
- Modify: `backend/tests/test_posthog_poller.py` — add auth failure test

**Implementation**:
1. Line 98 (`connect`): Catch `httpx.ConnectError`, `httpx.TimeoutException` separately from auth errors
2. Line 123 (`listen` loop): Catch `httpx.HTTPStatusError` for 401/403 → log "PostHog API key invalid" and stop polling
3. Line 145 (`_fetch_events`): Catch `httpx.HTTPStatusError`, `json.JSONDecodeError` specifically
4. Add new test: `test_posthog_auth_failure` — mock 401 response, verify poller logs and stops

**Validation**:
```bash
cd backend && uv run pytest tests/test_posthog_poller.py -v
```

**Acceptance Criteria**:
- [ ] No bare `except Exception` in posthog.py
- [ ] Auth failure (401/403) stops polling with clear log message
- [ ] Network errors retry silently (existing behavior preserved)
- [ ] Test covers auth failure scenario

---

#### Task 1.7: Add Claude CLI Availability Check at Startup
**Status**: todo

**Description**: Check for `claude` CLI at backend startup and log a warning if missing. Store availability in a module-level flag.

**Files**:
- Modify: `backend/src/clarity_backend/agent/runner.py:14` — expose availability flag
- Modify: `backend/src/clarity_backend/main.py:26-34` — check in lifespan
- Create: `backend/tests/test_agent_cli_check.py`

**Implementation**:
1. In runner.py: Add `CLAUDE_CLI_AVAILABLE = _CLAUDE_PATH is not None` as module-level constant
2. In main.py lifespan: After `init_db()`, log `"[Startup] Claude CLI: {available}"` with the path or "not found"
3. In agent routes: Return 503 with `{"error": "Claude CLI not installed", "install_url": "https://claude.ai/download"}` instead of creating a failed job

**Validation**:
```bash
cd backend && uv run pytest tests/test_agent_cli_check.py -v
```

**Acceptance Criteria**:
- [ ] Startup logs Claude CLI availability
- [ ] Agent fix endpoint returns 503 when CLI unavailable
- [ ] Response includes install URL

---

#### Task 1.8: E2E Test Infrastructure Setup
**Status**: todo

**Description**: Install Playwright, configure for Tauri webview and browser testing, create test infrastructure.

**Files**:
- Create: `playwright.config.ts`
- Create: `tests/e2e/helpers.ts` — shared utilities (start backend, wait for ready)
- Create: `tests/e2e/global-setup.ts` — start backend + frontend before tests
- Modify: `package.json` — add `test:e2e` script

**Implementation**:
1. `npm install -D @playwright/test`
2. Configure playwright for `http://localhost:3080` with `webServer` config starting both backend and frontend
3. Create helper to wait for backend health check (`GET /health`)
4. Add `"test:e2e": "playwright test"` to package.json

**Validation**:
```bash
npx playwright test --list
```

**Acceptance Criteria**:
- [ ] Playwright installed and configured
- [ ] Backend + frontend auto-start before tests
- [ ] Test list command works without errors

---

#### Task 1.9: E2E Tests — Critical User Journeys (1-5)
**Status**: todo

**Description**: Write E2E tests for the first 5 critical user journeys.

**Files**:
- Create: `tests/e2e/01-dashboard.spec.ts` — App loads, dashboard renders, morning brief visible
- Create: `tests/e2e/02-settings.spec.ts` — Settings page loads, save API keys, persist on reload
- Create: `tests/e2e/03-voice.spec.ts` — Voice button click, state transitions (mock audio)
- Create: `tests/e2e/04-triage.spec.ts` — Triage page loads items, snooze/dismiss actions
- Create: `tests/e2e/05-agent.spec.ts` — Agent page shows jobs list

**Implementation**:
- Use Playwright `page.goto()`, `page.click()`, `expect(page.locator(...))` patterns
- Mock backend responses where needed using `page.route()` interceptors
- Each test file: setup → action → assertion → cleanup

**Validation**:
```bash
npx playwright test tests/e2e/01-dashboard.spec.ts
```

**Acceptance Criteria**:
- [ ] 5 E2E tests pass with backend running
- [ ] Tests can run headless in CI

---

#### Task 1.10: E2E Tests — Critical User Journeys (6-10)
**Status**: todo

**Description**: Write E2E tests for remaining 5 critical user journeys.

**Files**:
- Create: `tests/e2e/06-inbox.spec.ts` — Inbox page, WebSocket connection indicator
- Create: `tests/e2e/07-stats.spec.ts` — Stats page renders charts
- Create: `tests/e2e/08-oauth.spec.ts` — OAuth flow (mock provider redirect)
- Create: `tests/e2e/09-voice-plane.spec.ts` — Voice creates Plane task via confirmation card
- Create: `tests/e2e/10-voice-errors.spec.ts` — Voice queries error count

**Validation**:
```bash
npx playwright test
```

**Acceptance Criteria**:
- [ ] All 10 E2E tests pass
- [ ] Total E2E suite runs in under 60 seconds

---

#### Task 1.11: Backend Test Coverage Push to 90%
**Status**: todo

**Description**: Fill gaps in backend test coverage for critical paths.

**Files**:
- Create: `backend/tests/test_settings_env_seeding.py` — env-to-settings mapping
- Create: `backend/tests/test_oauth_redirect.py` — new redirect-based OAuth callbacks
- Create: `backend/tests/test_agent_cli_check.py` — CLI availability check
- Create: `backend/tests/test_posthog_auth_failure.py` — auth failure handling
- Modify: `backend/tests/test_voice_commands.py` — add tests for Clarity voice commands

**Validation**:
```bash
cd backend && uv run pytest --cov=clarity_backend --cov-report=term-missing | grep TOTAL
```

**Acceptance Criteria**:
- [ ] Overall backend coverage ≥ 90%
- [ ] Voice module coverage ≥ 95%
- [ ] Auth module coverage ≥ 90%
- [ ] Agent module coverage ≥ 85%

---

### Phase 2: Claude Code Channel Integration

#### Task 2.1: Telegram Channel Plugin — Scaffold
**Status**: todo

**Description**: Create a custom Claude Code channel plugin that receives Telegram messages and forwards them to the Clarity backend as voice commands.

**Files**:
- Create: `.claude/plugins/clarity-telegram/index.ts` — main Bun script
- Create: `.claude/plugins/clarity-telegram/package.json` — plugin metadata
- Create: `.claude/plugins/clarity-telegram/.env.example` — token template

**Implementation**:
1. Follow the [Channels reference](https://code.claude.com/docs/en/channels-reference) plugin structure
2. Use Telegram Bot API polling (like the official telegram plugin)
3. On message: call `POST http://localhost:8070/api/voice/process` with `{ text: message.text }`
4. Reply to Telegram with the `response` field from the API
5. Support `/pair` command for allowlisting

**Validation**:
```bash
bun run .claude/plugins/clarity-telegram/index.ts --help
```

**Acceptance Criteria**:
- [ ] Plugin starts and connects to Telegram Bot API
- [ ] Text messages forwarded to backend voice API
- [ ] Response text sent back to Telegram
- [ ] Sender allowlist enforced

---

#### Task 2.2: Telegram Channel — Voice Message Support
**Status**: todo

**Description**: Add support for Telegram voice messages (audio files). Download, send to backend's audio processing endpoint.

**Files**:
- Modify: `.claude/plugins/clarity-telegram/index.ts` — handle voice/audio messages

**Implementation**:
1. Detect `message.voice` or `message.audio` in Telegram update
2. Download audio file via Telegram `getFile` API
3. POST to `http://localhost:8070/api/voice/process-audio` as multipart form data
4. Reply with transcription + command result

**Validation**:
```bash
# Send voice message to Telegram bot, verify response
```

**Acceptance Criteria**:
- [ ] Voice messages are transcribed via backend
- [ ] Command result returned to Telegram
- [ ] Audio files cleaned up after processing

---

#### Task 2.3: Webhook Receiver Channel for PostHog
**Status**: todo

**Description**: Build a channel that receives PostHog webhooks and pushes error events into the Claude Code session.

**Files**:
- Create: `.claude/plugins/clarity-webhooks/index.ts` — HTTP server for webhooks
- Create: `.claude/plugins/clarity-webhooks/package.json`

**Implementation**:
1. Start HTTP server on configurable port (default 8787)
2. `POST /webhook/posthog` — receive PostHog webhook payload
3. Extract error type, message, URL, user info
4. Push formatted event into Claude Code session via channel API
5. Claude receives event and can analyze with codebase context

**Validation**:
```bash
curl -X POST http://localhost:8787/webhook/posthog -d '{"event":"$exception","properties":{"$exception_type":"TypeError"}}'
```

**Acceptance Criteria**:
- [ ] Webhook server starts on configurable port
- [ ] PostHog events pushed into Claude Code session
- [ ] Claude can analyze and respond to errors

---

#### Task 2.4: Integration — Claude Code Launch Script
**Status**: todo

**Description**: Create a launch script that starts Claude Code with all channels enabled alongside the backend.

**Files**:
- Create: `scripts/start-clarity.sh` — unified launch script

**Implementation**:
```bash
#!/bin/bash
# Start backend
cd backend && uv run uvicorn clarity_backend.main:app --port 8070 &

# Start Claude Code with channels
claude --channels \
  plugin:clarity-telegram \
  plugin:clarity-webhooks \
  "$@"
```

**Validation**:
```bash
./scripts/start-clarity.sh --help
```

**Acceptance Criteria**:
- [ ] Single command starts backend + Claude Code with channels
- [ ] Telegram and webhook channels connect
- [ ] Ctrl+C cleanly shuts down all processes

---

### Phase 3: Extended Voice Capabilities

#### Task 3.1: Regulatory Database Query Intents
**Status**: todo

**Description**: Add new voice intents for regulatory limit queries and database searches.

**Files**:
- Modify: `backend/src/clarity_backend/voice/intent.py` — add `CLARITY_REGULATION_LIMIT` pattern
- Modify: `backend/src/clarity_backend/voice/commands.py` — add handler
- Create: `backend/tests/test_regulation_intents.py`

**Implementation**:
1. New intent pattern: `r"(what(?:'s| is) the )?limit (?:for |of )(.+?) (?:in |for )(.+)"` → extracts substance + country
2. Handler calls `ClarityClient.compliance_check(ingredient=substance, market=country)`
3. Response: "The limit for {substance} in {country} is {value} {unit}"

**Validation**:
```bash
cd backend && uv run pytest tests/test_regulation_intents.py -v
```

**Acceptance Criteria**:
- [ ] "What's the limit for vitamin D in France?" → correct response
- [ ] "Is glucosamine allowed in the UK?" → correct response (existing intent)
- [ ] Unknown substance/country → graceful error message

---

#### Task 3.2: Client-Aware Task Management
**Status**: todo

**Description**: Extend Plane voice commands to support client names as project aliases.

**Files**:
- Modify: `backend/src/clarity_backend/voice/intent.py` — enhance PLANE_CREATE_TASK pattern
- Modify: `backend/src/clarity_backend/voice/commands.py` — use project resolver with client names
- Modify: `backend/src/clarity_backend/voice/project_resolver.py` — add fuzzy matching for client names

**Implementation**:
1. Pattern: "Create a task for Nutricia to review their dossier" → `project_name="nutricia"`, `title="review their dossier"`
2. Project resolver checks `plane_projects` settings for alias match
3. If no match: suggest closest alias via fuzzy match
4. Train client names into vocabulary via `VocabularyEditor`

**Validation**:
```bash
cd backend && uv run pytest tests/test_plane_commands.py -v
```

**Acceptance Criteria**:
- [ ] "Create a task for [client] to [description]" creates task in correct Plane project
- [ ] Unknown client name suggests closest match
- [ ] Client names work in vocabulary editor

---

#### Task 3.3: PostHog Error → Agent Fix Pipeline
**Status**: todo

**Description**: Enrich agent fix context with PostHog session data when available.

**Files**:
- Modify: `backend/src/clarity_backend/agent/runner.py:42-58` — enhance prompt with PostHog context
- Modify: `backend/src/clarity_backend/services/posthog.py` — add method to fetch session replay URL
- Modify: `backend/src/clarity_backend/triage/routes.py` — expose PostHog context in triage item

**Implementation**:
1. Add `get_session_replay_url(event_id)` to PostHog service
2. When creating agent plan, include: error stack trace, URL, session replay link, occurrence count, trend
3. Agent prompt: "This error has occurred {count} times. Session replay: {url}. Stack trace: {trace}"

**Validation**:
```bash
cd backend && uv run pytest tests/test_agent.py -v
```

**Acceptance Criteria**:
- [ ] Agent plan includes PostHog context when available
- [ ] Session replay URL included in fix prompt
- [ ] Missing PostHog data doesn't break agent flow

---

#### Task 3.4: Scheduled Tasks — PostHog Monitoring Loop
**Status**: todo

**Description**: Create a `/loop` skill configuration for intelligent PostHog error monitoring.

**Files**:
- Create: `.claude/commands/clarity-monitor.md` — custom command for starting monitoring

**Implementation**:
1. Command: `/clarity-monitor` starts a `/loop 15m` that:
   - Fetches recent PostHog errors via backend API
   - Correlates with `git log` to find related commits
   - Checks if any are already being fixed by agent jobs
   - Reports new critical errors
2. Uses Claude Code's CronCreate tool under the hood

**Validation**:
```bash
# In Claude Code session:
/clarity-monitor
# Verify loop is created with CronList
```

**Acceptance Criteria**:
- [ ] Loop runs every 15 minutes
- [ ] Correlates errors with recent commits
- [ ] Skips errors already being handled by agent

---

### Phase 4: Polish & Hardening

#### Task 4.1: Fix Hardcoded URLs
**Status**: todo

**Description**: Make all localhost URLs configurable via environment variables.

**Files**:
- Modify: `backend/src/clarity_backend/config.py` — ensure all URLs have env var overrides
- Modify: `backend/src/clarity_backend/voice/project_resolver.py` — configurable Ollama URL
- Modify: `backend/src/clarity_backend/voice/ai_classifier.py` — configurable Ollama URL

**Validation**:
```bash
cd backend && uv run pytest tests/test_config.py -v
```

**Acceptance Criteria**:
- [ ] All localhost URLs have env var overrides
- [ ] Changing env var changes runtime behavior
- [ ] Defaults remain unchanged for development

---

#### Task 4.2: Error Handling — Circuit Breaker for External Services
**Status**: todo

**Description**: Add circuit breaker pattern to external API calls (PostHog, Plane, Clarity) to prevent cascading failures.

**Files**:
- Create: `backend/src/clarity_backend/utils/circuit_breaker.py`
- Modify: `backend/src/clarity_backend/integrations/clarity.py` — wrap with circuit breaker
- Modify: `backend/src/clarity_backend/services/posthog.py` — wrap with circuit breaker

**Implementation**:
1. Simple circuit breaker: 3 failures → open for 60s → half-open → retry
2. Wrap `ClarityClient` and `PostHogPoller` external calls
3. Log state transitions: closed → open → half-open → closed

**Validation**:
```bash
cd backend && uv run pytest tests/test_circuit_breaker.py -v
```

**Acceptance Criteria**:
- [ ] 3 consecutive failures trips circuit breaker
- [ ] Breaker auto-resets after 60s cooldown
- [ ] Breaker state logged for observability

---

#### Task 4.3: Tauri Rust — Replace unwrap() with Graceful Error Handling
**Status**: todo

**Description**: Replace `unwrap()` calls on mutex locks in Tauri Rust code with proper error handling.

**Files**:
- Modify: `src-tauri/src/commands.rs` — replace `unwrap()` with `map_err()`
- Modify: `src-tauri/src/whisper.rs` — replace `unwrap()` with `map_err()`

**Implementation**:
1. Find all `.unwrap()` on mutex locks
2. Replace with `.map_err(|_| "Whisper model lock poisoned".to_string())?`
3. Return user-friendly error strings via Tauri command results

**Validation**:
```bash
cd src-tauri && cargo clippy -- -D warnings
npm run tauri build
```

**Acceptance Criteria**:
- [ ] No `unwrap()` on mutex locks
- [ ] Clippy passes without warnings
- [ ] Tauri build succeeds

---

## Edge Cases

| Case | Expected Behavior | Test Coverage |
|------|-------------------|---------------|
| OAuth provider unreachable | Show error message, retry button | `tests/e2e/08-oauth.spec.ts` |
| PostHog API key invalid (401) | Stop polling, log clear message | `test_posthog_auth_failure.py` |
| Claude CLI not in PATH | Agent returns 503 with install URL | `test_agent_cli_check.py` |
| .env file has encrypted values | Skip env seeding, use JSON settings | `test_settings_env_seeding.py` |
| Telegram bot rate limited | Backoff, queue messages | `clarity-telegram/index.ts` |
| Voice button clicked rapidly | Debounce, prevent double-start | `useVoice.test.ts` |
| WebSocket disconnects mid-session | Auto-reconnect with backoff | `wsClient.test.ts` (existing) |
| Plane project alias not found | Suggest closest match via fuzzy | `test_plane_commands.py` |

---

## Validation Approach

### Level 1: Static Analysis
```bash
cd backend && uv run ruff check src/
npx tsc --noEmit
```

### Level 2: Unit Tests
```bash
cd backend && uv run pytest --cov=clarity_backend --cov-report=term-missing
npx vitest run --coverage
```

### Level 3: Integration Tests
```bash
cd backend && uv run pytest tests/ -v
```

### Level 4: Build Verification
```bash
npm run tauri build
```

### Level 5: E2E Tests
```bash
npx playwright test
```

### Level 6: Manual Testing
- [ ] Open Tauri app → click "Add Gmail Account" → complete OAuth → account appears
- [ ] Click voice button → speak "what errors do I have" → hear response
- [ ] Open Settings → see API keys pre-populated from .env
- [ ] Change voice shortcut → new shortcut works immediately
- [ ] Send Telegram message → receive voice command response

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Channels API changes (research preview) | Medium | High | Abstract channel interface; check claude-plugins-official for updates |
| tauri-plugin-shell breaks Tauri build | Low | High | Pin version; test build in CI |
| Playwright flaky in CI | Medium | Medium | Retry logic; headless Chrome stable |
| PostHog webhook format changes | Low | Medium | Version pin; schema validation on ingest |
| OpenAI Whisper API cost | Low | Low | Rate limit voice commands; cache frequent queries |

---

## Task Dependency Graph

```
Phase 1 (Stabilisation):
  1.1 (OAuth backend) ──→ 1.2 (OAuth frontend) ──→ 1.3 (OAuth Tauri shell)
  1.4 (Voice fix) ─────────────────────────────────→ 1.9 (E2E voice test)
  1.5 (Settings verify) ──→ 1.9 (E2E settings test)
  1.6 (PostHog fix) ───────→ 1.11 (Backend coverage)
  1.7 (CLI check) ─────────→ 1.11 (Backend coverage)
  1.8 (E2E setup) ─────────→ 1.9 (E2E 1-5) ──→ 1.10 (E2E 6-10)

Phase 2 (Channels) — depends on Phase 1 complete:
  2.1 (Telegram scaffold) ──→ 2.2 (Voice messages) ──→ 2.4 (Launch script)
  2.3 (Webhook channel) ────→ 2.4 (Launch script)

Phase 3 (Extended) — depends on Phase 2 complete:
  3.1 (Regulation intents) — independent
  3.2 (Client tasks) — independent
  3.3 (Agent enrichment) ──→ 3.4 (Monitor loop)

Phase 4 (Polish) — depends on Phase 3 complete:
  4.1 (URLs), 4.2 (Circuit breaker), 4.3 (Rust unwrap) — all independent
```

---

*Ready for implementation with `/prp-implement .claude/PRPs/plans/clarity-command-centre-v2.plan.md`*
