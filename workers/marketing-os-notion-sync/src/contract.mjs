export const NOTION_VERSION = "2025-09-03";

export const WORKER_MANAGED_FIELDS = [
  "Marketing OS Key",
  "Marketing OS Sync State",
  "Marketing OS Source Fingerprint",
  "Marketing OS Last Synced",
  "Marketing OS Sync Error",
  "Marketing OS Worker Managed Fields"
];

export const SOURCES = [
  { scope: "shared_campaign", dataSourceId: "4186d9fe-d6ab-4460-9622-cb7de438821e", keyPrefix: "marketing:campaign" },
  { scope: "canonical_email", dataSourceId: "fbc9f1df-1126-83a3-a049-87874c8d1a99", keyPrefix: "campaign-os:email" },
  { scope: "email_module", dataSourceId: "f309f1df-1126-821e-8d1b-8714c8bd2bb3", keyPrefix: "campaign-os:module" },
  { scope: "proof", dataSourceId: "d519f1df-1126-8203-ba7a-87a2e56b384d", keyPrefix: "marketing:proof" },
  { scope: "email_automation", dataSourceId: "c789ba58-02d5-45d4-b6b0-201de04febcc", keyPrefix: "campaign-os:automation" },
  { scope: "email_campaign", dataSourceId: "da751d10-2cf6-48af-9184-f8160bb5e3bd", keyPrefix: "marketing:email-campaign" },
  { scope: "audience_plan", dataSourceId: "bbc7227c-d718-4f82-b696-e7c7ed26a0be", keyPrefix: "marketing:audience" },
  { scope: "email_kpi", dataSourceId: "52eda403-7c9c-49d7-8f6e-cdc804d77fcf", keyPrefix: "marketing:email-kpi" },
  { scope: "marketing_kpi", dataSourceId: "3c19f1df-1126-8128-83c1-000bf78a0768", keyPrefix: "marketing:kpi" },
  { scope: "asset", dataSourceId: "bdd0ebbf-2f42-417c-b846-f12ff393beac", keyPrefix: "asset:notion" },
  { scope: "social", dataSourceId: "e59a1965-1b0a-42ca-bfa2-86904b604e3e", keyPrefix: "social:template" }
];

export const NATIVE_RELATION_FIELDS = {
  canonical_email: [{ property: "Modules Used", targetScope: "email_module" }],
  email_module: [{ property: "Used In Emails", targetScope: "canonical_email" }],
  proof: [{ property: "Used In", targetScope: "canonical_email" }]
};

export function slug(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 96) || "unlabelled";
}

export function textValue(property) {
  if (!property || typeof property !== "object") return "";
  if (Array.isArray(property.title)) return property.title.map(item => item.plain_text || item.text?.content || "").join("").trim();
  if (Array.isArray(property.rich_text)) return property.rich_text.map(item => item.plain_text || item.text?.content || "").join("").trim();
  if (typeof property.url === "string") return property.url;
  if (typeof property.select?.name === "string") return property.select.name;
  if (typeof property.status?.name === "string") return property.status.name;
  if (typeof property.number === "number") return String(property.number);
  if (typeof property.checkbox === "boolean") return property.checkbox ? "true" : "false";
  return "";
}

export function pageTitle(page) {
  const properties = page?.properties || {};
  for (const property of Object.values(properties)) {
    if (Array.isArray(property?.title)) return textValue(property);
  }
  return "";
}

export function existingKey(page) {
  return textValue(page?.properties?.["Marketing OS Key"]);
}

export function entityKey(source, page) {
  return existingKey(page) || `${source.keyPrefix}:${slug(pageTitle(page) || page?.id)}`;
}

export function relationshipRefs(sourceScope, page) {
  return (NATIVE_RELATION_FIELDS[sourceScope] || []).flatMap(({ property, targetScope }) => {
    const related = page?.properties?.[property]?.relation;
    if (!Array.isArray(related)) return [];
    return related.filter(reference => typeof reference?.id === "string").map(reference => ({
      relationName: property,
      targetScope,
      targetPageId: reference.id
    }));
  });
}

export function stableProperties(properties = {}) {
  const filtered = Object.entries(properties)
    .filter(([name]) => !WORKER_MANAGED_FIELDS.includes(name))
    .sort(([left], [right]) => left.localeCompare(right));
  return JSON.stringify(Object.fromEntries(filtered));
}

export async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("");
}

export async function hmacSignature(value, secret) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value));
  return `sha256=${Array.from(new Uint8Array(signature), byte => byte.toString(16).padStart(2, "0")).join("")}`;
}

export async function sourceFingerprint(page) {
  return sha256(stableProperties(page?.properties || {}));
}

export function richText(value) {
  return value ? { rich_text: [{ type: "text", text: { content: value.slice(0, 1900) } }] } : { rich_text: [] };
}

export function syncProperties({ key, fingerprint, timestamp, status = "Synced", error = "" }) {
  return {
    "Marketing OS Key": richText(key),
    "Marketing OS Sync State": { select: { name: status } },
    "Marketing OS Source Fingerprint": richText(fingerprint),
    "Marketing OS Last Synced": { date: { start: timestamp } },
    "Marketing OS Sync Error": richText(error),
    "Marketing OS Worker Managed Fields": richText(WORKER_MANAGED_FIELDS.join(", "))
  };
}

export function isEligibleWebhookEvent(event, sourceDataSourceIds) {
  if (!event?.id || !event?.entity?.id) return false;
  if (["data_source.content_updated", "data_source.schema_updated"].includes(event.type)) {
    return event.entity.type === "data_source" && sourceDataSourceIds.has(event.entity.id);
  }
  return ["page.properties_updated", "page.content_updated"].includes(event.type) && event.entity.type === "page";
}
