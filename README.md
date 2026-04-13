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
- sincronizacion inicial de documentos reales LFT y LSS desde PDF oficial
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
- `AUTO_SYNC_JURISPRUDENCE_ON_CONSULTATION`
- `AUTO_SYNC_JURISPRUDENCE_MAX_RESULTS`
- `AUTO_RUN_MIGRATIONS`
- `AUTO_RUN_COLLECTSTATIC`
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
docker compose exec backend python manage.py sync_official_legal_documents --sources lft lss
docker compose exec backend python manage.py sync_official_jurisprudence --prompt "despido embarazo trabajadora"
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
python manage.py sync_official_legal_documents --sources lft lss
python manage.py runserver
```

## Ingesta real inicial

Ya existe una primera version de ingesta real para leyes federales oficiales:

- `lft`: Ley Federal del Trabajo
- `lss`: Ley del Seguro Social

La sincronizacion descarga el PDF oficial de Camara de Diputados, extrae el texto, normaliza encabezados repetidos, guarda el documento completo y vuelve a fragmentarlo por articulos.

Comando:

```bash
cd backend
python manage.py sync_official_legal_documents --sources lft lss
```

Notas:

- este comando reemplaza el contenido demo de LFT/LSS por texto oficial real cuando la version coincide
- guarda metadatos de descarga en `metadata_json`
- el siguiente paso natural es ampliar la cobertura con mas jurisprudencia, DOF y automatizacion recurrente

## Ingesta real de jurisprudencia

Ya existe una primera version de ingesta real de jurisprudencia desde la API oficial del repositorio SCJN/Bicentenario.

Opciones disponibles:

1. desde una o varias queries juridicas concretas
2. desde un prompt libre del caso para que el sistema genere las queries jurisprudenciales automaticamente

Comandos:

```bash
cd backend
python manage.py sync_official_jurisprudence --query "riesgo de trabajo amputacion dedos mano indemnizacion"
python manage.py sync_official_jurisprudence --prompt "Despidieron a una mujer por estar embarazada" --max-results 8
python manage.py sync_official_jurisprudence --pack labor_pregnancy --max-results 8
```

La ingesta:

- consulta la API oficial del repositorio SCJN/Bicentenario
- recupera registros digitales, rubros y claves de tesis
- obtiene el detalle completo de cada tesis o usa el payload de busqueda como respaldo
- guarda la tesis como `LegalDocument`
- fragmenta e indexa el contenido para que entre al flujo RAG

Los documentos ingestados quedan marcados con:

- `metadata_json.source_kind = "scjn_repositorio_api"`

Packs predefinidos disponibles:

- `labor_pregnancy`
- `honorarios_subordinacion`
- `riesgo_trabajo`
- `dano_psicologico`
- `renuncia_forzada`
- `seguridad_social`

Para listarlos desde CLI:

```bash
python manage.py sync_official_jurisprudence --list-packs
```

Tambien puedes dispararlo por API usando el job de ingesta:

```json
{
  "jurisprudence_prompt": "Obligaciones patronales por accidente de trabajo con perdida de dedos de la mano",
  "jurisprudence_max_results": 8,
  "notes": "Investigacion jurisprudencial automatica"
}
```

## Investigacion jurisprudencial automatica en consultas

El sistema ya puede intentar sincronizar jurisprudencia real del SJF antes de responder una consulta.

Variables recomendadas:

- `ASYNC_CONSULTATIONS=true`
- `AUTO_SYNC_JURISPRUDENCE_ON_CONSULTATION=true`
- `AUTO_SYNC_JURISPRUDENCE_MAX_RESULTS=5`

Recomendacion operativa:

- activa esta opcion cuando ya tengas worker de Celery
- deja `ASYNC_CONSULTATIONS=true` para evitar timeouts en el request web
- el detalle de la consulta se actualiza automaticamente mientras el caso sigue en `queued` o `processing`

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

Para sincronizacion oficial por API usando el job de ingesta:

```json
{
  "official_source_slugs": ["lft", "lss"],
  "notes": "Sincronizacion oficial inicial"
}
```

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
- `AUTO_RUN_MIGRATIONS=true` para correr migraciones al arrancar el contenedor
- `AUTO_RUN_COLLECTSTATIC=true` para servir correctamente los estaticos del admin
- `BOOTSTRAP_LEGAL_DATA=true` solo si quieres sembrar datos demo al arrancar

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

## CHECKLIST_POST_DEPLOY_RENDER

Usa esta lista despues de cada deploy del backend en Render:

1. confirmar que el deploy termino en estado `Live`
2. abrir `https://<tu-backend>/api/health/` y validar respuesta `{"status":"ok","service":"consulta-juridica-backend"}`
3. revisar variables en Render:
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `SECRET_KEY`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `ASYNC_CONSULTATIONS=false` si no hay worker
- `ASYNC_ADMIN_JOBS=false` si no hay worker
4. abrir shell del servicio y correr:
```bash
cd /opt/render/project/src/backend
python manage.py migrate --noinput
```
5. si la base juridica aun no existe o quieres refrescar demo data, correr:
```bash
cd /opt/render/project/src/backend
python manage.py seed_demo_data
```
6. entrar al admin y validar que existan registros en:
- `Source`
- `LegalDocument`
- `DocumentFragment`
7. iniciar sesion desde el frontend
8. crear una consulta de prueba
9. confirmar que la consulta no quede en `queued`
10. confirmar que la consulta termine en `completed` o, si falla, que muestre un error explicito y no una respuesta vacia
11. abrir el detalle y validar:
- respuesta estructurada
- citas visibles
- fragmentos recuperados
- links a fuente oficial cuando existan
12. revisar logs de Render si algo no cuadra:
- logs del servicio web
- logs del worker, si existe


