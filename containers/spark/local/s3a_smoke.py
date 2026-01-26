import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, concat, lit


def main() -> int:
    spark = SparkSession.builder.getOrCreate()

    output_path = os.environ.get("S3A_OUTPUT", "s3a://spark-test/smoke/output")
    row_count = 100
    df = (
        spark.range(0, row_count)
        .repartition(10)
        .withColumn("name", concat(lit("row-"), col("id")))
        .withColumnRenamed("id", "value")
    )
    df.write.mode("overwrite").parquet(output_path)

    loaded = spark.read.parquet(output_path)
    count = loaded.count()
    if count != row_count:
        print(f"Expected {row_count} rows, got {count}", file=sys.stderr)
        return 1

    jvm = spark._jvm
    hadoop_conf = spark._jsc.hadoopConfiguration()
    path = jvm.org.apache.hadoop.fs.Path(output_path)
    fs = path.getFileSystem(hadoop_conf)
    if not fs.exists(path):
        print(f"Expected path {output_path} to exist", file=sys.stderr)
        return 1

    print("S3A smoke test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
