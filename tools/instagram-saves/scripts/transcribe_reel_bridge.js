#!/usr/bin/env node
const path = require('path');

async function main() {
  const payload = JSON.parse(process.argv[2] || '{}');
  const contentFactoryPath = payload.content_factory_path || '/Users/vincent/02_dev/content-factory';
  const transcriberPath = path.join(contentFactoryPath, 'reels-grabber', 'lib', 'transcriber.js');
  const { transcribeReel } = require(transcriberPath);

  const result = await transcribeReel({
    url: payload.url,
    accountId: payload.account_id || 'saved',
    shortcode: payload.shortcode,
    timeoutMs: payload.timeout_ms || 300000
  });

  process.stdout.write(JSON.stringify(result));
}

main().catch((error) => {
  process.stderr.write(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
