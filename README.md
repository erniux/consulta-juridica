# Consulta Juridica Laboral MX

Aplicacion full stack para consulta juridica laboral mexicana con arquitectura RAG. El MVP recibe una consulta en lenguaje natural, clasifica la materia, recupera fragmentos juridicos relevantes, genera una respuesta estructurada con citas visibles y guarda historial con trazabilidad documental.

## Stack

- Backend: Python, Django, Django REST Framework, PostgreSQL, pgvector, Celery, Redis, JWT
- Frontend: React, Vite, JavaScript, CSS
- Infra: Docker, Docker Compose

## Estado actual

El repositorio ya incluye:

- backend modular con `accounts`, `legal_sources`, `legal_documents`, `legal_indexing`, `consultations`, `llm_orchestrator`, `citations` y `admin_panel`
- autenticacion JWT
- flujo base de consultas con clasificacion, recuperacion, respuesta mock y citas
- historial y detalle de consultas
- seeds demo con fuentes, documentos y usuarios
- jobs de ingesta e indexacion
- Docker Compose para desarrollo local

## Estructura

```text
consulta-juridica/
  backend/
    apps/
      accounts/
      admin_panel/
      citations/
      consultations/
      legal_documents/
      legal_indexing/
      legal_sources/
      llm_orchestrator/
    common/
    config/
    requirements/
    scripts/
    manage.py
  frontend/
    src/
      components/
      hooks/
      layouts/
      pages/
      router/
      services/
      utils/
  docker/
    backend/
    frontend/
    postgres/
  docker-compose.yml
  .env.example
  README.md
```

## Variables de entorno

Archivo principal sugerido: `.env`

Variables backend relevantes:

- `SECRET_KEY`
- `DEBUG`
- `DJANGO_SETTINGS_MODULE`
- `DATABASE_URL`
- `REDIS_URL`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `LLM_PROVIDER`
- `OPENAI_API_KEY`
- `ASYNC_CONSULTATIONS`
- `ASYNC_ADMIN_JOBS`
- `BOOTSTRAP_LEGAL_DATA`

Variables frontend relevantes:

- `VITE_API_BASE_URL`

## Desarrollo local con Docker

```bash
docker compose up -d --build
```

Servicios esperados:

- Frontend: `http://localhost:15173`
- Backend API: `http://localhost:18000/api`
- Healthcheck: `http://localhost:18000/api/health/`

Comandos utiles:

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose exec backend python manage.py seed_demo_data
docker compose exec backend python manage.py test apps.accounts apps.consultations
docker compose down
```

## Desarrollo local sin Docker

### Backend

```bash
cd backend
set DB_ENGINE=sqlite
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Usuarios demo

Se crean con `seed_demo_data`:

- `admin / Admin12345!`
- `researcher / Research12345!`
- `demo / Demo12345!`

## Flujo principal

1. La persona usuaria inicia sesion.
2. Envia una consulta libre.
3. El backend guarda la consulta.
4. Se detecta materia y temas.
5. Se expanden terminos de busqueda.
6. Se recuperan fragmentos relevantes del indice.
7. Se guarda trazabilidad de recuperaciones.
8. El proveedor LLM mock genera una respuesta estructurada.
9. Se guardan citas visibles y respuesta final.
10. El frontend muestra resultado, citas y fragmentos.

## Endpoints principales

