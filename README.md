# RideOps

Projeto de Data Operations para dados sintéticos de corridas, com ETL em Python, PostgreSQL, análises SQL, alertas operacionais e dashboard no Looker Studio.

## Ambiente local

O banco roda em Docker. Não é necessário instalar PostgreSQL ou bibliotecas Python na máquina.

1. Copie `.env.example` para `.env` e troque `POSTGRES_PASSWORD` por uma senha somente local.
2. Garanta que sua conta tenha permissão de acessar o Docker.
3. Inicie o banco com `docker compose up -d`.
4. Verifique o status com `docker compose ps`.

O serviço `etl` usa Python em seu próprio contêiner. Ele espera o banco estar saudável e só é iniciado quando for chamado explicitamente, por exemplo: `docker compose run --rm etl python --version`.

Na primeira execução, o Docker baixa as imagens oficiais `postgres:16-alpine` e `python:3.13-slim`, além dos pacotes Python definidos em `requirements.txt`. Depois tudo fica em cache local.

## Gerar dados sintéticos

O gerador cria corridas fictícias somente de São Paulo e grava o resultado em `data/raw/rides.csv`.

```bash
docker compose run --rm etl python src/generate_rides.py --rows 100000
```

Para gerar sempre o mesmo conjunto de dados, informe uma semente:

```bash
docker compose run --rm etl python src/generate_rides.py --rows 100000 --seed 42
```

## Carregar dados tratados no banco

Com a tabela `rides` criada e o tratamento executado, carregue o arquivo tratado com o comando abaixo. Cada execução substitui a carga anterior para que o banco represente exatamente o CSV atual.

```bash
docker compose run --rm etl python src/load_rides.py
```

## Tratar dados para análise

O tratamento valida o arquivo bruto e cria colunas analíticas, como data, hora, dia da semana, indicador de horário de pico e valor por quilômetro.

```bash
docker compose run --rm etl python src/transform_rides.py
```

O resultado é salvo em `data/processed/rides.csv` e é a entrada do carregador para o PostgreSQL.
