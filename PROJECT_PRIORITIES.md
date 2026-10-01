# RideOps — Prioridades do Projeto

Este arquivo preserva os critérios de conclusão e priorização definidos antes da implementação. Toda nova funcionalidade deve ser avaliada pela pergunta:

> Isso ajuda um recrutador de Data Operations a perceber rapidamente que sei trabalhar com dados, Python, SQL, automação, BI e IA?

Se a resposta for não, a funcionalidade não pertence ao MVP.

## Prioridades para o MVP

O projeto estará pronto para entrar no currículo quando possuir:

- repositório GitHub público, organizado e sem segredos;
- README com problema de negócio, arquitetura, decisões, resultados e instruções de execução;
- scripts Python executáveis para geração, ETL, carga, alertas e exportação de dados;
- PostgreSQL executável via Docker Compose;
- schema, consultas e views SQL versionados;
- dashboard compartilhável no Google Looker Studio;
- screenshots do dashboard no repositório;
- dicionário de dados;
- diagrama de arquitetura;
- alertas operacionais funcionais;
- histórico de commits pequenos e descritivos.

## Ordem de prioridade

1. Dados sintéticos e ETL em Python/Pandas.
2. PostgreSQL, modelagem e análises SQL.
3. Views e exportação para o dashboard.
4. Dashboard no Looker Studio.
5. Alertas por regras de negócio.
6. Integração opcional com Jev.
7. Documentação final, screenshots e revisão de Git.

## Limites do MVP

Não adicionar frontend próprio, API REST, Airflow, Kafka, Kubernetes, microsserviços ou machine learning complexo antes de o fluxo principal estar completo e demonstrável.
