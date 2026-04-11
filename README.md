# Consulta Jurídica Laboral MX - MVP

Aplicación full stack para investigación jurídica laboral mexicana con base RAG. El MVP recibe una consulta en lenguaje natural, clasifica la materia, recupera fragmentos jurídicos relevantes, genera una respuesta estructurada con citas visibles y guarda historial con trazabilidad documental.

## Estado actual

El proyecto ya incluye:

- Backend en Django + DRF con JWT, apps modulares, servicios y admin.
- Base de datos principal preparada para PostgreSQL + pgvector.
- Celery + Redis configurados para procesos asíncronos.
- Frontend en React + Vite con login, nueva consulta, historial y detalle.
- Docker Compose funcional con `frontend`, `backend`, `db`, `redis` y `worker`.
- Seed inicial con fuentes, documentos y usuarios demo.
- Flujo end-to-end validado con respuesta mock estructurada y citas.

## Alcance del MVP implementado

- Materias iniciales: laboral individual, seguridad social y riesgos de trabajo.
- Fuentes objetivo: LFT, LSS, SJF y DOF.
- Consulta libre con clasificación temática.
- Recuperación híbrida inicial:
  - componente lexical por traslape de términos
  - componente semántico mock con embeddings determinísticos
- Respuesta LLM desacoplada por proveedor.
- Trazabilidad de fragmentos y citas usadas.
- Historial de consultas por usuario.
- Jobs básicos de ingesta e indexación.

## Arquitectura implementada

### Backend

Ruta base: `backend/`

- `accounts`
  - usuario custom con roles `admin`, `researcher`, `user`
  - JWT login, refresh, `me`, registro básico
- `legal_sources`
  - catálogo de fuentes oficiales
- `legal_documents`
  - documentos jurídicos versionados
- `legal_indexing`
  - fragmentación, embeddings, temas, búsquedas y jobs de ingesta/indexación
- `consultations`
  - consultas, recuperaciones y flujo principal del MVP
- `llm_orchestrator`
  - clasificación, expansión de consulta y proveedor LLM mock
- `citations`
  - citas visibles asociadas a la respuesta
- `admin_panel`
  - endpoints para correr jobs y seed demo

### Frontend

Ruta base: `frontend/`

- React + Vite + React Router + Axios
- Auth con JWT y refresh automático
- Rutas protegidas
- Pantallas:
  - login
  - nueva consulta
  - historial
  - detalle de consulta

### Infra

- Docker Compose con:
  - `db`: `pgvector/pgvector:pg17`
  - `redis`: Redis 7
  - `backend`: Django dev server
  - `worker`: Celery worker
  - `frontend`: Vite dev server

## Modelos principales

- `Source`
- `LegalDocument`
- `DocumentFragment`
- `DocumentEmbedding`
- `LegalTopic`
- `FragmentTopic`
- `Consultation`
- `ConsultationRetrieval`
- `ConsultationCitation`
- `IngestionJob`

## Flujo principal actual

1. La persona usuaria inicia sesión.
2. Envía una consulta libre.
3. El backend guarda la consulta.
4. Se detecta materia y temas.
5. Se expanden términos de búsqueda.
6. Se recuperan fragmentos relevantes del índice.
7. Se guarda trazabilidad de recuperaciones.
8. Un proveedor LLM mock genera una respuesta estructurada.
9. Se guardan citas visibles y respuesta final.
10. El frontend muestra el resultado, los fragmentos y las citas.

## Búsqueda y RAG

La implementación actual deja preparada la arquitectura para crecimiento real:

- `DocumentEmbedding` usa `pgvector` cuando la dependencia está presente.
- En entornos sin `pgvector`, existe un fallback compatible para desarrollo local.
- La recuperación actual mezcla:
  - score lexical
  - score semántico mock vía similitud de embeddings determinísticos
- El proveedor LLM está desacoplado en `backend/apps/llm_orchestrator/services/providers.py`
- `OpenAIProvider` quedó marcado como `TODO` para integración real con credenciales por variable de entorno.

## Endpoints disponibles

### Auth

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`
- `POST /api/auth/register/`

### Consultas

- `POST /api/consultations/`
- `GET /api/consultations/`
- `GET /api/consultations/{id}/`

### Fuentes y documentos

- `GET /api/sources/`
- `GET /api/documents/`
- `GET /api/documents/{id}/`
- `GET /api/fragments/{id}/`

### Búsqueda

- `POST /api/search/legal/`
- `POST /api/search/jurisprudence/`

### Admin técnico

- `POST /api/admin/ingestion/run/`
- `POST /api/admin/indexing/run/`
- `GET /api/admin/jobs/`

### Salud

- `GET /api/health/`

## Usuarios demo

Se crean automáticamente con el seed:

- `admin / Admin12345!`
- `researcher / Research12345!`
- `demo / Demo12345!`

## Variables de entorno

Archivo principal: `.env`

Ejemplos:

- `.env.example`
- `backend/.env.example`
- `frontend/.env.example`

Puertos host configurados por defecto en este repo:

- Backend: `18000`
- Frontend: `15173`
- PostgreSQL: `15432`
- Redis: `16379`

## Cómo levantar el proyecto

### Opción recomendada: Docker Compose

```bash
docker compose up -d --build
```

Servicios esperados:

- Frontend: `http://localhost:15173`
- Backend API: `http://localhost:18000/api`
- Healthcheck: `http://localhost:18000/api/health/`

