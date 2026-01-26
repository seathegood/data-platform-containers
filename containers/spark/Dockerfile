# syntax=docker/dockerfile:1.6

# Build arguments are provided via containers/spark/container.yaml
ARG BASE_IMAGE
ARG SPARK_VERSION
ARG HADOOP_VERSION
ARG HADOOP_AWS_VERSION
ARG AWS_SDK_BUNDLE_VERSION
ARG AWS_SDK_MODULES
ARG ICEBERG_VERSION
ARG ICEBERG_RUNTIME_FLAVOR
ARG EXTRA_JARS_URLS
ARG PANDAS_VERSION
ARG PYARROW_VERSION
ARG FASTPARQUET_VERSION
ARG GRPCIO_VERSION
ARG GRPCIO_STATUS_VERSION
ARG GOOGLEAPIS_COMMON_PROTOS_VERSION
ARG ZSTANDARD_VERSION
ARG JAXB_API_VERSION
ARG JAXB_IMPL_VERSION
ARG JAXB_CORE_VERSION
ARG ACTIVATION_VERSION
ARG SLF4J_API_VERSION
ARG OCI_SOURCE
ARG OCI_REVISION

# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS builder

ARG SPARK_VERSION
ARG HADOOP_VERSION
ARG HADOOP_AWS_VERSION
ARG AWS_SDK_BUNDLE_VERSION
ARG AWS_SDK_MODULES
ARG ICEBERG_VERSION
ARG ICEBERG_RUNTIME_FLAVOR
ARG EXTRA_JARS_URLS
ARG PANDAS_VERSION
ARG PYARROW_VERSION
ARG FASTPARQUET_VERSION
ARG GRPCIO_VERSION
ARG GRPCIO_STATUS_VERSION
ARG GOOGLEAPIS_COMMON_PROTOS_VERSION
ARG ZSTANDARD_VERSION
ARG JAXB_API_VERSION
ARG JAXB_IMPL_VERSION
ARG JAXB_CORE_VERSION
ARG ACTIVATION_VERSION
ARG SLF4J_API_VERSION

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

ENV SPARK_HOME=/opt/spark \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j.zip:${PYTHONPATH}

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Download and install Apache Spark
RUN curl -fsSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-without-hadoop.tgz" -o /tmp/spark.tgz \
    && mkdir -p /opt \
    && tar -xzf /tmp/spark.tgz -C /opt \
    && mv /opt/spark-${SPARK_VERSION}-bin-without-hadoop "$SPARK_HOME" \
    && ln -sf "$SPARK_HOME"/python/lib/py4j-*.zip "$SPARK_HOME"/python/lib/py4j.zip \
    && rm -rf \
        "$SPARK_HOME/examples" \
        "$SPARK_HOME/data" \
        "$SPARK_HOME/README.md" \
        "$SPARK_HOME/LICENSE" \
        "$SPARK_HOME/NOTICE" \
        "$SPARK_HOME/jars"/spark-examples* \
        "$SPARK_HOME/R" \
        "$SPARK_HOME/yarn" \
        "$SPARK_HOME/python/docs" \
        "$SPARK_HOME/python/test_support" \
        "$SPARK_HOME/python/test_coverage" \
        "$SPARK_HOME/jars/connect-repl" \
        "$SPARK_HOME/kubernetes/tests" \
        "$SPARK_HOME/kubernetes/dockerfiles" \
    && rm -f /tmp/spark.tgz

# Remove prebundled AWS/Hadoop jars so only the pinned versions remain.
RUN rm -f "$SPARK_HOME/jars"/hadoop-aws-*.jar \
    "$SPARK_HOME/jars"/aws-java-sdk-bundle-*.jar \
    "$SPARK_HOME/jars"/aws-java-sdk-*.jar \
    "$SPARK_HOME/jars"/bundle-*.jar

