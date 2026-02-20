# Guia de Deploy Híbrido: Adicionando o Worker Assíncrono na Azure

Este guia foca especificamente em como pegar a arquitetura atual que você já tem rodando na Azure e adicionar o **novo container do Worker Assíncrono** que acabamos de criar.

Como o Worker reaproveita a mesma base de código do backend (`backend/`), o processo de deploy é simplificado.

---

## 1. Atualizando a Imagem no Azure Container Registry (ACR)

Toda a lógica nova do Worker e as rotas atualizadas do FastAPI estão na pasta `/backend`. Você precisará gerar uma nova imagem de backend e enviá-la para o seu registry atual:

```bash
# Exemplo se usando ACR
az acr login --name seu_acr_aqui

# Faça o build e push da imagem atualizada do backend
docker build -t seu_acr_aqui.azurecr.io/smartdocs-backend:latest ./backend
docker push seu_acr_aqui.azurecr.io/smartdocs-backend:latest
```

> **Nota:** O seu App Service do Backend/API principal provavelmente vai reiniciar e puxar essa imagem nova assim que o push terminar (se o webhook de Continuous Deployment estiver ativo). Se não, reinicie o container da API manualmente.

---

## 2. Rodando as Migrações do Banco de Dados

Antes de subir o Worker, a nova tabela `document_processing_jobs` precisa ser criada no seu PostgreSQL Fleixble Server atual da Azure.

Como a sua API principal do Backend atualizada já vai estar rodando, você pode usar ela para rodar o Alembic:
1. Vá até o App Service do seu Backend API.
2. No menu lateral, procure por **SSH** ou **Console**.
3. Execute o comando de migração:  
   `alembic upgrade head`
4. Isso criará a tabela de jobs na nuvem.

---

## 3. Criando o Recurso do Worker (App Service / Container Instances)

Para a nuvem da Azure, o Worker nada mais é do que *um clone do seu Backend*, mas executando um script diferente no momento da inicialização. Se você já usa App Service / Web App for Containers, faça o seguinte:

1. Vá no portal da Azure e clique em **Create a resource** -> **Web App**.
2. **Nome:** Exs: `smartdocs-worker-prod`
3. **Publish:** Escolha `Container`.
4. **Operating System:** Escolha `Linux`.
5. Prossiga para a aba **Container**:
   - Escolha o mesmo ACR.
   - Selecione a **mesma imagem** que você acabou de subir: `smartdocs-backend:latest`
6. Clique em **Review + create** e crie o recurso.

### 4. Configurando o Worker

Após o App Service do Worker ser criado:

1. Vá em **Configuration** (ou **Environment variables** na nova interface).
2. **Copie EXATAMENTE as mesmas variáveis** que já existem hoje no seu App Service da API principal:
   - `DATABASE_URL` (Sua string com o PostgreSQL do Azure)
   - Chaves da OpenAI, Document Intelligence, Storage, etc.
3. **O PULO DO GATO (Comando de Inicialização)**
   - Ainda na tela de Configuração, vá até "General Settings" ou na aba de configurações do Docker ("Startup Command").
   - Digite o comando que vai substituir a inicialização padrão da API (que é o `uvicorn`):
     ```bash
     python worker_main.py
     ```
   - *Se esse comando não for configurado, você acabará subindo dois servidores HTTP e o worker não vai rodar a fila.*
4. Salve e deixe o container reiniciar.

---

## 5. (Opcional) Dicas de Infraestrutura para o Worker

- **"Always On" (Pode falhar):** O App Service sempre tenta fazer um ping HTTP na porta 80 ou 8000 do container para checar a saúde. Como o nosso worker **não é um site** (é só um loop python infinito imprimindo logs), o App Service pode achar que o container "travou" por não responder HTTP e reiniciar ele a cada x minutos de propósito. Se isso acontecer, você pode resolver isso passando a variável de ambiente `WEBSITES_CONTAINER_START_TIME_LIMIT` com valor `1800` para atrasar limites, ou migrando a execução do script `python worker_main.py` para ferramentas nativas para containers de background da Azure:
    - Trabalhar o Worker rodando no **Azure Container Instances (ACI)** (Ideal para jobs como este).
    - Trabalhar o Worker rodando nativamente no **Azure Container Apps** na modalidade "Background Processing". 

### Validando o Sucesso
Vá até **Log Stream** no App Service do Worker. Se conectou no banco e ligou certo, você verá o log infinito:
`Worker started. Polling every 5 seconds...`

Sempre que subir um arquivo pela UI da Azure, verá os logs de extração ocorrendo magicamente nessa tela independente do Backend principal!
