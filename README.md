# Integración Zammad ↔ OpenProject ↔ Mattermost (con Integrador FastAPI)

> **Security / credentials:** The demo requires unique runtime credentials. Never commit `docker/.env` or Kubernetes Secret values. See [SECURITY.md](SECURITY.md) and [Kubernetes secret setup](k8s/SECRETS.md). Do not deploy unchanged sample placeholders.


Este proyecto entrega **dos formas de despliegue** para ambiente local/laptop:
1) **Docker Compose** (rápido para pruebas).
2) **Kubernetes** (minikube/kind).

Incluye un microservicio **Integrador** (FastAPI) que:
- Expone `/zammad/webhook` para recibir eventos (simulables vía cURL) y crear/actualizar *Work Packages* en OpenProject.
- Publica notificaciones a Mattermost (Incoming Webhook).
- Ofrece `/slash/op` para comandos tipo *slash command* (búsqueda/alta básica).
- Jobs programables (en K8s como CronJobs) para `pull_openproject_updates` y `sla_reminders`.

> **Nota:** Las imágenes de Zammad, OpenProject y Mattermost descargarán recursos desde internet al primer arranque. Este stack es de **demostración local**; para producción, adaptar DNS, TLS, SSO (Keycloak/Azure AD), backups y seguridad.

---

## 0) Requisitos

- **Docker** y **docker compose** (v2).
- **kubectl** y **minikube** (o **kind**) si vas a usar Kubernetes.
- Puertos libres típicos: 8065 (Mattermost), 8080 (OpenProject), 8081 (Zammad-nginx), 8000 (Integrador).

---

## 1) Variables de entorno

Copia `.env.example` a `.env` y ajusta valores si lo necesitas:

```bash
cp docker/.env.example docker/.env
```

---

## 2) Despliegue con Docker Compose (local rápido)

```bash
cd docker
docker compose up -d
```

### URLs locales
- Mattermost: http://localhost:8065
- OpenProject: http://localhost:8080
- Zammad: http://localhost:8081
- Integrador (FastAPI docs): http://localhost:8000/docs

> Primer uso:
> - OpenProject: crea un **Personal Access Token (PAT)** y copia al `.env` (OP_TOKEN).
> - Mattermost: crea un **Incoming Webhook** en tu canal de pruebas y pon su URL en `.env` (MM_WEBHOOK_URL).
> - Zammad: para pruebas locales puedes **simular** un webhook con cURL al integrador (ver sección "Pruebas").

Para detener:
```bash
docker compose down
```

---

## 3) Despliegue en Kubernetes (minikube recomendado)

### 3.1 Levantar clúster y aplicar manifests
```bash
# Arranca minikube con suficiente RAM/CPU
minikube start --cpus=6 --memory=12288

# Crea namespaces y despliega base
kubectl apply -k k8s/base

# Despliega overlay dev (ajustable)
kubectl apply -k k8s/overlays/dev

# Espera a que todos los pods estén Running
kubectl get pods -A
```

### 3.2 Acceso a servicios (port-forward)
```bash
# OpenProject
kubectl -n openproject port-forward svc/openproject 8080:80

# Mattermost
kubectl -n mattermost port-forward svc/mattermost 8065:8065

# Zammad
kubectl -n zammad port-forward svc/zammad 8081:8080

# Integrador
kubectl -n integraciones port-forward svc/integrador 8000:8000
```

> Para Ingress y dominios locales, puedes habilitar el add-on de Ingress de minikube o usar kind + nginx-ingress. Este paquete usa **NodePort/port-forward** para simplificar pruebas.

---

## 4) Pruebas rápidas del Integrador

### 4.1 Estado/Docs
- http://localhost:8000/health
- http://localhost:8000/docs

### 4.2 Simular evento de Zammad (creación/actualización de ticket)
```bash
curl -X POST "http://localhost:8000/zammad/webhook"   -H "Content-Type: application/json"   -d '{
    "ticket": {
      "id": 3456,
      "title": "PTZ caída - CHH-PTZ-00987",
      "state": "open",
      "priority": "high",
      "owner": "luis.serrano",
      "due_at": "2025-08-20T15:00:00Z"
    }
  }'
```

El integrador intentará crear/actualizar el Work Package en OpenProject (requiere `OP_BASE_URL` y `OP_TOKEN` configurados).

### 4.3 Notificación a Mattermost
El integrador publicará en el Incoming Webhook configurado en `MM_WEBHOOK_URL` (si está definido).

### 4.4 Slash Command (demo)
Puedes simular el llamado:
```bash
curl -X POST "http://localhost:8000/slash/op"   -d 'token=test&text=buscar PTZ'
```

---

## 5) Estructura del repositorio

```
integrador/            # microservicio FastAPI
docker/                # docker-compose stack
k8s/
  base/                # namespaces, servicios base y deployments
  overlays/dev         # overlay dev (réplicas, env por defecto)
  overlays/prod        # overlay prod (ajustes de recursos)
scripts/               # utilidades varias
README.md
```

---

## 6) Notas y siguientes pasos hacia producción

- Cambiar a **TLS** detrás de Ingress (cert-manager).
- Integrar **SSO (OIDC/SAML)** en OP/Mattermost/Zammad.
- Consolidar **backups** (Postgres, adjuntos) y **observabilidad** (Prometheus/Grafana/Loki).
- Endurecer **NetworkPolicy**, **PodSecurity** y **Secrets** (External Secrets/Vault).

> Este paquete es un **esqueleto funcional** para pruebas y para dejar lista la estructura de integración. Ajusta campos personalizados de OpenProject, mapeos y el job de SLA según tu operación.
# centinela-integracion-op-mm-zammad
# centinela-integracion-op-mm-zammad
