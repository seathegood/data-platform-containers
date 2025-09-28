# syntax=docker/dockerfile:1.6

ARG AIRFLOW_VERSION=2.9.1
ARG PYTHON_VERSION=3.10

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

ARG AIRFLOW_VERSION
ARG PYTHON_VERSION

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

ENV CONSTRAINTS_FILE="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
    AIRFLOW__CORE__LOAD_EXAMPLES=False \
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

