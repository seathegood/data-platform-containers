# Spark Runtime

This image is a pure Spark runtime intended to be used as a base image by `data-platform-jobs`.
The entrypoint runs `spark-submit` directly and does not clone or install job code.

## Basic usage
Run a simple version check:

```bash
docker run --rm ghcr.io/mrossco/data-platform-containers/spark-runtime:4.0.1 --version
```

Run a Spark application (mount or bake your app into the image):

```bash
docker run --rm \
  -v "$PWD/app:/opt/app" \
  -w /opt/app \
  ghcr.io/mrossco/data-platform-containers/spark-runtime:4.0.1 \
  spark-submit /opt/app/main.py
```

The `data-platform-jobs` image should extend this runtime and bake the job code in.

## Local smoke test (MinIO)
Build the local image and run the S3A smoke test with MinIO:

```bash
make build PACKAGE=spark
docker compose -f docker-compose.spark.local.yml up --exit-code-from spark-smoke
```

The compose smoke run exercises:
- AWS SDK class availability and credentials provider resolution.
- S3A multi-partition writes (rename/copy path).
- Iceberg table create/alter/insert/read + snapshot expiration.
It writes data under `s3a://spark-test` and cleans up the compose stack afterward.

`make test PACKAGE=spark` runs the compose smoke test, so Docker and Docker Compose must be available.

## AWS SDK v2 modularization
The runtime uses a curated set of AWS SDK v2 modules (no `bundle` jar) to keep the image size smaller.
`AWS_SDK_MODULES` in `containers/spark/container.yaml` is the source of truth. If downstream workloads
hit `ClassNotFoundException` errors, add the missing module to that list and rebuild.

Some artifacts are not published for every AWS SDK version. For those, the build extracts just the
required classes from the AWS SDK `bundle` jar into a slim jar (see the Dockerfile's AWS SDK step).
If a new missing artifact appears, extend the extraction logic rather than reintroducing the full bundle.

## Catalog strategy (Glue vs. Hive Metastore)
This project defaults to open standards and uses AWS Glue only when it provides clear operational value.
If you need to remove Glue and revert to a Hive Metastore (HMS) backed catalog, use the steps below.

Remove AWS Glue:
- Remove `glue` from `AWS_SDK_MODULES` in `containers/spark/container.yaml`.
- Remove Glue-specific catalog configs in downstream jobs (for example, `spark.sql.catalog.glue_catalog`).
- Rebuild the image (`make build PACKAGE=spark`) and rerun the compose smoke tests.

Add Apache Hive Metastore:
- Add the Hive Metastore client jars to the image (either re-enable Hive jars in the Dockerfile pruning
  list or add them via `EXTRA_JARS_URLS`).
- Configure the catalog to use HMS:

```text
--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
--conf spark.sql.catalog.hive=org.apache.iceberg.spark.SparkCatalog
--conf spark.sql.catalog.hive.type=hive
--conf spark.sql.catalog.hive.uri=thrift://<hms-host>:9083
--conf spark.sql.catalog.hive.warehouse=s3a://<warehouse-bucket>/iceberg
```

If you reintroduce Hive jars, verify the smoke tests still pass and consider adding an HMS-specific
integration test in the downstream environment where the metastore is available.

## Pre-baked dependencies
Add shared wheels to `containers/spark/files/wheels/` to bake them into the image.
Base Python dependencies should live in `containers/spark/requirements.txt`.
Wheels must match the base Python minor version (e.g., `cp310` for Python 3.10).
Include platform-specific wheels (e.g., `manylinux2014_x86_64` and `manylinux2014_aarch64`) if you need multi-arch builds.
No wheels are baked by default. If you add wheels, ensure they match the base
Python minor version (currently 3.12).
The image also pins pandas/pyarrow and Spark Connect client dependencies to
match Spark requirements.
Downstream images should install extra Python dependencies at build time or
use a virtual environment, since the runtime user does not have write access
to system site-packages.
The Python packaging toolchain comes from the base image unless a newer
version is explicitly required.
Spark example artifacts are removed at build time to keep the image size
lean; downstream images should add their own sample data if needed.
The image creates a stable `py4j.zip` symlink in `/opt/spark/python/lib` so
`PYTHONPATH` works without relying on glob expansion.

## Build-time extras
Set `EXTRA_JARS_URLS` (comma-separated URLs) in `containers/spark/container.yaml` to bake additional jars into `$SPARK_HOME/jars`.
TODO: Add checksum verification (e.g., `EXTRA_JARS_SHA256S`) once the internal artifact repository is available.

## Iceberg placeholder
Iceberg jars are bundled. To enable later, pass Spark configs like:

```text
--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
--conf spark.sql.catalog.spark_catalog=org.apache.iceberg.spark.SparkSessionCatalog
--conf spark.sql.catalog.spark_catalog.type=hadoop
```

## S3A support
The image bakes Spark defaults into `$SPARK_HOME/conf/spark-defaults.conf` with
`spark.hadoop.fs.s3a.impl`, `spark.hadoop.fs.AbstractFileSystem.s3a.impl`, and
`spark.hadoop.fs.s3a.aws.credentials.provider` (AWS SDK v2). ECS IAM roles work
without static credentials. If you need MinIO or another S3-compatible endpoint,
set the following Spark configs:

```text
--conf spark.hadoop.fs.s3a.endpoint=http://minio:9000
--conf spark.hadoop.fs.s3a.path.style.access=true
--conf spark.hadoop.fs.s3a.connection.ssl.enabled=false
```

The runtime also includes Spark's `spark-hadoop-cloud` module so S3A committers
like the directory committer can use `org.apache.spark.internal.io.cloud.PathOutputCommitProtocol`.

## Logging defaults
The image ships a `log4j2.properties` that sets Spark and Hadoop loggers to WARN.
Override the file or pass custom log4j settings from `data-platform-jobs` if you
need more verbose output.