### Auth

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`
- `POST /api/auth/register/`

### Consultas

- `POST /api/consultations/`
- `GET /api/consultations/`
- `GET /api/consultations/{id}/`
- `DELETE /api/consultations/{id}/`

### Fuentes y documentos

- `GET /api/sources/`
- `GET /api/documents/`
- `GET /api/documents/{id}/`
- `GET /api/fragments/{id}/`

### Busqueda y jobs

- `POST /api/search/legal/`
- `POST /api/search/jurisprudence/`
- `POST /api/admin/ingestion/run/`
- `POST /api/admin/indexing/run/`
- `GET /api/admin/jobs/`

## Despliegue en Render + Neon

Si la app ya esta publicada pero las consultas salen vacias y en el admin ves `sources`, `documents` o `fragments` vacios, el problema no es Neon: la base juridica nunca fue cargada en produccion.

En local Docker esto si sucede porque `docker/backend/start-web.sh` ejecuta:

```bash
python manage.py migrate
python manage.py seed_demo_data
```

En Render normalmente el servicio web solo levanta `gunicorn`, asi que debes correr el bootstrap de datos al menos una vez sobre la base de Neon.

### Configuracion minima backend en Render

- Root Directory: `backend`
- Build Command:

```bash
pip install -r requirements/base.txt && python manage.py collectstatic --noinput
```

- Start Command:

```bash
sh ./scripts/start-gunicorn.sh
```

### Variables recomendadas backend

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `SECRET_KEY=<tu secreto real>`
- `DATABASE_URL=<conexion de Neon>`
- `REDIS_URL=<tu Redis>`
- `ALLOWED_HOSTS=<tu dominio backend de Render>`
- `CORS_ALLOWED_ORIGINS=<url del frontend>`
- `CSRF_TRUSTED_ORIGINS=<url del frontend y backend>`
- `LLM_PROVIDER=mock` para el MVP actual
- `ASYNC_CONSULTATIONS=false` si no desplegaste worker
- `ASYNC_ADMIN_JOBS=false` si no desplegaste worker

### Paso obligatorio despues del primer deploy

Abre el shell del servicio backend en Render y ejecuta:

```bash
cd /opt/render/project/src/backend
python manage.py migrate --noinput
python manage.py seed_demo_data
```

Con eso se poblaran:

- `Source`
- `LegalDocument`
- `DocumentFragment`
- `DocumentEmbedding`
- usuarios demo

### Opcion automatizada para bootstrap inicial

Si quieres automatizar el seed inicial en Render, puedes activar:

- `BOOTSTRAP_LEGAL_DATA=true`

y ejecutar una vez:

```bash
sh ./scripts/release.sh
```

Ese script corre migraciones y, si `BOOTSTRAP_LEGAL_DATA=true`, tambien ejecuta `seed_demo_data`.

Despues de tener datos cargados, puedes dejar `BOOTSTRAP_LEGAL_DATA=false` para no depender del seed en reinicios posteriores.

### Worker y Redis

Si vas a usar procesamiento asincrono real:

- despliega un worker aparte con Celery
- conecta `REDIS_URL`
- activa `ASYNC_CONSULTATIONS=true`
- activa `ASYNC_ADMIN_JOBS=true`

Si no tienes worker todavia, deja ambas variables en `false` para que el backend procese en el request y el MVP siga funcionando.

### Checklist de produccion

1. `python manage.py migrate --noinput`
2. `python manage.py seed_demo_data` o una ingesta real
3. verificar en admin que existan `Source`, `LegalDocument` y `DocumentFragment`
4. probar login
5. enviar una consulta
6. confirmar que la consulta termine en `completed`

## Que hace falta para una app realmente productiva

El seed demo sirve para validar el MVP, pero para una app productiva debes sustituirlo por una ingesta real y recurrente de fuentes juridicas oficiales:

- leyes vigentes
- reformas
- tesis y jurisprudencia
- metadatos oficiales
- reindexacion controlada

Tambien conviene agregar:

- proveedor LLM real
- observabilidad y alertas
- rate limiting
- auditoria
- monitoreo de jobs
- estrategia de versionado documental

## Validaciones realizadas en el MVP

Se validaron estos puntos durante la construccion:

- `python manage.py check`
- `python manage.py makemigrations`
- `python manage.py migrate`
- `python manage.py test apps.accounts apps.consultations`
- `npm install`
- `npm run build`
- `docker compose build backend frontend worker`
- `docker compose up -d`

## NEXT_STEPS

- conectar un proveedor LLM real en `llm_orchestrator`
- sustituir embeddings mock por embeddings reales sobre `pgvector`
- automatizar ingesta desde fuentes juridicas mexicanas autorizadas
- enriquecer parser juridico para articulos, fracciones, capitulos y tesis
- crear monitoreo y observabilidad de consultas y jobs
- agregar pruebas de API y UI mas amplias
