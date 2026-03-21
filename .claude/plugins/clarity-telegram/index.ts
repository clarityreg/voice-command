/**
 * Clarity Command Centre — Telegram Channel Plugin
 *
 * Bridges Telegram messages to the Clarity backend voice processing API.
 * Run with:  bun run index.ts
 *
 * Required env vars (or .env file in this directory):
 *   TELEGRAM_BOT_TOKEN   — from @BotFather
 *   CLARITY_API_URL      — defaults to http://localhost:8070
 */

import { join } from "node:path";
import { existsSync, readFileSync, writeFileSync } from "node:fs";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const __dir = new URL(".", import.meta.url).pathname;

function loadEnv(): void {
  const envPath = join(__dir, ".env");
  if (!existsSync(envPath)) return;
  const lines = readFileSync(envPath, "utf8").split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const val = trimmed.slice(eq + 1).trim();
    if (key && !(key in process.env)) {
      process.env[key] = val;
    }
  }
}

loadEnv();

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN ?? "";
const CLARITY_API_URL = (process.env.CLARITY_API_URL ?? "http://localhost:8070").replace(/\/$/, "");
const ALLOWLIST_PATH = join(__dir, ".allowlist.json");
const PAIRING_TTL_MS = 5 * 60 * 1000; // 6-digit codes expire after 5 minutes

if (!BOT_TOKEN) {
  console.error("[clarity-telegram] TELEGRAM_BOT_TOKEN is not set. Set it in .env or the environment.");
  process.exit(1);
}

const TG_API = `https://api.telegram.org/bot${BOT_TOKEN}`;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TelegramUser {
  id: number;
  first_name: string;
  username?: string;
}

interface TelegramChat {
  id: number;
  type: string;
}

interface TelegramVoiceFile {
  file_id: string;
  file_size?: number;
  mime_type?: string;
  duration: number;
}

interface TelegramMessage {
  message_id: number;
  from?: TelegramUser;
  chat: TelegramChat;
  text?: string;
  voice?: TelegramVoiceFile;
}

interface TelegramUpdate {
  update_id: number;
  message?: TelegramMessage;
}

interface TelegramGetUpdatesResult {
  ok: boolean;
  result: TelegramUpdate[];
}

