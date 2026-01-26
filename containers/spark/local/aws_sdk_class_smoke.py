from pyspark.sql import SparkSession


def main() -> int:
    spark = SparkSession.builder.appName("aws-sdk-class-smoke").getOrCreate()
    try:
        jvm = spark._jvm
        class_names = [
            "software.amazon.awssdk.arns.Arn",
            "software.amazon.awssdk.protocols.xml.AwsXmlProtocolFactory",
            "software.amazon.awssdk.protocols.jsoncore.JsonNodeParser",
            "software.amazon.awssdk.http.apache.ApacheHttpClient",
            "software.amazon.awssdk.http.auth.aws.scheme.AwsV4AuthScheme",
            "software.amazon.awssdk.services.glue.model.EntityNotFoundException",
            "software.amazon.awssdk.services.kms.model.EncryptionAlgorithmSpec",
            "org.apache.iceberg.aws.glue.GlueCatalog",
        ]
        missing = []
        for name in class_names:
            try:
                jvm.java.lang.Class.forName(name)
            except Exception:
                missing.append(name)
        if missing:
            raise RuntimeError(f"Missing AWS SDK classes: {', '.join(missing)}")
        print("AWS SDK class smoke test OK")
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
