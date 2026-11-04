# Kubernetes demo secret provisioning

The Kubernetes demonstration manifests are **not ready for deployment** until unique runtime secrets are created. Never place real credentials in versioned YAML.

## One-time setup

1. Apply the namespace resources first:

   ```bash
   kubectl apply -f k8s/base/namespaces.yaml
   ```

2. Create a local, ignored directory for the credentials:

   ```bash
   umask 077
   mkdir -p k8s/secrets
   ```

3. Create these three **local-only** files with unique random values (generate passwords using a trustworthy secret manager or `openssl rand -hex 32`):

   `k8s/secrets/openproject.env`:

   ```dotenv
   POSTGRES_PASSWORD=REPLACE_WITH_UNIQUE_DB_PASSWORD
   DATABASE_URL=postgres://openproject:REPLACE_WITH_THE_SAME_DB_PASSWORD@openproject-postgres:5432/openproject
   SECRET_KEY_BASE=REPLACE_WITH_AN_INDEPENDENT_RANDOM_SECRET
   ```

   `k8s/secrets/mattermost.env`:

   ```dotenv
   POSTGRES_PASSWORD=REPLACE_WITH_UNIQUE_DB_PASSWORD
   MM_SQLSETTINGS_DATASOURCE=postgres://mm:REPLACE_WITH_THE_SAME_DB_PASSWORD@mm-postgres:5432/mattermost?sslmode=disable
   ```

   `k8s/secrets/zammad.env`:

   ```dotenv
   POSTGRES_PASSWORD=REPLACE_WITH_UNIQUE_DB_PASSWORD
   ```

   Keep each paired database password and connection string consistent. Use URL-safe passwords in connection strings (hex strings work) to avoid parsing issues.

4. Provision the secrets **without putting credentials on the command line**:

   ```bash
   kubectl -n openproject create secret generic openproject-credentials --from-env-file=k8s/secrets/openproject.env --dry-run=client -o yaml | kubectl apply -f -
   kubectl -n mattermost create secret generic mattermost-credentials --from-env-file=k8s/secrets/mattermost.env --dry-run=client -o yaml | kubectl apply -f -
   kubectl -n zammad create secret generic zammad-credentials --from-env-file=k8s/secrets/zammad.env --dry-run=client -o yaml | kubectl apply -f -
   ```

   Never paste the generated Secret YAML (its data values are merely base64 encoded) into a public issue, CI log, or repository.

5. Deploy the manifests only after all three secrets exist. Pod startup intentionally fails if a required secret is missing.

## Docker Compose demo

Create `docker/.env` from `docker/.env.example`, generate independent credentials, and replace *every* `REPLACE_WITH_...` marker, including `OP_SECRET_KEY_BASE`. An absent OpenProject secret key now blocks Compose configuration rather than falling back to a shared default.

## General precautions

This is a local demonstration, **not a production-ready deployment**. In production use TLS, controlled network exposure, supported image versions, verified access policy, encrypted secrets at rest, and regular credential rotation. See [SECURITY.md](../SECURITY.md).