# Add Iceberg runtime
RUN mkdir -p "$SPARK_HOME/jars" \
    && curl -fsSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-${ICEBERG_RUNTIME_FLAVOR}/${ICEBERG_VERSION}/iceberg-spark-runtime-${ICEBERG_RUNTIME_FLAVOR}-${ICEBERG_VERSION}.jar" -o "$SPARK_HOME/jars/iceberg-spark-runtime-${ICEBERG_RUNTIME_FLAVOR}-${ICEBERG_VERSION}.jar"

# Ensure Hadoop client + AWS jars are present for s3a support (Spark "without Hadoop" build).
RUN if [[ "$HADOOP_AWS_VERSION" != "$HADOOP_VERSION" ]]; then \
        echo "HADOOP_AWS_VERSION must match HADOOP_VERSION (got ${HADOOP_AWS_VERSION} vs ${HADOOP_VERSION})" >&2; \
        exit 1; \
    fi
RUN if ! ls "$SPARK_HOME/jars"/hadoop-client-runtime-*.jar >/dev/null 2>&1; then \
        curl -fsSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client-runtime/${HADOOP_VERSION}/hadoop-client-runtime-${HADOOP_VERSION}.jar" -o "$SPARK_HOME/jars/hadoop-client-runtime-${HADOOP_VERSION}.jar"; \
    fi \
    && if ! ls "$SPARK_HOME/jars"/hadoop-client-api-*.jar >/dev/null 2>&1; then \
        curl -fsSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client-api/${HADOOP_VERSION}/hadoop-client-api-${HADOOP_VERSION}.jar" -o "$SPARK_HOME/jars/hadoop-client-api-${HADOOP_VERSION}.jar"; \
    fi \
    && if ! ls "$SPARK_HOME/jars"/hadoop-aws-*.jar >/dev/null 2>&1; then \
        curl -fsSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar" -o "$SPARK_HOME/jars/hadoop-aws-${HADOOP_AWS_VERSION}.jar"; \
    fi

# Add Spark's Hadoop cloud module for S3A committers.
RUN if ! find "$SPARK_HOME/jars" -maxdepth 1 -type f -name 'spark-hadoop-cloud_*.jar' -print -quit | grep -q .; then \
        core_jar="$(find "$SPARK_HOME/jars" -maxdepth 1 -type f -name 'spark-core_*.jar' -print -quit)"; \
        scala_suffix="$(basename "$core_jar")"; \
        scala_suffix="${scala_suffix#spark-core_}"; \
        scala_suffix="${scala_suffix%%-*}"; \
        if [[ -z "$scala_suffix" ]]; then \
          echo "spark-core jar not found for scala suffix detection" >&2; \
          exit 1; \
        fi; \
        jar_name="spark-hadoop-cloud_${scala_suffix}-${SPARK_VERSION}.jar"; \
        if ! curl -fsSL "https://repo1.maven.org/maven2/org/apache/spark/spark-hadoop-cloud_${scala_suffix}/${SPARK_VERSION}/${jar_name}" \
          -o "$SPARK_HOME/jars/${jar_name}"; then \
          tmp_tar="/tmp/spark-${SPARK_VERSION}-bin-hadoop3.tgz"; \
          curl -fsSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz" -o "$tmp_tar"; \
          tar -xzf "$tmp_tar" -C /tmp "spark-${SPARK_VERSION}-bin-hadoop3/jars/${jar_name}"; \
          mv "/tmp/spark-${SPARK_VERSION}-bin-hadoop3/jars/${jar_name}" "$SPARK_HOME/jars/${jar_name}"; \
          rm -rf "/tmp/spark-${SPARK_VERSION}-bin-hadoop3" "$tmp_tar"; \
        fi; \
    fi

# Add a minimal AWS SDK v2 module set (no bundle) for S3A support.
RUN python3 - <<'PY'
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from urllib.error import HTTPError

