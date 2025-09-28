# Stage 1: Builder - fetch and validate Hive, Hadoop, and JDBC
FROM eclipse-temurin:21-jdk-alpine AS builder

ARG HADOOP_VERSION=3.4.1
ARG HIVE_VERSION=4.1.0
ARG SCHEMA_VERSION=4.1.0
ARG PG_JDBC_VERSION=42.7.7
ARG SLF4J_VERSION=1.7.30

ENV HIVE_HOME=/opt/hive \
    HADOOP_HOME=/opt/hadoop

COPY versions.json /opt/versions.json

RUN apk update && apk add --no-cache \
    bash \
    wget \
    openssl \
    ca-certificates \
    jq

WORKDIR /build

# Download and verify Hive
RUN wget -q https://dlcdn.apache.org/hive/hive-${HIVE_VERSION}/apache-hive-${HIVE_VERSION}-bin.tar.gz && \
    wget -q https://dlcdn.apache.org/hive/hive-${HIVE_VERSION}/apache-hive-${HIVE_VERSION}-bin.tar.gz.sha256 && \
    sha256sum -c apache-hive-${HIVE_VERSION}-bin.tar.gz.sha256 && \
    tar -xzf apache-hive-${HIVE_VERSION}-bin.tar.gz

# Download and verify Hadoop
RUN wget -q https://dlcdn.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz && \
    wget -q https://dlcdn.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz.sha512 && \
    sha512sum -c hadoop-${HADOOP_VERSION}.tar.gz.sha512 && \
    tar -xzf hadoop-${HADOOP_VERSION}.tar.gz

# Download and verify JDBC driver
RUN PG_JDBC_SHA256=$(jq -r --arg ver "${PG_JDBC_VERSION}" '.postgresql[$ver].sha256' /opt/versions.json) && \
    wget -q https://jdbc.postgresql.org/download/postgresql-${PG_JDBC_VERSION}.jar -O postgresql-jdbc.jar && \
    echo "${PG_JDBC_SHA256}  postgresql-jdbc.jar" | sha256sum -c -

#Download missing SLF4J API Library 
RUN wget -q https://repo1.maven.org/maven2/org/slf4j/slf4j-api/${SLF4J_VERSION}/slf4j-api-${SLF4J_VERSION}.jar

# Stage 2: Runtime - minimal and secure image
FROM eclipse-temurin:21-jdk-alpine AS runtime

ARG HADOOP_VERSION=3.4.1
ARG HIVE_VERSION=4.1.0
ARG SCHEMA_VERSION=4.1.0
ARG PG_JDBC_VERSION=42.7.7
ARG SLF4J_VERSION=1.7.30

ARG BUILD_DATE
ARG TARGETARCH
ARG VCS_REF

ENV HIVE_VERSION=${HIVE_VERSION} \
    SCHEMA_VERSION=${SCHEMA_VERSION} \
    HIVE_EXECUTION_ENGINE=mr \
    HIVE_ROOT_LOGGER=INFO,console \
    HADOOP_HOME=/opt/hadoop \
    HADOOP_HDFS_HOME=/opt/hadoop \
    HADOOP_YARN_HOME=/opt/hadoop \
    HADOOP_COMMON_HOME=/opt/hadoop \
    HADOOP_MAPRED_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop \
    HADOOP_VERSION=${HADOOP_VERSION} \
    PG_JDBC_VERSION=${PG_JDBC_VERSION} \
    HIVE_HOME=/opt/hive \
    JAVA_TOOL_OPTIONS="-Djava.security.egd=file:/dev/urandom" \
    LOG4J_DISABLE_PACKAGE_SCAN=true \
    PATH="/opt/hive/bin:/opt/hadoop/bin:$PATH"

# OCI-compliant labels
LABEL org.opencontainers.image.vendor="Sea the Good, LLC" \
      org.opencontainers.image.url="https://github.com/seathegood/data-platform-containers" \
      org.opencontainers.image.title="Hive Metastore" \
      org.opencontainers.image.description="Minimal Hive Metastore image using an external PostgreSQL database" \
      org.opencontainers.image.documentation="https://github.com/seathegood/data-platform-containers/tree/main/containers/hive-metastore" \
      org.opencontainers.image.version=${HIVE_VERSION} \
      org.opencontainers.image.source="https://github.com/seathegood/data-platform-containers" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.created=${BUILD_DATE} \
      org.opencontainers.image.revision=${VCS_REF}

