from .. schema import LibrarianRequest, LibrarianResponse, Error
from .. knowledge import hash
from .. exceptions import RequestError

from minio import Minio
from minio.commonconfig import Part
import time
import io
import logging
from typing import Iterator, List, Tuple
from uuid import UUID

# Module logger
logger = logging.getLogger(__name__)

class BlobStore:

    def __init__(
            self,
            endpoint, access_key, secret_key, bucket_name,
            use_ssl=False, region=None,
    ):


        self.client = Minio(
            endpoint = endpoint,
            access_key = access_key,
            secret_key = secret_key,
            secure = use_ssl,
            region = region,
        )

        self.bucket_name = bucket_name

        protocol = "https" if use_ssl else "http"
        logger.info(f"Connected to S3-compatible storage at {protocol}://{endpoint}")

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

    def get_stream(self, object_id, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        """
        Stream document content in chunks.

        Yields chunks of the document, allowing processing without loading
        the entire document into memory.

        Args:
            object_id: The UUID of the document object
            chunk_size: Size of each chunk in bytes (default 1MB)

        Yields:
            Chunks of document content as bytes
        """
        resp = self.client.get_object(
            bucket_name=self.bucket_name,
            object_name="doc/" + str(object_id),
        )

        try:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            resp.close()
            resp.release_conn()

        logger.debug("Stream complete")

    def create_multipart_upload(self, object_id: UUID, kind: str) -> str:
        """
        Initialize a multipart upload.

        Args:
            object_id: The UUID for the new object
            kind: MIME type of the document

        Returns:
            The S3 upload_id for this multipart upload session
        """
        object_name = "doc/" + str(object_id)

        # Use minio's internal method to create multipart upload
        upload_id = self.client._create_multipart_upload(
            bucket_name=self.bucket_name,
            object_name=object_name,
            headers={"Content-Type": kind},
        )

        logger.info(f"Created multipart upload {upload_id} for {object_id}")
        return upload_id

    def upload_part(
        self,
        object_id: UUID,
        upload_id: str,
        part_number: int,
        data: bytes
    ) -> str:
        """
        Upload a single part of a multipart upload.

        Args:
            object_id: The UUID of the object being uploaded
            upload_id: The S3 upload_id from create_multipart_upload
            part_number: Part number (1-indexed, as per S3 spec)
            data: The chunk data to upload

        Returns:
            The ETag for this part (needed for complete_multipart_upload)
        """
        object_name = "doc/" + str(object_id)

        etag = self.client._upload_part(
            bucket_name=self.bucket_name,
            object_name=object_name,
            upload_id=upload_id,
            part_number=part_number,
            data=io.BytesIO(data),
            headers={"Content-Length": str(len(data))},
        )

        logger.debug(f"Uploaded part {part_number} for {object_id}, etag={etag}")
        return etag

    def complete_multipart_upload(
        self,
        object_id: UUID,
        upload_id: str,
        parts: List[Tuple[int, str]]
    ) -> None:
        """
        Complete a multipart upload, assembling all parts into the final object.

        S3 coalesces the parts server-side - no data transfer through this client.

        Args:
            object_id: The UUID of the object
            upload_id: The S3 upload_id from create_multipart_upload
            parts: List of (part_number, etag) tuples in order
        """
        object_name = "doc/" + str(object_id)

        # Convert to Part objects as expected by minio
        part_objects = [
            Part(part_number, etag)
            for part_number, etag in parts
        ]

        self.client._complete_multipart_upload(
            bucket_name=self.bucket_name,
            object_name=object_name,
            upload_id=upload_id,
            parts=part_objects,
        )

        logger.info(f"Completed multipart upload for {object_id}")

    def abort_multipart_upload(self, object_id: UUID, upload_id: str) -> None:
        """
        Abort a multipart upload, cleaning up any uploaded parts.

        Args:
            object_id: The UUID of the object
            upload_id: The S3 upload_id from create_multipart_upload
        """
        object_name = "doc/" + str(object_id)

        self.client._abort_multipart_upload(
            bucket_name=self.bucket_name,
            object_name=object_name,
            upload_id=upload_id,
        )

        logger.info(f"Aborted multipart upload {upload_id} for {object_id}")

