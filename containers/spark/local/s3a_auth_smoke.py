from pyspark.sql import SparkSession


def main() -> int:
    spark = SparkSession.builder.appName("s3a-auth-smoke").getOrCreate()
    try:
        jvm = spark._jvm
        conf = spark._jsc.hadoopConfiguration()
        conf.set("fs.s3a.access.key", "minio")
        conf.set("fs.s3a.secret.key", "minio123")
        conf.set("fs.s3a.session.token", "session-token")
        conf.set(
            "fs.s3a.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.TemporaryAWSCredentialsProvider",
        )
        provider = jvm.org.apache.hadoop.fs.s3a.TemporaryAWSCredentialsProvider(conf)
        creds = provider.resolveCredentials()
        if creds is None:
            raise RuntimeError("TemporaryAWSCredentialsProvider returned no credentials")
        if creds.accessKeyId() != "minio":
            raise RuntimeError("Unexpected access key from credentials provider")
        if creds.secretAccessKey() != "minio123":
            raise RuntimeError("Unexpected secret key from credentials provider")
        if creds.sessionToken() != "session-token":
            raise RuntimeError("Unexpected session token from credentials provider")
        print("S3A auth smoke test OK")
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
