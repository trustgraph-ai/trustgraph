# Tech Spec: S3-Compatible Storage Backend Support

## Overview

The Librarian service uses S3-compatible object storage for document blob storage. This spec documents the implementation that enables support for any S3-compatible backend including MinIO, Ceph RADOS Gateway (RGW), AWS S3, Cloudflare R2, DigitalOcean Spaces, and others.

## Architecture

### Storage Components
- **Blob Storage**: S3-compatible object storage via `minio` Python client library
- **Metadata Storage**: Cassandra (stores object_id mapping and document metadata)
- **Affected Component**: Librarian service only
- **Storage Pattern**: Hybrid storage with metadata in Cassandra, content in S3-compatible storage

### Implementation
- **Library**: `minio` Python client (supports any S3-compatible API)
- **Location**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
- **Operations**:
  - `add()` - Store blob with UUID object_id
  - `get()` - Retrieve blob by object_id
  - `remove()` - Delete blob by object_id
  - `ensure_bucket()` - Create bucket if not exists
- **Bucket**: `library`
- **Object Path**: `doc/{object_id}`
- **Supported MIME Types**: `text/plain`, `application/pdf`

### Key Files
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - BlobStore implementation
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - BlobStore initialization
3. `trustgraph-flow/trustgraph/librarian/service.py` - Service configuration
4. `trustgraph-flow/pyproject.toml` - Dependencies (`minio` package)
5. `docs/apis/api-librarian.md` - API documentation

## Supported Storage Backends

The implementation works with any S3-compatible object storage system:

### Tested/Supported
- **Ceph RADOS Gateway (RGW)** - Distributed storage system with S3 API (default configuration)
- **MinIO** - Lightweight self-hosted object storage

### Should Work (S3-Compatible)
- **AWS S3** - Amazon's cloud object storage
- **Cloudflare R2** - Cloudflare's S3-compatible storage
- **DigitalOcean Spaces** - DigitalOcean's object storage
- **Wasabi** - S3-compatible cloud storage
- **Backblaze B2** - S3-compatible backup storage
- Any other service implementing the S3 REST API

## Configuration

### CLI Arguments

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key>
```

### Environment Variables (Alternative)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
```

### Examples

**Ceph RADOS Gateway (default):**
```bash
--object-store-endpoint http://ceph-rgw:7480 \
--object-store-access-key object-user \
--object-store-secret-key object-password
```

**MinIO:**
```bash
--object-store-endpoint minio:9000 \
--object-store-access-key minioadmin \
--object-store-secret-key minioadmin
```

**AWS S3:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

## Authentication

All S3-compatible backends require AWS Signature Version 4 (or v2) authentication:

- **Access Key** - Public identifier (like username)
- **Secret Key** - Private signing key (like password)

The MinIO Python client handles all signature calculation automatically.

### Creating Credentials

**For MinIO:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**For Ceph RGW:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**For AWS S3:**
- Create IAM user with S3 permissions
- Generate access key in AWS Console

## Library Selection: MinIO Python Client

**Rationale:**
- Lightweight (~500KB vs boto3's ~50MB)
- S3-compatible - works with any S3 API endpoint
- Simpler API than boto3 for basic operations
- Already in use, no migration needed
- Battle-tested with MinIO and other S3 systems

## BlobStore Implementation

**Location:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

```python
from minio import Minio
import io
import logging

logger = logging.getLogger(__name__)

class BlobStore:
    """
    S3-compatible blob storage for document content.
    Supports MinIO, Ceph RGW, AWS S3, and other S3-compatible backends.
    """

    def __init__(self, endpoint, access_key, secret_key, bucket_name):
        """
        Initialize S3-compatible blob storage.

        Args:
            endpoint: S3 endpoint (e.g., "minio:9000", "ceph-rgw:8080")
            access_key: S3 access key
            secret_key: S3 secret key
            bucket_name: Bucket name for storage
        """
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,  # Set True for HTTPS
        )

        self.bucket_name = bucket_name

        logger.info(f"Connected to S3-compatible storage at {endpoint}")

        self.ensure_bucket()

    def ensure_bucket(self):
        """Create bucket if it doesn't exist"""
        found = self.client.bucket_exists(bucket_name=self.bucket_name)
        if not found:
            self.client.make_bucket(bucket_name=self.bucket_name)
            logger.info(f"Created bucket {self.bucket_name}")
        else:
            logger.debug(f"Bucket {self.bucket_name} already exists")

    async def add(self, object_id, blob, kind):
        """Store blob in S3-compatible storage"""
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=f"doc/{object_id}",
            length=len(blob),
            data=io.BytesIO(blob),
            content_type=kind,
        )
        logger.debug("Add blob complete")

    async def remove(self, object_id):
        """Delete blob from S3-compatible storage"""
        self.client.remove_object(
            bucket_name=self.bucket_name,
            object_name=f"doc/{object_id}",
        )
        logger.debug("Remove blob complete")

    async def get(self, object_id):
        """Retrieve blob from S3-compatible storage"""
        resp = self.client.get_object(
            bucket_name=self.bucket_name,
            object_name=f"doc/{object_id}",
        )
        return resp.read()
```

## Key Benefits

1. **No Vendor Lock-in** - Works with any S3-compatible storage
2. **Lightweight** - MinIO client is only ~500KB
3. **Simple Configuration** - Just endpoint + credentials
4. **No Data Migration** - Drop-in replacement between backends
5. **Battle-Tested** - MinIO client works with all major S3 implementations

## Implementation Status

All code has been updated to use generic S3 parameter names:

- ✅ `blob_store.py` - Updated to accept `endpoint`, `access_key`, `secret_key`
- ✅ `librarian.py` - Updated parameter names
- ✅ `service.py` - Updated CLI arguments and configuration
- ✅ Documentation updated

## Future Enhancements

1. **SSL/TLS Support** - Add `--s3-use-ssl` flag for HTTPS
2. **Retry Logic** - Implement exponential backoff for transient failures
3. **Presigned URLs** - Generate temporary upload/download URLs
4. **Multi-region Support** - Replicate blobs across regions
5. **CDN Integration** - Serve blobs via CDN
6. **Storage Classes** - Use S3 storage classes for cost optimization
7. **Lifecycle Policies** - Automatic archival/deletion
8. **Versioning** - Store multiple versions of blobs

## References

- MinIO Python Client: https://min.io/docs/minio/linux/developers/python/API.html
- Ceph RGW S3 API: https://docs.ceph.com/en/latest/radosgw/s3/
- S3 API Reference: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