base = "https://repo1.maven.org/maven2"
version = os.environ["AWS_SDK_BUNDLE_VERSION"]
modules = [m.strip() for m in os.environ.get("AWS_SDK_MODULES", "").split(",") if m.strip()]
spark_jars = os.environ.get("SPARK_HOME", "/opt/spark") + "/jars"
need_transfer_from_bundle = False
need_jsoncore_from_bundle = False
need_json_from_bundle = False
need_jackson_from_bundle = False
need_slf4j_from_bundle = False

def fetch(url):
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.read()
    except HTTPError as err:
        if err.code == 404:
            return None
        raise

def localname(tag):
    return tag.split("}", 1)[-1]

def parse_props(root, props):
    props_elem = root.find("./{*}properties")
    if props_elem is None:
        return
    for child in list(props_elem):
        props[localname(child.tag)] = (child.text or "").strip()

def parse_deps(root):
    deps = []
    deps_elem = root.find("./{*}dependencies")
    if deps_elem is None:
        return deps
    for dep in deps_elem.findall("./{*}dependency"):
        entry = {}
        for child in list(dep):
            entry[localname(child.tag)] = (child.text or "").strip()
        deps.append(entry)
    return deps

def resolve_version(value, props):
    if not value:
        return None
    match = re.match(r"^\$\{([^}]+)\}$", value)
    if match:
        return props.get(match.group(1))
    return value

def pom_url(group_id, artifact_id, ver):
    return f"{base}/{group_id.replace('.', '/')}/{artifact_id}/{ver}/{artifact_id}-{ver}.pom"

def jar_url(group_id, artifact_id, ver):
    return f"{base}/{group_id.replace('.', '/')}/{artifact_id}/{ver}/{artifact_id}-{ver}.jar"

parent_data = fetch(pom_url("software.amazon.awssdk", "aws-sdk-java-pom", version))
if parent_data is None:
    raise RuntimeError("AWS SDK parent POM not found")
parent_root = ET.fromstring(parent_data)

bom_data = fetch(pom_url("software.amazon.awssdk", "bom-internal", version))
if bom_data is None:
    raise RuntimeError("AWS SDK bom-internal POM not found")
bom_root = ET.fromstring(bom_data)
props = {
    "awsjavasdk.version": version,
    "project.version": version,
    "project.parent.version": version,
}
parse_props(parent_root, props)
parse_props(bom_root, props)

bom_versions = {}
dep_mgmt = bom_root.find("./{*}dependencyManagement/{*}dependencies")
if dep_mgmt is not None:
    for dep in dep_mgmt.findall("./{*}dependency"):
        group_id = dep.findtext("./{*}groupId", "").strip()
        artifact_id = dep.findtext("./{*}artifactId", "").strip()
        ver = dep.findtext("./{*}version", "").strip()
        ver = resolve_version(ver, props)
        if group_id and artifact_id and ver:
            bom_versions[(group_id, artifact_id)] = ver

queue = []
for module in modules:
    queue.append(("software.amazon.awssdk", module, version))

seen = set()
download = []

while queue:
    group_id, artifact_id, ver = queue.pop()
    key = (group_id, artifact_id, ver)
    if key in seen:
        continue
    seen.add(key)

    if group_id == "org.slf4j" and artifact_id.startswith("slf4j-"):
        continue

    download.append((group_id, artifact_id, ver))
    pom_data = fetch(pom_url(group_id, artifact_id, ver))
    if pom_data is None and group_id == "software.amazon.awssdk":
        if artifact_id == "s3-transfer-manager":
            need_transfer_from_bundle = True
            continue
        if artifact_id == "protocols-json":
            need_json_from_bundle = True
            continue
        if artifact_id == "protocols-jsoncore":
            need_jsoncore_from_bundle = True
            continue
        if artifact_id == "thirdparty-jackson-core":
            need_jackson_from_bundle = True
            continue
        if artifact_id == "thirdparty-slf4j-api":
            need_slf4j_from_bundle = True
            continue
    if pom_data is None:
        raise RuntimeError(f"Missing POM for {group_id}:{artifact_id}:{ver}")
    root = ET.fromstring(pom_data)
    module_props = dict(props)
    parse_props(root, module_props)

    for dep in parse_deps(root):
        scope = dep.get("scope", "")
        optional = dep.get("optional", "false").lower() == "true"
        dep_type = dep.get("type", "")
        if scope in ("test", "provided") or optional:
            continue
        if dep_type and dep_type != "jar":
            continue
        dep_group = dep.get("groupId", "")
        dep_artifact = dep.get("artifactId", "")
        dep_ver = dep.get("version") or ""
        if not dep_group or not dep_artifact:
            continue
        if dep_group == "org.slf4j" and dep_artifact.startswith("slf4j-"):
            continue
        dep_ver = resolve_version(dep_ver, module_props)
        if dep_ver and dep_ver.startswith("${"):
            dep_ver = None
        if not dep_ver:
            dep_ver = bom_versions.get((dep_group, dep_artifact))
        if not dep_ver:
            continue
        queue.append((dep_group, dep_artifact, dep_ver))

