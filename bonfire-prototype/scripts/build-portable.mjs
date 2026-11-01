import { build } from 'vite';
import react from '@vitejs/plugin-react';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const result = await build({
  root,
  configFile: false,
  plugins: [react()],
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    write: false,
    emptyOutDir: false,
    lib: { entry: root + 'src/main.jsx', name: 'BonfirePrototype', formats: ['iife'] },
    cssCodeSplit: false,
  },
});
const chunks = (Array.isArray(result) ? result : [result]).flatMap(r => r.output);
const javascript = chunks.filter(c => c.type === 'chunk').map(c => c.code).join('\n')
  .replaceAll('/The_Bonfire_Faction_Management_Requirements_EN.pdf', './The_Bonfire_Faction_Management_Requirements_EN.pdf')
  .replace(/<\/script/gi, '<\\/script');
const css = chunks.filter(c => c.type === 'asset' && c.fileName.endsWith('.css'))
  .map(c => String(c.source)).join('\n')
  .replace(/@import\s*(?:url\(\s*(?:"[^"]*"|'[^']*'|[^)]*)\s*\)|"[^"]*"|'[^']*')\s*;/g, '');
if (!css.trimStart().startsWith(':root{') || /@import|fonts\.googleapis/.test(css)) {
  throw new Error('Portable CSS is incomplete or still contains a remote font import.');
}
const html = `<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Bonfire Faction Management</title><style>${css}</style></head>
<body><div id="root"></div><script>${javascript}</script></body></html>`;
await writeFile(new URL('../Open Prototype.html', import.meta.url), html.replaceAll('./The_Bonfire_Faction_Management_Requirements_EN.pdf', './public/The_Bonfire_Faction_Management_Requirements_EN.pdf'));
await writeFile(new URL('../../The_Bonfire_Faction_Management.html', import.meta.url), html);
await writeFile(new URL('../../The_Bonfire_Faction_Management_Offline.html', import.meta.url), html);
console.log('Portable HTML generated. Open it directly; no server or network is required.');
