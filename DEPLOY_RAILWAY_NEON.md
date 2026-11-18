# Deploy Django Railway + Neon

1. Crie banco PostgreSQL no Neon e copie a connection string.
2. Envie o conteudo desta pasta (onde esta manage.py) para um repositorio no GitHub.
3. Na Railway, New Project > Deploy from GitHub Repo.
4. Configure Variables: DATABASE_URL (connection string Neon completa com sslmode=require), SECRET_KEY (chave aleatoria forte), DEBUG=False.
5. Settings > Deploy > Pre-Deploy Command: python manage.py migrate
6. Settings > Deploy > Custom Start Command (caso necessario): gunicorn loja.wsgi:application --bind 0.0.0.0:$PORT
7. Settings > Networking > Generate Domain.
8. Teste GET /api/produtos/ e POST /api/usuarios/cadastrar/.

Para static files (admin), configure Build Command de forma adequada ao buildpack ou rode collectstatic no build.

Este pacote corrige a codificacao UTF-16 do requirements.txt para UTF-8, sem alterar as dependencias.