os.makedirs(spark_jars, exist_ok=True)
for group_id, artifact_id, ver in sorted(set(download)):
    if group_id == "software.amazon.awssdk" and artifact_id == "protocols-json" and need_json_from_bundle:
        continue
    if group_id == "software.amazon.awssdk" and artifact_id == "protocols-jsoncore" and need_jsoncore_from_bundle:
        continue
    if group_id == "software.amazon.awssdk" and artifact_id == "thirdparty-jackson-core" and need_jackson_from_bundle:
        continue
    if group_id == "software.amazon.awssdk" and artifact_id == "thirdparty-slf4j-api" and need_slf4j_from_bundle:
        continue
    jar_path = os.path.join(spark_jars, f"{artifact_id}-{ver}.jar")
    if os.path.exists(jar_path):
        continue
    urllib.request.urlretrieve(jar_url(group_id, artifact_id, ver), jar_path)

if need_transfer_from_bundle:
    bundle_path = "/tmp/aws-sdk-bundle.jar"
    urllib.request.urlretrieve(jar_url("software.amazon.awssdk", "bundle", version), bundle_path)
    transfer_jar = os.path.join(spark_jars, f"s3-transfer-manager-{version}.jar")
    with zipfile.ZipFile(bundle_path) as src, zipfile.ZipFile(transfer_jar, "w") as dst:
        for name in src.namelist():
            if name.startswith("software/amazon/awssdk/transfer/"):
                dst.writestr(name, src.read(name))
            elif name.startswith("META-INF/services/"):
                data = src.read(name)
                if b"software.amazon.awssdk.transfer" in data:
                    dst.writestr(name, data)

if need_jsoncore_from_bundle:
    bundle_path = "/tmp/aws-sdk-bundle.jar"
    if not os.path.exists(bundle_path):
        urllib.request.urlretrieve(jar_url("software.amazon.awssdk", "bundle", version), bundle_path)
    jsoncore_jar = os.path.join(spark_jars, f"protocols-jsoncore-{version}.jar")
    with zipfile.ZipFile(bundle_path) as src, zipfile.ZipFile(jsoncore_jar, "w") as dst:
        for name in src.namelist():
            if name.startswith("software/amazon/awssdk/protocols/jsoncore/"):
                dst.writestr(name, src.read(name))
            elif name.startswith("META-INF/services/"):
                data = src.read(name)
                if b"protocols.jsoncore" in data:
                    dst.writestr(name, data)

if need_json_from_bundle:
    bundle_path = "/tmp/aws-sdk-bundle.jar"
    if not os.path.exists(bundle_path):
        urllib.request.urlretrieve(jar_url("software.amazon.awssdk", "bundle", version), bundle_path)
    json_jar = os.path.join(spark_jars, f"protocols-json-{version}.jar")
    with zipfile.ZipFile(bundle_path) as src, zipfile.ZipFile(json_jar, "w") as dst:
        for name in src.namelist():
            if name.startswith("software/amazon/awssdk/protocols/json/"):
                dst.writestr(name, src.read(name))
            elif name.startswith("META-INF/services/"):
                data = src.read(name)
                if b"protocols.json" in data:
                    dst.writestr(name, data)

