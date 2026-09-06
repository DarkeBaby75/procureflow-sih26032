import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sourceDir = path.join(root, 'hosted');
const outputDir = path.join(root, 'dist');
const template = await readFile(path.join(root, 'worker', 'index.template.js'), 'utf8');
const assets = {};

for (const name of await readdir(sourceDir)) {
  const filename = path.join(sourceDir, name);
  assets[`/${name === 'index.html' ? '' : name}`] = await readFile(filename, 'utf8');
}

await rm(outputDir, { recursive: true, force: true });
await mkdir(path.join(outputDir, 'server'), { recursive: true });
await writeFile(
  path.join(outputDir, 'server', 'index.js'),
  template.replace('__PROCUREFLOW_ASSETS__', JSON.stringify(assets)),
  'utf8',
);

console.log(`Built ${Object.keys(assets).length} embedded assets and the hosted SMS worker.`);