# Install Prerequisites
RUN apk update && apk add --no-cache \
    bash \
    netcat-openbsd \
    ca-certificates \
    postgresql-client

# Create non-root user and working directories
RUN addgroup -S hive && \
    adduser -S -G hive hive && \
    mkdir -p \
      $HIVE_HOME \
      $HIVE_HOME/conf \
      $HADOOP_HOME \
      $HIVE_HOME/logs \
      $HIVE_HOME/tmp \
      $HIVE_HOME/licenses

# Copy only required Hive Metastore JARs, minimal Hadoop libs, and configs from builder stage
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/guava-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/hive-common-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/hive-metastore-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/hive-cli-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/hive-exec-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/datanucleus-api-jdo-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/datanucleus-core-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/datanucleus-rdbms-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/log4j-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/slf4j-api-${SLF4J_VERSION}.jar $HIVE_HOME/lib/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/share/hadoop/common/lib/hadoop-shaded-guava-*.jar $HADOOP_HOME/lib/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/share/hadoop/common/lib/woodstox-core-*.jar $HADOOP_HOME/lib/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/share/hadoop/common/hadoop-common-*.jar $HADOOP_HOME/lib/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/share/hadoop/common/lib/commons-collections-*.jar $HADOOP_HOME/lib/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/share/hadoop/common/lib/commons-configuration2-*.jar $HADOOP_HOME/lib/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/share/hadoop/common/lib/hadoop-auth-*.jar $HADOOP_HOME/lib/
COPY --from=builder /build/postgresql-jdbc.jar $HIVE_HOME/lib/postgresql-jdbc.jar

# Copy license and notice files
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/LICENSE $HIVE_HOME/licenses/LICENSE-hive.txt
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/NOTICE $HIVE_HOME/licenses/NOTICE-hive.txt
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/LICENSE.txt $HIVE_HOME/licenses/LICENSE-hadoop.txt
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/NOTICE.txt $HIVE_HOME/licenses/NOTICE-hadoop.txt

# Apache HttpComponents for org.apache.http.config.Lookup
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/bin/ext/ $HIVE_HOME/bin/ext/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/bin/hive $HIVE_HOME/bin/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/bin/hive-config.sh $HIVE_HOME/bin/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/commons-cli-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/commons-dbcp2-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/commons-pool2-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/lib/caffeine-*.jar $HIVE_HOME/lib/
COPY --from=builder /build/apache-hive-${HIVE_VERSION}-bin/scripts/ $HIVE_HOME/scripts/

# Hadoop binaries and configs
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/bin/hadoop $HADOOP_HOME/bin/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/etc/hadoop/core-site.xml $HADOOP_HOME/etc/hadoop/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/libexec/ $HADOOP_HOME/libexec/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/share/hadoop/common/ $HADOOP_HOME/share/hadoop/common/
COPY --from=builder /build/hadoop-${HADOOP_VERSION}/share/hadoop/common/lib/ $HADOOP_HOME/share/hadoop/common/lib/

RUN rm -f $HADOOP_HOME/share/hadoop/common/lib/slf4j-reload4j-*.jar

# Secure permissions
RUN chown -R hive:hive $HIVE_HOME $HADOOP_HOME && \
    chmod -R go-rwx $HIVE_HOME $HADOOP_HOME

# Entry scripts and healthcheck
COPY --chmod=0755 --chown=hive:hive files/entrypoint.sh /usr/local/bin/entrypoint-${TARGETARCH}.sh
RUN mv /usr/local/bin/entrypoint-${TARGETARCH}.sh /usr/local/bin/entrypoint.sh && \
    sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

COPY --chmod=0755 --chown=hive:hive files/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN sed -i 's/\r$//' /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

WORKDIR $HIVE_HOME
USER hive

VOLUME ["/opt/hive/logs", "/opt/hive/tmp"]
EXPOSE 9083

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
  CMD /usr/local/bin/healthcheck.sh
