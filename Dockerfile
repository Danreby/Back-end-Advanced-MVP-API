FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# dependências de sistema necessárias para compilar bibliotecas
RUN apt-get update && apt-get install -y build-essential libssl-dev libffi-dev default-libmysqlclient-dev gcc && rm -rf /var/lib/apt/lists/*

# copia requirements e instala dependências
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# copia o código
COPY . /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
