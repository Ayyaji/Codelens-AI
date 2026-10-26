/** Turn an uploaded note into reviewable chunks. TXT and MD are read as text. */

const MAX_CHUNK = 900;

export function chunkText(text) {
  const clean = String(text || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .trim();
  if (!clean) throw new Error("No text could be extracted.");

  const pieces = [];
  let buffer = "";
  const blocks = clean.split(/\n{2,}/);
  for (const block of blocks) {
    const part = block.trim();
    if (!part) continue;
    const next = buffer ? `${buffer}\n\n${part}` : part;
    if (buffer && (next.length > MAX_CHUNK || part.startsWith("#"))) {
      pieces.push(buffer);
      buffer = part;
    } else {
      buffer = next;
    }
  }
  if (buffer) pieces.push(buffer);

  return pieces.map((content, index) => {
    const heading = content.match(/^#{1,3}\s+(.+)$/m);
    const firstLine = content.split("\n")[0].replace(/^#+\s*/, "").trim();
    return {
      index,
      title: (heading?.[1] || firstLine || `Chunk ${index + 1}`).slice(0, 80),
      content,
    };
  });
}

export async function extractFileText(file) {
  const name = String(file?.name || "").toLowerCase();
  if (name.endsWith(".txt") || name.endsWith(".md") || name.endsWith(".markdown")) {
    return file.text();
  }
  if (name.endsWith(".docx")) return extractDocx(file);
  if (name.endsWith(".pdf")) return extractPdf(file);
  throw new Error("Upload a PDF, DOCX, TXT, or MD file.");
}

async function extractDocx(file) {
  const buffer = await file.arrayBuffer();
  const xml = await readZipText(buffer, "word/document.xml");
  const text = xml
    .replace(/<w:p[^>]*\/>/g, "\n")
    .replace(/<w:p[\s>]/g, "\n<w:p ")
    .replace(/<w:tab\/>/g, "\t")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  if (!text) throw new Error("The DOCX had no document text.");
  return text;
}

async function extractPdf(file) {
  const raw = new TextDecoder("latin1").decode(await file.arrayBuffer());
  if (!raw.startsWith("%PDF")) throw new Error("That file is not a PDF.");
  const pieces = [];
  for (const match of raw.matchAll(/\((?:\\.|[^\\)])+\)\s*Tj/g)) {
    pieces.push(unescapePdf(match[0].replace(/\)\s*Tj$/, "").slice(1)));
  }
  const text = pieces.join(" ").replace(/[ \t]{2,}/g, " ").trim();
  if (text.length < 40) {
    throw new Error("No extractable text in this PDF. Export it as TXT, MD, or DOCX and upload that.");
  }
  return text;
}

function unescapePdf(value) {
  return value
    .replace(/\\n/g, "\n")
    .replace(/\\r/g, "")
    .replace(/\\t/g, " ")
    .replace(/\\([()\\])/g, "$1")
    .replace(/\\(\d{3})/g, (_, oct) => String.fromCharCode(parseInt(oct, 8)));
}

async function readZipText(buffer, wanted) {
  const bytes = new Uint8Array(buffer);
  const view = new DataView(buffer);
  let offset = 0;
  while (offset + 30 <= bytes.length && view.getUint32(offset, true) === 0x04034b50) {
    const method = view.getUint16(offset + 8, true);
    const compSize = view.getUint32(offset + 18, true);
    const nameLen = view.getUint16(offset + 26, true);
    const extraLen = view.getUint16(offset + 28, true);
    const nameStart = offset + 30;
    const dataStart = nameStart + nameLen + extraLen;
    if (dataStart + compSize > bytes.length) break;
    const name = new TextDecoder().decode(bytes.subarray(nameStart, nameStart + nameLen));
    if (name === wanted) {
      const data = bytes.subarray(dataStart, dataStart + compSize);
      if (method === 0) return new TextDecoder().decode(data);
      if (method === 8) return inflateRaw(data);
      throw new Error("That DOCX uses a compression method the browser cannot read.");
    }
    offset = dataStart + compSize;
  }
  throw new Error("This DOCX has no word/document.xml.");
}

async function inflateRaw(data) {
  if (typeof DecompressionStream !== "function") {
    throw new Error("This browser cannot decompress a DOCX.");
  }
  const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
  return new Response(stream).text();
}
