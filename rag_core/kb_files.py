"""Turn a teacher upload into the chunks the library reviews.

TXT and MD are decoded as text. DOCX is the document XML. PDF uses pypdf.
Chunking follows the same rules as ``frontend/src/lib/kbExtract.js`` so a file
the browser would split is split the same way on the server.
"""

import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

MAX_CHUNK = 900
MAX_UPLOAD_BYTES = 5_000_000
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md", ".markdown")
_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class UploadRejected(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def safe_filename(filename: str | None) -> str:
    name = Path(filename or "").name.strip()
    return name or "upload.txt"


def extension_allowed(filename: str) -> bool:
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def filename_title(filename: str | None) -> str:
    base = re.sub(r"\.[^.]+$", "", filename or "Uploaded note")
    base = re.sub(r"[_-]+", " ", base).strip()
    return (base[:140] or "Uploaded note")


def chunk_text(text: str) -> list[dict]:
    clean = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not clean:
        raise ValueError("No text could be extracted.")
    pieces: list[str] = []
    buffer = ""
    for block in re.split(r"\n{2,}", clean):
        part = block.strip()
        if not part:
            continue
        nxt = f"{buffer}\n\n{part}" if buffer else part
        if buffer and (len(nxt) > MAX_CHUNK or part.startswith("#")):
            pieces.append(buffer)
            buffer = part
        else:
            buffer = nxt
    if buffer:
        pieces.append(buffer)
    chunks = []
    for index, content in enumerate(pieces):
        heading = re.search(r"^#{1,3}\s+(.+)$", content, re.M)
        first = re.sub(r"^#+\s*", "", content.split("\n", 1)[0]).strip()
        title = (heading.group(1).strip() if heading else "") or first or f"Chunk {index + 1}"
        chunks.append({"index": index, "title": title[:80], "content": content})
    return chunks


def extract_note(raw: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _pdf_text(raw)
    if name.endswith(".docx"):
        return _docx_text(raw)
    text = raw.decode("utf-8", errors="replace").replace("\x00", "").strip()
    if not text:
        raise ValueError("No text could be extracted.")
    return text


def _pdf_text(raw: bytes) -> str:
    if not raw.startswith(b"%PDF"):
        raise ValueError("That file is not a PDF.")
    from pypdf import PdfReader

    try:
        reader = PdfReader(BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        raise ValueError(
            "No extractable text in this PDF. Export it as TXT, MD, or DOCX and upload that."
        ) from exc
    text = text.replace("\x00", "").strip()
    if len(text) < 40:
        raise ValueError(
            "No extractable text in this PDF. Export it as TXT, MD, or DOCX and upload that."
        )
    return text


def _docx_text(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            xml = archive.read("word/document.xml")
    except KeyError as exc:
        raise ValueError("This DOCX has no word/document.xml.") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError("That file is not a DOCX.") from exc
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ValueError("This DOCX has no word/document.xml.") from exc
    paragraphs = []
    for para in root.iter(f"{_WORD_NS}p"):
        texts = []
        for node in para.iter(f"{_WORD_NS}t"):
            if node.text:
                texts.append(node.text)
            if node.tail:
                texts.append(node.tail)
        paragraphs.append("".join(texts))
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(paragraphs)).strip()
    if not text:
        raise ValueError("The DOCX had no document text.")
    return text
