"""
RAG search tool for the LangChain agent.

Provides a tool that performs vector similarity search against
document chunks stored in pgvector, with optional filtering by
document IDs or document type for precise, scoped searches.
"""

from typing import Any

from langchain_core.tools import tool
from loguru import logger
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import generate_single_embedding


# Similarity threshold: discard chunks with cosine distance > 0.65 (similarity < 35%)
_MAX_DISTANCE = 0.65


def make_rag_search_tool(
    db: AsyncSession,
    user_id: int,
    is_admin: bool,
) -> Any:
    """Factory that creates a rag_search tool bound to the current request context."""

    @tool
    async def rag_search(
        query: str,
        document_ids: str = "",
        document_type: str = "",
    ) -> str:
        """Busca semântica nos documentos extraídos usando RAG.

        Use esta ferramenta para encontrar informações textuais nos documentos:
        cláusulas, termos, condições, obrigações, penalidades, conteúdo descritivo.

        IMPORTANTE: Se você sabe QUAIS documentos são relevantes (por ter usado
        database_query antes), SEMPRE passe os document_ids para focar a busca.

        Args:
            query: Pergunta ou termo de busca em linguagem natural.
            document_ids: Opcional. IDs de documentos (ex: "42,87").
                          Aceita formatos "1,2", "[1, 2]" ou lista.
            document_type: Opcional. Tipo de documento ou termo no nome do arquivo
                           (ex: "contrato", "relatorio").

        Returns:
            Trechos relevantes encontrados, ou mensagem de que nada foi encontrado.
        """
        # Log the search parameters
        logger.info(f"[Tool rag_search] Query: {query[:100]}")
        logger.info(
            f"[Tool rag_search] Filtros: document_ids={document_ids or '(todos)'}, "
            f"document_type={document_type or '(todos)'}, "
            f"user_id={user_id}, is_admin={is_admin}"
        )

        try:
            # Step 1: Generate embedding for the query
            logger.info("[Tool rag_search] Gerando embedding da query...")
            query_embedding = await generate_single_embedding(query)
            logger.info(f"[Tool rag_search] Embedding gerado ({len(query_embedding)} dimensões)")

            # Step 2: Build filtered similarity search query
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            # Build WHERE clauses dynamically
            where_clauses = [
                "d.status = 'processed'",
                f"(dc.embedding <=> :embedding) < {_MAX_DISTANCE}",
            ]
            params: dict[str, Any] = {"embedding": embedding_str}

            # Filter by user (non-admin)
            if not is_admin:
                where_clauses.append("d.user_id = :user_id")
                params["user_id"] = user_id

            # Filter by document IDs
            if document_ids and document_ids.strip():
                try:
                    # Cleanup input like "[1, 2]" or "1, 2"
                    clean_ids = document_ids.replace("[", "").replace("]", "")
                    ids = [int(x.strip()) for x in clean_ids.split(",") if x.strip()]
                    
                    if ids:
                        placeholders = ",".join(str(i) for i in ids)
                        where_clauses.append(f"dc.document_id IN ({placeholders})")
                        logger.info(f"[Tool rag_search] Filtro por document_ids: {ids}")
                except ValueError:
                    logger.warning(f"[Tool rag_search] document_ids inválidos: {document_ids} (ignorando filtro)")

            # Filter by document type (checks type OR filename)
            if document_type and document_type.strip():
                where_clauses.append("(d.type ILIKE :doc_type OR d.filename ILIKE :doc_type)")
                params["doc_type"] = f"%{document_type.strip()}%"
                logger.info(f"[Tool rag_search] Filtro por tipo/nome: {document_type}")

            where_sql = " AND ".join(where_clauses)

            sql = sql_text(f"""
                SELECT
                    dc.content,
                    dc.section_type,
                    dc.chunk_index,
                    dc.token_count,
                    d.filename,
                    d.id AS document_id,
                    d.type AS doc_type,
                    (dc.embedding <=> :embedding) AS distance
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE {where_sql}
                ORDER BY dc.embedding <=> :embedding
                LIMIT 10
            """)

            result = await db.execute(sql, params)
            rows = result.fetchall()

            logger.info(f"[Tool rag_search] Encontrados {len(rows)} chunks (threshold: similaridade > {(1 - _MAX_DISTANCE):.0%})")

            if not rows:
                filter_desc = ""
                if document_ids:
                    filter_desc += f" nos documentos {document_ids}"
                if document_type:
                    filter_desc += f" do tipo '{document_type}'"
                logger.info("[Tool rag_search] Nenhum chunk relevante encontrado")
                return f"Nenhum trecho relevante encontrado{filter_desc} nos documentos processados."

            # Step 3: Format results with context
            chunks_text = []
            unique_docs = set()

            for i, row in enumerate(rows, 1):
                similarity = 1 - row.distance
                section_label = row.section_type or "texto"
                doc_type_label = f", Tipo: {row.doc_type}" if row.doc_type else ""
                
                unique_docs.add(f"{row.filename} (ID:{row.document_id})")
                
                chunks_text.append(
                    f"--- Trecho {i} (Documento: {row.filename} [ID:{row.document_id}]"
                    f"{doc_type_label}, "
                    f"Seção: {section_label}, "
                    f"Similaridade: {similarity:.0%}) ---\n"
                    f"{row.content}"
                )
                logger.info(
                    f"[Tool rag_search]   Chunk {i}: doc={row.filename} "
                    f"similaridade={similarity:.0%} seção={section_label}"
                )

            docs_summary = ", ".join(sorted(unique_docs))
            header = (
                f"Encontrados {len(rows)} trechos relevantes em {len(unique_docs)} documento(s):\n"
                f"[{docs_summary}]\n\n"
            )
            return header + "\n\n".join(chunks_text)

        except Exception as e:
            logger.error(f"[Tool rag_search] Erro na busca RAG: {e}")
            return f"Erro ao realizar busca semântica: {e}"

    return rag_search
