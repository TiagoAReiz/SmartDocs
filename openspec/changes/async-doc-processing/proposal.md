# Processamento Assíncrono de Documentos via Fila no PostgreSQL

## Problem Statement

Atualmente, o processamento de extração de dados de documentos PDF utilizando o Azure Document Intelligence ocorre de forma síncrona dentro da requisição HTTP do FastAPI. Isso causa três problemas graves:
1. **Timeouts:** Documentos grandes demoram muito para serem processados pela inteligência artificial, estourando o tempo limite da requisição HTTP.
2. **Travamento de Interface (Blocking UI):** O usuário fica esperando com a tela carregando sem garantia de resposta e sem chance de navegar para outras telas durante o processamento.
3. **Desperdício de Recursos e Gargalos:** Os *workers* do FastAPI ficam travados aguardando resposta de IO externo (Nuver Azure), reduzindo a capacidade do backend de lidar com o tráfego regular e a busca/chat do sistema.

Esta mudança visa modernizar a estabilidade do sistema ao transferir a comunicação com o Azure AI para *background workers* independentes usando as próprias tabelas do PostgreSQL moderno (`FOR UPDATE SKIP LOCKED`) como ecossistema de filas, mantendo as requisições HTTP locais incrivelmente rápidas.

## Capabilities
- `async-extraction`: Novo modelo de processamento em background independente para extração do Azure, suportado por tabela transacional de controle no BD e rotina worker apartada do Uvicorn.
- `status-polling`: Capacidade do Frontend (React/SWR) de consultar o estado pendente/em andamento ou finalizado de um processamento de documento através de rotas dedicadas no backend, informando o usuário em tempo real com feedbacks visuais sem prender conexões HTTP longas.

## Changed Capabilities
- `document-upload`: A rota atual de upload no backend passará de "Síncrona Extratorativa" para "Geradora de Mensagem enfileirada", retornando `200 OK` na hora com status provisório "Processando".

## Impact
- **Banco de Dados:** Criação de nova tabela/schema (ex: `document_processing_jobs`) para controle de estados concorrentes.
- **Backend (APIs):** O Endpoint de Upload atual será drasticizado para apenas salvar o binário e enfileirar a ação. Criação de novo script worker e rotas para GetStatus do processamento de PDF.
- **Frontend:** Implementação de lógicas de "polling" (SWR) sobre os status de documento e redesenho breve de transições de loading visual ao inserir documento na página de upload ou no data table.
- **Infra (Docker):** O container Docker Compose do Backend pode precisar subir o serviço main server do Uvicorn e o serviço do worker paralelamente.
