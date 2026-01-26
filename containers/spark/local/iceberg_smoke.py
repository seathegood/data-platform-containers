from pyspark.sql import SparkSession


def main() -> int:
    spark = (
        SparkSession.builder.appName("iceberg-smoke")
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.local.type", "hadoop")
        .config("spark.sql.catalog.local.warehouse", "s3a://spark-test/iceberg")
        .getOrCreate()
    )

    try:
        spark.sql("CREATE DATABASE IF NOT EXISTS local.smoke")
        spark.sql("DROP TABLE IF EXISTS local.smoke.iceberg_smoke")
        spark.sql(
            "CREATE TABLE local.smoke.iceberg_smoke (id INT, name STRING) USING iceberg"
        )
        spark.sql(
            "INSERT INTO local.smoke.iceberg_smoke VALUES (1, 'alpha'), (2, 'beta')"
        )
        spark.sql("ALTER TABLE local.smoke.iceberg_smoke ADD COLUMN category STRING")
        spark.sql(
            "INSERT INTO local.smoke.iceberg_smoke VALUES (3, 'gamma', 'delta')"
        )
        rows = spark.sql("SELECT * FROM local.smoke.iceberg_smoke ORDER BY id").collect()
        expected = [
            (1, "alpha", None),
            (2, "beta", None),
            (3, "gamma", "delta"),
        ]
        if [(r.id, r.name, r.category) for r in rows] != expected:
            raise RuntimeError("Iceberg query returned unexpected rows")
        spark.sql(
            """
            CALL local.system.expire_snapshots(
              table => 'local.smoke.iceberg_smoke',
              older_than => TIMESTAMP '2999-01-01 00:00:00',
              retain_last => 1
            )
            """
        )
        print("Iceberg smoke test OK")
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
