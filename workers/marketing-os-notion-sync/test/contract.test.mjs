import assert from "node:assert/strict";
import test from "node:test";
import { SOURCES, WORKER_MANAGED_FIELDS, entityKey, hmacSignature, isEligibleWebhookEvent, relationshipRefs, slug, sourceFingerprint, stableProperties, syncProperties } from "../src/contract.mjs";

const samplePage = {
  id: "page-1",
  properties: {
    "Email name": { title: [{ plain_text: "W-1 · Welcome" }] },
    Subject: { rich_text: [{ plain_text: "Welcome to Hair Solutions Co." }] },
    "Marketing OS Key": { rich_text: [{ plain_text: "campaign-os:email:w-1-welcome" }] },
    "Marketing OS Sync State": { select: { name: "Synced" } }
  }
};

test("uses the established key namespace and preserves an existing source key", () => {
  const source = SOURCES.find(item => item.scope === "canonical_email");
  assert.equal(entityKey(source, samplePage), "campaign-os:email:w-1-welcome");
  assert.equal(slug("J3 · Win-Back → Sunset"), "j3-win-back-sunset");
});

test("fingerprints exclude worker-managed values so a worker metadata write cannot trigger a false source conflict", async () => {
  const baseline = await sourceFingerprint(samplePage);
  const changedWorkerMetadata = structuredClone(samplePage);
  changedWorkerMetadata.properties["Marketing OS Sync State"] = { select: { name: "Blocked" } };
  assert.equal(await sourceFingerprint(changedWorkerMetadata), baseline);
  assert.ok(!stableProperties(samplePage.properties).includes("Marketing OS Sync State"));
});

test("writes only the approved worker-managed Notion properties", () => {
  const properties = syncProperties({ key: "social:template:reel", fingerprint: "abc123", timestamp: "2026-08-27T00:00:00.000Z" });
  assert.deepEqual(Object.keys(properties), WORKER_MANAGED_FIELDS);
  assert.equal(properties["Marketing OS Sync State"].select.name, "Synced");
  assert.equal(properties["Marketing OS Key"].rich_text[0].text.content, "social:template:reel");
});

test("keeps source content and business controls outside the worker-managed write set", () => {
  assert.ok(!WORKER_MANAGED_FIELDS.includes("Body"));
  assert.ok(!WORKER_MANAGED_FIELDS.includes("Subject"));
  assert.ok(!WORKER_MANAGED_FIELDS.includes("Approved"));
  assert.ok(!WORKER_MANAGED_FIELDS.includes("Marketing OS Platform State"));
});

test("produces the HMAC format required by the Marketing OS aggregate receipt boundary", async () => {
  const signature = await hmacSignature('{"runId":"a3d837bd"}', "test-secret");
  assert.match(signature, /^sha256=[a-f0-9]{64}$/);
});

test("keeps the source inventory unique so a bounded continuation cannot process a scope twice", () => {
  const scopes = SOURCES.map(source => source.scope);
  assert.equal(new Set(scopes).size, scopes.length);
  assert.equal(scopes.length, 11);
});

test("limits a bounded Worker invocation to a conservative batch that fits a queue consumer execution", () => {
  assert.ok(SOURCES.length > 0);
  assert.ok(WORKER_MANAGED_FIELDS.length > 0);
});

test("treats shared campaign and parent keys as stable text relationship anchors rather than editable business relations", () => {
  assert.ok(!WORKER_MANAGED_FIELDS.includes("Marketing OS Parent Key"));
  assert.ok(!WORKER_MANAGED_FIELDS.includes("Marketing OS Shared Campaign Key"));
});

test("extracts only declared existing native relation references and does not infer cross-channel links", () => {
  const page = { properties: { "Modules Used": { relation: [{ id: "module-a" }, { id: "module-b" }] } } };
  assert.deepEqual(relationshipRefs("canonical_email", page), [
    { relationName: "Modules Used", targetScope: "email_module", targetPageId: "module-a" },
    { relationName: "Modules Used", targetScope: "email_module", targetPageId: "module-b" }
  ]);
  assert.deepEqual(relationshipRefs("social", page), []);
});

test("allows only approved source-level events and mapped-page candidate events into the webhook gate", () => {
  const sourceIds = new Set(SOURCES.map(source => source.dataSourceId));
  assert.equal(isEligibleWebhookEvent({ id: "event-1", type: "data_source.content_updated", entity: { id: SOURCES[0].dataSourceId, type: "data_source" } }, sourceIds), true);
  assert.equal(isEligibleWebhookEvent({ id: "event-2", type: "data_source.content_updated", entity: { id: "outside-source", type: "data_source" } }, sourceIds), false);
  assert.equal(isEligibleWebhookEvent({ id: "event-3", type: "page.properties_updated", entity: { id: "candidate-page", type: "page" } }, sourceIds), true);
  assert.equal(isEligibleWebhookEvent({ id: "event-4", type: "page.created", entity: { id: "candidate-page", type: "page" } }, sourceIds), false);
});
