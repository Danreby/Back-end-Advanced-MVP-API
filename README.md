# Back-end Advanced — README

Guia rápido de **instalação e execução** do projeto.

---

## Requisitos

* Python 3.10+ instalado
* pip disponível
* Docker & Docker Compose
* (Opcional) MySQL client se quiser conectar ao banco localmente

---

## 1. Clonar o repositório

```bash
git clone <URL-DO-REPOSITORIO>
cd <PASTA-DO-PROJETO>
```

---

## 2. Criar e ativar o ambiente virtual

### Unix / macOS

```bash
python -m venv venv
source venv/bin/activate
```

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

---

## 3. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## 4. Subir serviços com Docker Compose

```bash
docker-compose up -d
```

Comandos úteis:

* Ver logs em tempo real:

```bash
docker-compose logs -f
```

* Parar e remover contêineres:

```bash
docker-compose down
```

---

## 5. Variáveis de ambiente

Se a aplicação usa um arquivo `.env`, crie um `.env` a partir do `.env.example` (se existir) e ajuste as variáveis (URI do banco, chaves, etc.). Por exemplo:

```
DATABASE_URL=mysql://root:senha@db:3306/nome_do_banco
SECRET_KEY=minha_chave_secreta
```

---

## 6. Rodar a API em modo desenvolvimento

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

* `--reload`: reinicia o servidor automaticamente ao detectar mudanças no código.
* Passe `--host 0.0.0.0` se quiser expor para outras máquinas da rede (útil ao rodar dentro de container).

---

## 7. Acessar a documentação / Swagger UI

* Se a sua aplicação serve a documentação na raiz, abra no navegador:

```
Swagger
http://localhost:8000

ReDoc
http://localhost:8000/redoc
```

---

## 8. API externa usada

A aplicação consome a API externa abaixo (documentação):

```
https://www.giantbomb.com/api/documentation/
```

---

## 9. Rodar o seeder (criar usuário padrão)

```bash
python -m app.seed_admin
```

Credenciais padrão geradas pelo seeder (conforme seu passo):

* **Login:** `admin@example.com`
* **Senha:** `admin123`

---

## 10. Acessar o banco de dados (dentro do container)

Exemplo de comando para acessar o MySQL rodando em um container Docker:

```bash
docker exec -it back-end-advanced-mvp-api-db-1 mysql -u root -p
```

Em seguida informe a senha do `root`.

---

## Comandos úteis (resumo)

```bash
# ativar venv (Unix)
source venv/bin/activate

# ativar venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# instalar dependências
pip install -r requirements.txt

# subir containers
docker-compose up -d

# rodar a API local
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# executar seeder de admin
python -m app.seed_admin

# entrar no MySQL do container
docker exec -it back-end-advanced-mvp-api-db-1 mysql -u root -p
```