interface ClarityVoiceResponse {
  intent: { type: string; confidence: number; params: Record<string, unknown> };
  response: string;
  data: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Allowlist — persisted to .allowlist.json
// ---------------------------------------------------------------------------

interface Allowlist {
  allowed_ids: number[];
}

function readAllowlist(): Set<number> {
  if (!existsSync(ALLOWLIST_PATH)) return new Set();
  try {
    const raw = JSON.parse(readFileSync(ALLOWLIST_PATH, "utf8")) as Allowlist;
    return new Set(raw.allowed_ids ?? []);
  } catch {
    return new Set();
  }
}

function writeAllowlist(ids: Set<number>): void {
  const data: Allowlist = { allowed_ids: Array.from(ids) };
  writeFileSync(ALLOWLIST_PATH, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function isAllowed(userId: number): boolean {
  return readAllowlist().has(userId);
}

function authorizeUser(userId: number): void {
  const ids = readAllowlist();
  ids.add(userId);
  writeAllowlist(ids);
  console.log(`[clarity-telegram] Authorized user ${userId}`);
}

// ---------------------------------------------------------------------------
// In-memory pairing code store  { code -> { userId, chatId, expiresAt } }
// ---------------------------------------------------------------------------

interface PendingPair {
  userId: number;
  chatId: number;
  expiresAt: number;
}

const pendingPairs = new Map<string, PendingPair>();

function generatePairingCode(): string {
  return String(Math.floor(100_000 + Math.random() * 900_000));
}

function createPairingCode(userId: number, chatId: number): string {
  // Revoke any existing code for this user
  for (const [code, entry] of pendingPairs.entries()) {
    if (entry.userId === userId) pendingPairs.delete(code);
  }
  const code = generatePairingCode();
  pendingPairs.set(code, { userId, chatId, expiresAt: Date.now() + PAIRING_TTL_MS });
  return code;
}

/**
 * Called by an external process (e.g. Claude Code `/pair <code>` command) to
 * complete pairing.  Returns true when a valid unexpired code is found and the
 * user is added to the allowlist.
 */
export function completePairing(code: string): { success: boolean; userId?: number } {
  const entry = pendingPairs.get(code);
  if (!entry) return { success: false };
  if (Date.now() > entry.expiresAt) {
    pendingPairs.delete(code);
    return { success: false };
  }
  pendingPairs.delete(code);
  authorizeUser(entry.userId);
  return { success: true, userId: entry.userId };
}

// ---------------------------------------------------------------------------
// Telegram API helpers
// ---------------------------------------------------------------------------

async function tgCall<T>(method: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${TG_API}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Telegram ${method} HTTP ${res.status}: ${await res.text()}`);
  }
  const json = (await res.json()) as { ok: boolean; result: T; description?: string };
  if (!json.ok) throw new Error(`Telegram ${method} error: ${json.description ?? "unknown"}`);
  return json.result;
}

async function sendMessage(chatId: number, text: string): Promise<void> {
  await tgCall("sendMessage", { chat_id: chatId, text, parse_mode: "Markdown" });
}

async function getFileUrl(fileId: string): Promise<string> {
  const file = await tgCall<{ file_path: string }>("getFile", { file_id: fileId });
  return `https://api.telegram.org/file/bot${BOT_TOKEN}/${file.file_path}`;
}

async function downloadFile(fileId: string): Promise<Blob> {
  const url = await getFileUrl(fileId);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to download Telegram file: HTTP ${res.status}`);
  return res.blob();
}

// ---------------------------------------------------------------------------
// Clarity backend API helpers
// ---------------------------------------------------------------------------

async function processText(text: string): Promise<ClarityVoiceResponse> {
  const res = await fetch(`${CLARITY_API_URL}/api/voice/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`Clarity API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<ClarityVoiceResponse>;
}

async function processAudio(audioBlob: Blob, mimeType = "audio/ogg"): Promise<ClarityVoiceResponse> {
  const form = new FormData();
  // Telegram voice messages are Opus-encoded OGG files
  const ext = mimeType.includes("ogg") ? "ogg" : "webm";
  form.append("audio", audioBlob, `voice.${ext}`);

  const res = await fetch(`${CLARITY_API_URL}/api/voice/process-audio`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Clarity audio API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<ClarityVoiceResponse>;
}

async function backendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${CLARITY_API_URL}/api/status`, { signal: AbortSignal.timeout(5_000) });
    return res.ok;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

async function handlePairCommand(msg: TelegramMessage): Promise<void> {
  const userId = msg.from?.id;
  const chatId = msg.chat.id;
  if (!userId) return;

  const code = createPairingCode(userId, chatId);
  await sendMessage(
    chatId,
    `Your pairing code is:\n\n*${code}*\n\nIn your Claude Code session, run:\n\`/pair ${code}\`\n\nThis code expires in 5 minutes.`,
  );
  console.log(`[clarity-telegram] Pairing code ${code} issued for user ${userId}`);
}

async function handleStatusCommand(msg: TelegramMessage): Promise<void> {
  const healthy = await backendHealth();
  const statusEmoji = healthy ? "green circle" : "red circle";
  const label = healthy ? "online" : "unreachable";
  await sendMessage(
    msg.chat.id,
    `Clarity backend (${CLARITY_API_URL}): ${statusEmoji} ${label}`,
  );
}

async function handleHelpCommand(msg: TelegramMessage): Promise<void> {
  await sendMessage(
    msg.chat.id,
    [
      "*Clarity Command Centre — Telegram Bridge*",
      "",
      "Send any message and it will be forwarded to Clarity as a voice command.",
      "Voice notes are transcribed and processed automatically.",
      "",
      "*Commands*",
      "/pair — generate a pairing code to authorize this account",
      "/status — check whether the Clarity backend is reachable",
      "/help — show this message",
      "",
      `_Backend: ${CLARITY_API_URL}_`,
    ].join("\n"),
  );
}

// ---------------------------------------------------------------------------
// Message dispatcher
// ---------------------------------------------------------------------------

async function handleMessage(msg: TelegramMessage): Promise<void> {
  const userId = msg.from?.id;
  const chatId = msg.chat.id;
  const text = msg.text?.trim() ?? "";

  // Built-in commands are always available, even for unauthorized users,
  // because /pair is how a new user joins the allowlist.
  if (text === "/start" || text === "/help") {
    await handleHelpCommand(msg);
    return;
  }

  if (text === "/pair") {
    await handlePairCommand(msg);
    return;
  }

  // All other interactions require an authorized sender.
  if (!userId || !isAllowed(userId)) {
    await sendMessage(
      chatId,
      "This account is not authorized.\n\nSend /pair to get a pairing code, then run `/pair <code>` in your Claude Code session.",
    );
    return;
  }

  if (text === "/status") {
    await handleStatusCommand(msg);
    return;
  }

  // Voice note
  if (msg.voice) {
    const voice = msg.voice;
    try {
      console.log(`[clarity-telegram] Processing voice message (${voice.duration}s) from user ${userId}`);
      const audioBlob = await downloadFile(voice.file_id);
      const clarityResp = await processAudio(audioBlob, voice.mime_type ?? "audio/ogg");
      await sendMessage(chatId, clarityResp.response || "Command processed.");
    } catch (err) {
      console.error("[clarity-telegram] Voice processing error:", err);
      await sendMessage(chatId, "Failed to process your voice message. Is the Clarity backend running?");
    }
    return;
  }

  // Plain text command
  if (text) {
    try {
      console.log(`[clarity-telegram] Processing text "${text}" from user ${userId}`);
      const clarityResp = await processText(text);
      const intentLabel = clarityResp.intent?.type ?? "unknown";
      const confidence = Math.round((clarityResp.intent?.confidence ?? 0) * 100);
      const reply = [
        clarityResp.response || "Command processed.",
        `\n_Intent: ${intentLabel} (${confidence}% confidence)_`,
      ].join("\n");
      await sendMessage(chatId, reply);
    } catch (err) {
      console.error("[clarity-telegram] Text processing error:", err);
      await sendMessage(chatId, "Failed to reach the Clarity backend. Is it running?");
    }
    return;
  }

  // Unsupported message type (photo, sticker, etc.)
  await sendMessage(chatId, "Only text and voice messages are supported.");
}

// ---------------------------------------------------------------------------
// Long-polling loop
// ---------------------------------------------------------------------------

async function poll(): Promise<void> {
  let offset = 0;
  console.log(`[clarity-telegram] Polling Telegram for updates (backend: ${CLARITY_API_URL})`);

  while (true) {
    let updates: TelegramUpdate[] = [];
    try {
      const result = await fetch(`${TG_API}/getUpdates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ offset, timeout: 30, allowed_updates: ["message"] }),
        signal: AbortSignal.timeout(40_000), // slightly longer than TG timeout
      });

      if (!result.ok) {
        console.error(`[clarity-telegram] getUpdates HTTP ${result.status} — retrying in 5s`);
        await Bun.sleep(5_000);
        continue;
      }

      const body = (await result.json()) as TelegramGetUpdatesResult;
      if (!body.ok) {
        console.error("[clarity-telegram] getUpdates !ok — retrying in 5s");
        await Bun.sleep(5_000);
        continue;
      }

      updates = body.result;
    } catch (err) {
      // Network error or timeout — back off briefly and retry
      console.error("[clarity-telegram] Poll error:", err);
      await Bun.sleep(5_000);
      continue;
    }

    for (const update of updates) {
      // Advance offset so this update is not re-delivered
      offset = update.update_id + 1;

      if (!update.message) continue;
      try {
        await handleMessage(update.message);
      } catch (err) {
        console.error("[clarity-telegram] Unhandled error for update", update.update_id, err);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Entrypoint
// ---------------------------------------------------------------------------

poll().catch((err) => {
  console.error("[clarity-telegram] Fatal error:", err);
  process.exit(1);
});
