"""
RAG search tool for the LangChain agent.

Provides a tool that performs vector similarity search against
document chunks stored in pgvector, returning the most relevant
text passages for a given query.
"""

from typing import Any

from langchain_core.tools import tool
from loguru import logger
from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import generate_single_embedding


def make_rag_search_tool(
    db: AsyncSession,
    user_id: int,
    is_admin: bool,
) -> Any:
    """Factory that creates a rag_search tool bound to the current request context.

    The tool performs cosine similarity search against document chunks
    and returns the top-k most relevant passages.
    """

    @tool
    async def rag_search(query: str) -> str:
        """Busca semântica nos documentos extraídos usando RAG (Retrieval-Augmented Generation).

        Use esta ferramenta quando precisar encontrar informações textuais como:
        - Cláusulas específicas de contratos
        - Termos e condições
        - Conteúdo descritivo dos documentos
        - Obrigações, direitos, penalidades
        - Qualquer texto que não seja facilmente buscável por dados estruturados

        NÃO use esta ferramenta para dados numéricos exatos (valores, contagens, datas).
        Para esses, use a ferramenta database_query.

        Args:
            query: A pergunta ou termo de busca em linguagem natural.

        Returns:
            Os trechos mais relevantes encontrados nos documentos.
        """
        logger.info(f"[Tool rag_search] Buscando: {query[:100]}")
        logger.info(f"[Tool rag_search] user_id={user_id}, is_admin={is_admin}")

        try:
            # Step 1: Generate embedding for the query
            logger.info("[Tool rag_search] Gerando embedding da query...")
            query_embedding = await generate_single_embedding(query)
            logger.info(f"[Tool rag_search] Embedding gerado ({len(query_embedding)} dimensões)")

            # Step 2: Build similarity search query with pgvector
            # Using cosine distance operator <=> for similarity ranking
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            if is_admin:
                # Admin sees all documents
                sql = sql_text("""
                    SELECT
                        dc.content,
                        dc.section_type,
                        dc.chunk_index,
                        dc.token_count,
                        dc.metadata_json,
                        d.filename,
                        d.id AS document_id,
                        (dc.embedding <=> :embedding) AS distance
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    WHERE d.status = 'processed'
                    ORDER BY dc.embedding <=> :embedding
                    LIMIT 10
                """)
                result = await db.execute(
                    sql, {"embedding": embedding_str}
                )
            else:
                # Non-admin only sees their own documents
                sql = sql_text("""
                    SELECT
                        dc.content,
                        dc.section_type,
                        dc.chunk_index,
                        dc.token_count,
                        dc.metadata_json,
                        d.filename,
                        d.id AS document_id,
                        (dc.embedding <=> :embedding) AS distance
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    WHERE d.status = 'processed'
                      AND d.user_id = :user_id
                    ORDER BY dc.embedding <=> :embedding
                    LIMIT 10
                """)
                result = await db.execute(
                    sql, {"embedding": embedding_str, "user_id": user_id}
                )

            rows = result.fetchall()
            logger.info(f"[Tool rag_search] Encontrados {len(rows)} chunks relevantes")

            if not rows:
                logger.info("[Tool rag_search] Nenhum chunk encontrado no banco")
                return "Nenhum trecho relevante encontrado nos documentos processados."

            # Step 3: Format results with context
            chunks_text = []
            for i, row in enumerate(rows, 1):
                similarity = 1 - row.distance  # Convert distance to similarity
                section_label = row.section_type or "texto"
                chunks_text.append(
                    f"--- Trecho {i} (Documento: {row.filename}, "
                    f"Seção: {section_label}, "
                    f"Similaridade: {similarity:.2%}) ---\n"
                    f"{row.content}"
                )

            header = f"Encontrados {len(rows)} trechos relevantes:\n\n"
            return header + "\n\n".join(chunks_text)

        except Exception as e:
            logger.error(f"[Tool rag_search] Erro na busca RAG: {e}")
            return f"Erro ao realizar busca semântica: {e}"

    return rag_search
