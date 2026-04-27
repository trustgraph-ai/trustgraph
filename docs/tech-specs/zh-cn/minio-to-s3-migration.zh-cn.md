---
layout: default
title: "技术规范：S3 兼容的存储后端支持"
parent: "Chinese (Beta)"
---

# 技术规范：S3 兼容的存储后端支持

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

Librarian 服务使用 S3 兼容的对象存储来存储文档 Blob。此规范记录了实现，该实现支持任何 S3 兼容的后端，包括 MinIO、Ceph RADOS Gateway (RGW)、AWS S3、Cloudflare R2、DigitalOcean Spaces 等。

## 架构

### 存储组件
**Blob 存储**: 通过 `minio` Python 客户端库实现的 S3 兼容对象存储
**元数据存储**: Cassandra (存储 object_id 映射和文档元数据)
**受影响的组件**: 仅限 Librarian 服务
**存储模式**: 混合存储，元数据存储在 Cassandra 中，内容存储在 S3 兼容的存储中

### 实现
**库**: `minio` Python 客户端 (支持任何 S3 兼容的 API)
**位置**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
**操作**:
  `add()` - 使用 UUID object_id 存储 Blob
  `get()` - 根据 object_id 检索 Blob
  `remove()` - 根据 object_id 删除 Blob
  `ensure_bucket()` - 如果不存在，则创建 Bucket
**Bucket**: `library`
**对象路径**: `doc/{object_id}`
**支持的 MIME 类型**: `text/plain`, `application/pdf`

### 关键文件
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - BlobStore 实现
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - BlobStore 初始化
3. `trustgraph-flow/trustgraph/librarian/service.py` - 服务配置
4. `trustgraph-flow/pyproject.toml` - 依赖项 (`minio` 包)
5. `docs/apis/api-librarian.md` - API 文档

## 支持的存储后端

此实现适用于任何 S3 兼容的对象存储系统：

### 已测试/支持
**Ceph RADOS Gateway (RGW)** - 具有 S3 API 的分布式存储系统 (默认配置)
**MinIO** - 轻量级的自托管对象存储
**Garage** - 轻量级的分布式 S3 兼容存储

### 应该可以工作 (S3 兼容)
**AWS S3** - Amazon 的云对象存储
**Cloudflare R2** - Cloudflare 的 S3 兼容存储
**DigitalOcean Spaces** - DigitalOcean 的对象存储
**Wasabi** - S3 兼容的云存储
**Backblaze B2** - S3 兼容的备份存储
任何实现 S3 REST API 的服务

## 配置

### 命令行参数

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**注意：** 请不要在端点中包含 `http://` 或 `https://`。 使用 `--object-store-use-ssl` 启用 HTTPS。

### 环境变量（备选方案）

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### 示例

**Ceph RADOS 网关（默认）：**
```bash
--object-store-endpoint ceph-rgw:7480 \
--object-store-access-key object-user \
--object-store-secret-key object-password
```

**MinIO:**
```bash
--object-store-endpoint minio:9000 \
--object-store-access-key minioadmin \
--object-store-secret-key minioadmin
```

**云存储（兼容S3）：**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 使用 SSL：**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## 身份验证

所有兼容 S3 的后端都需要 AWS 签名版本 4（或 v2）身份验证：

**访问密钥** - 公开标识符（类似于用户名）
**密钥** - 私有签名密钥（类似于密码）

MinIO Python 客户端会自动处理所有签名计算。

### 创建凭证

**对于 MinIO：**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**适用于 Ceph RGW：**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**适用于 AWS S3：**
创建具有 S3 权限的 IAM 用户
在 AWS 控制台中生成访问密钥

## 库选择：MinIO Python 客户端

**理由：**
轻量级（约 500KB，而 boto3 约为 50MB）
与 S3 兼容，适用于任何 S3 API 端点
对于基本操作，API 比 boto3 更简单
已在使用中，无需迁移
经过 MinIO 和其他 S3 系统的严格测试

## BlobStore 实施

**位置：** `trustgraph-flow/trustgraph/librarian/blob_store.py`

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

    def __init__(self, endpoint, access_key, secret_key, bucket_name,
                 use_ssl=False, region=None):
        """
        Initialize S3-compatible blob storage.

        Args:
            endpoint: S3 endpoint (e.g., "minio:9000", "ceph-rgw:7480")
            access_key: S3 access key
            secret_key: S3 secret key
            bucket_name: Bucket name for storage
            use_ssl: Use HTTPS instead of HTTP (default: False)
            region: S3 region (optional, e.g., "us-east-1")
        """
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=use_ssl,
            region=region,
        )

        self.bucket_name = bucket_name

        protocol = "https" if use_ssl else "http"
        logger.info(f"Connected to S3-compatible storage at {protocol}://{endpoint}")

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

## 关键优势

1. **无厂商锁定** - 适用于任何兼容 S3 的存储
2. **轻量级** - MinIO 客户端仅约 500KB
3. **简单配置** - 仅需端点 + 凭据
4. **无需数据迁移** - 作为后端之间的直接替代方案
5. **经过严格测试** - MinIO 客户端与所有主要的 S3 实现兼容

## 实现状态

所有的代码都已更新为使用通用的 S3 参数名称：

✅ `blob_store.py` - 更新为接受 `endpoint`, `access_key`, `secret_key`
✅ `librarian.py` - 更新了参数名称
✅ `service.py` - 更新了 CLI 参数和配置
✅ 文档已更新

## 未来增强功能

1. **SSL/TLS 支持** - 添加 `--s3-use-ssl` 标志以支持 HTTPS
2. **重试逻辑** - 针对瞬时错误实现指数级退避
3. **预签名 URL** - 生成临时上传/下载 URL
4. **多区域支持** - 在区域之间复制数据块
5. **CDN 集成** - 通过 CDN 提供数据块
6. **存储类别** - 使用 S3 存储类别进行成本优化
7. **生命周期策略** - 自动归档/删除
8. **版本控制** - 存储数据块的多个版本

## 参考文献

MinIO Python 客户端: https://min.io/docs/minio/linux/developers/python/API.html
Ceph RGW S3 API: https://docs.ceph.com/en/latest/radosgw/s3/
S3 API 参考: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
