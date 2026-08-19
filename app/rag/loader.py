"""Extract text and page metadata from local PDF documents."""

import logging
from pathlib import Path

from pypdf import PdfReader

from app.rag.models import PageDocument

logger = logging.getLogger(__name__)


def load_pdf_pages(knowledge_dir: Path) -> list[PageDocument]:
    """Load every text PDF in deterministic filename/page order."""
    pdf_paths = sorted(knowledge_dir.glob("*.pdf"), key=lambda path: path.name.lower())
    if not pdf_paths:
        raise FileNotFoundError(f"知识库目录中没有 PDF：{knowledge_dir}")

    pages: list[PageDocument] = []
    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                logger.warning("Skipping empty PDF page: file=%s page=%s", pdf_path.name, page_number)
                continue
            pages.append(
                PageDocument(file=pdf_path.name, page=page_number, content=text)
            )

    if not pages:
        raise ValueError(f"知识库 PDF 没有可提取的文本：{knowledge_dir}")
    return pages
