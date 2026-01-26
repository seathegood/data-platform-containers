# syntax=docker/dockerfile:1.6

# Build arguments are sourced from containers/airflow/container.yaml
ARG BASE_IMAGE
ARG AIRFLOW_VERSION
ARG PYTHON_VERSION
ARG CONSTRAINTS_BASE

# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

ARG BASE_IMAGE
ARG AIRFLOW_VERSION
ARG PYTHON_VERSION
ARG CONSTRAINTS_BASE

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

USER root
# base image maintained upstream; OS packages pinned during release process
# hadolint ignore=DL3008
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends \ 
        build-essential \ 
        curl \ 
        git \ 
        libffi-dev \ 
        libpq5 \ 
        libpq-dev \ 
        libsasl2-dev \ 
        libssl-dev \ 
        locales \ 
        openssh-client \ 
        unixodbc \ 
        unixodbc-dev \ 
    && apt-get clean \ 
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/airflow/requirements.txt
COPY files/airflow_ext /opt/airflow/airflow_ext
COPY files/webserver_config.py /opt/airflow/webserver_config.py

ENV CONSTRAINTS_FILE="${CONSTRAINTS_BASE}/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
    AIRFLOW__CORE__LOAD_EXAMPLES=False \
    # Ensure the Airflow webserver loads the FAB config in this image.
    AIRFLOW__WEBSERVER__WEB_SERVER_CONFIG=/opt/airflow/webserver_config.py \
    # Keep custom auth manager importable via AIRFLOW__CORE__AUTH_MANAGER.
    PYTHONPATH=/opt/airflow:${PYTHONPATH} \
    PIP_DEFAULT_TIMEOUT=60

RUN --mount=type=cache,target=/root/.cache/pip \
    CONSTRAINTS_PATH=$(mktemp) && \
    curl -sSL --retry 5 --retry-delay 5 --fail "$CONSTRAINTS_FILE" -o "$CONSTRAINTS_PATH" && \
    if grep -qE "^[^#]" /opt/airflow/requirements.txt; then \
        python -m pip install --no-cache-dir --constraint "$CONSTRAINTS_PATH" -r /opt/airflow/requirements.txt; \
    else \
        echo "No additional Python dependencies specified."; \
    fi && \
    rm -f "$CONSTRAINTS_PATH"

USER airflow
