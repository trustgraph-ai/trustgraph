from .. schema import LibrarianRequest, LibrarianResponse, Error
from .. knowledge import hash
from .. exceptions import RequestError

from minio import Minio
import time
import io
import logging

# Module logger
logger = logging.getLogger(__name__)

class BlobStore:

    def __init__(
            self,
            endpoint, access_key, secret_key, bucket_name,
    ):


        self.client = Minio(
            endpoint = endpoint,
            access_key = access_key,
            secret_key = secret_key,
            secure = False,
        )

        self.bucket_name = bucket_name

        logger.info(f"Connected to S3-compatible storage at {endpoint}")

        self.ensure_bucket()

    def ensure_bucket(self):

        # Make the bucket if it doesn't exist.
        found = self.client.bucket_exists(bucket_name=self.bucket_name)
        if not found:
            self.client.make_bucket(bucket_name=self.bucket_name)
            logger.info(f"Created bucket {self.bucket_name}")
        else:
            logger.debug(f"Bucket {self.bucket_name} already exists")

    async def add(self, object_id, blob, kind):

        # FIXME: Loop retry
        self.client.put_object(
            bucket_name = self.bucket_name,
            object_name = "doc/" + str(object_id),
            length = len(blob),
            data = io.BytesIO(blob),
            content_type = kind,
        )

        logger.debug("Add blob complete")

    async def remove(self, object_id):

        # FIXME: Loop retry
        self.client.remove_object(
            bucket_name = self.bucket_name,
            object_name = "doc/" + str(object_id),
        )

        logger.debug("Remove blob complete")


    async def get(self, object_id):

        # FIXME: Loop retry
        resp = self.client.get_object(
            bucket_name = self.bucket_name,
            object_name = "doc/" + str(object_id),
        )

        return resp.read()

