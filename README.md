# Email Marketing

Hair Solutions Co. email marketing. The sole marketing campaign and lifecycle platform is
**Shopify Messaging + Shopify Flow**. The 53-email programme builds and ships there.

MailerLite is retained only for legacy/reference assets. It is
**not** a campaign or lifecycle platform for this project; the live account had zero campaigns
when re-verified on 2026-08-24. MailerSend remains a separate, transactional-only experiment.

## Email Marketing — Campaign OS

The connector-readable operating system is live in the public
[`vincent-laroche/marketing-os` repository](https://github.com/vincent-laroche/marketing-os)
and [GitHub Project #4](https://github.com/users/vincent-laroche/projects/4).

- 69 canonical Issues: 7 Campaigns, 53 Emails, 8 Tasks, and 1 Bug;
- Email Issues are native sub-issues of their Campaign;
- Issues and pull requests are canonical; the Project mirrors operational state;
- 28 custom fields and six native views cover production, review, launch, performance, and
  Shopify Messaging/Flow readiness;
- `tools/github_campaign_os/` compiles, synchronizes, and verifies the system idempotently;
- `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md` govern new work;
- `tools/email-preview/` provides a fail-closed fictional-fixture renderer that emits rendered
  HTML, a full desktop screenshot, a full mobile screenshot, and exact provenance;
- the GitHub Pages Actions publication workflow is configured; CR-1 is the sole Email approved for
  the first public proof, while repository Pages enablement and the live deployment remain separate
  verified states under Issue #79;
- custom-domain and Cloudflare changes remain separate, unapproved gates.

Merge or approval never configures Shopify, schedules, activates, or sends email.

## Marketing OS

This public repository is the shared Hair Solutions Co. Marketing OS. The Email OS remains the protected production-grade domain, and Social Media OS is a governed domain beside it. The shared operating contract is documented in [`docs/marketing-os/OPERATING-CONTRACT.md`](docs/marketing-os/OPERATING-CONTRACT.md), and the concrete platform design is in [`docs/marketing-os/ARCHITECTURE.md`](docs/marketing-os/ARCHITECTURE.md).

Email source, Campaign OS records, and fail-closed fictional previews remain under the existing Email OS paths. Social source records live under `social-media/` and use the hierarchy `Social Campaign → Content Concept → platform Publication`. The migrated read-only operator dashboard lives under `apps/social-studio/`; it is not the canonical database and must remain authenticated if hosted. Large media stays in the approved asset system; Git stores asset identity, approved URLs, fingerprints, rights, consent, and permitted-use metadata.

The Social Media OS includes a fail-closed source validator, deterministic source manifest builder, dry-run GitHub Issue plan compiler, publication preview generator, Instagram feed-grid generator, reusable Markdown source templates, the imported committed social template library, and the migrated Social Studio application. The initial campaign records are clearly marked non-production fixtures and must be replaced with approved source material before production. No repository operation publishes or schedules social content.

**Nothing is tracked in prose.** Issues and pull requests are canonical (`AGENTS.md` §8). A
finding, a defect, or a "next step" that is not in an Issue or a pull request does not exist —
never leave one in `PROJECT.md`, a plan document, or a chat message. Open an Issue, then cite
the number. `PROJECT.md` is a chronological log, not a backlog.

## Project-local agent suite

Twelve bounded specialists under `.codex/agents/` cover the programme's major workflows without
turning agent prompts into a second database:

- five read-only roles: Project management, lifecycle architecture, audience/consent,
  deliverability/release, and performance analysis;
- four local-write roles: Email production, reusable modules, preview/QA, and Campaign OS
  engineering;
- three approval-gated external operators: Shopify Messaging drafts, disabled Shopify Flow graphs,
  and native Shopify notification templates.

Every role loads `.codex/agents/EMAIL-AGENT-CONTRACT.md`, uses the deterministic routes in
`.codex/agents/ROUTING.md`, resolves work through a canonical or filed Issue, distinguishes five
evidence levels, and returns the same evidence packet. Specialists never spawn other specialists;
the parent agent owns routing and integration. Draft operators default to read-only and cannot
schedule, activate, publish, or send.

Validate the installed prompts and safety invariants with:

```bash
python3 tools/validate_project_agents.py
python3 -m unittest tests.email_operations.test_project_agents -v
```

## Layout

| Path | What it is |
|---|---|
| `Email Reference File/` | **Source of truth.** Notion export of the email system — see below. |
| `shopify-messaging/` | Active 53-email Shopify Messaging build, ledgers, automation plan, and Shopify audience-tag tooling. |
| `github-campaign-os/` | Generated 69-Issue manifest, 28-field Project schema, and read-back reports. |
| `social-media/` | Social source records, templates, schemas, and references. |
| `apps/social-studio/` | Migrated read-only operator dashboard source; not the canonical Social OS database. |
| `docs/marketing-os/ARCHITECTURE.md` | Shared platform architecture and management contract. |
| `docs/social-media/` | Migrated social strategy and design references. |
| `data/social-media/` | Public-safe campaign calendar and production-matrix sources. |
| `tools/github_campaign_os/` | Idempotent Issue/Project compiler, synchronizers, and verifiers. |
| `tools/email-preview/` | Fail-closed Shopify Liquid preview compiler and screenshot/gallery tooling. |
| `tools/instagram-saves/` | Instagram saved-posts → Notion sync and content-idea CLI (moved from `instagram-saves-content-engine`). |
| `email-previews/publication-ledger.json` | Append-only, reviewed publication and withdrawal events for public Pages previews. Active URLs exist only after the matching event is merged to `main`. |
| `.codex/agents/` | Twelve project-local specialists plus their shared operating contract and routing guide. |
| `shopify-messaging/PREVIEW-READINESS.md` | Generated source-readiness inventory: which of the 53 render, and why the rest do not. |
| `mailerlite/` | Legacy MailerLite builders, rendered emails, and API research. Reference only; do not create or push campaigns from it. |
| `mailersend/` | Transactional-only service-email experiment. Never a marketing campaign path. |
| `exports/` | HubSpot CRM exports. PII-bearing, **gitignored**. |
| `export_hubspot.py` | One-shot full HubSpot export (workflows, contacts, deals, orders). |
| `AGENTS.md` | Durable project context and rules. Read first. |
| `PROJECT.md` | Living status log. Read second. |

## `Email Reference File/` — the source of truth

Everything about campaigns, journeys, email structure, module composition, and copy comes
from here. Nothing else in this repo overrides it.

| Path | Contents |
|---|---|
| `emails_master …_all.csv` | The emails database — every email, its journey, timing, and metadata. |
| `modules_master …_all.csv` | The modules database — every module and which emails use it. |
| `emails_modules_hubspot versionr/` | 58 email copy decks (`.md`, incl. 5 `Journey · … Master` docs) **and** 104 complete HubSpot module trios (`module.html` + `fields.json` + `meta.json`), light and dark. |
| `modules_master/` | 80 per-module Notion pages. |
| `Atelier Zero — Resolved HTML Module Previews (102)/` | 104 rendered module previews. The historical folder name is retained even though the verified count is now 104. |

Email families: `W-` welcome, `PP-` post-purchase, `CR-` cart recovery, `WB-` win-back,
`RO-` reorder, `C-` consultation, `BR-` browse, `NL-01…20` newsletter.

## Email preview workflow

Relevant pull requests render safe fictional-fixture previews into one authenticated GitHub Actions
artifact that expires after 14 days. The workflow posts one bounded evidence comment to the pull
request and every affected canonical Email Issue. Expiry is expected: rerunning the exact Actions
run reproduces the artifact from its source revision.

Public publication is a different, manual workflow. It accepts only an Email code and an exact
40-character source SHA, then verifies that the requested Email and the complete public set carry
`preview_public: true` at that committed `main` revision. The full set must render, materialize,
deploy, and pass HTTPS read-back as one snapshot. A separate ledger-only pull request records the
verified URLs; only after that ledger reaches `main` may the Campaign OS synchronize an Email's
clickable `Preview URL`. Merge, approval, scheduling, or a true flag alone never publishes.

No fixture, customer data, token, checkout URL, real unsubscribe link, or private artifact URL is
eligible for the public gallery. Custom-domain and Cloudflare/DNS work are not part of this setup.

## `shopify-messaging/`

This is the active implementation surface for the 53 marketing emails. `emails/` holds the
Shopify-ready HTML, `BUILD-LEDGER.md` records build evidence, and `PHASE5-PLAN.md` records the
current segment, consent, collision, and automation state. Nothing is activated or sent merely
because it exists here.

## `mailerlite/` — legacy/reference only

`ml_content_*.py` hold the per-journey copy (verbatim from the reference file);
`ml_components.py` renders it against the Figma Email Design System v3 tokens;
`build_emails.py` writes `emails/*.html`; `push_campaigns.py` and `configure_campaigns.py`
create and configure drafts via the API. Those scripts are retained as historical implementation
evidence; they are not part of the current Shopify campaign workflow. **Do not create, push,
schedule, or send a marketing campaign through MailerLite from this project.**

`mailerlite/BUILD-LEDGER.md` and `mailerlite/API-SURFACE.md` are historical records only.

## History

The HubSpot-era material — `modules/`, `emails/approved-html/`, `emails/atelier-zero/`,
`emails/second-pass/`, `legacy-csv-snapshots-2026-07-05/`, and the v3 build proofs — was
removed from the working tree on 2026-08-18. It remains in git history at commit `e892e64`
and earlier; recover with `git show e892e64:<path>` or `git checkout e892e64 -- <path>`.
