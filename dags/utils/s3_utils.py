from contextlib import contextmanager

import boto3

from roger.config import S3Config


class S3Utils:

    def __init__(
            self,
            s3_config: S3Config
            ):
        self.config = s3_config

    @contextmanager
    def connect(
            self,
    ):
        session = boto3.session.Session(
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
        )

        s3 = session.resource(
            's3',
            endpoint_url=self.config.host,
        )
        bucket = s3.Bucket(self.config.bucket)
        yield bucket

    def get(self, remote_file_name: str, local_file_name: str):
        with self.connect() as bucket:
            bucket.download_file(remote_file_name, local_file_name)

    def put(self, local_file_name: str, remote_file_name: str):
        with self.connect() as bucket:
            bucket.upload_file(local_file_name, remote_file_name)

    def ls(self):
        with self.connect() as bucket:
            return [
                obj
                for obj in bucket.objects.all()
            ]
