import { NOTION_VERSION, SOURCES, entityKey, hmacSignature, isEligibleWebhookEvent, relationshipRefs, sourceFingerprint, syncProperties } from "./contract.mjs";

const NOTION_BASE = "https://api.notion.com/v1";
const MAX_PAGES_PER_INVOCATION = 15;
const MAX_NOTION_RETRIES = 2;
const WEBHOOK_TOKEN_TTL_MS = 10 * 60 * 1000;
const encoder = new TextEncoder();
const APPROVED_DATA_SOURCE_IDS = new Set(SOURCES.map(source => source.dataSourceId));

function notionHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
  };
}

function pause(milliseconds) {
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}

function base64(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

function bytesFromBase64(value) {
  return Uint8Array.from(atob(value), character => character.charCodeAt(0));
}

async function webhookEncryptionKey(secret) {
  const keyMaterial = await crypto.subtle.digest("SHA-256", encoder.encode(secret));
  return crypto.subtle.importKey("raw", keyMaterial, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
}

async function encryptWebhookToken(token, secret) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await webhookEncryptionKey(secret), encoder.encode(token));
  return { ciphertext: base64(new Uint8Array(encrypted)), iv: base64(iv) };
}

async function decryptWebhookToken(ciphertext, iv, secret) {
  const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv: bytesFromBase64(iv) }, await webhookEncryptionKey(secret), bytesFromBase64(ciphertext));
  return new TextDecoder().decode(plaintext);
}

function plainTextProperty(page, propertyName) {
  const property = page?.properties?.[propertyName];
  if (Array.isArray(property?.rich_text)) return property.rich_text.map(part => part.plain_text || "").join("").trim();
  if (Array.isArray(property?.title)) return property.title.map(part => part.plain_text || "").join("").trim();
  return "";
}

function stableRelationshipAnchor(page) {
  return plainTextProperty(page, "Marketing OS Parent Key") || plainTextProperty(page, "Marketing OS Shared Campaign Key");
}

async function notion(env, path, options = {}) {
  let response;
  for (let attempt = 0; attempt <= MAX_NOTION_RETRIES; attempt += 1) {
    response = await fetch(`${NOTION_BASE}${path}`, {
      ...options,
      headers: { ...notionHeaders(env.NOTION_API_KEY), ...(options.headers || {}) }
    });
    if (response.ok) return response.status === 204 ? null : response.json();
    const retryable = response.status === 429 || response.status >= 500;
    if (!retryable || attempt === MAX_NOTION_RETRIES) break;
    const retryAfter = Number(response.headers.get("Retry-After"));
    await pause(Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter * 1000 : 500 * (attempt + 1));
  }
  throw new Error(`Notion ${options.method || "GET"} ${path} failed: ${response?.status || "network"}`);
}

