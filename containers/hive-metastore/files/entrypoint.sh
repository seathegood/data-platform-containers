#!/bin/sh
set -euo pipefail

echo "Starting Hive Metastore container..."
rm -f /tmp/metastore-ready

# Set required defaults and paths
export HADOOP_HOME=${HADOOP_HOME:-/opt/hadoop}
export HADOOP_CONF_DIR=${HADOOP_CONF_DIR:-$HADOOP_HOME/conf}
export HADOOP_HDFS_HOME=${HADOOP_HDFS_HOME:-/opt/hadoop}
export HIVE_HOME=${HIVE_HOME:-/opt/hive}
export HIVE_CONF_DIR=${HIVE_CONF_DIR:-$HIVE_HOME/conf}
export PATH="$HADOOP_HOME/bin:$PATH"

# Validate required environment variables
: "${METASTORE_DB_USER:?Missing METASTORE_DB_USER}"
: "${METASTORE_DB_PASSWORD:?Missing METASTORE_DB_PASSWORD}"
: "${METASTORE_DB_HOST:?Missing METASTORE_DB_HOST}"
: "${METASTORE_DB:?Missing METASTORE_DB}"
: "${METASTORE_DB_PORT:?Missing METASTORE_DB_PORT}"
: "${METASTORE_PORT:?Missing METASTORE_PORT}"

# Compose JDBC connection string
: "${METASTORE_DB_URL:=jdbc:postgresql://${METASTORE_DB_HOST}:${METASTORE_DB_PORT}/${METASTORE_DB}}"

# Set hive schema version (fall back to baked-in default)
SCHEMA_VERSION="${SCHEMA_VERSION:-4.1.0}"

# Log config
echo "Hive Home:       $HIVE_HOME"
echo "Hive Config:     $HIVE_CONF_DIR"
echo "Metastore Port:  $METASTORE_PORT"
echo "Schema Version:  $SCHEMA_VERSION"
echo "JDBC URL:        $METASTORE_DB_URL"


echo "Listing Hive libraries:"
find "$HIVE_HOME/lib" -type f -name "*.jar" | sort

echo "Listing Hadoop libraries:"
find "$HADOOP_HOME" -type f -name "*.jar" | sort

echo "Listing Hadoop config files:"
find "$HADOOP_CONF_DIR" -type f | sort

echo "Listing Hadoop bin scripts:"
find "$HADOOP_HOME/bin" -type f | sort

# Ensure log directories exist
mkdir -p "$HIVE_HOME/logs" "$HIVE_HOME/tmp" "$HIVE_CONF_DIR"

# If no custom hive-site.xml is mounted, generate one
if [ ! -f "$HIVE_CONF_DIR/hive-site.xml" ]; then
  echo "Generating default hive-site.xml..."
  cat <<EOF > "$HIVE_CONF_DIR/hive-site.xml"
<configuration>
  <property>
    <name>javax.jdo.option.ConnectionURL</name>
    <value>${METASTORE_DB_URL}</value>
  </property>
  <property>
    <name>javax.jdo.option.ConnectionDriverName</name>
    <value>org.postgresql.Driver</value>
  </property>
  <property>
    <name>javax.jdo.option.ConnectionUserName</name>
    <value>${METASTORE_DB_USER}</value>
  </property>
  <property>
    <name>javax.jdo.option.ConnectionPassword</name>
    <value>${METASTORE_DB_PASSWORD}</value>
  </property>
  <property>
    <name>datanucleus.schema.autoCreateAll</name>
    <value>true</value>
  </property>
  <property>
    <name>hive.metastore.uris</name>
    <value>thrift://0.0.0.0:${METASTORE_PORT}</value>
  </property>
</configuration>
EOF
else
  echo "Using mounted hive-site.xml"
fi

# Wait for the Postgres DB to be ready
echo "Waiting for PostgreSQL at ${METASTORE_DB_HOST}:${METASTORE_DB_PORT}..."
timeout=60
elapsed=0
while ! nc -z "${METASTORE_DB_HOST}" "${METASTORE_DB_PORT}"; do
  echo "  ...still waiting (${elapsed}s elapsed)"
  sleep 5
  elapsed=$((elapsed + 5))
  if [ "$elapsed" -ge "$timeout" ]; then
    echo "Timed out waiting for PostgreSQL"
    exit 1
  fi
done

# Checking for existing Hive schema...
echo "Checking for existing Hive schema..."
if ! VERSION_ROW=$(PGPASSWORD="$METASTORE_DB_PASSWORD" psql -h "$METASTORE_DB_HOST" -U "$METASTORE_DB_USER" -d "$METASTORE_DB" -Atc 'SELECT "SCHEMA_VERSION" FROM "VERSION" WHERE "VER_ID" = 1;' 2>/dev/null); then
  echo "No schema detected. Running direct schema initialization SQL..."
  PGPASSWORD="$METASTORE_DB_PASSWORD" psql -h "$METASTORE_DB_HOST" -U "$METASTORE_DB_USER" -d "$METASTORE_DB" -f "$HIVE_HOME/scripts/metastore/upgrade/postgres/hive-schema-${SCHEMA_VERSION}.postgres.sql"
else
  echo "Detected schema version: $VERSION_ROW"
  if [ "$VERSION_ROW" != "$SCHEMA_VERSION" ]; then
    UPGRADE_SCRIPT="$HIVE_HOME/scripts/metastore/upgrade/postgres/upgrade-${VERSION_ROW}-to-${SCHEMA_VERSION}.postgres.sql"
    if [ -f "$UPGRADE_SCRIPT" ]; then
      echo "Running upgrade script: $UPGRADE_SCRIPT"
      PGPASSWORD="$METASTORE_DB_PASSWORD" psql -h "$METASTORE_DB_HOST" -U "$METASTORE_DB_USER" -d "$METASTORE_DB" -f "$UPGRADE_SCRIPT"
    else
      echo "ERROR: No upgrade script found for version $VERSION_ROW"
      exit 1
    fi
  else
    echo "Hive schema is up-to-date."
  fi
fi

#
# Generate minimal log4j.properties if not present
if [ ! -f "$HADOOP_CONF_DIR/log4j.properties" ]; then
  echo "Generating default log4j.properties..."
  cat <<EOF > "$HADOOP_CONF_DIR/log4j.properties"
log4j.rootLogger=INFO, console
log4j.appender.console=org.apache.log4j.ConsoleAppender
log4j.appender.console.layout=org.apache.log4j.PatternLayout
log4j.appender.console.layout.ConversionPattern=%d{ISO8601} %-5p %c: %m%n
EOF
fi

# Handle SIGTERM/SIGINT
cleanup() {
  echo "Received termination signal. Stopping Hive Metastore..."
  kill "$pid"
  wait "$pid"
  echo "Hive Metastore stopped."
  rm -f /tmp/metastore-ready
  exit 0
}
trap cleanup TERM INT

#
# Start Hive Metastore in background
echo "Launching Hive Metastore on port $METASTORE_PORT..."
"$HIVE_HOME/bin/hive" --service metastore &
pid=$!
touch /tmp/metastore-ready
wait "$pid"
