# Specification: Admin Audit Dashboard

## OVERVIEW
Um painel administrativo para visualizar o rastro de auditoria de quem modificou, criou ou excluiu os dados críticos do sistema SmartDocs. 

## ADDED Requirements

### Requirement: audit-dashboard-view
A interface de frontend deve possuir uma view exclusiva para administradores (`/admin/audit`) que renderiza as entradas da tabela de auditoria extraídas de um endpoint restrito.

### Requirement: audit-data-table
A tabela do dashboard deve possibilitar busca e pesquisa paginada (no mínimo).

### Requirement: audit-filters
Os filtros na API/UI devem suportar pesquisas rápidas por E-mail do usuário autor, Tipo de Ação (ex: UPDATE) e Entidade Afetada (ex: DOCUMENT).

### Requirement: audit-sorting
Deve ser possível ordenar temporalmente os logs (`created_at`) de forma ascendente ou descendente, ou, alternativamente, alfabeticamente pela coluna do Email do Usuário de acordo com a solicitação do usuário.

### Requirement: diff-viewer
Os registros de log contêm uma dupla de JSONs (`old_values` e `new_values`). A interface deve prever a capacidade de expandir ou detalhar um registro individual para visualizar o que foi modificado em si num formato razoavelmente "legível" (ex: "Antes: {title: 'Teste'} -> Depois: {title: 'App'}").

## SCENARIOS

### Scenario: Filtering by User Email
- **WHEN** o admin digita "joao@email.com" no campo de busca da DataTable no painel de Auditoria e clica em Filtrar.
- **THEN** a tabela recarrega batendo no endpoint apropriado passando o filtro e devolve apenas ações daquele e-mail mantendo a paginação correta.
