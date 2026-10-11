// The real-render half of the At a Glance diagram check (components/readme_diagram/render_check.py).
//
// It renders each Mermaid source with the pinned `mermaid` package in a headless Chrome or Edge,
// then measures what a reader would see: every node and cluster label against its box, where the
// three mother blocks sit, and whether a label still fits when the browser draws it in a wider
// font than the one it was measured in (the way a hosted renderer clips text).
//
//   node measure.mjs --out result.json [--png-dir dir] [--package mermaid]
//        [--fonts Verdana,Georgia] [--config '{"theme":"default"}'] file.mmd ...
//
// Environment: RP_MERMAID_TOOLS (required) is the directory `npm ci --ignore-scripts` installed
// package.json into; RP_BROWSER optionally names the browser executable. Nothing here touches the
// network: the sources are read from disk and the page is built in memory.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const toolsDir = process.env.RP_MERMAID_TOOLS;
if (!toolsDir) {
  console.error('RP_MERMAID_TOOLS is not set');
  process.exit(2);
}
const require = createRequire(path.join(path.resolve(toolsDir), 'package.json'));

const args = process.argv.slice(2);
const opts = { out: null, pngDir: null, pkg: 'mermaid', fonts: ['Arial', 'Verdana', 'Tahoma', 'Segoe UI', 'Georgia'], config: {}, files: [] };
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--out') opts.out = args[++i];
  else if (a === '--png-dir') opts.pngDir = args[++i];
  else if (a === '--package') opts.pkg = args[++i];
  else if (a === '--fonts') opts.fonts = args[++i].split(',').filter(Boolean);
  else if (a === '--config') opts.config = JSON.parse(args[++i]);
  else opts.files.push(a);
}
if (!opts.out) {
  console.error('--out is required');
  process.exit(2);
}

const BROWSERS = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
];
const executablePath = process.env.RP_BROWSER || BROWSERS.find((p) => fs.existsSync(p));
if (!executablePath) {
  console.error('no Chrome or Edge found; set RP_BROWSER');
  process.exit(2);
}

const puppeteer = (await import(pathToFileURL(require.resolve('puppeteer-core')).href)).default;
const mermaidPkg = require(`${opts.pkg}/package.json`);
const mermaidJs = fs.readFileSync(require.resolve(`${opts.pkg}/dist/mermaid.min.js`), 'utf8');

const browser = await puppeteer.launch({
  executablePath,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars'],
  defaultViewport: { width: 1600, height: 1000, deviceScaleFactor: 1.5 },
});
const page = await browser.newPage();
await page.setContent(
  '<!doctype html><html><body style="margin:0;background:#fff"><div id="host" style="display:inline-block;padding:12px"></div></body></html>',
);
await page.addScriptTag({ content: mermaidJs });

