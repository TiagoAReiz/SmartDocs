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
        filename: str = "",
    ) -> str:
        """Busca semântica nos documentos extraídos usando RAG.

        Use esta ferramenta para encontrar informações textuais nos documentos:
        cláusulas, termos, condições, obrigações, penalidades, conteúdo descritivo.

        IMPORTANTE: Se você sabe QUAIS documentos são relevantes (por ter usado
        database_query antes), SEMPRE passe os document_ids reais do banco de dados (tabela `documents.id`) para focar a busca.
        ⚠️ NUNCA use os números de uma lista enumerada que você gerou (ex: "1. Documento") como se fossem IDs reais.

        Args:
            query: Pergunta ou termo de busca em linguagem natural.
            document_ids: Opcional. IDs reais da tabela `documents` (ex: "42,87").
                          Aceita formatos "1,2", "[1, 2]" ou lista.
            document_type: Opcional. Tipo de documento ou termo no nome do arquivo
                           (ex: "contrato", "relatorio").
            filename: Opcional. Nome do arquivo (parcial ou completo) se você quiser filtrar um arquivo listado no histórico.

        Returns:
            Trechos relevantes encontrados, ou mensagem de que nada foi encontrado.
        """
        # Log the search parameters
        logger.info(f"[Tool rag_search] Query: {query[:100]}")
        logger.info(
            f"[Tool rag_search] Filtros: document_ids={document_ids or '(todos)'}, "
            f"document_type={document_type or '(todos)'}, filename={filename or '(todos)'}, "
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
            base_where_clauses = ["d.status = 'processed'"]
            params: dict[str, Any] = {"embedding": embedding_str}

            # Filter by user (non-admin)
            if not is_admin:
                base_where_clauses.append("d.user_id = :user_id")
                params["user_id"] = user_id

            # Filter by document IDs
            if document_ids and document_ids.strip():
                try:
                    # Cleanup input like "[1, 2]" or "1, 2"
                    clean_ids = document_ids.replace("[", "").replace("]", "")
                    ids = [int(x.strip()) for x in clean_ids.split(",") if x.strip()]
                    
                    if ids:
                        placeholders = ",".join(str(i) for i in ids)
                        base_where_clauses.append(f"dc.document_id IN ({placeholders})")
                        logger.info(f"[Tool rag_search] Filtro por document_ids: {ids}")
                except ValueError:
                    logger.warning(f"[Tool rag_search] document_ids inválidos: {document_ids} (ignorando filtro)")

            # Filter by document type (checks type OR filename)
            if document_type and document_type.strip():
                base_where_clauses.append("(d.type ILIKE :doc_type OR d.filename ILIKE :doc_type)")
                params["doc_type"] = f"%{document_type.strip()}%"
                logger.info(f"[Tool rag_search] Filtro por tipo/nome: {document_type}")

            # Filter by explicit filename
            if filename and filename.strip():
                base_where_clauses.append("d.filename ILIKE :filename_filter")
                params["filename_filter"] = f"%{filename.strip()}%"
                logger.info(f"[Tool rag_search] Filtro por filename: {filename}")

            # Helper to execute query
            async def execute_query(clauses, limit=10):
                where_sql = " AND ".join(clauses)
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
                    LIMIT {limit}
                """)
                result = await db.execute(sql, params)
                return result.fetchall()

            # 1. Try Strict Search
            strict_clauses = base_where_clauses + [f"(dc.embedding <=> :embedding) < {_MAX_DISTANCE}"]
            rows = await execute_query(strict_clauses)
            logger.info(f"[Tool rag_search] Encontrados {len(rows)} chunks (threshold: similaridade > {(1 - _MAX_DISTANCE):.0%})")

            # 2. Fallback: Relaxed Search (if filtered by ID or filename and no results)
            is_filtered = bool((document_ids and document_ids.strip()) or (filename and filename.strip()))
            if not rows and is_filtered:
                logger.info("[Tool rag_search] Fallback: Buscando sem threshold de similaridade nos documentos filtrados...")
                rows = await execute_query(base_where_clauses, limit=5)
                logger.info(f"[Tool rag_search] Encontrados {len(rows)} chunks no fallback")

            if not rows:
                filter_desc = ""
                if document_ids:
                    filter_desc += f" nos IDs {document_ids}"
                if filename:
                    filter_desc += f" (arquivo '{filename}')"
                if document_type:
                    filter_desc += f" do tipo '{document_type}'"
                logger.info("[Tool rag_search] Nenhum chunk relevante encontrado")
                
                # ReAct Behavioral Guardrail: If they used document_ids and failed, it's 99% a hallucination.
                if document_ids:
                    return (
                        f"Nenhum trecho encontrado{filter_desc}. "
                        f"DICA OBRIGATÓRIA: Se você pegou esses IDs ('{document_ids}') de uma lista numerada do chat (1, 2, 3...), "
                        f"VOCÊ ALUCINOU OS IDs! O número do item na lista não é o ID do banco. "
                        f"FAÇA UMA NOVA CHAMADA para 'rag_search' AGORA, deixando 'document_ids' VAZIO e usando o parâmetro 'filename' "
                        f"com o nome do arquivo que você quer resumir."
                    )
                
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
