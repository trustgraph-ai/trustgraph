---
layout: default
title: "Especificación Técnica: Soporte para Backend de Almacenamiento Compatible con S3"
parent: "Spanish (Beta)"
---

# Especificación Técnica: Soporte para Backend de Almacenamiento Compatible con S3

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumen

El servicio Librarian utiliza almacenamiento de objetos compatible con S3 para el almacenamiento de blobs de documentos. Esta especificación documenta la implementación que permite el soporte para cualquier backend compatible con S3, incluyendo MinIO, Ceph RADOS Gateway (RGW), AWS S3, Cloudflare R2, DigitalOcean Spaces, y otros.

## Arquitectura

### Componentes de Almacenamiento
**Almacenamiento de Blobs**: Almacenamiento de objetos compatible con S3 a través de la biblioteca de cliente `minio` de Python.
**Almacenamiento de Metadatos**: Cassandra (almacena el mapeo de object_id y los metadatos del documento).
**Componente Afectado**: Solo el servicio Librarian.
**Patrón de Almacenamiento**: Almacenamiento híbrido con metadatos en Cassandra y contenido en almacenamiento compatible con S3.

### Implementación
**Biblioteca**: Cliente `minio` de Python (soporta cualquier API compatible con S3).
**Ubicación**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
**Operaciones**:
  `add()` - Almacenar blob con object_id UUID.
  `get()` - Recuperar blob por object_id.
  `remove()` - Eliminar blob por object_id.
  `ensure_bucket()` - Crear bucket si no existe.
**Bucket**: `library`
**Ruta del Objeto**: `doc/{object_id}`
**Tipos MIME Soportados**: `text/plain`, `application/pdf`

### Archivos Clave
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - Implementación de BlobStore.
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - Inicialización de BlobStore.
3. `trustgraph-flow/trustgraph/librarian/service.py` - Configuración del servicio.
4. `trustgraph-flow/pyproject.toml` - Dependencias (paquete `minio`).
5. `docs/apis/api-librarian.md` - Documentación de la API.

## Backends de Almacenamiento Soportados

La implementación funciona con cualquier sistema de almacenamiento de objetos compatible con S3:

### Probado/Soportado
**Ceph RADOS Gateway (RGW)** - Sistema de almacenamiento distribuido con API S3 (configuración predeterminada).
**MinIO** - Almacenamiento de objetos auto-alojado ligero.
**Garage** - Almacenamiento S3-compatible geo-distribuido ligero.

### Debería Funcionar (Compatible con S3)
**AWS S3** - Almacenamiento de objetos en la nube de Amazon.
**Cloudflare R2** - Almacenamiento S3-compatible de Cloudflare.
**DigitalOcean Spaces** - Almacenamiento de objetos de DigitalOcean.
**Wasabi** - Almacenamiento en la nube S3-compatible.
**Backblaze B2** - Almacenamiento de respaldo S3-compatible.
Cualquier otro servicio que implemente la API REST S3.

## Configuración

### Argumentos de la Línea de Comandos

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**Nota:** No incluya `http://` ni `https://` en el punto final. Use `--object-store-use-ssl` para habilitar HTTPS.

### Variables de entorno (Alternativa)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### Ejemplos

**Ceph RADOS Gateway (predeterminado):**
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

**Almacenamiento (compatible con S3):**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 con SSL:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## Autenticación

Todos los backends compatibles con S3 requieren la autenticación AWS Signature Version 4 (o v2):

**Clave de acceso** - Identificador público (como nombre de usuario)
**Clave secreta** - Clave de firma privada (como contraseña)

El cliente de Python de MinIO gestiona automáticamente todos los cálculos de firma.

### Creación de credenciales

**Para MinIO:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**Para Ceph RGW:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**Para AWS S3:**
Crear usuario IAM con permisos de S3
Generar clave de acceso en la consola de AWS

## Selección de la biblioteca: Cliente de Python para MinIO

**Justificación:**
Ligera (~500 KB frente a los ~50 MB de boto3)
Compatible con S3: funciona con cualquier punto final de la API de S3
API más simple que boto3 para operaciones básicas
Ya en uso, no se necesita migración
Probada en batalla con MinIO y otros sistemas S3

## Implementación de BlobStore

**Ubicación:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

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

## Beneficios Clave

1. **Sin dependencia de un proveedor** - Funciona con cualquier almacenamiento compatible con S3.
2. **Ligero** - El cliente MinIO tiene un tamaño de aproximadamente 500 KB.
3. **Configuración sencilla** - Solo necesita el punto de acceso y las credenciales.
4. **Sin migración de datos** - Reemplazo directo entre diferentes backends.
5. **Probado en batalla** - El cliente MinIO funciona con todas las principales implementaciones de S3.

## Estado de la implementación

Todo el código se ha actualizado para utilizar nombres de parámetros S3 genéricos:

✅ `blob_store.py` - Actualizado para aceptar `endpoint`, `access_key`, `secret_key`
✅ `librarian.py` - Nombres de parámetros actualizados
✅ `service.py` - Argumentos de la línea de comandos y configuración actualizados
✅ Documentación actualizada

## Mejoras futuras

1. **Soporte para SSL/TLS** - Agregar la bandera `--s3-use-ssl` para HTTPS.
2. **Lógica de reintento** - Implementar un reintento exponencial para fallos transitorios.
3. **URLs prefirmadas** - Generar URLs temporales de carga/descarga.
4. **Soporte para múltiples regiones** - Replicar blobs a través de regiones.
5. **Integración con CDN** - Servir blobs a través de una CDN.
6. **Clases de almacenamiento** - Utilizar clases de almacenamiento de S3 para la optimización de costos.
7. **Políticas de ciclo de vida** - Archivado/eliminación automática.
8. **Versionado** - Almacenar múltiples versiones de blobs.

## Referencias

Cliente de MinIO para Python: https://min.io/docs/minio/linux/developers/python/API.html
API S3 de Ceph RGW: https://docs.ceph.com/en/latest/radosgw/s3/
Referencia de la API S3: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