// Runs inside the page: render one source, then measure it natively and once per stress font.
async function renderAndMeasure(src, domId, config, fonts) {
  // eslint-disable-next-line no-undef
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'default', logLevel: 'fatal', ...config });
  let svg;
  try {
    // eslint-disable-next-line no-undef
    ({ svg } = await mermaid.render(domId, src));
  } catch (e) {
    return { error: String((e && e.message) || e).slice(0, 300) };
  }
  const host = document.getElementById('host');
  host.innerHTML = svg;
  const svgEl = host.querySelector('svg');
  if (!svgEl || svgEl.querySelector('.error-icon, .error-text')) return { error: 'mermaid drew its error graphic' };
  const vb = svgEl.viewBox.baseVal;
  svgEl.style.maxWidth = 'none';
  svgEl.setAttribute('width', String(Math.ceil(vb.width)));
  svgEl.setAttribute('height', String(Math.ceil(vb.height)));

  const rect = (el) => {
    const r = el.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height };
  };
  const overflow = (inner, outer) => ({
    x: Math.max(0, outer.x - inner.x, inner.x + inner.w - (outer.x + outer.w)),
    y: Math.max(0, outer.y - inner.y, inner.y + inner.h - (outer.y + outer.h)),
  });
  const bare = (id) => id.replace(/^m\d+-/, '').replace(/^flowchart-/, '').replace(/-\d+$/, '');
  const labelOf = (g) => {
    const fo = g.querySelector('foreignObject');
    if (fo && fo.firstElementChild) {
      const content = rect(fo.firstElementChild);
      const box = rect(fo);
      return {
        mode: 'html',
        text: (fo.textContent || '').replace(/\s+/g, ' ').trim(),
        lines: Math.max(1, Math.round(content.h / 24)),
        textRect: content,
        clipX: Math.max(0, content.x + content.w - (box.x + box.w)),
        clipY: Math.max(0, content.y + content.h - (box.y + box.h)),
      };
    }
    const t = g.querySelector('text');
    if (!t) return null;
    const outer = t.querySelectorAll('tspan.text-outer-tspan');
    return {
      mode: 'svg',
      text: (t.textContent || '').replace(/\s+/g, ' ').trim(),
      lines: Math.max(1, outer.length),
      lineTexts: Array.from(outer).map((o) => (o.textContent || '').replace(/\s+/g, ' ').trim()),
      textRect: rect(t),
      clipX: 0,
      clipY: 0,
    };
  };
  const snapshot = () => {
    const nodes = [];
    for (const g of svgEl.querySelectorAll('g.node')) {
      const shape = g.querySelector('rect, path, polygon, circle, ellipse');
      const label = labelOf(g);
      if (!shape || !label) continue;
      const s = rect(shape);
      const o = overflow(label.textRect, s);
      nodes.push({ id: bare(g.id), text: label.text, lines: label.lines, line_texts: label.lineTexts || [], mode: label.mode, shape: s, text_rect: label.textRect, spill_x: o.x, spill_y: o.y, clip_x: label.clipX, clip_y: label.clipY });
    }
    const clusters = [];
    for (const g of svgEl.querySelectorAll('g.cluster')) {
      const shape = g.querySelector('rect');
      const label = labelOf(g);
      if (!shape) continue;
      const s = rect(shape);
      const o = label ? overflow(label.textRect, s) : { x: 0, y: 0 };
      clusters.push({ id: bare(g.id), text: label ? label.text : '', line_texts: label ? (label.lineTexts || []) : [], mode: label ? label.mode : 'none', shape: s, spill_x: o.x, spill_y: o.y, clip_x: label ? label.clipX : 0, clip_y: label ? label.clipY : 0 });
    }
    return { foreign_objects: svgEl.querySelectorAll('foreignObject').length, nodes, clusters };
  };

  const native = snapshot();
  const stress = {};
  for (const font of fonts) {
    const style = document.createElement('style');
    style.textContent = `#${domId} *{font-family:'${font}',sans-serif !important}`;
    document.head.appendChild(style);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    stress[font] = snapshot();
    style.remove();
  }
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  return { svg: { w: vb.width, h: vb.height }, native, stress };
}

const results = [];
let index = 0;
for (const file of opts.files) {
  const name = path.basename(file).replace(/\.mmd$/, '');
  const src = fs.readFileSync(file, 'utf8');
  const record = { name };
  try {
    const out = await page.evaluate(renderAndMeasure, src, `m${index}`, opts.config, opts.fonts);
    Object.assign(record, out);
    if (opts.pngDir && !out.error) {
      fs.mkdirSync(opts.pngDir, { recursive: true });
      // measure() left the last stress font removed, so the page shows the native rendering.
      const el = await page.$('#host');
      await el.screenshot({ path: path.join(opts.pngDir, `${name}.png`) });
    }
  } catch (e) {
    record.error = String((e && e.message) || e).slice(0, 300);
  }
  results.push(record);
  index++;
}
fs.mkdirSync(path.dirname(path.resolve(opts.out)), { recursive: true });
fs.writeFileSync(opts.out, JSON.stringify({ mermaid: mermaidPkg.version, browser: await browser.version(), results }, null, 1));
await browser.close();