if need_jackson_from_bundle:
    bundle_path = "/tmp/aws-sdk-bundle.jar"
    if not os.path.exists(bundle_path):
        urllib.request.urlretrieve(jar_url("software.amazon.awssdk", "bundle", version), bundle_path)
    jackson_jar = os.path.join(spark_jars, f"thirdparty-jackson-core-{version}.jar")
    with zipfile.ZipFile(bundle_path) as src, zipfile.ZipFile(jackson_jar, "w") as dst:
        for name in src.namelist():
            if name.startswith("software/amazon/awssdk/thirdparty/jackson/core/"):
                dst.writestr(name, src.read(name))
            elif name.startswith("META-INF/services/"):
                data = src.read(name)
                if b"jackson.core" in data:
                    dst.writestr(name, data)

if need_slf4j_from_bundle:
    bundle_path = "/tmp/aws-sdk-bundle.jar"
    if not os.path.exists(bundle_path):
        urllib.request.urlretrieve(jar_url("software.amazon.awssdk", "bundle", version), bundle_path)
    slf4j_jar = os.path.join(spark_jars, f"thirdparty-slf4j-api-{version}.jar")
    with zipfile.ZipFile(bundle_path) as src, zipfile.ZipFile(slf4j_jar, "w") as dst:
        for name in src.namelist():
            if name.startswith("software/amazon/awssdk/thirdparty/org/slf4j/"):
                dst.writestr(name, src.read(name))
            elif name.startswith("META-INF/services/"):
                data = src.read(name)
                if b"org.slf4j" in data:
                    dst.writestr(name, data)
PY

# Ensure SLF4J API matches Spark's Log4j2 binding (bundle removed).
# Prune unused Spark feature jars to reduce image size (keep Spark SQL/Core + Kubernetes).
# NOTE: If future workloads need MLlib/GraphX/Streaming/Spark Connect, these patterns must be revisited.
RUN curl -fsSL "https://repo1.maven.org/maven2/org/slf4j/slf4j-api/${SLF4J_API_VERSION}/slf4j-api-${SLF4J_API_VERSION}.jar" -o "$SPARK_HOME/jars/slf4j-api-${SLF4J_API_VERSION}.jar" \
  && rm -f \
      "$SPARK_HOME/jars"/spark-mllib_*.jar \
      "$SPARK_HOME/jars"/spark-mllib-local_*.jar \
      "$SPARK_HOME/jars"/spark-graphx_*.jar \
      "$SPARK_HOME/jars"/spark-streaming_*.jar \
      "$SPARK_HOME/jars"/spark-connect_*.jar \
      "$SPARK_HOME/jars"/spark-hive_*.jar \
      "$SPARK_HOME/jars"/spark-hive-thriftserver_*.jar \
      "$SPARK_HOME/jars"/spark-sql-kafka-*.jar \
      "$SPARK_HOME/jars"/spark-token-provider-kafka-*.jar \
      "$SPARK_HOME/jars"/kafka-*.jar \
      "$SPARK_HOME/jars"/scala-compiler-*.jar \
      "$SPARK_HOME/jars"/jline-*.jar \
      "$SPARK_HOME/jars"/hive-*.jar \
      "$SPARK_HOME/jars"/orc-*.jar \
      "$SPARK_HOME/jars"/hive-storage-api-*.jar \
      "$SPARK_HOME/jars"/rocksdbjni-*.jar \
      "$SPARK_HOME/jars"/breeze_*.jar \
      "$SPARK_HOME/jars"/breeze-*.jar \
      "$SPARK_HOME/jars"/spire_*.jar \
      "$SPARK_HOME/jars"/spire-*.jar \
      "$SPARK_HOME/jars"/cats-kernel_*.jar \
      "$SPARK_HOME/jars"/algebra_*.jar \
      "$SPARK_HOME/jars"/lapack-*.jar \
      "$SPARK_HOME/jars"/arpack_*.jar \
      "$SPARK_HOME/jars"/arpack-*.jar \
      "$SPARK_HOME/jars"/arpack_combined_all-*.jar \
      "$SPARK_HOME/jars"/JTransforms-*.jar \
      "$SPARK_HOME/jars"/commons-math3-*.jar \
      "$SPARK_HOME/jars"/datasketches-*.jar \
      "$SPARK_HOME/jars"/spark-repl_*.jar \
      "$SPARK_HOME/jars"/spark-shell_*.jar \
  && rm -f "$SPARK_HOME/jars"/netty-tcnative-boringssl-static-*-windows-*.jar \
           "$SPARK_HOME/jars"/netty-tcnative-boringssl-static-*-osx-*.jar \
  && arch="$(dpkg --print-architecture)" \
  && if [[ "$arch" == "amd64" ]]; then keep="linux-x86_64"; elif [[ "$arch" == "arm64" ]]; then keep="linux-aarch_64"; else keep=""; fi \
  && if [[ -n "$keep" ]]; then \
       find "$SPARK_HOME/jars" -maxdepth 1 -type f -name 'netty-tcnative-boringssl-static-*.jar' \
         ! -name "*-${keep}.jar" -print -delete; \
     fi

