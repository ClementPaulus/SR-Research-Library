"""Write a small, valid, text-extractable PDF without external dependencies (acceptance fixtures only).

The output uses the standard Helvetica font and Tj text operators, which pypdf extracts reliably.
"""

from __future__ import annotations


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(lines: list, title: str = "", author: str = "") -> bytes:
    """Return PDF bytes rendering ``lines`` (one paragraph per entry, wrapped at ~95 chars) on as many pages as needed."""
    wrapped: list = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        words, current = line.split(), ""
        for word in words:
            if len(current) + len(word) + 1 > 95:
                wrapped.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        wrapped.append(current)
    per_page = 48
    pages = [wrapped[i:i + per_page] for i in range(0, len(wrapped), per_page)] or [[""]]

    objects: list = []  # 1-based object bodies

    def add(body: str) -> int:
        objects.append(body)
        return len(objects)

    font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    content_ids = []
    pages_id_placeholder = len(objects) + 1 + 2 * len(pages)  # pages object comes after page/content pairs
    for page_lines in pages:
        stream_lines = ["BT", "/F1 11 Tf", "14 TL", "50 760 Td"]
        for text in page_lines:
            stream_lines.append(f"({_escape(text)}) Tj T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        content = add(f"<< /Length {len(stream.encode('latin-1', 'replace'))} >>\nstream\n{stream}\nendstream")
        page = add(f"<< /Type /Page /Parent {pages_id_placeholder} 0 R /MediaBox [0 0 612 792] "
                   f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {content} 0 R >>")
        content_ids.append(content)
        page_ids.append(page)
    pages_id = add(f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {len(page_ids)} >>")
    assert pages_id == pages_id_placeholder
    catalog = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
    info = add(f"<< /Title ({_escape(title)}) /Author ({_escape(author)}) /Producer (SR portal acceptance fixture) >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n{body}\nendobj\n".encode("latin-1", "replace")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
