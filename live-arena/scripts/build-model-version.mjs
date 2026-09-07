import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';

// Portable LF-normalized source custody, not an execution attestation. The frozen
// referee digest separately binds game rules and the bundled tactical opponent.
export async function buildModelVersion(referee) {
  const sources = {};
  for (const name of ['src/models.ts', 'src/model-version-transport.ts', 'src/model-development.ts',
    'src/frontier-version.ts', 'src/self-improvement.ts', 'src/strategic-value.ts', 'src/learning.ts', 'package-lock.json']) {
    const text = (await readFile(new URL('../' + name, import.meta.url), 'utf8')).replaceAll('\r\n', '\n');
    sources[name] = createHash('sha256').update(text).digest('hex');
  }
  const digest = createHash('sha256').update(JSON.stringify({ referee, sources })).digest('hex');
  await writeFile(new URL('../src/model-version-manifest.ts', import.meta.url),
    `// Generated source custody; not identity or execution attestation.\nexport default ${JSON.stringify({ digest, referee, sources })} as const;\n`);
}
