"""
LangChain tools for the SmartDocs agent.

These tools are injected into the LangChain agent so it can decide
autonomously when to query the database vs. respond directly.
"""

from typing import Any

from langchain_core.tools import tool
from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine
from app.services.sql_guard import validate_sql, SQLGuardError


# Tables hidden from the agent for security
_HIDDEN_TABLES = {"users", "alembic_version"}


async def _fetch_db_schema() -> str:
    """Dynamically introspect the database and return schema description.

    Queries the actual DB so any migration/column change is picked up
    automatically.  Sensitive tables (users, alembic_version) are excluded.
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
    return f"""Gere uma query SELECT PostgreSQL para responder a pergunta do usuário.
{schema}

Regras:
1. Gere APENAS SELECT queries válidas para PostgreSQL
2. NUNCA use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
3. Use JOINs quando necessário para relacionar tabelas
4. Sempre inclua aliases descritivos para as colunas
5. Para datas, use funções PostgreSQL (NOW(), INTERVAL, etc.)
6. Retorne APENAS o SQL, sem explicações, sem markdown, sem blocos de código
7. Use aspas duplas para nomes de colunas com espaços ou caracteres especiais
8. Sempre inclua a tabela documents no FROM sem alias (use exatamente "documents")
9. Quando consultar outras tabelas, sempre relacione com documents
10. Para perguntas sobre contratos assinados, prefira buscar em document_fields usando chaves como "DATA DE ASSINATURA", "CONTRATO Nº", "RAZÃO SOCIAL", "CNPJ"
11. Quando a data estiver em texto DD/MM/AAAA, filtre usando to_date(valor, 'DD/MM/YYYY') = DATE 'YYYY-MM-DD'
12. Para consolidar dados de várias chaves do mesmo documento, use agregação com MAX(CASE WHEN ... THEN ... END) e GROUP BY documents.id
13. Nunca use SELECT *; selecione apenas colunas necessárias e use aliases amigáveis
14. Nunca aplique to_date em document_fields.field_value sem antes filtrar a chave do campo
"""


def make_database_query_tool(
    db: AsyncSession,
    user_id: int,
    is_admin: bool,
    llm: Any,
    schema: str,
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
