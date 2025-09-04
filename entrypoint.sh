#!/bin/sh
set -e

echo "⏳ Aguardando o MySQL em db:3306..."
until nc -z db 3306; do
  sleep 2
done

echo "✅ MySQL está pronto. Subindo a aplicação..."
exec "$@"
