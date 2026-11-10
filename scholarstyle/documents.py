"""Bounded document extraction and transparent text-only Word export."""
import difflib
import html
import re
from pathlib import Path

MAX_BYTES = 512 * 1024 * 1024
MAX_TEXT = 12_000_000


def extract(path, progress=lambda message: None, cancelled=lambda: False):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("文件超过 512 MB 上限。请拆分后导入。")
    parts, size = [], 0

    def add(value):
        nonlocal size
        if cancelled():
            raise InterruptedError("任务已取消")
        value = value.strip()
        size += len(value)
        if size > MAX_TEXT:
            raise ValueError("提取文本超过 1200 万字符。请拆分文档。")
        if value:
            parts.append(value)

    if path.suffix.lower() == '.pdf':
        from pypdf import PdfReader
        with path.open('rb') as stream:
            reader = PdfReader(stream)
            if reader.is_encrypted and not reader.decrypt(''):
                raise ValueError("PDF 已加密，请先解密。")
            for i, page in enumerate(reader.pages):
                progress(f"读取 {path.name} · 第 {i + 1}/{len(reader.pages)} 页")
                add(page.extract_text() or '')
    elif path.suffix.lower() == '.docx':
        from docx import Document
        from docx.table import Table
        # Inspect the archive before python-docx expands it in memory.
        from zipfile import ZipFile
        with ZipFile(path) as archive:
            if sum(x.file_size for x in archive.infolist()) > MAX_BYTES * 2:
                raise ValueError("Word 解压后超过 1 GB，请拆分文档。")
        doc = Document(path)
        for block in doc.iter_inner_content():
            if isinstance(block, Table):
                for row in block.rows:
                    add(' | '.join(cell.text for cell in row.cells))
            else:
                add(block.text)
    else:
        raise ValueError("支持 .docx 和含文本的 .pdf；旧版 .doc 请另存为 .docx。")
    text = '\n\n'.join(parts)
    if len(text.strip()) < 50:
        raise ValueError("未提取到足够文本。扫描 PDF 请先 OCR 后导入。")
    return text


def chunks(text, limit=4000):
    """Lossless, bounded chunks, preferring paragraph/sentence boundaries."""
    while text:
        end = min(limit, len(text))
        if end < len(text):
            cut = max(text.rfind('\n\n', 0, end), text.rfind('. ', 0, end))
            if cut > limit // 2:
                end = cut + 2
            else:
                space = text.rfind(' ', 0, end)
                if space > limit // 2:
                    end = space + 1
        yield text[:end]
        text = text[end:]


def diff_tokens(before, after):
    a, b = re.findall(r'\s+|\S+', before), re.findall(r'\s+|\S+', after)
    for tag, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            yield 'equal', ''.join(a[i:j])
        else:
            if tag in ('delete', 'replace'):
                yield 'delete', ''.join(a[i:j])
            if tag in ('insert', 'replace'):
                yield 'insert', ''.join(b[k:l])


def diff_html(before, after):
    result = []
    for tag, value in diff_tokens(before, after):
        safe = html.escape(value).replace('\n', '<br>')
        if tag == 'delete':
            safe = f'<span style="color:#b42318;background-color:#fee4e2;text-decoration:line-through">{safe}</span>'
        elif tag == 'insert':
            safe = f'<span style="color:#067647;background-color:#dcfae6">{safe}</span>'
        result.append(safe)
    return ''.join(result)


def export_word(path, records, marked=False, source=None):
    from docx import Document
    from docx.shared import Pt, RGBColor
    doc = Document()
    doc.styles['Normal'].font.name = 'Times New Roman'
    doc.styles['Normal'].font.size = Pt(12)
    # Reassemble first: chunk boundaries must not create artificial paragraphs.
    before = ''.join(r['original'] for r in records)
    after = ''.join(r['revised'] for r in records)
    if marked:
        doc.add_paragraph('Revision comparison · green: added · red strikethrough: removed')
        p = doc.add_paragraph()
        for kind, value in diff_tokens(before, after):
            run = p.add_run(value)
            if kind != 'equal':
                run.font.color.rgb = RGBColor.from_string('067647' if kind == 'insert' else 'B42318')
                run.font.strike = kind == 'delete'
    else:
        for paragraph in after.split('\n\n'):
            doc.add_paragraph(paragraph)
    if source:
        from io import BytesIO
        from docx.shared import Inches
        source = Path(source)
        if not source.exists():
            raise ValueError('Original draft is missing; restore it before exporting images.')
        images = []
        if source.suffix.lower() == '.docx':
            from zipfile import ZipFile
            with ZipFile(source) as archive:
                images = [(name, archive.read(name)) for name in archive.namelist()
                          if name.startswith('word/media/') and not name.endswith('/')]
        elif source.suffix.lower() == '.pdf':
            from pypdf import PdfReader
            with source.open('rb') as stream:
                reader = PdfReader(stream)
                seen = set()
                for page in reader.pages:
                    for image in page.images:
                        import hashlib
                        digest = hashlib.sha256(image.data).hexdigest()
                        if digest not in seen:
                            images.append((image.name, image.data))
                            seen.add(digest)
        if images:
            doc.add_page_break()
            doc.add_heading('Original figures (unchanged)', level=1)
            for name, data in images:
                try:
                    picture = doc.add_picture(BytesIO(data))
                    maximum = Inches(6)
                    if picture.width > maximum:
                        picture.height = int(picture.height * maximum / picture.width)
                        picture.width = maximum
                except Exception as error:
                    raise ValueError(f'Cannot embed original image {name}; export stopped to avoid losing figures.') from error
    import os
    import tempfile
    path = Path(path)
    handle, temporary = tempfile.mkstemp(suffix='.docx', dir=path.parent)
    os.close(handle)
    try:
        doc.save(temporary)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
