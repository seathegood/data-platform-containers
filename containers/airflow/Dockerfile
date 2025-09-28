# syntax=docker/dockerfile:1.6

ARG AIRFLOW_VERSION=2.9.1
ARG PYTHON_VERSION=3.10
ARG CONSTRAINTS_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

USER root
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

ENV CONSTRAINTS_FILE=${CONSTRAINTS_URL} \
    AIRFLOW__CORE__LOAD_EXAMPLES=False

RUN --mount=type=cache,target=/root/.cache/pip \
    if grep -qE "^[^#]" /opt/airflow/requirements.txt; then \
        python -m pip install --no-cache-dir --constraint "${CONSTRAINTS_FILE}" -r /opt/airflow/requirements.txt; \
    else \
        echo "No additional Python dependencies specified."; \
    fi

USER airflow

