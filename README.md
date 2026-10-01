# RideOps

Projeto de Data Operations para dados sintéticos de corridas, com ETL em Python, PostgreSQL, análises SQL, alertas operacionais e dashboard no Looker Studio.

## Ambiente local

O banco roda em Docker. Não é necessário instalar PostgreSQL ou bibliotecas Python na máquina.

1. Copie `.env.example` para `.env` e troque `POSTGRES_PASSWORD` por uma senha somente local.
2. Garanta que sua conta tenha permissão de acessar o Docker.
3. Inicie o banco com `docker compose up -d`.
4. Verifique o status com `docker compose ps`.

Na primeira execução, o Docker baixa a imagem oficial `postgres:16-alpine`; depois ela fica em cache local.
