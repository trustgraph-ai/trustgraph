---
layout: default
title: "Технические характеристики: Поддержка хранилища, совместимого с S3"
parent: "Russian (Beta)"
---

# Технические характеристики: Поддержка хранилища, совместимого с S3

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Обзор

Сервис Librarian использует объектное хранилище, совместимое с S3, для хранения двоичных данных документов. Этот документ описывает реализацию, которая обеспечивает поддержку любого хранилища, совместимого с S3, включая MinIO, Ceph RADOS Gateway (RGW), AWS S3, Cloudflare R2, DigitalOcean Spaces и другие.

## Архитектура

### Компоненты хранения
**Хранилище двоичных данных**: Объектное хранилище, совместимое с S3, через `minio` Python клиентскую библиотеку.
**Хранилище метаданных**: Cassandra (хранит сопоставление object_id и метаданные документов).
**Затронутый компонент**: Только сервис Librarian.
**Схема хранения**: Гибридное хранилище с метаданными в Cassandra и содержимым в хранилище, совместимом с S3.

### Реализация
**Библиотека**: `minio` Python клиент (поддерживает любой API, совместимый с S3).
**Расположение**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
**Операции**:
  `add()` - Сохранение двоичных данных с object_id в формате UUID.
  `get()` - Получение двоичных данных по object_id.
  `remove()` - Удаление двоичных данных по object_id.
  `ensure_bucket()` - Создание бакета, если он не существует.
**Бакет**: `library`
**Путь к объекту**: `doc/{object_id}`
**Поддерживаемые типы MIME**: `text/plain`, `application/pdf`

### Основные файлы
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - Реализация BlobStore.
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - Инициализация BlobStore.
3. `trustgraph-flow/trustgraph/librarian/service.py` - Конфигурация сервиса.
4. `trustgraph-flow/pyproject.toml` - Зависимости (пакет `minio`).
5. `docs/apis/api-librarian.md` - Документация API.

## Поддерживаемые системы хранения

Реализация работает с любой системой объектного хранения, совместимой с S3:

### Протестировано/Поддерживается
**Ceph RADOS Gateway (RGW)** - Распределенная система хранения с API S3 (конфигурация по умолчанию).
**MinIO** - Легковесное объектное хранилище для самостоятельного размещения.
**Garage** - Легковесное географически распределенное хранилище, совместимое с S3.

### Должно работать (совместимо с S3)
**AWS S3** - Облачное объектное хранилище от Amazon.
**Cloudflare R2** - Хранилище от Cloudflare, совместимое с S3.
**DigitalOcean Spaces** - Объектное хранилище от DigitalOcean.
**Wasabi** - Облачное хранилище, совместимое с S3.
**Backblaze B2** - Хранилище резервных копий, совместимое с S3.
Любая другая служба, реализующая REST API S3.

## Конфигурация

### Аргументы командной строки

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**Примечание:** Не включайте `http://` или `https://` в конечную точку. Используйте `--object-store-use-ssl` для включения HTTPS.

### Переменные окружения (Альтернативный способ)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### Примеры

**Ceph RADOS Gateway (по умолчанию):**
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

**Гараж (совместимый с S3):**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 с использованием SSL:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## Аутентификация

Все бэкенды, совместимые с S3, требуют аутентификации AWS Signature Version 4 (или v2):

**Access Key** - Публичный идентификатор (например, имя пользователя)
**Secret Key** - Приватный ключ для подписи (например, пароль)

Python-клиент MinIO автоматически обрабатывает все вычисления подписи.

### Создание учетных данных

**Для MinIO:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**Для Ceph RGW:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**Для AWS S3:**
Создайте пользователя IAM с разрешениями S3
Сгенерируйте ключ доступа в консоли AWS

## Выбор библиотеки: MinIO Python Client

**Обоснование:**
Легковесная (~500 КБ против ~50 МБ у boto3)
Совместима с S3 - работает с любым конечным пунктом API S3
Более простой API, чем boto3, для основных операций
Уже используется, не требуется миграция
Проверена в боевых условиях с MinIO и другими системами S3

## Реализация BlobStore

**Расположение:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

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

## Ключевые преимущества

1. **Отсутствие привязки к конкретному поставщику** - Работает с любым хранилищем, совместимым с S3.
2. **Легковесность** - Клиент MinIO занимает всего около 500 КБ.
3. **Простая настройка** - Только конечная точка и учетные данные.
4. **Отсутствие миграции данных** - Замена между бэкендами без перебоев.
5. **Проверено в боевых условиях** - Клиент MinIO работает со всеми основными реализациями S3.

## Статус реализации

Весь код был обновлен для использования общих имен параметров S3:

✅ `blob_store.py` - Обновлено для приема `endpoint`, `access_key`, `secret_key`
✅ `librarian.py` - Обновлены имена параметров
✅ `service.py` - Обновлены аргументы командной строки и конфигурация
✅ Обновлена документация

## Планируемые улучшения

1. **Поддержка SSL/TLS** - Добавить флаг `--s3-use-ssl` для HTTPS.
2. **Логика повторных попыток** - Реализовать экспоненциальную задержку для временных сбоев.
3. **Временные URL-адреса** - Генерировать временные URL-адреса для загрузки/скачивания.
4. **Поддержка нескольких регионов** - Репликация объектов между регионами.
5. **Интеграция с CDN** - Предоставление объектов через CDN.
6. **Классы хранения** - Использование классов хранения S3 для оптимизации затрат.
7. **Политики жизненного цикла** - Автоматическое архивирование/удаление.
8. **Версионирование** - Хранение нескольких версий объектов.

## Ссылки

MinIO Python Client: https://min.io/docs/minio/linux/developers/python/API.html
Ceph RGW S3 API: https://docs.ceph.com/en/latest/radosgw/s3/
S3 API Reference: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
