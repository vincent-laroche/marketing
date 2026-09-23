import { writeFile } from "node:fs/promises";

const [outputPath] = process.argv.slice(2);
const token = process.env.NOTION_API_KEY;
if (!outputPath || !token) throw new Error("NOTION_API_KEY and an output path are required.");

const response = await fetch("https://marketing-os-notion-sync.notionsync.workers.dev/webhooks/notion/pending-token", {
  headers: { Authorization: `Bearer ${token}` },
});
if (!response.ok) throw new Error(`No pending webhook verification token: ${response.status}`);
const { verification_token: verificationToken } = await response.json();
if (typeof verificationToken !== "string" || !verificationToken) throw new Error("Invalid pending verification token.");

const runner = `async () => cloudflare.request({
  method: "PUT",
  path: "/accounts/" + accountId + "/workers/scripts/marketing-os-notion-sync/secrets",
  body: ${JSON.stringify({ name: "NOTION_WEBHOOK_VERIFICATION_TOKEN", type: "secret_text", text: verificationToken })}
})`;
await writeFile(outputPath, JSON.stringify({ code: runner }));
