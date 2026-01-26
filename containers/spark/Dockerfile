# syntax=docker/dockerfile:1.6

ARG SPARK_VERSION=4.0.1
ARG HADOOP_VERSION=3.3.4
ARG ICEBERG_VERSION=1.6.0
ARG AWS_SDK_VERSION=2.25.50
ARG HADOOP_AWS_VERSION=3.3.4

FROM eclipse-temurin:17-jre-jammy

ARG SPARK_VERSION
ARG HADOOP_VERSION
ARG ICEBERG_VERSION
ARG AWS_SDK_VERSION
ARG HADOOP_AWS_VERSION

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    SPARK_HOME=/opt/spark \
    JAVA_HOME=/opt/java/openjdk \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/spark/bin:/opt/spark/sbin:$PATH

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        python3 \
        python3-pip \
        procps \
        tini \
        libgomp1 \
        libsnappy1v5 \
        libzstd1 \
        libjemalloc2 \
    && rm -rf /var/lib/apt/lists/*

# Download and install Apache Spark
RUN curl -fsSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION%%.*}.tgz" -o /tmp/spark.tgz \
    && mkdir -p /opt \
    && tar -xzf /tmp/spark.tgz -C /opt \
    && mv /opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION%%.*} "$SPARK_HOME" \
    && rm -f /tmp/spark.tgz

# Add Iceberg runtime and AWS dependencies
RUN mkdir -p "$SPARK_HOME/jars" \
    && curl -fsSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-4.0_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-4.0_2.12-${ICEBERG_VERSION}.jar" -o "$SPARK_HOME/jars/iceberg-spark-runtime-4.0_2.12-${ICEBERG_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar" -o "$SPARK_HOME/jars/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/${AWS_SDK_VERSION}/bundle-${AWS_SDK_VERSION}.jar" -o "$SPARK_HOME/jars/aws-sdk-bundle-${AWS_SDK_VERSION}.jar"

# Python dependencies commonly used in Spark jobs
COPY requirements.txt /tmp/requirements.txt
RUN if grep -qE "^[^#]" /tmp/requirements.txt; then \
        python3 -m pip install --no-cache-dir -r /tmp/requirements.txt; \
    fi \
    && python3 -m pip install --no-cache-dir \
        pyspark==${SPARK_VERSION} \
        pandas==2.1.4 \
        pyarrow==14.0.2 \
        fastparquet==2024.2.0 \
    && rm -f /tmp/requirements.txt \
    && mkdir -p /opt/conf

# Entry point and healthcheck scripts
COPY files/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY files/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

WORKDIR /opt/spark

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["--help"]
