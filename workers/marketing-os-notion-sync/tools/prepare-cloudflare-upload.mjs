import { readFile, writeFile } from "node:fs/promises";

const [bundlePath, outputPath] = process.argv.slice(2);
if (!bundlePath || !outputPath) throw new Error("Usage: node prepare-cloudflare-upload.mjs <bundle-path> <output-path>");

const code = await readFile(bundlePath, "utf8");
const encoded = Buffer.from(code).toString("base64");
const runner = `async () => {
  const code = atob(${JSON.stringify(encoded)});
  const metadata = {
    main_module: "worker.mjs",
    compatibility_date: "2026-08-27",
    compatibility_flags: ["nodejs_compat"],
    bindings: [
      { type: "d1", name: "SYNC_DB", id: "45cbd382-a5bc-4804-8d97-ccf4bf61b638" },
      { type: "plain_text", name: "MARKETING_OS_RECEIPT_URL", text: "https://haircampaign-k3lybt53.manus.space/api/sync/notion/receipt" },
      { type: "queue", name: "SYNC_QUEUE", queue_name: "marketing-os-notion-sync-continuations" }
    ]
  };
  const boundary = "MarketingOsSync" + Date.now();
  const body = [
    "--" + boundary,
    "Content-Disposition: form-data; name=\\"metadata\\"",
    "Content-Type: application/json",
    "",
    JSON.stringify(metadata),
    "--" + boundary,
    "Content-Disposition: form-data; name=\\"worker.mjs\\"; filename=\\"worker.mjs\\"",
    "Content-Type: application/javascript+module",
    "",
    code,
    "--" + boundary + "--",
    ""
  ].join("\\r\\n");
  return cloudflare.request({
    method: "PUT",
    path: "/accounts/" + accountId + "/workers/scripts/marketing-os-notion-sync",
    body,
    contentType: "multipart/form-data; boundary=" + boundary,
    rawBody: true
  });
}`;

await writeFile(outputPath, JSON.stringify({ code: runner }));
