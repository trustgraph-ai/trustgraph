# Garage S3-Compatible Object Storage

## Overview

Garage is a lightweight, self-hosted S3-compatible object storage system used as an alternative to Ceph for storing documents and other objects in the TrustGraph system. It provides a simpler deployment model while maintaining S3 API compatibility.

## Features

- **S3-Compatible API**: Full compatibility with AWS S3 SDK and CLI tools
- **Lightweight**: Minimal resource requirements compared to Ceph
- **Simple Deployment**: Single container with no complex dependencies
- **Distributed**: Supports multi-node clusters (though configured for single-node by default)

## Architecture

### Components

1. **Garage Daemon** (`garage`)
   - Main storage service container
   - Provides S3 API on port 3900
   - Admin API on port 3903
   - RPC communication on port 3901

2. **Init Container** (`garage-init`)
   - Runs once to initialize the cluster
   - Configures cluster layout
   - Creates S3 access credentials
   - Uses remote RPC to communicate with daemon (no shared volumes)

### Storage

Garage uses two separate volumes:

- **Metadata Volume** (`garage-meta`): Stores cluster metadata and LMDB database
- **Data Volume** (`garage-data`): Stores actual object data

## Configuration Parameters

All configuration is done via Jsonnet parameters with the `garage-` prefix:

### S3 Credentials

```jsonnet
"garage-access-key":: "GK000000000000000000000001",
"garage-secret-key":: "b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427",
```

**Format Requirements:**
- **Access Key ID**: Must start with `GK` followed by exactly 24 hex characters (0-9, a-f)
- **Secret Key**: Must be exactly 64 hex characters

**Generate Secure Credentials:**

```bash
# Generate Access Key ID (GK + 24 hex chars)
echo "GK$(openssl rand -hex 12)"

# Generate Secret Key (64 hex chars)
openssl rand -hex 32
```

### Cluster Configuration

```jsonnet
"garage-rpc-secret":: "bbba746a9e289bad64a9e7a36a4299dac8d6e0b8cc2a6c2937fe756df4492008",
"garage-admin-token":: "batts-rockhearted-unpartially",
"garage-region":: "garage",
"garage-replication-factor":: "1",
```

- **rpc-secret**: 64 hex characters for node-to-node RPC authentication
- **admin-token**: Bearer token for Admin API access
- **region**: S3 region name
- **replication-factor**: Number of data replicas (set to 1 for single-node, 3+ for production)

### Storage Volumes

```jsonnet
"garage-meta-size":: "5G",
"garage-data-size":: "100G",
```

Both values can be overridden using the `.with()` function:

```jsonnet
.with("meta-size", "10G")
.with("data-size", "500G")
```

## Integration with Librarian

The librarian component automatically connects to Garage for object storage:

```jsonnet
"--object-store-endpoint", url.object_store,
"--object-store-access-key", $["garage-access-key"],
"--object-store-secret-key", $["garage-secret-key"],
```

The object store endpoint is defined in `values/url.jsonnet`:

```jsonnet
object_store: "http://garage:3900",
```

## Testing Garage with S3 Clients

### Using AWS CLI

```bash
# Set credentials
export AWS_ACCESS_KEY_ID="GK000000000000000000000001"
export AWS_SECRET_ACCESS_KEY="b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427"
export AWS_ENDPOINT_URL="http://localhost:3900"
export AWS_DEFAULT_REGION="garage"

# Create a bucket
aws s3 mb s3://test-bucket

# Upload a file
echo "Hello from Garage!" > test.txt
aws s3 cp test.txt s3://test-bucket/

# List files
aws s3 ls s3://test-bucket/

# Download a file
aws s3 cp s3://test-bucket/test.txt downloaded.txt

# Verify
cat downloaded.txt
```

### Using s3cmd

Create configuration file `~/.s3cfg`:

```ini
[default]
access_key = GK000000000000000000000001
secret_key = b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
host_base = localhost:3900
host_bucket = localhost:3900
use_https = False
```

Then use s3cmd:

```bash
# List buckets
s3cmd ls

# Create bucket
s3cmd mb s3://my-bucket

# Upload file
s3cmd put file.txt s3://my-bucket/

# Download file
s3cmd get s3://my-bucket/file.txt
```

## Deployment Details

### Initialization Process

The init container performs these steps:

1. **Wait for Garage daemon** - Polls `/health` endpoint until daemon is ready
2. **Get Node ID** - Queries `/v2/GetNodeInfo?node=self` via Admin API
3. **Configure Layout** - Assigns node to cluster with specified capacity via RPC
4. **Apply Layout** - Activates the cluster layout
5. **Import Credentials** - Creates S3 access key with provided credentials
6. **Grant Permissions** - Enables bucket creation for the key

All operations are **idempotent** - the init container can be restarted safely and will skip already-configured items.

### Network Architecture

- **S3 API**: Port 3900 (HTTP)
- **RPC**: Port 3901 (internal cluster communication)
- **Web UI**: Port 3902 (optional web interface)
- **Admin API**: Port 3903 (cluster management)
- **K2V API**: Port 3904 (key-value store)

### No Shared Volumes

The init container communicates with the Garage daemon entirely over the network:

- Admin API (HTTP) for status queries
- RPC (via garage CLI `-h` and `-s` flags) for cluster management

This design works across all orchestrators (Kubernetes, Docker Compose) without requiring shared volume mounts.

## Version Information

Current deployment uses **Garage v2.1.0**

- Image: `docker.io/dxflrs/garage:v2.1.0`
- Documentation: https://garagehq.deuxfleurs.fr/documentation/

## Troubleshooting

### Init Container Fails

Check logs: `podman logs <container-name>`

Common issues:
- **403 Forbidden**: Check `garage-admin-token` is correct
- **Invalid layout version**: Cluster already initialized, init will retry
- **Node ID null**: Admin API not responding, check daemon logs

### S3 Access Denied

Verify credentials format:
- Access Key ID must start with `GK` + 24 hex chars
- Secret Key must be 64 hex chars
- Credentials must match what was imported during init

### Check Garage Status

```bash
# Query cluster status
curl -H "Authorization: Bearer <admin-token>" \
  http://localhost:3903/v2/GetClusterStatus

# Check health
curl http://localhost:3903/health
```

## Production Considerations

1. **Generate Secure Credentials**: Never use default credentials in production
2. **Set Replication Factor**: Use 3+ for redundancy in multi-node clusters
3. **Increase Storage Size**: Adjust `garage-data-size` based on expected usage
4. **Secure Admin Token**: Use a strong random token for `garage-admin-token`
5. **Monitor Storage**: Watch disk usage on data volume
6. **Backup Metadata**: The metadata volume contains critical cluster state

## References

- [Garage Documentation](https://garagehq.deuxfleurs.fr/documentation/)
- [Garage Admin API v2](https://garagehq.deuxfleurs.fr/api/garage-admin-v2.json)
- [Quick Start Guide](https://garagehq.deuxfleurs.fr/documentation/quick-start/)