### Comandos útiles

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose exec backend python manage.py seed_demo_data
docker compose down
```

## Ejecución local sin Docker

### Backend

La ruta principal sigue siendo PostgreSQL + pgvector, pero para smoke tests locales rápidos puedes usar SQLite:

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

## Validaciones realizadas

Se validó en este trabajo:

- `python manage.py check`
- `python manage.py makemigrations`
- `python manage.py migrate`
- `python manage.py test apps.consultations`
- `npm install`
- `npm run build`
- `docker compose config`
- `docker compose build backend frontend worker`
- `docker compose up -d`
- login JWT contra backend dockerizado
- creación de consulta contra backend dockerizado con estado `completed` y `6` citas

## Estructura del repositorio

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
  .env
  .env.example
  README.md
```

## Notas de implementación

- El worker y el backend comparten código, pero el seed quedó centralizado para evitar duplicados al arrancar.
- El motor LLM real no está conectado todavía; el proveedor actual es mock pero la interfaz ya está desacoplada.
- La respuesta jurídica siempre exige citas. Si no hay evidencia suficiente, la consulta no debe publicarse como respuesta válida.
- El seed inicial contiene fragmentos de LFT, LSS y una tesis demo del SJF para probar el flujo completo.

## NEXT_STEPS

- Conectar un proveedor LLM real en `llm_orchestrator` con prompts auditables y validación de salida.
- Sustituir embeddings mock por embeddings reales y consultas vectoriales SQL nativas sobre `pgvector`.
- Incorporar parser jurídico más fino para artículos, fracciones, capítulos y tesis.
- Agregar soporte robusto a jurisprudencia y precedentes con metadatos oficiales completos.
- Añadir rate limiting, observabilidad y auditoría más profunda.
- Crear panel admin frontend para jobs, documentos y errores.
- Incorporar pruebas API y de UI más amplias.
- Preparar ingestión oficial automatizada desde fuentes mexicanas autorizadas.


## Nota para apps con búsqueda y fuentes citadas

Si este proyecto evoluciona hacia una app con recuperación documental, RAG o asistentes de consulta, conviene dejar claros estos conceptos en la UI:

### `score`

`score` es una puntuación de relevancia. Sirve para ordenar fragmentos o documentos recuperados según qué tan útiles parecen para una consulta.

Importante:

- no debe interpretarse como porcentaje de verdad o exactitud
- sirve sobre todo para comparar resultados entre sí
- un valor mayor normalmente implica mejor coincidencia para esa consulta específica

### `hybrid`

`hybrid` normalmente indica búsqueda híbrida. Esto significa que el motor combinó:

- búsqueda lexical por palabras clave
- búsqueda semántica o vectorial por significado

Este enfoque suele mejorar la recuperación cuando el usuario no escribe exactamente las mismas palabras que aparecen en la fuente.

### Fuentes citadas

Las fuentes citadas ayudan a que el usuario:

- valide de dónde salió una respuesta
- revise el contexto original
- profundice por su cuenta en el documento o fragmento citado

En una app orientada a usuario final, es recomendable mostrar:

- nombre de la fuente o documento
- fragmento recuperado
- score como señal técnica de relevancia
- tipo de búsqueda, por ejemplo `hybrid`
- link directo para profundizar cuando exista

### Referencias útiles

- Azure AI Search overview:
  https://learn.microsoft.com/azure/search/search-what-is-azure-search
- Hybrid search overview:
  https://learn.microsoft.com/azure/search/hybrid-search-overview
- Relevance scoring:
  https://learn.microsoft.com/azure/search/index-similarity-and-scoring
- Retrieval-Augmented Generation (RAG) overview:
  https://learn.microsoft.com/azure/search/retrieval-augmented-generation-overview

Esta aclaración es importante porque `score`, `hybrid` y las fuentes citadas son información sensible de producto: si se muestran sin contexto, el usuario puede malinterpretarlas; si se explican bien, también sirven como base para que otra persona construya su propia app sobre una arquitectura similar.

---

## Roadmap

Siguientes pasos planeados para el proyecto:

- conectar `detail_processor.py` con `UberTrip`
- implementar extracción de campos clave desde `raw_data`
- realizar upsert de viajes normalizados
- integrar lógica de métricas
- exponer resultados agregados por API
- construir frontend para visualización
- generar indicadores operativos y analíticos
- fortalecer validaciones y observabilidad del pipeline
- consolidar la app `integrations` para callbacks y pruebas futuras

---

## Enfoque de portafolio

`uber-dashboard` representa una aplicación backend orientada a procesamiento de datos reales con una arquitectura modular y escalable.

Este proyecto demuestra habilidades en:

- diseño de APIs con Django REST Framework
- modelado de datos en PostgreSQL
- ingestión y procesamiento de JSON
- trazabilidad de procesos backend
- separación entre datos crudos y datos normalizados
- organización por servicios y responsabilidades
- trabajo con Docker en entorno de desarrollo
- control de versiones con Git y GitHub
- preparación técnica de integraciones externas
- diseño de pipelines orientados a análisis posterior

---

## Estado del repositorio

Proyecto en desarrollo activo y ya versionado en GitHub.

La base funcional del pipeline ya está implementada y probada. El siguiente enfoque será la capa de normalización y métricas para convertir el procesamiento técnico en información útil para análisis y toma de decisiones.

---

## Autora

**Erna Tercero Rodríguez**

Proyecto desarrollado como parte de mi portafolio profesional en backend, data workflows, integración técnica y procesamiento de información.