async function ensureSchema(db) {
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS marketing_notion_mapping (
      scope TEXT NOT NULL,
      entity_key TEXT NOT NULL,
      notion_page_id TEXT NOT NULL,
      notion_url TEXT NOT NULL,
      source_fingerprint TEXT NOT NULL,
      parent_key TEXT NOT NULL DEFAULT '',
      last_write_source TEXT NOT NULL,
      last_write_at INTEGER NOT NULL,
      sync_state TEXT NOT NULL,
      PRIMARY KEY (scope, entity_key),
      UNIQUE (notion_page_id)
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS marketing_sync_runs (
      id TEXT PRIMARY KEY,
      started_at INTEGER NOT NULL,
      completed_at INTEGER,
      source_count INTEGER NOT NULL,
      record_count INTEGER NOT NULL DEFAULT 0,
      blocked_count INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL,
      error TEXT
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS marketing_sync_errors (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entity_key TEXT NOT NULL,
      source TEXT NOT NULL,
      error_code TEXT NOT NULL,
      error_message TEXT NOT NULL,
      raw_context TEXT NOT NULL,
      created_at INTEGER NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS marketing_sync_sources (
      run_id TEXT NOT NULL,
      scope TEXT NOT NULL,
      cursor TEXT,
      observed_count INTEGER NOT NULL DEFAULT 0,
      changed_count INTEGER NOT NULL DEFAULT 0,
      blocked_count INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL,
      error TEXT,
      PRIMARY KEY (run_id, scope)
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS marketing_notion_relation (
      source_scope TEXT NOT NULL,
      source_key TEXT NOT NULL,
      relation_name TEXT NOT NULL,
      target_scope TEXT NOT NULL,
      target_page_id TEXT NOT NULL,
      observed_at INTEGER NOT NULL,
      PRIMARY KEY (source_scope, source_key, relation_name, target_scope, target_page_id)
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS marketing_webhook_verification (
      singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
      token_ciphertext TEXT NOT NULL,
      token_iv TEXT NOT NULL,
      expires_at INTEGER NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS marketing_webhook_events (
      event_id TEXT PRIMARY KEY,
      subscription_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      outcome TEXT NOT NULL,
      run_id TEXT,
      received_at INTEGER NOT NULL
    )`)
  ]);
}

async function createRunIfAbsent(env, runId) {
  const existing = await env.SYNC_DB.prepare(`SELECT status FROM marketing_sync_runs WHERE id = ?`).bind(runId).first();
  if (existing) return existing.status;
  const statements = [
    env.SYNC_DB.prepare(`INSERT INTO marketing_sync_runs (id, started_at, source_count, status) VALUES (?, ?, ?, 'running')`)
      .bind(runId, Date.now(), SOURCES.length),
    ...SOURCES.map(source => env.SYNC_DB.prepare(`INSERT INTO marketing_sync_sources (run_id, scope, status) VALUES (?, ?, 'pending')`)
      .bind(runId, source.scope))
  ];
  await env.SYNC_DB.batch(statements);
  return "running";
}

async function persistNativeRelationships(env, source, key, page) {
  const references = relationshipRefs(source.scope, page);
  const statements = [
    env.SYNC_DB.prepare(`DELETE FROM marketing_notion_relation WHERE source_scope = ? AND source_key = ?`)
      .bind(source.scope, key),
    ...references.map(reference => env.SYNC_DB.prepare(`INSERT INTO marketing_notion_relation
      (source_scope, source_key, relation_name, target_scope, target_page_id, observed_at)
      VALUES (?, ?, ?, ?, ?, ?)`)
      .bind(source.scope, key, reference.relationName, reference.targetScope, reference.targetPageId, Date.now()))
  ];
  await env.SYNC_DB.batch(statements);
}

async function syncPage(env, source, page, timestamp) {
  const key = entityKey(source, page);
  const fingerprint = await sourceFingerprint(page);
  const parentKey = stableRelationshipAnchor(page);
  const existing = await env.SYNC_DB.prepare(`SELECT source_fingerprint, last_write_source FROM marketing_notion_mapping WHERE scope = ? AND entity_key = ?`)
    .bind(source.scope, key).first();
  if (existing?.source_fingerprint === fingerprint) {
    await env.SYNC_DB.prepare(`UPDATE marketing_notion_mapping SET parent_key = ?, notion_page_id = ?, notion_url = ? WHERE scope = ? AND entity_key = ?`)
      .bind(parentKey, page.id, page.url, source.scope, key).run();
    await persistNativeRelationships(env, source, key, page);
    return { key, changed: false };
  }
  if (existing && existing.last_write_source !== "notion") {
    const message = `Conflict: Notion source changed after ${existing.last_write_source} wrote the mapped record.`;
    await env.SYNC_DB.prepare(`INSERT INTO marketing_sync_errors (entity_key, source, error_code, error_message, raw_context, created_at) VALUES (?, 'notion', 'marketing_sync_conflict', ?, ?, ?)`)
      .bind(key, message, JSON.stringify({ scope: source.scope, notionUrl: page.url }), Date.now()).run();
    return { key, changed: false, blocked: true };
  }
  await notion(env, `/pages/${page.id}`, {
    method: "PATCH",
    body: JSON.stringify({ properties: syncProperties({ key, fingerprint, timestamp }) })
  });
  await env.SYNC_DB.prepare(`INSERT INTO marketing_notion_mapping
    (scope, entity_key, notion_page_id, notion_url, source_fingerprint, parent_key, last_write_source, last_write_at, sync_state)
    VALUES (?, ?, ?, ?, ?, ?, 'notion', ?, 'Synced')
    ON CONFLICT(scope, entity_key) DO UPDATE SET
      notion_page_id = excluded.notion_page_id,
      notion_url = excluded.notion_url,
      source_fingerprint = excluded.source_fingerprint,
      parent_key = excluded.parent_key,
      last_write_source = excluded.last_write_source,
      last_write_at = excluded.last_write_at,
    sync_state = excluded.sync_state`
  ).bind(source.scope, key, page.id, page.url, fingerprint, parentKey, Date.parse(timestamp)).run();
  await persistNativeRelationships(env, source, key, page);
  return { key, changed: true };
}

async function recordSourceFailure(env, runId, source, error) {
  const message = error instanceof Error ? error.message : "Unknown source synchronization error";
  await env.SYNC_DB.batch([
    env.SYNC_DB.prepare(`UPDATE marketing_sync_sources SET status = 'failed', blocked_count = blocked_count + 1, error = ? WHERE run_id = ? AND scope = ?`)
      .bind(message, runId, source.scope),
    env.SYNC_DB.prepare(`INSERT INTO marketing_sync_errors (entity_key, source, error_code, error_message, raw_context, created_at) VALUES (?, 'notion', 'marketing_source_query_failed', ?, ?, ?)`)
      .bind(`${source.scope}:${runId}`, message, JSON.stringify({ scope: source.scope, dataSourceId: source.dataSourceId }), Date.now())
  ]);
}

async function processSourceBatch(env, runId, source, state, capacity) {
  let payload;
  try {
    payload = await notion(env, `/data_sources/${source.dataSourceId}/query`, {
      method: "POST",
      body: JSON.stringify({ page_size: capacity, ...(state.cursor ? { start_cursor: state.cursor } : {}) })
    });
  } catch (error) {
    await recordSourceFailure(env, runId, source, error);
    return { processed: 0, terminal: true };
  }

  let observed = 0;
  let changed = 0;
  let blocked = 0;
  for (const page of payload.results || []) {
    try {
      const result = await syncPage(env, source, page, new Date().toISOString());
      observed += 1;
      if (result.changed) changed += 1;
      if (result.blocked) blocked += 1;
    } catch (error) {
      observed += 1;
      blocked += 1;
      const message = error instanceof Error ? error.message : "Unknown page sync error";
      await env.SYNC_DB.prepare(`INSERT INTO marketing_sync_errors (entity_key, source, error_code, error_message, raw_context, created_at) VALUES (?, 'notion', 'marketing_sync_failed', ?, ?, ?)`)
        .bind(page.id, message, JSON.stringify({ source: source.scope, notionUrl: page.url }), Date.now()).run();
    }
    await pause(350);
  }
  const terminal = !payload.has_more;
  await env.SYNC_DB.prepare(`UPDATE marketing_sync_sources
    SET cursor = ?, observed_count = observed_count + ?, changed_count = changed_count + ?, blocked_count = blocked_count + ?, status = ?
    WHERE run_id = ? AND scope = ?`)
    .bind(terminal ? null : payload.next_cursor, observed, changed, blocked, terminal ? "completed" : "running", runId, source.scope).run();
  return { processed: observed, terminal };
}

async function summarizeRun(env, runId) {
  const sourceSummary = await env.SYNC_DB.prepare(`SELECT
    COUNT(*) AS source_count,
    SUM(CASE WHEN status IN ('completed', 'failed') THEN 1 ELSE 0 END) AS terminal_count,
    COALESCE(SUM(observed_count), 0) AS record_count,
    COALESCE(SUM(changed_count), 0) AS changed_count,
    COALESCE(SUM(blocked_count), 0) AS blocked_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_source_count
    FROM marketing_sync_sources WHERE run_id = ?`).bind(runId).first();
  return {
    terminal: Number(sourceSummary?.terminal_count || 0) === SOURCES.length,
    recordCount: Number(sourceSummary?.record_count || 0),
    changedCount: Number(sourceSummary?.changed_count || 0),
    blockedCount: Number(sourceSummary?.blocked_count || 0),
    failedSourceCount: Number(sourceSummary?.failed_source_count || 0)
  };
}

async function notifyMarketingOs(env, result) {
  if (!env.MARKETING_OS_RECEIPT_URL) return;
  const rawBody = JSON.stringify({ ...result, source: "cloudflare-worker", status: "completed", completedAt: new Date().toISOString() });
  const response = await fetch(env.MARKETING_OS_RECEIPT_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Marketing-OS-Signature": await hmacSignature(rawBody, env.NOTION_API_KEY)
    },
    body: rawBody
  });
  if (!response.ok) throw new Error(`Marketing OS receipt endpoint failed: ${response.status}`);
}

async function enqueueContinuation(env, runId) {
  if (!env.SYNC_QUEUE?.send) throw new Error("SYNC_QUEUE binding is required for bounded reconciliation continuation.");
  await env.SYNC_QUEUE.send({ runId });
}

export async function runSyncBatch(env, runId = crypto.randomUUID()) {
  if (!env.NOTION_API_KEY) throw new Error("NOTION_API_KEY is required.");
  await ensureSchema(env.SYNC_DB);
  const existingStatus = await createRunIfAbsent(env, runId);
  if (existingStatus !== "running") return { runId, terminal: true };

  try {
    let remaining = MAX_PAGES_PER_INVOCATION;
    while (remaining > 0) {
      const state = await env.SYNC_DB.prepare(`SELECT scope, cursor FROM marketing_sync_sources WHERE run_id = ? AND status IN ('pending', 'running') ORDER BY rowid LIMIT 1`)
        .bind(runId).first();
      if (!state) break;
      const source = SOURCES.find(candidate => candidate.scope === state.scope);
      if (!source) throw new Error(`Unknown configured synchronization scope: ${state.scope}`);
      const result = await processSourceBatch(env, runId, source, state, remaining);
      remaining -= result.processed;
      if (result.processed === 0 && !result.terminal) break;
    }

    const summary = await summarizeRun(env, runId);
    if (!summary.terminal) {
      await enqueueContinuation(env, runId);
      return { runId, terminal: false, ...summary };
    }
    await env.SYNC_DB.prepare(`UPDATE marketing_sync_runs SET completed_at = ?, record_count = ?, blocked_count = ?, status = 'completed', error = NULL WHERE id = ?`)
      .bind(Date.now(), summary.recordCount, summary.blockedCount, runId).run();
    const result = { runId, recordCount: summary.recordCount, changedCount: summary.changedCount, blockedCount: summary.blockedCount };
    try {
      await notifyMarketingOs(env, result);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Marketing OS receipt failed";
      await env.SYNC_DB.prepare(`INSERT INTO marketing_sync_errors (entity_key, source, error_code, error_message, raw_context, created_at) VALUES (?, 'marketing_os', 'marketing_os_receipt_failed', ?, ?, ?)`)
        .bind(runId, message, "{}", Date.now()).run();
    }
    return { ...result, terminal: true, failedSourceCount: summary.failedSourceCount };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown synchronization error";
    await env.SYNC_DB.prepare(`UPDATE marketing_sync_runs SET completed_at = ?, status = 'failed', error = ? WHERE id = ?`)
      .bind(Date.now(), message, runId).run();
    throw error;
  }
}

async function syncStatus(env) {
  await ensureSchema(env.SYNC_DB);
  const [latestRun, mappingState] = await Promise.all([
    env.SYNC_DB.prepare(`SELECT id, started_at, completed_at, source_count, record_count, blocked_count, status FROM marketing_sync_runs ORDER BY started_at DESC LIMIT 1`).first(),
    env.SYNC_DB.prepare(`SELECT sync_state AS state, COUNT(*) AS count FROM marketing_notion_mapping GROUP BY sync_state`).all()
  ]);
  return { ok: true, service: "marketing-os-notion-sync", operations: "disabled", latestRun: latestRun || null, mappings: mappingState.results || [] };
}

async function captureWebhookVerificationToken(env, token) {
  const encrypted = await encryptWebhookToken(token, env.NOTION_API_KEY);
  await env.SYNC_DB.prepare(`INSERT INTO marketing_webhook_verification (singleton, token_ciphertext, token_iv, expires_at)
    VALUES (1, ?, ?, ?)
    ON CONFLICT(singleton) DO UPDATE SET token_ciphertext = excluded.token_ciphertext, token_iv = excluded.token_iv, expires_at = excluded.expires_at`)
    .bind(encrypted.ciphertext, encrypted.iv, Date.now() + WEBHOOK_TOKEN_TTL_MS).run();
}

async function consumeWebhookVerificationToken(env) {
  await ensureSchema(env.SYNC_DB);
  const stored = await env.SYNC_DB.prepare(`SELECT token_ciphertext, token_iv, expires_at FROM marketing_webhook_verification WHERE singleton = 1`).first();
  if (!stored || Number(stored.expires_at) < Date.now()) {
    await env.SYNC_DB.prepare(`DELETE FROM marketing_webhook_verification WHERE singleton = 1`).run();
    return null;
  }
  await env.SYNC_DB.prepare(`DELETE FROM marketing_webhook_verification WHERE singleton = 1`).run();
  return decryptWebhookToken(stored.token_ciphertext, stored.token_iv, env.NOTION_API_KEY);
}

async function approvedWebhookEvent(env, payload) {
  if (!isEligibleWebhookEvent(payload, APPROVED_DATA_SOURCE_IDS)) return false;
  if (payload.entity.type === "data_source") return true;
  const mapped = await env.SYNC_DB.prepare(`SELECT 1 FROM marketing_notion_mapping WHERE notion_page_id = ? LIMIT 1`)
    .bind(payload.entity.id).first();
  return Boolean(mapped);
}

async function recordWebhookEvent(env, payload, outcome, runId = null) {
  const result = await env.SYNC_DB.prepare(`INSERT OR IGNORE INTO marketing_webhook_events
    (event_id, subscription_id, event_type, entity_id, outcome, run_id, received_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)`)
    .bind(payload.id, payload.subscription_id || "unknown", payload.type, payload.entity.id, outcome, runId, Date.now()).run();
  return Number(result.meta?.changes || 0) === 1;
}

async function validWebhook(request, env, rawBody) {
  if (!env.NOTION_WEBHOOK_VERIFICATION_TOKEN) return false;
  const supplied = request.headers.get("X-Notion-Signature") || "";
  if (!supplied.startsWith("sha256=")) return false;
  const expected = await hmacSignature(rawBody, env.NOTION_WEBHOOK_VERIFICATION_TOKEN);
  if (expected.length !== supplied.length) return false;
  let mismatch = 0;
  for (let index = 0; index < expected.length; index += 1) mismatch |= expected.charCodeAt(index) ^ supplied.charCodeAt(index);
  return mismatch === 0;
}

function trustedSyncRequest(request, env) {
  const supplied = request.headers.get("Authorization") || "";
  const expected = `Bearer ${env.NOTION_API_KEY || ""}`;
  if (!env.NOTION_API_KEY || supplied.length !== expected.length) return false;
  let mismatch = 0;
  for (let index = 0; index < expected.length; index += 1) mismatch |= expected.charCodeAt(index) ^ supplied.charCodeAt(index);
  return mismatch === 0;
}

function validRunId(value) {
  return typeof value === "string" && /^[A-Za-z0-9-]{8,64}$/.test(value);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") return Response.json({ ok: true, service: "marketing-os-notion-sync", operations: "disabled" });
    if (request.method === "GET" && url.pathname === "/status") return Response.json(await syncStatus(env));
    if (request.method === "GET" && url.pathname === "/webhooks/notion/pending-token") {
      if (!trustedSyncRequest(request, env)) return new Response("Unauthorized", { status: 401 });
      const token = await consumeWebhookVerificationToken(env);
      return token ? Response.json({ verification_token: token }, { headers: { "Cache-Control": "no-store" } }) : new Response("No pending verification token", { status: 404 });
    }
    if (request.method === "POST" && url.pathname === "/sync") {
      if (!trustedSyncRequest(request, env)) return new Response("Unauthorized", { status: 401 });
      const continuationId = request.headers.get("X-Marketing-OS-Continuation");
      const runId = validRunId(continuationId) ? continuationId : crypto.randomUUID();
      ctx.waitUntil(runSyncBatch(env, runId));
      return Response.json({ accepted: true, runId, operations: "disabled" }, { status: 202 });
    }
    if (request.method !== "POST" || url.pathname !== "/webhooks/notion") return new Response("Not found", { status: 404 });

    const rawBody = await request.text();
    let payload;
    try {
      payload = JSON.parse(rawBody);
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }
    if (typeof payload.verification_token === "string" && payload.verification_token) {
      await ensureSchema(env.SYNC_DB);
      await captureWebhookVerificationToken(env, payload.verification_token);
      return Response.json({ ok: true });
    }
    if (!(await validWebhook(request, env, rawBody))) return new Response("Invalid webhook signature", { status: 401 });
    await ensureSchema(env.SYNC_DB);
    if (!(await approvedWebhookEvent(env, payload))) {
      await recordWebhookEvent(env, payload, "ignored");
      return Response.json({ accepted: false, ignored: true });
    }
    const runId = crypto.randomUUID();
    if (!(await recordWebhookEvent(env, payload, "accepted", runId))) return Response.json({ accepted: false, duplicate: true });
    ctx.waitUntil(runSyncBatch(env, runId));
    return Response.json({ accepted: true, runId }, { status: 202 });
  },
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(runSyncBatch(env));
  },
  async queue(batch, env, ctx) {
    const work = Promise.all(batch.messages.map(async message => {
      const runId = message.body?.runId;
      if (!validRunId(runId)) {
        message.ack();
        return;
      }
      try {
        await runSyncBatch(env, runId);
        message.ack();
      } catch {
        message.retry({ delaySeconds: 5 });
      }
    }));
    ctx.waitUntil(work);
    await work;
  }
};
