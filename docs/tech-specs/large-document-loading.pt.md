# Especificação Técnica de Carregamento de Documentos Grandes

## Visão Geral

Esta especificação aborda problemas de escalabilidade e experiência do usuário ao carregar
documentos grandes no TrustGraph. A arquitetura atual trata o upload de documentos
como uma operação atômica única, causando pressão de memória em vários pontos do
pipeline e não fornecendo feedback ou opções de recuperação aos usuários.

Esta implementação visa os seguintes casos de uso:

1. **Processamento de PDF Grandes**: Fazer upload e processar arquivos PDF de centenas de megabytes
   sem esgotar a memória
2. **Uploads Retomáveis**: Permitir que uploads interrompidos continuem de onde
   pararam, em vez de reiniciar
3. **Feedback de Progresso**: Fornecer aos usuários visibilidade em tempo real do upload
   e do progresso do processamento
4. **Processamento Eficiente em Memória**: Processar documentos de forma streaming
   sem manter arquivos inteiros na memória

## Objetivos

**Upload Incremental**: Suportar upload de documentos em partes via REST e WebSocket
**Transferências Retomáveis**: Permitir a recuperação de uploads interrompidos
**Visibilidade do Progresso**: Fornecer feedback de upload/processamento aos clientes
**Eficiência de Memória**: Eliminar o buffer de documentos completos em todo o pipeline
**Compatibilidade com Versões Anteriores**: Os fluxos de trabalho existentes de documentos pequenos continuam inalterados
**Processamento em Streaming**: A decodificação de PDF e o particionamento de texto operam em streams

## Contexto

### Arquitetura Atual

O fluxo de envio de documentos passa pelo seguinte caminho:

1. **Cliente** envia o documento via REST (`POST /api/v1/librarian`) ou WebSocket
2. **API Gateway** recebe a solicitação completa com o conteúdo do documento codificado em base64
3. **LibrarianRequestor** traduz a solicitação para uma mensagem Pulsar
4. **Librarian Service** recebe a mensagem, decodifica o documento na memória
5. **BlobStore** faz upload do documento para Garage/S3
6. **Cassandra** armazena metadados com a referência do objeto
7. Para processamento: o documento é recuperado do S3, decodificado, particionado - tudo na memória

Arquivos chave:
Ponto de entrada REST/WebSocket: `trustgraph-flow/trustgraph/gateway/service.py`
Núcleo do Librarian: `trustgraph-flow/trustgraph/librarian/librarian.py`
Armazenamento de blobs: `trustgraph-flow/trustgraph/librarian/blob_store.py`
Tabelas do Cassandra: `trustgraph-flow/trustgraph/tables/library.py`
Esquema da API: `trustgraph-base/trustgraph/schema/services/library.py`

### Limitações Atuais

O design atual apresenta vários problemas de memória e UX que se agravam:

1. **Operação de Upload Atômica**: O documento inteiro deve ser transmitido em um
   único pedido. Documentos grandes exigem solicitações de longa duração sem
   indicação de progresso e sem mecanismo de repetição se a conexão falhar.

2. **Design da API**: As APIs REST e WebSocket esperam o documento completo
   em uma única mensagem. O esquema (`LibrarianRequest`) tem um campo `content`
   contendo o documento inteiro codificado em base64.

3. **Memória do Librarian**: O serviço librarian decodifica o documento inteiro
   na memória antes de fazer upload para o S3. Para um PDF de 500 MB, isso significa manter
   500 MB+ na memória do processo.

4. **Memória do Decodificador de PDF**: Quando o processamento começa, o decodificador de PDF carrega
   o PDF inteiro na memória para extrair o texto. Bibliotecas como PyPDF normalmente
   exigem acesso ao documento completo.

5. **Memória do Particionador**: O particionador de texto recebe o texto extraído completo
   e o mantém na memória enquanto produz os chunks.

