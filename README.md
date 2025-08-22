# gerar o venv
python -m venv venv
# Linux / mac
source venv/bin/activate
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# instalar as dependencias
pip install

# docker-compose.yml
docker-compose up -d

# rodar a api
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000