#  Deploy operativo de Consulta Jurídica

## Arquitectura actual

- **Frontend:** Render
- **Backend API (Django/DRF):** Northflank
- **Worker (Celery):** Northflank
- **Redis:** Northflank
- **PostgreSQL:** Neon

---

## URLs importantes

### Backend Northflank
- Base URL:
  - `https://http--consulta-juridica--g9k22bk2hqyc.code.run`
- Healthcheck:
  - `https://http--consulta-juridica--g9k22bk2hqyc.code.run/api/health/`

### Frontend Render
- La variable del frontend debe apuntar al backend de Northflank:

```env
VITE_API_BASE_URL=https://http--consulta-juridica--g9k22bk2hqyc.code.run/api
```

---

## Servicios en Northflank

### 1. Backend
- **Service name:** `consulta-juridica`
- Función:
  - expone la API Django/DRF
  - recibe requests del frontend
  - envía tareas a Celery cuando aplica

### 2. Worker
- **Service name:** `consulta-juridica-worker`
- Función:
  - procesa tareas asíncronas de Celery

### 3. Job de migraciones
- **Job name:** `consulta-juridica-job`
- CMD:

```bash
python manage.py migrate
```

### 4. Job de carga inicial de leyes reales
- **Job recomendado:** `consulta-juridica-sync-legal-docs`
- CMD:

```bash
python manage.py sync_official_legal_documents --sources lft lss
```

### 5. Job de carga inicial de jurisprudencia real
- **Job recomendado:** `consulta-juridica-sync-jurisprudence`
- CMD de ejemplo:

```bash
python manage.py sync_official_jurisprudence --prompt "despido embarazo trabajadora" --max-results 5
```

### 6. Redis
- **Addon name:** `consulta-juridica-redis`
- Función:
  - broker de Celery
  - result backend de Celery

---

## Variables importantes

### Frontend (Render)

```env
VITE_API_BASE_URL=https://http--consulta-juridica--g9k22bk2hqyc.code.run/api
```

### Backend / Worker (Northflank secret group)

Variables importantes del grupo `consulta-juridica-runtime`:

```env
DATABASE_URL=...
SECRET_KEY=...
REDIS_URL=...
CELERY_BROKER_URL=...
CELERY_RESULT_BACKEND=...
ASYNC_CONSULTATIONS=true
ASYNC_ADMIN_JOBS=true
AUTO_SYNC_JURISPRUDENCE_ON_CONSULTATION=true
AUTO_SYNC_JURISPRUDENCE_MAX_RESULTS=5
AUTO_RUN_COLLECTSTATIC=true
BOOTSTRAP_LEGAL_DATA=false
```

