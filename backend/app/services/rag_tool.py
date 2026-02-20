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
            filename: Opcional. Nome do arquivo (parcial ou completo) se você quiser filtrar um arquivo listado no histórico.

        Returns:
            Trechos relevantes encontrados, ou mensagem de que nada foi encontrado.
        """
        # Log the search parameters
        logger.info(f"[Tool rag_search] Query: {query[:100]}")
        logger.info(
            f"[Tool rag_search] Filtros: document_ids={document_ids or '(todos)'}, "
            f"filename={filename or '(todos)'}, "
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

            # Filter by explicit filename
            if filename and filename.strip():
                base_where_clauses.append("d.filename ILIKE :filename_filter")
                params["filename_filter"] = f"%{filename.strip()}%"
                logger.info(f"[Tool rag_search] Filtro por filename: {filename}")

            # Helper to execute query using Hybrid RRF
            async def execute_query(clauses, limit=10, use_threshold=True):
                where_sql = " AND ".join(clauses)
                
                # RRF Formula constants
                # For more strict or relaxed ranks, change k.
                k = 60
                
                # Build the robust Hybrid Query
                sql = sql_text(f"""
                    WITH vector_search AS (
                        SELECT
                            dc.id AS chunk_id,
                            dc.content,
                            dc.section_type,
                            dc.chunk_index,
                            dc.token_count,
                            d.filename,
                            d.id AS document_id,
                            (dc.embedding <=> :embedding) AS distance,
                            RANK() OVER (ORDER BY (dc.embedding <=> :embedding)) AS semantic_rank
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE {where_sql}
                        -- Only keep chunks inside the distance threshold (if enabled)
                        {"AND (dc.embedding <=> :embedding) < " + str(_MAX_DISTANCE) if use_threshold else ""}
                        ORDER BY distance
                        LIMIT {limit * 2} 
                    ),
                    keyword_search AS (
                        SELECT
                            dc.id AS chunk_id,
                            -- Assuming exact match query uses the same user input:
                            RANK() OVER (ORDER BY ts_rank_cd(dc.search_vector, websearch_to_tsquery('portuguese', :exact_query)) DESC) AS keyword_rank
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE {where_sql}
                        AND dc.search_vector @@ websearch_to_tsquery('portuguese', :exact_query)
                        ORDER BY keyword_rank
                        LIMIT {limit * 2}
                    )
                    SELECT
                        COALESCE(v.content, (SELECT content FROM document_chunks WHERE id = COALESCE(v.chunk_id, k.chunk_id))) AS content,
                        COALESCE(v.section_type, (SELECT section_type FROM document_chunks WHERE id = COALESCE(v.chunk_id, k.chunk_id))) AS section_type,
                        COALESCE(v.chunk_index, (SELECT chunk_index FROM document_chunks WHERE id = COALESCE(v.chunk_id, k.chunk_id))) AS chunk_index,
                        COALESCE(v.token_count, (SELECT token_count FROM document_chunks WHERE id = COALESCE(v.chunk_id, k.chunk_id))) AS token_count,
                        COALESCE(v.filename, (SELECT filename FROM documents WHERE id = COALESCE(v.document_id, (SELECT document_id FROM document_chunks WHERE id = k.chunk_id)))) AS filename,
                        COALESCE(v.document_id, (SELECT document_id FROM document_chunks WHERE id = k.chunk_id)) AS document_id,
                        COALESCE(v.distance, 1.0) AS distance,
                        COALESCE(v.semantic_rank, 1000) AS semantic_rank,
                        COALESCE(k.keyword_rank, 1000) AS keyword_rank,
                        -- Reciprocal Rank Fusion (RRF)
                        COALESCE(1.0 / ({k} + v.semantic_rank), 0.0) + 
                        COALESCE(1.0 / ({k} + k.keyword_rank), 0.0) AS rrf_score
                    FROM vector_search v
                    FULL OUTER JOIN keyword_search k ON v.chunk_id = k.chunk_id
                    ORDER BY rrf_score DESC
                    LIMIT {limit}
                """)
                # We need to add 'exact_query' to params just before execution
                exec_params = params.copy()
                exec_params["exact_query"] = query
                
                result = await db.execute(sql, exec_params)
                return result.fetchall()

            # 1. Try Strict Search (Threshold applied inside CTE)
            strict_clauses = base_where_clauses
            rows = await execute_query(strict_clauses, use_threshold=True)
            logger.info(f"[Tool rag_search] Encontrados {len(rows)} chunks (Busca Híbrida RRF)")

            # 2. Fallback: Relaxed Search (if filtered by ID or filename and no results)
            is_filtered = bool((document_ids and document_ids.strip()) or (filename and filename.strip()))
            if not rows and is_filtered:
                logger.info("[Tool rag_search] Fallback: Buscando sem threshold de similaridade nos documentos filtrados...")
                rows = await execute_query(base_where_clauses, limit=5, use_threshold=False)
                logger.info(f"[Tool rag_search] Encontrados {len(rows)} chunks no fallback (Busca Híbrida)")

            if not rows:
                filter_desc = ""
                if document_ids:
                    filter_desc += f" nos IDs {document_ids}"
                if filename:
                    filter_desc += f" (arquivo '{filename}')"
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
                
                unique_docs.add(f"{row.filename} (ID:{row.document_id})")
                
                chunks_text.append(
                    f"--- Trecho {i} (Documento: {row.filename} [ID:{row.document_id}], "
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