# Provide SLF4J binding for dependencies that still ship SLF4J 1.x.
RUN log4j_core_jar="$(find "$SPARK_HOME/jars" -maxdepth 1 -type f -name 'log4j-core-*.jar' -print -quit)" \
    && if [[ -z "$log4j_core_jar" ]]; then \
         echo "log4j-core jar not found in Spark distribution" >&2; \
         exit 1; \
       fi \
    && log4j_version="$(basename "$log4j_core_jar")" \
    && log4j_version="${log4j_version#log4j-core-}" \
    && log4j_version="${log4j_version%.jar}" \
    && if ! ls "$SPARK_HOME/jars"/log4j-slf4j-impl-*.jar >/dev/null 2>&1; then \
         curl -fsSL "https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-slf4j-impl/${log4j_version}/log4j-slf4j-impl-${log4j_version}.jar" \
           -o "$SPARK_HOME/jars/log4j-slf4j-impl-${log4j_version}.jar"; \
       fi

# JAXB jars for Java 17 compatibility in AWS SDK and XML utilities.
RUN curl -fsSL "https://repo1.maven.org/maven2/javax/xml/bind/jaxb-api/${JAXB_API_VERSION}/jaxb-api-${JAXB_API_VERSION}.jar" -o "$SPARK_HOME/jars/jaxb-api-${JAXB_API_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/com/sun/xml/bind/jaxb-impl/${JAXB_IMPL_VERSION}/jaxb-impl-${JAXB_IMPL_VERSION}.jar" -o "$SPARK_HOME/jars/jaxb-impl-${JAXB_IMPL_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/com/sun/xml/bind/jaxb-core/${JAXB_CORE_VERSION}/jaxb-core-${JAXB_CORE_VERSION}.jar" -o "$SPARK_HOME/jars/jaxb-core-${JAXB_CORE_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/javax/activation/javax.activation-api/${ACTIVATION_VERSION}/javax.activation-api-${ACTIVATION_VERSION}.jar" -o "$SPARK_HOME/jars/javax.activation-api-${ACTIVATION_VERSION}.jar"

# Optional extra jars (comma-separated URLs).
RUN if [[ -n "${EXTRA_JARS_URLS:-}" ]]; then \
        IFS=',' read -r -a extra_jars <<< "$EXTRA_JARS_URLS"; \
        for jar_url in "${extra_jars[@]}"; do \
          jar_name="$(basename "$jar_url")"; \
          curl -fsSL "$jar_url" -o "$SPARK_HOME/jars/$jar_name"; \
        done; \
    fi

