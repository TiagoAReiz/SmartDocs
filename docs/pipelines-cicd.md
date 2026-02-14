# 🚀 CI/CD Pipelines — SmartDocs

Pipelines GitHub Actions para deploy automático do backend (Azure Container Apps) e frontend (Vercel).

---

## Visão Geral

```
GitHub Push (main)
    ├── Backend Pipeline
    │   ├── CI: lint → test → build Docker image
    │   └── CD: push ACR → deploy Container Apps
    │
    └── Frontend Pipeline
        ├── CI: lint → type-check → build
        └── CD: deploy Vercel (automático via integração)
```

---

## Repositório: Estrutura

```
smartdocs/               # monorepo ou dois repos separados
├── backend/             # FastAPI
├── frontend/            # Next.js
└── .github/
    └── workflows/
        ├── backend-ci.yml
        ├── backend-cd.yml
        ├── frontend-ci.yml
        └── frontend-cd.yml
```

---

## Backend — CI

**Arquivo:** `.github/workflows/backend-ci.yml`
**Trigger:** push e PR em `main` com mudanças em `backend/`

```yaml
name: Backend CI

on:
  push:
    branches: [main, develop]
    paths: ['backend/**']
  pull_request:
    branches: [main]
    paths: ['backend/**']

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:17-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: smartdocs_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install ruff

      - name: Lint (Ruff)
        run: |
          cd backend
          ruff check .
          ruff format --check .

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/smartdocs_test
          JWT_SECRET: test-secret-key-ci
        run: |
          cd backend
          python -m pytest tests/ -v --tb=short

  build-image:
    runs-on: ubuntu-latest
    needs: lint-and-test

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          cd backend
          docker build -t smartdocs-backend:test .

      - name: Verify image runs
        run: |
          docker run --rm smartdocs-backend:test python -c "import fastapi; print('OK')"
```

---

## Backend — CD

**Arquivo:** `.github/workflows/backend-cd.yml`
**Trigger:** push em `main` com mudanças em `backend/` (só após CI passar)

```yaml
name: Backend CD

on:
  push:
    branches: [main]
    paths: ['backend/**']

env:
  ACR_NAME: smartdocsacr          # Azure Container Registry
  IMAGE_NAME: smartdocs-backend
  RESOURCE_GROUP: rg-smartdocs
  CONTAINER_APP: smartdocs-api    # Azure Container App name

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Login no Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Login no ACR
        run: az acr login --name ${{ env.ACR_NAME }}

      - name: Build e Push imagem
        run: |
          cd backend
          IMAGE_TAG=${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}
          IMAGE_LATEST=${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:latest
          docker build -t $IMAGE_TAG -t $IMAGE_LATEST .
          docker push $IMAGE_TAG
          docker push $IMAGE_LATEST

      - name: Deploy no Container Apps
        run: |
          az containerapp update \
            --name ${{ env.CONTAINER_APP }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Verificar deploy
        run: |
          URL=$(az containerapp show \
            --name ${{ env.CONTAINER_APP }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query "properties.configuration.ingress.fqdn" -o tsv)
          echo "App URL: https://$URL"
          curl -f "https://$URL/docs" || echo "⚠️ Health check falhou"
```

---

## Frontend — CI

**Arquivo:** `.github/workflows/frontend-ci.yml`
**Trigger:** push e PR em `main` com mudanças em `frontend/`

```yaml
name: Frontend CI

on:
  push:
    branches: [main, develop]
    paths: ['frontend/**']
  pull_request:
    branches: [main]
    paths: ['frontend/**']

jobs:
  lint-and-build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Lint (ESLint)
        run: |
          cd frontend
          npm run lint

      - name: Type check
        run: |
          cd frontend
          npx tsc --noEmit

      - name: Build
        env:
          NEXT_PUBLIC_API_URL: https://api.smartdocs.example.com
        run: |
          cd frontend
          npm run build
```

---

## Frontend — CD

### Opção A: Vercel (Recomendado)

Vercel já tem integração nativa com GitHub — **não precisa de workflow**.

**Setup:**
1. Conectar repo no [vercel.com](https://vercel.com)
2. Configurar root directory: `frontend/`
3. Adicionar variável de ambiente: `NEXT_PUBLIC_API_URL`
4. Todo push em `main` faz deploy automático
5. PRs geram preview deploys

### Opção B: Azure Static Web Apps (via GitHub Actions)

**Arquivo:** `.github/workflows/frontend-cd.yml`

```yaml
name: Frontend CD (Azure)

on:
  push:
    branches: [main]
    paths: ['frontend/**']

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install e Build
        env:
          NEXT_PUBLIC_API_URL: ${{ secrets.API_URL }}
        run: |
          cd frontend
          npm ci
          npm run build

      - name: Deploy Azure Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_SWA_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "frontend"
          output_location: ".next"
```

---

## Secrets do GitHub (o que configurar)

### Backend
| Secret | Descrição |
|--------|-----------|
| `AZURE_CREDENTIALS` | JSON do Service Principal (`az ad sp create-for-rbac`) |

### Frontend (se usar Azure SWA)
| Secret | Descrição |
|--------|-----------|
| `AZURE_SWA_TOKEN` | Token do Azure Static Web Apps |
| `API_URL` | URL do backend (Container App) |

### Como gerar `AZURE_CREDENTIALS`

```bash
az ad sp create-for-rbac \
  --name "smartdocs-github-deploy" \
  --role contributor \
  --scopes /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/rg-smartdocs \
  --sdk-auth
```

Copiar o JSON gerado e colar como secret `AZURE_CREDENTIALS` no GitHub.

---

## Fluxo Completo

```
Developer faz push na main
    │
    ├── backend/ mudou?
    │   ├── CI: ruff lint → pytest → docker build ✅
    │   └── CD: push ACR → az containerapp update ✅
    │
    └── frontend/ mudou?
        ├── CI: eslint → tsc → next build ✅
        └── CD: Vercel auto-deploy ✅ (ou Azure SWA)
```

| Evento | CI | CD |
|--------|----|----|
| PR aberto | ✅ Roda testes | ❌ Não deploya |
| Push em `develop` | ✅ Roda testes | ❌ Não deploya |
| Push em `main` | ✅ Roda testes | ✅ Deploy produção |
