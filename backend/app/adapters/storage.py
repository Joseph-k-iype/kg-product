from hashlib import sha256
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager
from urllib3.util import Timeout
from app.config import settings
from app.domain.contracts import ArtifactRef


class ObjectStore:
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
            http_client=PoolManager(timeout=Timeout(connect=3, read=10), retries=1),
        )
        self.bucket = settings.minio_bucket

    def put(self, data: bytes, content_type: str) -> ArtifactRef:
        digest = sha256(data).hexdigest()
        key = "sha256/" + digest
        if not self.client.bucket_exists(self.bucket):
            try:
                self.client.make_bucket(self.bucket)
            except S3Error as e:
                if e.code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                    raise
        self.client.put_object(self.bucket, key, BytesIO(data), len(data), content_type=content_type)
        return ArtifactRef(key, digest, digest)

    def get(self, ref: ArtifactRef) -> bytes:
        response = self.client.get_object(self.bucket, ref.key)
        try:
            data = response.read()
            if sha256(data).hexdigest() != ref.sha256:
                raise ValueError("Stored artifact checksum mismatch")
            return data
        finally:
            response.close()
            response.release_conn()

    def verify(self, key: str, digest: str):
        self.get(ArtifactRef(key, digest, digest))