### CORS / hosts

Ejemplo útil:

```env
ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=https://consulta-juridica-frontend.onrender.com
CSRF_TRUSTED_ORIGINS=https://consulta-juridica-frontend.onrender.com,https://http--consulta-juridica--g9k22bk2hqyc.code.run
```

---

## CMDs configurados

### Backend
Usa el CMD por defecto del Dockerfile:

```bash
sh ./scripts/start-gunicorn.sh
```

### Worker
CMD override:

```bash
celery -A config worker --loglevel=info
```

### Job de migraciones
CMD override:

```bash
python manage.py migrate
```

### Job de carga legal inicial
CMD override:

```bash
python manage.py sync_official_legal_documents --sources lft lss
```

### Job de carga jurisprudencial inicial
CMD override de ejemplo:

```bash
python manage.py sync_official_jurisprudence --prompt "despido embarazo trabajadora" --max-results 5
```

---

## Docker

### Build config usada en Northflank

```text
Build context: /
Dockerfile location: /backend/Dockerfile
```

---

## Flujo rápido cuando cambias Secrets

Si cambias una variable en Northflank:

1. Ir a **Secrets**
2. Editar `consulta-juridica-runtime`
3. Guardar
4. Ir a **Services > consulta-juridica > Builds**
5. Dar **Rebuild**
6. Ir a **Services > consulta-juridica-worker > Builds**
7. Dar **Rebuild**
8. Esperar a que ambos estén en **Running**

---

## Cómo ver logs

### Backend
Ruta:

- `Services > consulta-juridica > View latest runtime logs`
- o `Deployments / Builds` y abrir logs del deployment actual

Buscar aquí:
- requests HTTP
- errores de API
- errores de login
- errores de CORS / auth

### Worker
Ruta:

- `Services > consulta-juridica-worker > View latest runtime logs`

Buscar aquí:
- arranque de Celery
- conexión a Redis
- tareas procesadas
- errores de tareas asíncronas

### Job de migraciones
Ruta:

- `Jobs > consulta-juridica-job > Runs > abrir run > Logs`

---

## Cómo hacer rebuild

### Backend
Ruta:

- `Services > consulta-juridica > Builds > Rebuild`

### Worker
Ruta:

- `Services > consulta-juridica-worker > Builds > Rebuild`

### Cuándo usar Rebuild
Úsalo cuando:
- cambiaste código
- cambiaste secrets y quieres asegurarte de que todo se reconstruya bien
- necesitas refrescar el contenedor completo

### Cuándo usar Deploy
Úsalo cuando quieres desplegar una build vieja ya existente.

---

## Cómo ejecutar migraciones manualmente

1. Ir a `Jobs > consulta-juridica-job`
2. Correr el job manualmente con el botón **Run**
3. Revisar:
   - `Runs > abrir run > Logs`

Salida esperada:

```text
No migrations to apply.
Process terminated with exit code 0
```

---

## Checklist rápida de operación

### Si el frontend no pega al backend correcto
1. Revisar en Render:

```env
VITE_API_BASE_URL=https://http--consulta-juridica--g9k22bk2hqyc.code.run/api
```

2. Redeploy frontend
3. Revisar en DevTools > Network que ya no apunte a `onrender.com`

### Si el worker no procesa consultas
1. Revisar secret:

```env
ASYNC_CONSULTATIONS=true
```

2. Rebuild backend
3. Rebuild worker
4. Enviar nueva consulta
5. Revisar logs del worker

### Si hay error de CORS
1. Revisar:

```env
CORS_ALLOWED_ORIGINS=https://consulta-juridica-frontend.onrender.com
```

2. Guardar
3. Rebuild backend

---

## Estado actual

Infraestructura validada:

- Backend responde healthcheck
- Worker Celery corriendo
- Redis conectado
- Migraciones OK
- Frontend apuntando a Northflank

---

## Nota práctica

Si algo no refleja cambios, la secuencia más útil es:

1. guardar cambios en secrets
2. rebuild backend
3. rebuild worker
4. probar desde frontend
5. revisar logs
