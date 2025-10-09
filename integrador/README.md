# Integrador Zammad ↔ OpenProject ↔ Mattermost

Integrador es un microservicio construido con FastAPI que conecta eventos de tickets de Zammad con work packages de OpenProject y envía notificaciones a Mattermost.

## Árbol del proyecto

```
app/
  __init__.py
  config.py
  main.py
  models.py
  routers/
    slash.py
    webhook.py
  security.py
  services/
    mattermost.py
    openproject.py
Dockerfile
docker-compose.yml
.env.example
pyproject.toml
tests/
  conftest.py
  test_health.py
  test_slash.py
  test_webhook.py
```

## Configuración

1. Copia `.env.example` a `.env` y ajusta los valores requeridos (`OP_TOKEN`, `MM_WEBHOOK_URL`, `API_KEY`, etc.).
2. Instala dependencias locales:

```bash
cd integrador
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Ejecución local

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints principales:
- `POST /zammad/webhook` – recibe eventos de Zammad (requiere cabecera `X-API-Key`).
- `POST /slash/op` – slash commands desde Mattermost.
- `GET /health` – verificación de estado.
- `GET /metrics` – métricas Prometheus.

## Docker Compose

```bash
cd integrador
docker compose up --build -d
```

El servicio queda disponible en `http://localhost:8000`. El healthcheck integrado comprueba `/health` y el contenedor se reinicia automáticamente (`restart: unless-stopped`).

## Kubernetes (kustomize)

Manifiestos base y overlays se encuentran en `k8s/`. Para desplegar en desarrollo:

```bash
cd integrador/k8s
kustomize build overlays/dev | kubectl apply -f -
```

Para producción sustituye `dev` por `prod`. Los manifiestos incluyen Deployment (réplicas=2), Service, ConfigMap, Secret e Ingress opcional con TLS (cert-manager).

## Pruebas

```bash
cd integrador
pytest
```

## Seguridad y resiliencia

- Autenticación mediante API key en endpoints POST (`X-API-Key`).
- Validación estricta de payloads con Pydantic y sanitización básica de mensajes.
- Retries y timeouts configurables en clientes HTTP (OpenProject y Mattermost).
- Logs estructurados en JSON con correlation id (`corr_id`) y duración por petición.
- Configuración externalizada vía variables de entorno con soporte `_FILE` para secretos.
- Métricas Prometheus y middleware de correlación para observabilidad.

## Slash commands soportados

- `buscar <texto>` – consulta work packages en OpenProject.
- `crear <título> | <descripción>` – genera un nuevo work package.

Cada comando responde con un mensaje formateado compatible con Mattermost.
