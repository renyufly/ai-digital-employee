"""Agent-facing local knowledge-base search tool."""
'''
把 RAG 检索功能包装成一个标准 Agent Tool：
输入问题 → 调用知识库检索 → 返回上下文、来源或统一错误
'''
import logging
from functools import lru_cache

from app.agent.schemas import ToolResult
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import InvalidVectorStoreError, RAGNotReadyError

logger = logging.getLogger(__name__)


@lru_cache
def _default_retriever() -> KnowledgeRetriever:
    '''
    创建默认的 KnowledgeRetriever，并通过 @lru_cache 缓存这个对象
    '''
    """Reuse the local model and FAISS index across sequential tool calls."""
    return KnowledgeRetriever()


def search_company_docs(
    query: str, retriever: KnowledgeRetriever | None = None
) -> ToolResult:
    """Return retrieved context and sources; the later Agent writes the answer."""
    '''
    Agent 给出 query -> KnowledgeRetriever.retrieve(query)
    -> Embedding + FAISS 相似度检索 -> 得到相关 sources
    -> 封装成 ToolResult
    '''
    try:
        sources = (retriever or _default_retriever()).retrieve(query)

    except ValueError as exc:
        return ToolResult(
            success=False,
            error_code="INVALID_ARGUMENT",
            message=str(exc),
        )
    except RAGNotReadyError as exc:
        return ToolResult(
            success=False,
            error_code="RAG_NOT_READY",
            message=str(exc),
        )
    except InvalidVectorStoreError:
        logger.exception("RAG vector store validation failed")
        return ToolResult(
            success=False,
            error_code="RAG_NOT_READY",
            message="知识库索引无效，请重新运行构建脚本",
        )
    except Exception:
        logger.exception("Unexpected knowledge retrieval failure")
        return ToolResult(
            success=False,
            error_code="TOOL_INTERNAL_ERROR",
            message="知识库检索失败",
        )

    if not sources:
        ''' 没搜到相关内容 '''
        return ToolResult(
            success=False,
            error_code="NO_RELEVANT_DOCUMENT",
            message="现有企业资料中没有足够相关的信息",
        )

    '''
    query：用户查询
    context: 检索到的文档正文，之后给 LLM 用来生成答案
    sources：来源信息，例如文件名、页码、chunk、相似度，方便前端展示引用
    注意：只负责检索，不负责生成最终回答.
    '''
    return ToolResult(
        success=True,
        data={
            "query": query.strip(),
            "context": [source.content for source in sources],
        },
        error_code=None,
        message=f"检索到 {len(sources)} 条相关企业资料",
        sources=sources,
    )
