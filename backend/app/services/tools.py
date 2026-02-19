"""
LangChain tools for the SmartDocs agent.

These tools are injected into the LangChain agent so it can decide
autonomously when to query the database vs. respond directly.
"""

from typing import Any, Callable, Optional

from langchain_core.tools import tool
from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine
from app.services.sql_guard import validate_sql, SQLGuardError


# Tables hidden from the agent for security
_HIDDEN_TABLES = {"users", "alembic_version", "chat_messages", "document_chunks"}


async def _fetch_db_schema() -> str:
    """Dynamically introspect the database and return schema description.

    Queries the actual DB so any migration/column change is picked up
    automatically.  Sensitive tables are excluded.
    """

    def _inspect_sync(connection):
        insp = inspect(connection)
        tables_info = []
        relationships = []

        for table_name in sorted(insp.get_table_names()):
            if table_name in _HIDDEN_TABLES:
                continue

            columns = insp.get_columns(table_name)
            col_names = [c["name"] for c in columns]
            tables_info.append(f"- {table_name} ({', '.join(col_names)})")

            # Detect foreign keys for relationships
            for fk in insp.get_foreign_keys(table_name):
                referred = fk["referred_table"]
                if referred in _HIDDEN_TABLES:
                    continue
                local_cols = ", ".join(fk["constrained_columns"])
                remote_cols = ", ".join(fk["referred_columns"])
                relationships.append(
                    f"- {table_name}.{local_cols} → {referred}.{remote_cols}"
                )

        schema = "Tabelas disponíveis:\n\n" + "\n".join(tables_info)
        if relationships:
            schema += "\n\nRelacionamentos:\n" + "\n".join(relationships)
        return schema

    async with engine.connect() as conn:
        return await conn.run_sync(_inspect_sync)


def _build_sql_prompt(schema: str) -> str:
    """Build the SQL generation prompt with the given schema."""
    return f"""Você é um gerador de SQL PostgreSQL para o sistema SmartDocs.
O sistema extrai dados de documentos via OCR e os armazena em múltiplas camadas.

{schema}

## Tipos de dado por tabela

### documents
- extracted_text: texto OCR completo do documento (pode conter parágrafos, cláusulas, qualquer conteúdo)
- status: 'uploaded', 'processing', 'processed', 'failed'
- type: tipo classificado (ex: 'contrato', 'relatorio')
- raw_json: metadados da extração (JSON)

### document_fields
- field_key: nome do campo extraído (ex: "CNPJ", "RAZÃO SOCIAL", "DATA DE ASSINATURA", "CONTRATO Nº")
- field_value: valor em texto do campo (pode conter datas em DD/MM/AAAA, valores monetários, nomes, etc.)
- confidence: confiança da extração (0.0 a 1.0)
- IMPORTANTE: os nomes dos campos (field_key) variam conforme o documento. Use ILIKE para busca flexível.

### document_tables
- headers: JSON array com nomes das colunas (ex: ["Item", "Quantidade", "Valor Unitário"])
- rows: JSON array de arrays com os dados (ex: [["Serviço A", "10", "R$ 500,00"]])
- Para consultar dentro do JSON, use: headers::text ILIKE '%termo%' ou rows::text ILIKE '%termo%'

### contracts
- contract_value: NUMERIC(15,2) — valor monetário
- start_date, end_date: DATE — datas em formato ISO
- status: texto livre (ex: "ativo", "encerrado")

### document_logs
- event_type: tipo do evento ('upload', 'extraction_complete', 'processing_failed', 'conversion_complete')
- message: descrição do evento

## Regras SQL

1. Gere APENAS queries SELECT válidas para PostgreSQL
2. NUNCA use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
3. Use JOINs quando necessário para relacionar tabelas
4. Sempre inclua aliases descritivos para as colunas
5. Para datas, use funções PostgreSQL (NOW(), INTERVAL, etc.)
6. Retorne APENAS o SQL, sem explicações, sem markdown, sem blocos de código
7. Sempre inclua a tabela documents no FROM quando precisar filtrar por documento
8. Para buscar texto livre em extracted_text, use: documents.extracted_text ILIKE '%termo%'
9. Para buscar campos por nome flexível: document_fields.field_key ILIKE '%nome_aproximado%'
10. Para consolidar múltiplos campos do MESMO documento:
    MAX(CASE WHEN df.field_key ILIKE '%chave%' THEN df.field_value END) AS alias
    com GROUP BY documents.id
11. Para filtrar por data em document_fields.field_value (formato DD/MM/AAAA):
    to_date(df.field_value, 'DD/MM/YYYY') — MAS SOMENTE após filtrar por field_key primeiro
12. Para buscar dentro de JSON em document_tables:
    dt.headers::text ILIKE '%termo%' ou dt.rows::text ILIKE '%termo%'
13. Nunca use SELECT *; selecione apenas colunas necessárias
14. Use LIMIT razoável (máx 100 linhas)
15. Para descobrir quais field_keys existem, use:
    SELECT DISTINCT field_key FROM document_fields ORDER BY field_key
16. Para contar documentos por tipo/status, agrupe por documents.type ou documents.status
"""


