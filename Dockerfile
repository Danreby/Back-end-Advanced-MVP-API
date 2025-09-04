FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# dependências de sistema necessárias (mysqlclient etc) + netcat caso precise
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    default-libmysqlclient-dev \
    gcc \
    netcat \
  && rm -rf /var/lib/apt/lists/*

# copia requirements e instala dependências
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# copia o código
COPY . /app

# copia entrypoint e dá permissão
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# entrypoint faz o wait-for-db e depois inicia o CMD
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
