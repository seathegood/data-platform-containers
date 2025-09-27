#!/usr/bin/env bash
set -euo pipefail

COMMAND=${1:-run}
shift || true

HIVE_HOME="${HIVE_HOME:-/opt/hive-metastore}"
CONF_DIR="${HIVE_CONF_DIR:-${HIVE_HOME}/conf}"

render_config() {
  cat >"${CONF_DIR}/metastore-site.xml" <<XML
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
  <property>
    <name>javax.jdo.option.ConnectionURL</name>
    <value>jdbc:postgresql://${METASTORE_DB_HOST:?set METASTORE_DB_HOST}:${METASTORE_DB_PORT:-5432}/${METASTORE_DB_NAME:-metastore}</value>
  </property>
  <property>
    <name>javax.jdo.option.ConnectionDriverName</name>
    <value>org.postgresql.Driver</value>
  </property>
  <property>
    <name>javax.jdo.option.ConnectionUserName</name>
    <value>${METASTORE_DB_USER:-metastore}</value>
  </property>
  <property>
    <name>javax.jdo.option.ConnectionPassword</name>
    <value>${METASTORE_DB_PASS:?set METASTORE_DB_PASS}</value>
  </property>
</configuration>
XML
}

case "${COMMAND}" in
  run)
    render_config
    exec "${HIVE_HOME}/bin/start-metastore" "$@"
    ;;
  schema)
    render_config
    exec "${HIVE_HOME}/bin/schematool" -dbType postgres "$@"
    ;;
  *)
    exec "${COMMAND}" "$@"
    ;;
esac