**Exemplo de Impacto na Memória** (PDF de 500 MB):
Gateway: ~700 MB (overhead de codificação base64)
Librarian: ~500 MB (bytes decodificados)
Decodificador de PDF: ~500 MB + buffers de extração
Particionador: texto extraído (variável, potencialmente 100 MB+)

A memória máxima pode exceder 2 GB para um único documento grande.

## Design Técnico

### Princípios de Design

1. **API Facade**: Toda a interação do cliente passa pela API do librarian. Os clientes
   não têm acesso direto ou conhecimento do armazenamento subjacente S3/Garage.

2. **Upload Multipart do S3**: Use o upload multipart padrão do S3 internamente.
   Isso é amplamente suportado em sistemas compatíveis com S3 (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2, etc.), garantindo a portabilidade.

3. **Conclusão Atômica**: Os uploads multipart do S3 são inerentemente atômicos - as partes carregadas
   são invisíveis até que `CompleteMultipartUpload` seja chamado. Nenhum arquivo temporário ou operação de renomeação necessária.
   
4. **Estado Rastreável**: As sessões de upload são rastreadas no Cassandra, fornecendo
visibilidade para uploads incompletos e permitindo a capacidade de retomada.
   
### Fluxo de Upload em Partes


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

O cliente nunca interage diretamente com o S3. O "librarian" traduz entre
nossa API de upload em partes e as operações multipart do S3 internamente.

### Operações da API do "Librarian"

#### `begin-upload`

Inicializar uma sessão de upload em partes.

Requisição:
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

Resposta:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

O bibliotecário:
1. Gera um `upload_id` e `object_id` únicos (UUID para armazenamento de blobs).
2. Chama o S3 `CreateMultipartUpload`, recebe `s3_upload_id`.
3. Cria um registro de sessão no Cassandra.
4. Retorna `upload_id` para o cliente.

#### `upload-chunk`

Envie um único bloco.

Requisição:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

Resposta:
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

O bibliotecário:
1. Busca a sessão por `upload_id`
2. Valida a propriedade (o usuário deve corresponder ao criador da sessão)
3. Chama o S3 `UploadPart` com os dados do chunk, recebe `etag`
4. Atualiza o registro da sessão com o índice do chunk e o etag
5. Retorna o progresso para o cliente

Os chunks com falha podem ser retentados - basta enviar o mesmo `chunk-index` novamente.

#### `complete-upload`

Finalize o upload e crie o documento.

Requisição:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

Resposta:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

O bibliotecário:
1. Consulta a sessão, verifica se todos os fragmentos foram recebidos.
2. Chama o S3 `CompleteMultipartUpload` com as etiquetas de parte (S3 combina as partes
   internamente - custo de memória zero para o bibliotecário).
3. Cria um registro de documento no Cassandra com metadados e referência ao objeto.
4. Exclui o registro da sessão de upload.
5. Retorna o ID do documento para o cliente.

#### `abort-upload`

Cancelar um upload em andamento.

Requisição:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

O bibliotecário:
1. Chama o S3 `AbortMultipartUpload` para limpar partes.
2. Exclui o registro da sessão do Cassandra.

#### `get-upload-status`

Consulta o status de um upload (para a capacidade de retomada).

Requisição:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

Resposta:
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

Listar uploads incompletos para um usuário.

Requisição:
```json
{
  "operation": "list-uploads"
}
```

Resposta:
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

### Upload de Sessão de Armazenamento

Acompanhe uploads em andamento no Cassandra:

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

**Comportamento do TTL:**
As sessões expiram após 24 horas se não forem concluídas.
Quando o TTL do Cassandra expira, o registro da sessão é excluído.
Partes S3 órfãs são limpas pela política de ciclo de vida do S3 (configure no bucket).

### Tratamento de Falhas e Atomicidade

**Falha no upload de chunks:**
O cliente tenta novamente o chunk com falha (mesmo `upload_id` e `chunk-index`).
O `UploadPart` do S3 é idempotente para o mesmo número de parte.
A sessão rastreia quais chunks foram bem-sucedidos.

**Desconexão do cliente durante o upload:**
A sessão permanece no Cassandra com os chunks recebidos registrados.
O cliente pode chamar `get-upload-status` para ver o que está faltando.
Retomar enviando apenas os chunks ausentes e, em seguida, `complete-upload`.

**Falha no upload completo:**
O `CompleteMultipartUpload` do S3 é atômico - ou tem sucesso total ou falha.
Em caso de falha, as partes permanecem e o cliente pode tentar novamente `complete-upload`.
Nenhum documento parcial é visível.

**Expiração da sessão:**
O TTL do Cassandra exclui o registro da sessão após 24 horas.
A política de ciclo de vida do bucket S3 limpa uploads multipartes incompletos.
Não é necessário nenhum processo de limpeza manual.

### Atomicidade Multipart do S3

Os uploads multipart do S3 fornecem atomicidade integrada:

1. **As partes são invisíveis:** As partes carregadas não podem ser acessadas como objetos.
   Elas existem apenas como partes de um upload multipart incompleto.

2. **Conclusão atômica:** `CompleteMultipartUpload` ou tem sucesso (o objeto
   aparece atomicamente) ou falha (nenhum objeto é criado). Nenhum estado parcial.

3. **Não é necessário renomear:** A chave do objeto final é especificada em
   `CreateMultipartUpload`. As partes são combinadas diretamente para essa chave.

4. **Coalescência no lado do servidor:** O S3 combina as partes internamente. O bibliotecário
   nunca lê as partes de volta - nenhuma sobrecarga de memória, independentemente do tamanho do documento.

### Extensões BlobStore

**Arquivo:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

Adicionar métodos de upload multipart:

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

### Considerações sobre o Tamanho do Chunk

**Mínimo do S3**: 5MB por parte (exceto a última parte)
**Máximo do S3**: 10.000 partes por upload
**Valor padrão prático**: chunks de 5MB
  Documento de 500MB = 100 chunks
  Documento de 5GB = 1.000 chunks
**Granularidade do progresso**: Chunks menores = atualizações de progresso mais detalhadas
**Eficiência da rede**: Chunks maiores = menos viagens de ida e volta

O tamanho do chunk pode ser configurável pelo cliente dentro de limites (5MB - 100MB).

### Processamento de Documentos: Recuperação em Streaming

O fluxo de upload visa colocar documentos no armazenamento de forma eficiente. O fluxo de processamento visa extrair e dividir documentos sem carregá-los inteiramente na memória.

#### Princípio de Design: Identificador, Não Conteúdo


Atualmente, quando o processamento é acionado, o conteúdo do documento flui através de mensagens Pulsar. Isso carrega documentos inteiros na memória. Em vez disso:

As mensagens Pulsar carregam apenas o **identificador do documento**
Os processadores buscam o conteúdo do documento diretamente do "librarian"
A busca ocorre como um **stream para um arquivo temporário**
A análise específica do documento (PDF, texto, etc.) funciona com arquivos, não com buffers de memória

Isso mantém o "librarian" independente da estrutura do documento. A análise de PDF, a extração de texto e outras lógicas específicas do formato permanecem nos decodificadores respectivos.

#### Fluxo de Processamento


#### Fluxo de Processamento

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

#### API de fluxo do Bibliotecário

Adicionar uma operação de recuperação de documentos em fluxo:

**`stream-document`**

Requisição:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

Resposta: Blocos binários transmitidos (não uma única resposta).

Para a API REST, isso retorna uma resposta transmitida com `Transfer-Encoding: chunked`.

Para chamadas internas de serviço a serviço (do processador para o bibliotecário), isso pode ser:
Transmissão direta do S3 via URL pré-assinada (se a rede interna permitir)
Respostas em blocos sobre o protocolo do serviço
Um endpoint de transmissão dedicado

O requisito principal: os dados fluem em blocos, nunca totalmente armazenados em buffer no bibliotecário.

#### Alterações no Decodificador PDF

**Implementação atual** (que consome muita memória):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**Nova implementação** (arquivo temporário, incremental):

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

Perfil de memória:
Arquivo temporário no disco: tamanho do PDF (o disco é barato)
Na memória: uma página de texto por vez
Memória máxima: limitada, independente do tamanho do documento

#### Alterações no decodificador de documentos de texto

Para documentos de texto simples, ainda mais simples - nenhum arquivo temporário necessário:

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

Documentos de texto podem ser transmitidos diretamente sem um arquivo temporário, pois são
estruturados linearmente.

#### Integração com o Chunker (Fragmentador)

O fragmentador recebe um iterador de texto (páginas ou parágrafos) e produz
fragmentos incrementalmente:

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

#### Pipeline de Processamento de Ponta a Ponta

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

Em nenhum momento, o documento completo ou o texto extraído completo são mantidos na memória.

#### Considerações sobre Arquivos Temporários

**Localização**: Utilize o diretório temporário do sistema (`/tmp` ou equivalente). Para
implantações em contêineres, certifique-se de que o diretório temporário tenha espaço suficiente
e esteja em armazenamento rápido (não montado em rede, se possível).

**Limpeza**: Utilize gerenciadores de contexto (`with tempfile...`) para garantir a limpeza
mesmo em caso de exceções.

**Processamento concorrente**: Cada tarefa de processamento recebe seu próprio arquivo temporário.
Não há conflitos entre o processamento paralelo de documentos.

**Espaço em disco**: Os arquivos temporários são de curta duração (duração do processamento). Para
um arquivo PDF de 500 MB, são necessários 500 MB de espaço temporário durante o processamento. O limite de tamanho pode
ser imposto no momento do upload, caso o espaço em disco seja limitado.

### Interface de Processamento Unificada: Documentos Filhos

A extração de PDF e o processamento de documentos de texto precisam ser integrados ao mesmo
pipeline downstream (divisão em partes → incorporações → armazenamento). Para alcançar isso com uma interface consistente de "busca por ID", os blocos de texto extraídos são armazenados de volta
no sistema de gerenciamento de documentos como documentos filhos.

#### Fluxo de Processamento com Documentos Filhos

Saída do contrato (deve seguir exatamente o formato abaixo).
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

O componente de divisão em partes (chunker) possui uma interface uniforme:
Recebe um ID de documento (via Pulsar)
Transmite o conteúdo do "bibliotecário"
Divide em partes

Ele não sabe nem se importa se o ID se refere a:
Um documento de texto carregado por um usuário
Um trecho de texto extraído de uma página PDF
Qualquer tipo de documento futuro

#### Metadados do Documento Filho

Estenda o esquema do documento para rastrear relacionamentos pai/filho:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**Tipos de documentos:**

| `document_type` | Descrição |
|-----------------|-------------|
| `source` | Documento carregado pelo usuário (PDF, texto, etc.) |
| `extracted` | Derivado de um documento de origem (por exemplo, texto da página de um PDF) |

**Campos de metadados:**

| Campo | Documento de Origem | Filho Extraído |
|-------|-----------------|-----------------|
| `id` | fornecido pelo usuário ou gerado | gerado (por exemplo, `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | ID do documento pai |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`, etc. | `text/plain` |
| `title` | fornecido pelo usuário | gerado (por exemplo, "Página 3 do Relatório.pdf") |
| `user` | usuário autenticado | o mesmo que o pai |

#### API do Bibliotecário para Documentos Filhos

**Criando documentos filhos** (interno, usado por pdf-extractor):

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

Para pequenas extrações de texto (o texto de uma página típica é menor que 100 KB), o upload em uma única operação é aceitável. Para extrações de texto muito grandes, um upload em partes pode ser usado.

**Listando documentos filhos** (para depuração/administração):

**Listagem de documentos filhos** (para depuração/administração):

```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

Resposta:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### Comportamento visível ao usuário

**`list-documents` comportamento padrão:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

Apenas os documentos de nível superior (originais) aparecem na lista de documentos do usuário.
Os documentos filhos são filtrados por padrão.

**Flag opcional "incluir_filhos"** (para administração/depuração):

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### Exclusão em Cadeia

Quando um documento pai é excluído, todos os filhos devem ser excluídos:

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

#### Considerações sobre Armazenamento

Blocos de texto extraídos duplicam conteúdo:
O PDF original é armazenado no "Garage" (espaço de armazenamento).
O texto extraído por página também é armazenado no "Garage".

Este compromisso permite:
**Interface de "chunker" uniforme**: O "chunker" sempre busca por ID.
**Retomada/repetição**: É possível reiniciar no estágio do "chunker" sem reextrair o PDF.
**Depuração**: O texto extraído pode ser inspecionado.
**Separação de responsabilidades**: O extrator de PDF e o "chunker" são serviços independentes.

Para um PDF de 500MB com 200 páginas, com uma média de 5KB de texto por página:
Armazenamento do PDF: 500MB
Armazenamento do texto extraído: ~1MB no total
Sobrecarga: insignificante

#### Saída do Extrator de PDF

O extrator de PDF, após processar um documento:

1. Transfere o PDF do "librarian" para um arquivo temporário.
2. Extrai o texto página por página.
3. Para cada página, armazena o texto extraído como um documento filho através do "librarian".
4. Envia os IDs dos documentos filhos para a fila do "chunker".
Após a última linha traduzida, fornecer uma linha final contendo exatamente: [[__END_OF_TRANSLATION__]]
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

O componente de divisão recebe esses IDs de elementos filhos e os processa da mesma forma que processaria um documento de texto carregado por um usuário.

### Atualizações do Cliente

#### SDK Python


O SDK Python (`trustgraph-base/trustgraph/api/library.py`) deve lidar com uploads divididos de forma transparente. A interface pública permanece inalterada:


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

Internamente, o SDK detecta o tamanho do documento e alterna a estratégia:

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

**Callbacks de progresso** (melhoria opcional):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

Isso permite que as interfaces de usuário exibam o progresso do upload sem alterar a API básica.

#### Ferramentas de Linha de Comando (CLI)

**`tg-add-library-document`** continua a funcionar inalterado:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

Uma exibição de progresso opcional pode ser adicionada:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**Ferramentas legadas removidas:**

`tg-load-pdf` - descontinuado, use `tg-add-library-document`
`tg-load-text` - descontinuado, use `tg-add-library-document`

**Comandos de administração/depuração** (opcional, baixa prioridade):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

Estes poderiam ser flags no comando existente, em vez de ferramentas separadas.

#### Atualizações da Especificação da API

A especificação OpenAPI (`specs/api/paths/librarian.yaml`) precisa de atualizações para:

**Novas operações:**

`begin-upload` - Inicializar sessão de upload em partes
`upload-chunk` - Enviar parte individual
`complete-upload` - Finalizar upload
`abort-upload` - Cancelar upload
`get-upload-status` - Consultar o progresso do upload
`list-uploads` - Listar uploads incompletos para o usuário
`stream-document` - Recuperação de documentos em streaming
`add-child-document` - Armazenar texto extraído (interno)
`list-children` - Listar documentos filhos (administrador)

**Operações modificadas:**

`list-documents` - Adicionar parâmetro `include-children`

**Novos esquemas:**

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**Atualizações da especificação WebSocket** (`specs/websocket/`):

Espelhe as operações REST para clientes WebSocket, permitindo atualizações de progresso em tempo real
durante o upload.

#### Considerações de UX

As atualizações da especificação da API permitem melhorias na interface do usuário:

**Interface do usuário de progresso do upload:**
Barra de progresso mostrando as partes enviadas
Tempo estimado restante
Capacidade de pausar/retomar

**Recuperação de erros:**
Opção "retomar upload" para uploads interrompidos
Lista de uploads pendentes na reconexão

**Tratamento de arquivos grandes:**
Detecção do tamanho do arquivo no lado do cliente
Upload automático em partes para arquivos grandes
Feedback claro durante uploads longos

Essas melhorias de UX exigem trabalho na interface do usuário, guiado pela especificação da API atualizada.
