import { writeFile } from "node:fs/promises";

const [secretName, environmentName, outputPath] = process.argv.slice(2);
const token = process.env[environmentName];
if (!secretName || !environmentName || !outputPath || !token) throw new Error("secret name, environment variable name, and output path are required.");

const runner = `async () => cloudflare.request({
  method: "PUT",
  path: "/accounts/" + accountId + "/workers/scripts/marketing-os-notion-sync/secrets",
  body: ${JSON.stringify({ name: secretName, type: "secret_text", text: token })}
})`;

await writeFile(outputPath, JSON.stringify({ code: runner }));