# Python dependencies commonly used in Spark jobs
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir \
        -r /tmp/requirements.txt \
        pandas==${PANDAS_VERSION} \
        pyarrow==${PYARROW_VERSION} \
        fastparquet==${FASTPARQUET_VERSION} \
        grpcio==${GRPCIO_VERSION} \
        grpcio-status==${GRPCIO_STATUS_VERSION} \
        googleapis-common-protos==${GOOGLEAPIS_COMMON_PROTOS_VERSION} \
        zstandard==${ZSTANDARD_VERSION} \
    && rm -f /tmp/requirements.txt

# Trim test/dev-only files from heavyweight Python packages to reduce image size.
RUN rm -rf \
      /usr/local/lib/python3.12/site-packages/pandas/tests \
      /usr/local/lib/python3.12/site-packages/pyarrow/tests \
      /usr/local/lib/python3.12/site-packages/pyarrow/include \
  || true

# Trim pip and Python bytecode caches; runtime does not install packages dynamically.
RUN rm -rf \
      /usr/local/lib/python3.12/site-packages/pip \
      /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
      /usr/local/lib/python3.12/site-packages/pip/_vendor \
  || true \
  && find /usr/local/lib/python3.12/site-packages -type d -name '__pycache__' -prune -exec rm -rf {} + \
  && find /usr/local/lib/python3.12/site-packages -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# Optional pre-baked wheels (from containers/spark/files/wheels/).
COPY files/wheels/ /opt/wheels/
RUN if compgen -G "/opt/wheels/*.whl" > /dev/null; then \
        py_tag="$(python3 -c 'import sys; print(f"cp{sys.version_info.major}{sys.version_info.minor}")')"; \
        mismatch=(); \
        while IFS= read -r -d '' wheel; do \
          if [[ "$wheel" =~ cp3[0-9]+ ]] && [[ "$wheel" != *"$py_tag"* ]]; then \
            mismatch+=("$wheel"); \
          fi; \
        done < <(find /opt/wheels -maxdepth 1 -type f -name "*.whl" -print0); \
        if ((${#mismatch[@]})); then \
          echo "Wheel ABI mismatch for $py_tag: ${mismatch[*]}" >&2; \
          exit 1; \
        fi; \
        python3 -m pip install --no-cache-dir --no-index --find-links=/opt/wheels \
          boto3==1.42.27 \
          PyYAML==6.0.3; \
    fi \
    && rm -rf /opt/wheels

# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS runtime

ARG OCI_SOURCE
ARG OCI_REVISION

LABEL org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.revision="${OCI_REVISION}"

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    SPARK_HOME=/opt/spark \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j.zip:${PYTHONPATH} \
    PATH=/opt/spark/bin:/opt/spark/sbin:$PATH

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        openjdk-17-jre-headless \
        procps \
        tini \
        libgomp1 \
        libsnappy1v5 \
        libzstd1 \
        libjemalloc2 \
    && rm -rf /var/lib/apt/lists/*

RUN arch="$(dpkg --print-architecture)" \
    && ln -s "/usr/lib/jvm/java-17-openjdk-${arch}" /usr/lib/jvm/java-17-openjdk

COPY --from=builder /opt/spark/ /opt/spark/

# Note: We intentionally do not ship Hadoop native libraries in this image.
# Spark/Iceberg S3A works correctly without them; Hadoop will fall back to built-in Java classes.

COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
# Note: We intentionally do not copy /usr/local/bin from the builder.
# Python libraries are carried via site-packages; copying bin scripts can bloat the image and override base image tools.

# Bake sensible Spark defaults into the image for S3A support.
COPY files/spark-defaults.conf "$SPARK_HOME/conf/spark-defaults.conf"
COPY files/log4j2.properties "$SPARK_HOME/conf/log4j2.properties"

# Entry point and healthcheck scripts
COPY files/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY files/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh \
    && groupadd -g 10001 spark \
    && useradd -u 10001 -g 10001 -m -s /bin/bash spark \
    && mkdir -p /opt/workdir \
    && chown -R spark:spark /opt/workdir

USER spark
WORKDIR /opt/workdir

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD []
