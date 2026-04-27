---
layout: default
title: "Техническая спецификация по загрузке больших документов"
parent: "Russian (Beta)"
---

# Техническая спецификация по загрузке больших документов

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Обзор

Эта спецификация рассматривает проблемы масштабируемости и удобства использования при загрузке
больших документов в TrustGraph. Текущая архитектура рассматривает загрузку документов
как единую атомарную операцию, что приводит к перегрузке памяти на нескольких этапах
процесса и не предоставляет пользователям обратной связи или возможностей восстановления.

Эта реализация нацелена на следующие сценарии использования:

1. **Обработка больших PDF-файлов**: Загрузка и обработка PDF-файлов объемом в сотни мегабайт
   без переполнения памяти
2. **Возобновляемая загрузка**: Возможность продолжить прерванную загрузку с того места,
   где она была остановлена, а не перезапускать ее.
3. **Информативность о ходе выполнения**: Предоставление пользователям информации в режиме реального времени
   о ходе загрузки и обработки.
4. **Эффективная обработка памяти**: Обработка документов потоковым способом
   без хранения целых файлов в памяти.

## Цели

**Инкрементная загрузка**: Поддержка загрузки документов по частям через REST и WebSocket
**Возобновляемые передачи**: Возможность восстановления после прерванных загрузок
**Информативность о ходе выполнения**: Предоставление клиентам информации о ходе загрузки/обработки
**Эффективность использования памяти**: Исключение полной буферизации документов на протяжении всего процесса
**Обратная совместимость**: Существующие процессы загрузки небольших документов продолжают работать без изменений
**Потоковая обработка**: Декодирование PDF и разбиение текста на фрагменты выполняются в потоковом режиме

## Описание

### Текущая архитектура

Процесс отправки документов проходит по следующему пути:

1. **Клиент** отправляет документ через REST (`POST /api/v1/librarian`) или WebSocket
2. **API Gateway** получает полный запрос с содержимым документа в кодировке base64
3. **LibrarianRequestor** преобразует запрос в сообщение Pulsar
4. **Librarian Service** получает сообщение, декодирует документ в память
5. **BlobStore** загружает документ в Garage/S3
6. **Cassandra** хранит метаданные со ссылкой на объект
7. Для обработки: документ извлекается из S3, декодируется, разбивается на фрагменты — все в памяти

Основные файлы:
Точка входа REST/WebSocket: `trustgraph-flow/trustgraph/gateway/service.py`
Основной модуль Librarian: `trustgraph-flow/trustgraph/librarian/librarian.py`
Хранилище объектов: `trustgraph-flow/trustgraph/librarian/blob_store.py`
Таблицы Cassandra: `trustgraph-flow/trustgraph/tables/library.py`
Схема API: `trustgraph-base/trustgraph/schema/services/library.py`

### Текущие ограничения

Текущая конструкция имеет несколько взаимосвязанных проблем, связанных с памятью и удобством использования:

1. **Атомарная операция загрузки**: Весь документ должен быть передан в одном запросе.
   Загрузка больших документов требует длительных запросов без индикации хода выполнения
   и без механизма повторной отправки в случае сбоя соединения.

2. **Дизайн API**: И REST, и WebSocket API ожидают получения всего документа
   в одном сообщении. Схема (`LibrarianRequest`) имеет одно поле `content`
   для хранения всего документа в кодировке base64.

3. **Память Librarian**: Сервис Librarian декодирует весь документ
   в память перед загрузкой в S3. Для PDF-файла объемом 500 МБ это означает
   выделение 500 МБ + в оперативной памяти.

4. **Память декодера PDF**: При начале обработки декодер PDF-файла загружает
   весь PDF-файл в память для извлечения текста. Такие библиотеки, как PyPDF,
   обычно требуют полного доступа к документу.

5. **Память разбивающего на фрагменты**: Разбивающий на фрагменты получает весь извлеченный текст
   и хранит его в памяти при создании фрагментов.

**Пример влияния на память** (PDF-файл объемом 500 МБ):
Gateway: ~700 МБ (дополнительный объем для кодирования base64)
Librarian: ~500 МБ (декодированные байты)
Декодер PDF: ~500 МБ + буферы извлечения
Разбивающий на фрагменты: извлеченный текст (переменная, потенциально 100 МБ+)

Общий пиковый объем используемой памяти может превысить 2 ГБ для одного большого документа.

## Технический дизайн

### Принципы проектирования

1. **API Facade**: Все взаимодействия с клиентом осуществляются через API Librarian. Клиенты
   не имеют прямого доступа к хранилищу S3/Garage и не знают о его существовании.

2. **Многокомпонентная загрузка в S3**: Используется стандартная многокомпонентная загрузка в S3.
   Это широко поддерживается в системах, совместимых с S3 (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2 и т. д.), что обеспечивает переносимость.

3. **Атомарное завершение**: Многокомпонентные загрузки в S3 по своей природе являются атомарными — загруженные
   фрагменты невидимы до вызова `CompleteMultipartUpload`. Не требуются временные
   файлы или операции переименования.

4. **Отслеживаемое состояние**: Сессии загрузки отслеживаются в Cassandra, что обеспечивает
   информацию о незавершенных загрузках и позволяет восстановить загрузку.

### Поток загрузки по частям

```
Client                    Librarian API                   S3/Garage
  │                            │                              │
  │── begin-upload ───────────►│                              │
  │   (metadata, size)         │── CreateMultipartUpload ────►│
  │                            │◄── s3_upload_id ─────────────│
  │◄── upload_id ──────────────│   (store session in          │
  │                            │    Cassandra)                │
  │                            │                              │
  │── upload-chunk ───────────►│                              │
  │   (upload_id, index, data) │── UploadPart ───────────────►│
  │                            │◄── etag ─────────────────────│
  │◄── ack + progress ─────────│   (store etag in session)    │
  │         ⋮                  │         ⋮                    │
  │   (repeat for all chunks)  │                              │
  │                            │                              │
  │── complete-upload ────────►│                              │
  │   (upload_id)              │── CompleteMultipartUpload ──►│
  │                            │   (parts coalesced by S3)    │
  │                            │── store doc metadata ───────►│ Cassandra
  │◄── document_id ────────────│   (delete session)           │
```

Клиент никогда не взаимодействует с S3 напрямую. Библиотека преобразует
наши API загрузки по частям в многокомпонентные операции S3 внутри себя.

### Операции API библиотеки

#### `begin-upload`

Инициализация сессии загрузки по частям.

Запрос:
```json
{
  "operation": "begin-upload",
  "document-metadata": {
    "id": "doc-123",
    "kind": "application/pdf",
    "title": "Large Document",
    "user": "user-id",
    "tags": ["tag1", "tag2"]
  },
  "total-size": 524288000,
  "chunk-size": 5242880
}
```

Ответ:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

Библиотекарь:
1. Генерирует уникальный `upload_id` и `object_id` (UUID для хранения объектов)
2. Вызывает `CreateMultipartUpload` S3, получает `s3_upload_id`
3. Создает запись сессии в Cassandra
4. Возвращает `upload_id` клиенту

#### `upload-chunk`

Загрузка одного фрагмента.

Запрос:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

Ответ:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "chunks-received": 1,
  "total-chunks": 100,
  "bytes-received": 5242880,
  "total-bytes": 524288000
}
```

Библиотекарь:
1. Ищет сессию по `upload_id`
2. Проверяет право собственности (пользователь должен совпадать с создателем сессии)
3. Вызывает S3 `UploadPart` с данными фрагмента, получает `etag`
4. Обновляет запись сессии с индексом фрагмента и etag
5. Возвращает прогресс клиенту

Неудачные фрагменты можно повторить - просто отправьте тот же `chunk-index` снова.

#### `complete-upload`

Завершите загрузку и создайте документ.

Запрос:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

Ответ:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Библиотекарь:
1. Ищет сессию, проверяет, все ли фрагменты получены.
2. Вызывает S3 `CompleteMultipartUpload` с информацией о частях (S3 объединяет части
   внутри себя - нулевая стоимость по памяти для библиотекаря).
3. Создает запись документа в Cassandra с метаданными и ссылкой на объект.
4. Удаляет запись сессии загрузки.
5. Возвращает идентификатор документа клиенту.

#### `abort-upload`

Отмена загрузки, находящейся в процессе.

Запрос:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

Библиотекарь:
1. Вызывает S3 `AbortMultipartUpload` для очистки разделов.
2. Удаляет запись сессии из Cassandra.

#### `get-upload-status`

Проверка статуса загрузки (для возможности возобновления).

Запрос:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

Ответ:
```json
{
  "upload-id": "upload-abc-123",
  "state": "in-progress",
  "chunks-received": [0, 1, 2, 5, 6],
  "missing-chunks": [3, 4, 7, 8],
  "total-chunks": 100,
  "bytes-received": 36700160,
  "total-bytes": 524288000
}
```

#### `list-uploads`

Список неполных загрузок для пользователя.

Запрос:
```json
{
  "operation": "list-uploads"
}
```

Ответ:
```json
{
  "uploads": [
    {
      "upload-id": "upload-abc-123",
      "document-metadata": { "title": "Large Document", ... },
      "progress": { "chunks-received": 43, "total-chunks": 100 },
      "created-at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Загрузка данных сессии

Отслеживание текущих загрузок в Cassandra:

```sql
CREATE TABLE upload_session (
    upload_id text PRIMARY KEY,
    user text,
    document_id text,
    document_metadata text,      -- JSON: title, kind, tags, comments, etc.
    s3_upload_id text,           -- internal, for S3 operations
    object_id uuid,              -- target blob ID
    total_size bigint,
    chunk_size int,
    total_chunks int,
    chunks_received map<int, text>,  -- chunk_index → etag
    created_at timestamp,
    updated_at timestamp
) WITH default_time_to_live = 86400;  -- 24 hour TTL

CREATE INDEX upload_session_user ON upload_session (user);
```

**Поведение TTL:**
Сессии истекают через 24 часа, если не завершены.
Когда TTL Cassandra истекает, запись сессии удаляется.
Оставшиеся фрагменты S3 очищаются политикой жизненного цикла S3 (настраивается на бакете).

### Обработка ошибок и атомарность

**Ошибка загрузки фрагмента:**
Клиент повторяет загрузку неудачного фрагмента (с теми же `upload_id` и `chunk-index`).
Операция `UploadPart` S3 является идемпотентной для одного и того же номера фрагмента.
Сессия отслеживает, какие фрагменты были успешно загружены.

**Разрыв соединения клиента во время загрузки:**
Сессия остается в Cassandra с записью о полученных фрагментах.
Клиент может вызвать `get-upload-status`, чтобы узнать, что отсутствует.
Возобновление путем загрузки только отсутствующих фрагментов, затем `complete-upload`.

**Ошибка полной загрузки:**
Операция `CompleteMultipartUpload` S3 является атомарной - либо успешно завершается полностью, либо не удается.
В случае сбоя фрагменты остаются, и клиент может повторить `complete-upload`.
Ни один частичный документ никогда не отображается.

**Истечение срока действия сессии:**
TTL Cassandra удаляет запись сессии через 24 часа.
Политика жизненного цикла бакета S3 очищает неполные многокомпонентные загрузки.
Не требуется ручная очистка.

### Атомарность многокомпонентной загрузки S3

Многокомпонентные загрузки S3 обеспечивают встроенную атомарность:

1. **Фрагменты невидимы**: Загруженные фрагменты не могут быть доступны в качестве объектов.
   Они существуют только как части незавершенной многокомпонентной загрузки.

2. **Атомарное завершение**: `CompleteMultipartUpload` либо успешно завершается (объект
   появляется атомарно), либо не удается (объект не создается). Отсутствует частичное состояние.

3. **Не требуется переименование**: Конечный ключ объекта указывается во время
   `CreateMultipartUpload`. Фрагменты объединяются непосредственно в этот ключ.

4. **Объединение на стороне сервера**: S3 объединяет фрагменты внутренне. Библиотекарь
   никогда не считывает фрагменты обратно - нулевые накладные расходы памяти независимо от размера документа.

### Расширения BlobStore

**Файл:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

Добавлены методы многокомпонентной загрузки:

```python
class BlobStore:
    # Existing methods...

    def create_multipart_upload(self, object_id: UUID, kind: str) -> str:
        """Initialize multipart upload, return s3_upload_id."""
        # minio client: create_multipart_upload()

    def upload_part(
        self, object_id: UUID, s3_upload_id: str,
        part_number: int, data: bytes
    ) -> str:
        """Upload a single part, return etag."""
        # minio client: upload_part()
        # Note: S3 part numbers are 1-indexed

    def complete_multipart_upload(
        self, object_id: UUID, s3_upload_id: str,
        parts: List[Tuple[int, str]]  # [(part_number, etag), ...]
    ) -> None:
        """Finalize multipart upload."""
        # minio client: complete_multipart_upload()

    def abort_multipart_upload(
        self, object_id: UUID, s3_upload_id: str
    ) -> None:
        """Cancel multipart upload, clean up parts."""
        # minio client: abort_multipart_upload()
```

### Особенности размера фрагментов

**Минимальный размер для S3**: 5 МБ на часть (кроме последней части)
**Максимальный размер для S3**: 10 000 частей на загрузку
**Рекомендуемый размер по умолчанию**: фрагменты по 5 МБ
  Документ объемом 500 МБ = 100 фрагментов
  Документ объемом 5 ГБ = 1000 фрагментов
**Гранулярность прогресса**: Меньшие фрагменты = более точные обновления прогресса
**Эффективность сети**: Большие фрагменты = меньше сетевых запросов

Размер фрагмента может быть настроен клиентом в пределах заданных ограничений (от 5 МБ до 100 МБ).

### Обработка документов: Потоковая загрузка

Процесс загрузки предназначен для эффективной передачи документов в хранилище. Процесс обработки предназначен для извлечения и разделения документов на фрагменты без полной загрузки
их в память.


#### Основной принцип: Идентификатор, а не содержимое

В настоящее время, при запуске обработки, содержимое документа передается через сообщения Pulsar. Это приводит к полной загрузке документов в память. Вместо этого:


Сообщения Pulsar содержат только **идентификатор документа**
Обработчики получают содержимое документа непосредственно из хранилища.
Получение происходит в виде **потока во временный файл**
Разбор документов, специфичный для каждого формата (PDF, текст и т.д.), работает с файлами, а не с буферами памяти.

Это позволяет хранилищу быть независимым от структуры документа. Разбор PDF, извлечение текста и другая логика, специфичная для формата, остается в соответствующих декодерах.


#### Процесс обработки

```
Pulsar              PDF Decoder                Librarian              S3
  │                      │                          │                  │
  │── doc-id ───────────►│                          │                  │
  │  (processing msg)    │                          │                  │
  │                      │                          │                  │
  │                      │── stream-document ──────►│                  │
  │                      │   (doc-id)               │── GetObject ────►│
  │                      │                          │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (write to temp file)   │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (append to temp file)  │                  │
  │                      │         ⋮                │         ⋮        │
  │                      │◄── EOF ──────────────────│                  │
  │                      │                          │                  │
  │                      │   ┌──────────────────────────┐              │
  │                      │   │ temp file on disk        │              │
  │                      │   │ (memory stays bounded)   │              │
  │                      │   └────────────┬─────────────┘              │
  │                      │                │                            │
  │                      │   PDF library opens file                    │
  │                      │   extract page 1 text ──►  chunker          │
  │                      │   extract page 2 text ──►  chunker          │
  │                      │         ⋮                                   │
  │                      │   close file                                │
  │                      │   delete temp file                          │
```

#### API потоковой передачи данных для библиотекаря

Добавить операцию получения документов в режиме потоковой передачи:

**`stream-document`**

Запрос:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

Ответ: Потоковые двоичные фрагменты (не единый ответ).

Для REST API это возвращает потоковый ответ с `Transfer-Encoding: chunked`.

Для внутренних вызовов между сервисами (от процессора к библиотеке), это может быть:
Прямая потоковая передача данных через S3 с использованием предварительно подписанного URL (если внутренняя сеть это позволяет).
Фрагментированные ответы через протокол сервиса.
Специальный конечный пункт для потоковой передачи данных.

Основное требование: данные передаются фрагментами, никогда полностью не буферизуются в библиотеке.

#### Изменения декодера PDF

**Текущая реализация** (требует много памяти):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**Новая реализация** (временный файл, постепенная):

```python
def decode_pdf_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield extracted text page by page."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream document to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Open PDF from file (not memory)
        reader = PdfReader(tmp.name)

        # Yield pages incrementally
        for page in reader.pages:
            yield page.extract_text()

        # tmp file auto-deleted on context exit
```

Профиль использования памяти:
Временный файл на диске: размер PDF (диск дешевый).
В памяти: текст одной страницы за раз.
Максимальный объем памяти: ограничен, не зависит от размера документа.

#### Изменения в декодере текстовых документов

Для обычных текстовых документов еще проще - временный файл не нужен:

```python
def decode_text_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield text in chunks as it streams from storage."""

    buffer = ""
    for chunk in librarian_client.stream_document(doc_id):
        buffer += chunk.decode('utf-8')

        # Yield complete lines/paragraphs as they arrive
        while '\n\n' in buffer:
            paragraph, buffer = buffer.split('\n\n', 1)
            yield paragraph + '\n\n'

    # Yield remaining buffer
    if buffer:
        yield buffer
```

Текстовые документы могут передаваться напрямую без временного файла, поскольку они имеют
линейную структуру.

#### Интеграция с модулем разбиения на части (Chunker)

Модуль разбиения на части (chunker) получает итератор текстовых данных (страниц или абзацев) и
создает фрагменты постепенно:

```python
class StreamingChunker:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process(self, text_stream: Iterator[str]) -> Iterator[str]:
        """Yield chunks as text arrives."""
        buffer = ""

        for text_segment in text_stream:
            buffer += text_segment

            while len(buffer) >= self.chunk_size:
                chunk = buffer[:self.chunk_size]
                yield chunk
                # Keep overlap for context continuity
                buffer = buffer[self.chunk_size - self.overlap:]

        # Yield remaining buffer as final chunk
        if buffer.strip():
            yield buffer
```

#### Конвейер сквозной обработки

```python
async def process_document(doc_id: str, librarian_client, embedder):
    """Process document with bounded memory."""

    # Get document metadata to determine type
    metadata = await librarian_client.get_document_metadata(doc_id)

    # Select decoder based on document type
    if metadata.kind == 'application/pdf':
        text_stream = decode_pdf_streaming(doc_id, librarian_client)
    elif metadata.kind == 'text/plain':
        text_stream = decode_text_streaming(doc_id, librarian_client)
    else:
        raise UnsupportedDocumentType(metadata.kind)

    # Chunk incrementally
    chunker = StreamingChunker(chunk_size=1000, overlap=100)

    # Process each chunk as it's produced
    for chunk in chunker.process(text_stream):
        # Generate embeddings, store in vector DB, etc.
        embedding = await embedder.embed(chunk)
        await store_chunk(doc_id, chunk, embedding)
```

В любой момент времени полный документ или полностью извлеченный текст не хранятся в памяти.

#### Особенности использования временных файлов

**Расположение**: Используйте системную временную директорию (`/tmp` или эквивалент). Для
контейнеризированных развертываний убедитесь, что временная директория имеет достаточно места
и находится на быстром носителе (желательно не на сетевом диске).

**Очистка**: Используйте контекстные менеджеры (`with tempfile...`) для обеспечения очистки
даже в случае возникновения исключений.

**Параллельная обработка**: Каждый процесс обработки получает свой временный файл.
Отсутствуют конфликты между параллельной обработкой документов.

**Место на диске**: Временные файлы существуют недолго (продолжительность обработки). Для
PDF-файла объемом 500 МБ требуется 500 МБ временного пространства во время обработки. Ограничение размера может
быть применено во время загрузки, если место на диске ограничено.

### Унифицированный интерфейс обработки: Дочерние документы

Извлечение текста из PDF-файлов и обработка текстовых документов должны быть интегрированы в одну
общую цепочку обработки (разделение на фрагменты → создание векторных представлений → хранение). Для достижения этого с
использованием единого интерфейса "получение по ID", извлеченные текстовые фрагменты сохраняются обратно
в систему как дочерние документы.

#### Поток обработки с использованием дочерних документов

```
PDF Document                                         Text Document
     │                                                     │
     ▼                                                     │
pdf-extractor                                              │
     │                                                     │
     │ (stream PDF from librarian)                         │
     │ (extract page 1 text)                               │
     │ (store as child doc → librarian)                    │
     │ (extract page 2 text)                               │
     │ (store as child doc → librarian)                    │
     │         ⋮                                           │
     ▼                                                     ▼
[child-doc-id, child-doc-id, ...]                    [doc-id]
     │                                                     │
     └─────────────────────┬───────────────────────────────┘
                           ▼
                       chunker
                           │
                           │ (receives document ID)
                           │ (streams content from librarian)
                           │ (chunks incrementally)
                           ▼
                    [chunks → embedding → storage]
```

Модуль разбиения на фрагменты имеет один унифицированный интерфейс:
Получение идентификатора документа (через Pulsar)
Получение содержимого от хранилища данных
Разбиение на фрагменты

Он не знает и не заботится о том, относится ли идентификатор к:
Текстовому документу, загруженному пользователем
Извлеченному текстовому фрагменту из страницы PDF
Любому будущему типу документов

#### Метаданные дочернего документа

Расширьте схему документа для отслеживания отношений родитель/дочерний элемент:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**Типы документов:**

| `document_type` | Описание |
|-----------------|-------------|
| `source` | Документ, загруженный пользователем (PDF, текст и т.д.) |
| `extracted` | Полученный из исходного документа (например, текст страницы PDF) |

**Поля метаданных:**

| Поле | Исходный документ | Извлеченный дочерний элемент |
|-------|-----------------|-----------------|
| `id` | Предоставлено пользователем или сгенерировано | сгенерировано (например, `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | Идентификатор родительского документа |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf` и т.д. | `text/plain` |
| `title` | Предоставлено пользователем | сгенерировано (например, "Страница 3 отчета Report.pdf") |
| `user` | Аутентифицированный пользователь | то же, что и у родительского элемента |

#### API для дочерних документов

**Создание дочерних документов** (внутреннее, используется pdf-extractor):

```json
{
  "operation": "add-child-document",
  "parent-id": "doc-123",
  "document-metadata": {
    "id": "doc-123-page-1",
    "kind": "text/plain",
    "title": "Page 1"
  },
  "content": "<base64-encoded-text>"
}
```

Для небольших извлеченных фрагментов текста (обычный текст страницы обычно менее 100 КБ) однокрасная загрузка является приемлемой. Для очень больших извлечений текста можно использовать загрузку по частям.

**Список дочерних документов** (для отладки/администрирования):

**Отображение дочерних документов** (для отладки/администрирования):

```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

Ответ:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### Поведение, видимое пользователю

**`list-documents` поведение по умолчанию:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

Только документы верхнего уровня отображаются в списке документов пользователя.
Дочерние документы по умолчанию отфильтровываются.

**Необязательный флаг `include-children`** (для администраторов/отладки):

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### Каскадное удаление

При удалении родительского документа все дочерние элементы должны быть удалены:

```python
def delete_document(doc_id: str):
    # Find all children
    children = query("SELECT id, object_id FROM document WHERE parent_id = ?", doc_id)

    # Delete child blobs from S3
    for child in children:
        blob_store.delete(child.object_id)

    # Delete child metadata from Cassandra
    execute("DELETE FROM document WHERE parent_id = ?", doc_id)

    # Delete parent blob and metadata
    parent = get_document(doc_id)
    blob_store.delete(parent.object_id)
    execute("DELETE FROM document WHERE id = ? AND user = ?", doc_id, user)
```

#### Соображения по поводу хранения

Извлеченные текстовые фрагменты дублируют контент:
Оригинальный PDF-файл хранится в хранилище "Garage".
Извлеченный текст для каждой страницы также хранится в хранилище "Garage".

Этот компромисс позволяет:
**Единый интерфейс для разбиения на фрагменты**: Разбиватель всегда получает данные по идентификатору.
**Возобновление/повтор**: Можно перезапустить на этапе разбиения на фрагменты без повторной извлечения PDF-файла.
**Отладка**: Извлеченный текст можно просмотреть.
**Разделение ответственности**: Сервисы извлечения PDF и разбиения на фрагменты являются независимыми.

Для PDF-файла объемом 500 МБ с 200 страницами, в среднем 5 КБ текста на страницу:
Хранение PDF: 500 МБ.
Хранение извлеченного текста: около 1 МБ в общей сложности.
Дополнительные затраты: незначительные.

#### Вывод извлечения текста из PDF-файла

Сервис извлечения текста из PDF-файла, после обработки документа:

1. Получает PDF-файл из хранилища "librarian" во временный файл.
2. Извлекает текст страницу за страницей.
3. Для каждой страницы сохраняет извлеченный текст как дочерний документ через хранилище "librarian".
4. Отправляет идентификаторы дочерних документов в очередь разбивателя на фрагменты.
Выходной документ.
```python
async def extract_pdf(doc_id: str, librarian_client, output_queue):
    """Extract PDF pages and store as child documents."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream PDF to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Extract pages
        reader = PdfReader(tmp.name)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            # Store as child document
            child_id = f"{doc_id}-page-{page_num}"
            await librarian_client.add_child_document(
                parent_id=doc_id,
                document_id=child_id,
                kind="text/plain",
                title=f"Page {page_num}",
                content=text.encode('utf-8')
            )

            # Send to chunker queue
            await output_queue.send(child_id)
```

Модуль, отвечающий за разделение на части, получает эти идентификаторы дочерних элементов и обрабатывает их так же, как он бы обрабатывал текстовый документ, загруженный пользователем.

### Обновления для клиентов

#### Python SDK


Python SDK (`trustgraph-base/trustgraph/api/library.py`) должен обрабатывать
загрузку данных, разделенных на части, прозрачно. Публичный интерфейс остается неизменным:

```python
# Existing interface - no change for users
library.add_document(
    id="doc-123",
    title="Large Report",
    kind="application/pdf",
    content=large_pdf_bytes,  # Can be hundreds of MB
    tags=["reports"]
)
```

Внутри, SDK определяет размер документа и переключает стратегию:

```python
class Library:
    CHUNKED_UPLOAD_THRESHOLD = 2 * 1024 * 1024  # 2MB

    def add_document(self, id, title, kind, content, tags=None, ...):
        if len(content) < self.CHUNKED_UPLOAD_THRESHOLD:
            # Small document: single operation (existing behavior)
            return self._add_document_single(id, title, kind, content, tags)
        else:
            # Large document: chunked upload
            return self._add_document_chunked(id, title, kind, content, tags)

    def _add_document_chunked(self, id, title, kind, content, tags):
        # 1. begin-upload
        session = self._begin_upload(
            document_metadata={...},
            total_size=len(content),
            chunk_size=5 * 1024 * 1024
        )

        # 2. upload-chunk for each chunk
        for i, chunk in enumerate(self._chunk_bytes(content, session.chunk_size)):
            self._upload_chunk(session.upload_id, i, chunk)

        # 3. complete-upload
        return self._complete_upload(session.upload_id)
```

**Функции обратного вызова для отслеживания прогресса** (необязательное улучшение):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

Это позволяет пользовательским интерфейсам отображать ход загрузки без изменения основного API.

#### Инструменты командной строки

**`tg-add-library-document`** продолжает работать без изменений:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

Возможно, можно добавить опциональное отображение прогресса:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**Устаревшие инструменты удалены:**

`tg-load-pdf` - устарело, используйте `tg-add-library-document`
`tg-load-text` - устарело, используйте `tg-add-library-document`

**Команды администратора/отладки** (опционально, низкий приоритет):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

Это могут быть флаги для существующей команды, а не отдельные инструменты.

#### Обновления спецификации API

Спецификация OpenAPI (`specs/api/paths/librarian.yaml`) требует обновлений для:

**Новые операции:**

`begin-upload` - Инициализация сессии загрузки по частям
`upload-chunk` - Загрузка отдельного фрагмента
`complete-upload` - Завершение загрузки
`abort-upload` - Отмена загрузки
`get-upload-status` - Запрос хода загрузки
`list-uploads` - Список незавершенных загрузок для пользователя
`stream-document` - Получение документа в режиме потоковой передачи
`add-child-document` - Сохранение извлеченного текста (внутреннее использование)
`list-children` - Список дочерних документов (для администраторов)

**Измененные операции:**

`list-documents` - Добавлен параметр `include-children`

**Новые схемы:**

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**Обновления спецификации WebSocket** (`specs/websocket/`):

Отразите операции REST для клиентов WebSocket, обеспечивая обновления хода загрузки в режиме реального времени.


#### Соображения пользовательского интерфейса

Обновления спецификации API позволяют улучшить пользовательский интерфейс:

**Интерфейс отображения хода загрузки:**
Индикатор прогресса, показывающий загруженные фрагменты
Оценка оставшегося времени
Возможность приостановки/возобновления

**Восстановление после ошибок:**
Опция "Возобновить загрузку" для прерванных загрузок
Список ожидающих загрузок при повторном подключении

**Обработка больших файлов:**
Обнаружение размера файла на стороне клиента
Автоматическая загрузка по частям для больших файлов
Четкая обратная связь во время длительных загрузок

Эти улучшения пользовательского интерфейса требуют работы на стороне клиентской части, основанной на обновленной спецификации API.
