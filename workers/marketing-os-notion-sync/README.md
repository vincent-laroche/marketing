# Marketing OS Notion Sync Worker

This Worker performs **field-scoped metadata synchronization** for the approved existing Hair Solutions Co. Notion sources. It does not copy or update canonical email copy, planning/business fields, approvals, claims, rights, consent, audience eligibility, Shopify state, Social platform state, schedules, activations, sends, or publications.

## Runtime contract

The Worker reads approved Notion data-source records into its isolated `marketing_*` D1 tables. It writes back only the six declared worker-managed metadata properties: `Marketing OS Key`, `Marketing OS Sync State`, `Marketing OS Source Fingerprint`, `Marketing OS Last Synced`, `Marketing OS Sync Error`, and `Marketing OS Worker Managed Fields`.

It also reads existing native Notion relationships into `marketing_notion_relation` without making any corresponding Notion write. The declared mappings are canonical email `Modules Used` → Email module, Email module `Used In Emails` → canonical email, and Proof Bank `Used In` → canonical email. Stable text keys are read from `Marketing OS Shared Campaign Key` and `Marketing OS Parent Key`; they are not populated, changed, or inferred by this Worker.

| Concern | Control |
| --- | --- |
| Source identity | Stable per-source keys and Notion page IDs. |
| Idempotency | Source fingerprints exclude worker-managed properties. Unchanged records do not generate metadata writes. |
| Native relationships | Existing Notion relation references are persisted in D1 by source page ID and resolved against the matching source mapping. |
| Webhook audit | Every verified event is recorded by event ID, subscription ID, type, entity ID, outcome, and run ID only. Payload content and signatures are never stored. |
| Conflicts | A source change after a non-Notion writer is fail-closed and recorded in `marketing_sync_errors`. |
| Scale | Reconciliation uses a durable Cloudflare Queue as a sequential, 15-record continuation consumer. |
| Worker-to-app evidence | Only aggregate receipts are sent to the HMAC-protected Marketing OS endpoint. |
| Operations | Email sends, Flow activation, audience mutation, Social publishing, and Social scheduling remain unavailable. |

## Operating procedure

Use the authenticated **Sync Health** control in Marketing OS to request a reconciliation. The response means the run was accepted, not that it completed. Review aggregate-only status on the same screen after the Worker posts its receipt. The recurring Worker schedule is intentionally paused until Notion webhook verification and any further approved relationship data are available.

The Worker’s public status endpoint exposes only run-level aggregates and mapping-state counts. It does not disclose source record content or credentials. During the Notion verification handshake only, the incoming verification token is encrypted in D1 with a 10-minute expiry and can be consumed once by an authenticated operator endpoint. It must immediately be rebound as the Worker’s `NOTION_WEBHOOK_VERIFICATION_TOKEN` secret; it is never returned by the public webhook endpoint, placed in a receipt, logged, or committed. After rebinding, complete the Notion UI verification. All later webhook events require the raw-body HMAC signature.

## Verification and recovery

For each controlled run, verify all four conditions: the D1 run is `completed`; `blocked_count` is zero or exceptions are consciously resolved; only worker-managed metadata changed; and the matching aggregate receipt persisted in Marketing OS. For canonical email and Social fixture evidence, compare current Notion fingerprints against the D1 source fingerprints; a mismatch is a fail-closed condition, not permission to overwrite source data.

If any source returns an authorization error, any receipt fails, or an unexpected source/business change is detected, keep the recurring schedule paused. Review `marketing_sync_errors`, correct access or configuration, and run another idempotent manual reconciliation. Do not delete mappings, purge queues, overwrite a source, or use this Worker to perform a marketing action as recovery.
