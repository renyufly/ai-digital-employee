"""Extract text and page metadata from local PDF documents."""
'''
读取知识库目录里的所有 PDF，把每一页的文字提取出来，
并记录“文件名 + 页码 + 内容”
'''
'''
使用 pypdf 也是因为当前知识库是文本型 PDF；
扫描 PDF 则需要 OCR.
'''

import logging
from pathlib import Path

from pypdf import PdfReader

from app.rag.models import PageDocument

logger = logging.getLogger(__name__)


def load_pdf_pages(knowledge_dir: Path) -> list[PageDocument]:
    """Load every text PDF in deterministic filename/page order."""

    '''
    找到目录下所有 PDF，并按文件名排序，保证每次读取顺序一致
    '''
    pdf_paths = sorted(knowledge_dir.glob("*.pdf"), key=lambda path: path.name.lower())
    if not pdf_paths:
        raise FileNotFoundError(f"知识库目录中没有 PDF：{knowledge_dir}")

    pages: list[PageDocument] = []
    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path) # 用 pypdf 打开 PDF
        for page_number, page in enumerate(reader.pages, start=1):
            ''' 逐页读取，页码从 1 开始 '''

            '''
            提取当前页文字；如果提取不到就变成空字符串
            '''
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
