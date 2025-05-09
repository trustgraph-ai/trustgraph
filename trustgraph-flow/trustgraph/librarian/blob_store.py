from .. schema import LibrarianRequest, LibrarianResponse, Error
from .. knowledge import hash
from .. exceptions import RequestError

from minio import Minio
import time
import io

class BlobStore:

    def __init__(
            self,
            minio_host, minio_access_key, minio_secret_key, bucket_name, 
    ):


        self.minio = Minio(
            minio_host,
            access_key = minio_access_key,
            secret_key = minio_secret_key,
            secure = False,
        )

        self.bucket_name = bucket_name

        print("Connected to minio", flush=True)

        self.ensure_bucket()

    def ensure_bucket(self):

        # Make the bucket if it doesn't exist.
        found = self.minio.bucket_exists(self.bucket_name)
        if not found:
            self.minio.make_bucket(self.bucket_name)
            print("Created bucket", self.bucket_name, flush=True)
        else:
            print("Bucket", self.bucket_name, "already exists", flush=True)

    async def add(self, object_id, blob, kind):

        # FIXME: Loop retry
        self.minio.put_object(
            bucket_name = self.bucket_name,
            object_name = "doc/" + str(object_id),
            length = len(blob),
            data = io.BytesIO(blob),
            content_type = kind,
        )

        print("Add blob complete", flush=True)

    async def remove(self, object_id):

        # FIXME: Loop retry
        self.minio.remove_object(
            bucket_name = self.bucket_name,
            object_name = "doc/" + str(object_id),
        )

        print("Remove blob complete", flush=True)


    async def get(self, object_id):

        # FIXME: Loop retry
        resp = self.minio.get_object(
            bucket_name = self.bucket_name,
            object_name = "doc/" + str(object_id),
        )

        return resp.read()

