// Requires sharp for SVG rasterization; used only when maintaining documentation.
import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const sharp = require('sharp');
const assets = new URL('../../docs/assets/', import.meta.url);
const logo = await sharp(await readFile(new URL('source/logo-master.png', assets)))
  .resize(512, 512).png({ compressionLevel: 9 }).toBuffer();
await writeFile(new URL('brand/logo.png', assets), logo);
const watershed = await readFile(new URL('figures/watershed.jpg', assets));
const replacements = {
  '{{LOGO_URI}}': `data:image/png;base64,${logo.toString('base64')}`,
  '{{WATERSHED_URI}}': `data:image/jpeg;base64,${watershed.toString('base64')}`,
};

for (const [name, destination] of [
  ['build-workflow', 'figures'],
  ['social-preview', 'brand'],
]) {
  let svg = await readFile(new URL(`source/${name}.svg`, assets), 'utf8');
  for (const [placeholder, value] of Object.entries(replacements)) {
    svg = svg.replaceAll(placeholder, value);
  }
  await writeFile(new URL(`${destination}/${name}.svg`, assets), svg);
  await sharp(Buffer.from(svg)).png({ compressionLevel: 9, palette: true }).toFile(
    fileURLToPath(new URL(`${destination}/${name}.png`, assets)),
  );
  if (name === 'build-workflow') {
    // Preserve links to the figure from the original README.
    await writeFile(new URL('../ewhb_architecture.svg', assets), svg);
  }
  console.log(`Rendered ${destination}/${name}.svg and .png`);
}