def make_database_query_tool(
    db: AsyncSession,
    user_id: int,
    is_admin: bool,
    llm: Any,
    schema: str,
    on_data_callback: Optional[Callable[[list[dict[str, Any]]], None]] = None,
) -> Any:
    """
    Factory that creates a database_query tool bound to the current
    request's db session, user_id, is_admin flag, LLM instance,
    and pre-fetched schema.
    """
    sql_prompt = _build_sql_prompt(schema)

    @tool
    async def database_query(question: str) -> str:
        """Consulta o banco de dados PostgreSQL baseado em uma pergunta em linguagem natural.
        Use esta ferramenta SEMPRE que o usuário perguntar sobre documentos, contratos,
        campos extraídos, tabelas, ou qualquer dado armazenado no sistema.
        NÃO use esta ferramenta para perguntas de saudação ou conversação geral."""

        logger.info(f"[Tool database_query] Gerando SQL para: {question[:100]}")

        # Step 1: Generate SQL using the LLM
        sql_response = await llm.ainvoke(
            [
                {"role": "system", "content": sql_prompt},
                {"role": "user", "content": question},
            ]
        )
        sql = sql_response.content.strip()

        # Clean up markdown code blocks if the model wraps the SQL
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(
                lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            )
            sql = sql.strip()

        logger.info(f"[Tool database_query] SQL gerado: {sql[:200]}")

        # Step 2: Validate SQL with guardrails
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                validated_sql = validate_sql(
                    sql, user_id=user_id, is_admin=is_admin
                )
                break
            except SQLGuardError as e:
                if attempt < max_retries:
                    logger.warning(
                        f"[Tool database_query] SQL inválido (tentativa {attempt + 1}): {e}"
                    )
                    fix_response = await llm.ainvoke(
                        [
                            {"role": "system", "content": sql_prompt},
                            {"role": "user", "content": question},
                            {"role": "assistant", "content": sql},
                            {
                                "role": "user",
                                "content": f"O SQL gerado é inválido: {e}. Corrija gerando apenas SELECT válido.",
                            },
                        ]
                    )
                    sql = fix_response.content.strip()
                    if sql.startswith("```"):
                        lines = sql.split("\n")
                        sql = "\n".join(
                            lines[1:-1]
                            if lines[-1].strip() == "```"
                            else lines[1:]
                        )
                        sql = sql.strip()
                else:
                    return f"Erro: não foi possível gerar SQL válido após {max_retries} tentativas. Detalhe: {e}"

        # Step 3: Execute query
        try:
            result = await db.execute(text(validated_sql))
            columns = list(result.keys())
            rows = result.fetchall()
            row_count = len(rows)
        except Exception as e:
            await db.rollback()
            logger.error(f"[Tool database_query] Erro ao executar SQL: {e}")
            return f"Erro ao executar a consulta no banco de dados: {e}"

        # Step 4: Format results
        if row_count == 0:
            return f"A consulta não retornou resultados.\nSQL usado: {validated_sql}"

        data = [dict(zip(columns, row)) for row in rows]
        results_text = "\n".join(
            [str(row) for row in data[:20]]
        )
        if row_count > 20:
            results_text += f"\n... e mais {row_count - 20} linhas"

        # Capture raw data via callback if provided
        if on_data_callback:
            logger.info(f"[Tool database_query] Executando callback com {len(data)} linhas")
            try:
                on_data_callback(data)
            except Exception as e:
                logger.error(f"[Tool database_query] Erro ao executar callback de dados: {e}")

        return (
            f"Resultados ({row_count} linhas):\n{results_text}\n"
            f"SQL usado: {validated_sql}"
        )

    return database_query


def make_get_schema_tool(schema: str) -> Any:
    """Factory that creates a get_database_schema tool with pre-fetched schema."""

    @tool
    def get_database_schema() -> str:
        """Retorna o esquema do banco de dados com as tabelas e colunas disponíveis.
        Use esta ferramenta quando precisar entender a estrutura do banco antes de fazer consultas."""
        return schema

    return get_database_schema
