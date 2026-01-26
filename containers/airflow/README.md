# Airflow Runtime

This image extends `apache/airflow` with pinned constraints, optional providers, and
the FAB webserver config used for remote-user authentication. By default Airflow’s
native username/password login is available; enable remote-user auth only when
running behind an ALB or similar proxy that asserts user identity. The image ships the
`airflow_ext.alb_fab_auth_manager.AlbFabAuthManager` module to bridge ALB OIDC headers
to Airflow 3 UI JWT cookies via `AIRFLOW__CORE__AUTH_MANAGER`.

## Local Compose
Use `docker-compose.airflow.local.yml` from the repo root to run a local stack that
mirrors production settings without remote dependencies (S3, ECS). It uses the local
image tag `airflow-runtime:local` and mounts only `dags`, `logs`, and `plugins` to
avoid masking `/opt/airflow/webserver_config.py`.

```bash
make build PACKAGE=airflow
docker tag ghcr.io/mrossco/data-platform-containers/airflow-runtime:latest airflow-runtime:local
docker compose -f docker-compose.airflow.local.yml up
```

The init step runs `airflow db reset -y` to ensure a clean local database each time.
Update `AIRFLOW__CORE__FERNET_KEY` and `AIRFLOW__API__SECRET_KEY` in the compose file
before longer-term use.

### ALB Header Proxy
The local compose stack includes an `alb-proxy` service that injects ALB-style OIDC
headers and forwards traffic to the webserver on port `8081`. Update
`containers/airflow/local/alb-proxy/nginx.conf` with your desired claims (or swap in a
token from your IdP) and set `AIRFLOW__API__BASE_URL` to `http://localhost:8081` for
clean redirects during local testing.

### Tests
Unit tests run with `make test PACKAGE=airflow`. Integration checks that exercise the
local compose stack are opt-in via `AIRFLOW_INTEGRATION=1 make test PACKAGE=airflow`.
If needed, override the auth manager prefix with `AUTH_MANAGER_PREFIX=/auth` when
running the integration test.
