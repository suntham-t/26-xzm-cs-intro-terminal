// Extract per-page text from a PDF into JSON, for the content pipeline.
//
// Usage:  node content/notes/_extract-pdf-text.mjs <input.pdf> <out.json> [toolsDir]
//
// STATUS: this is now the FALLBACK engine.  _build-json.py prefers pypdfium2
//   (in-process, no node and no node_modules needed) and only shells out to this
//   script when pypdfium2 cannot be imported or its extraction raises -- use
//   CT_EXTRACTOR=node to force this path, CT_EXTRACTOR=pdfium to forbid it.
//   The JSON shape below is the frozen contract both engines must satisfy.
//
// Why this file exists in the project (and not in $env:TEMP):
//   `--add chNN` has to derive `non_content_pages` for a brand-new chapter, which
//   needs a page-by-page text dump of the deck.  A one-off script in TEMP cannot
//   serve a pipeline that runs every week, so this is the production tool.
//
// Why it resolves pdfjs-dist by ABSOLUTE URL instead of `import 'pdfjs-dist/...'`:
//   Node resolves bare specifiers relative to the *importing file*, so a script
//   living in content/notes/ can never see D:\opencode\course\_tools\node_modules.
//   pdfjs-dist/legacy/build/pdf.mjs is fully bundled (zero top-level imports), so
//   importing it by absolute file: URL is safe and keeps the dependency where it
//   already is (we do not install anything, and we do not duplicate node_modules).
import { pathToFileURL } from 'url';
import fs from 'fs';
import path from 'path';

const TOOLS_DEFAULT = 'D:/opencode/course/_tools';

const pdfPath = process.argv[2];
const outPath = process.argv[3];
const toolsDir = process.argv[4] || process.env.CT_TOOLS || TOOLS_DEFAULT;

if (!pdfPath || !outPath) {
  console.error('usage: node _extract-pdf-text.mjs <input.pdf> <out.json> [toolsDir]');
  process.exit(2);
}
if (!fs.existsSync(pdfPath)) {
  console.error(`PDF not found: ${pdfPath}`);
  process.exit(2);
}

const pdfjsEntry = path.join(toolsDir, 'node_modules', 'pdfjs-dist', 'legacy', 'build', 'pdf.mjs');
if (!fs.existsSync(pdfjsEntry)) {
  console.error(`pdfjs-dist not found at ${pdfjsEntry}`);
  console.error('set CT_TOOLS=<dir containing node_modules/pdfjs-dist> to override');
  process.exit(2);
}
const { getDocument } = await import(pathToFileURL(pdfjsEntry).href);

const data = new Uint8Array(fs.readFileSync(pdfPath));
const doc = await getDocument({ data, useSystemFonts: false, disableFontFace: true }).promise;

const pages = [];
for (let i = 1; i <= doc.numPages; i++) {
  const page = await doc.getPage(i);
  const tc = await page.getTextContent();
  let text = '';
  for (const item of tc.items) {
    if (typeof item.str === 'string') text += item.str;
    if (item.hasEOL) text += ' | ';
  }
  text = text.replace(/\s+/g, ' ').trim();
  pages.push({ page: i, chars: text.length, text });
}

fs.writeFileSync(outPath, JSON.stringify({
  pdf: path.resolve(pdfPath),
  numPages: doc.numPages,
  pages,
}, null, 1), 'utf8');

console.log(`numPages ${doc.numPages}`);
console.log(`wrote ${outPath}`);
