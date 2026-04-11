# Especificação Técnica: Suporte a Backend de Armazenamento Compatível com S3

## Visão Geral

O serviço Librarian utiliza armazenamento de objetos compatível com S3 para o armazenamento de blobs de documentos. Esta especificação documenta a implementação que permite o suporte a qualquer backend compatível com S3, incluindo MinIO, Ceph RADOS Gateway (RGW), AWS S3, Cloudflare R2, DigitalOcean Spaces e outros.

## Arquitetura

### Componentes de Armazenamento
**Armazenamento de Blobs**: Armazenamento de objetos compatível com S3 através da biblioteca cliente `minio` Python.
**Armazenamento de Metadados**: Cassandra (armazena o mapeamento object_id e os metadados do documento).
**Componente Afetado**: Apenas o serviço Librarian.
**Padrão de Armazenamento**: Armazenamento híbrido com metadados no Cassandra e conteúdo no armazenamento compatível com S3.

### Implementação
**Biblioteca**: Cliente `minio` Python (suporta qualquer API compatível com S3).
**Localização**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
**Operações**:
  `add()` - Armazenar blob com object_id UUID.
  `get()` - Recuperar blob por object_id.
  `remove()` - Excluir blob por object_id.
  `ensure_bucket()` - Criar bucket se não existir.
**Bucket**: `library`
**Caminho do Objeto**: `doc/{object_id}`
**Tipos MIME Suportados**: `text/plain`, `application/pdf`

### Arquivos Chave
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - Implementação do BlobStore.
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - Inicialização do BlobStore.
3. `trustgraph-flow/trustgraph/librarian/service.py` - Configuração do serviço.
4. `trustgraph-flow/pyproject.toml` - Dependências (pacote `minio`).
5. `docs/apis/api-librarian.md` - Documentação da API.

## Backends de Armazenamento Suportados

A implementação funciona com qualquer sistema de armazenamento de objetos compatível com S3:

### Testados/Suportados
**Ceph RADOS Gateway (RGW)** - Sistema de armazenamento distribuído com API S3 (configuração padrão).
**MinIO** - Armazenamento de objetos auto-hospedado leve.
**Garage** - Armazenamento S3-compatível geo-distribuído leve.

### Deve Funcionar (Compatível com S3)
**AWS S3** - Armazenamento de objetos em nuvem da Amazon.
**Cloudflare R2** - Armazenamento S3-compatível da Cloudflare.
**DigitalOcean Spaces** - Armazenamento de objetos da DigitalOcean.
**Wasabi** - Armazenamento em nuvem S3-compatível.
**Backblaze B2** - Armazenamento de backup S3-compatível.
Qualquer outro serviço que implemente a API REST S3.

## Configuração

### Argumentos da Linha de Comando

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**Observação:** Não inclua `http://` ou `https://` no endpoint. Use `--object-store-use-ssl` para habilitar HTTPS.

### Variáveis de Ambiente (Alternativa)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### Exemplos

**Ceph RADOS Gateway (padrão):**
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

**Armazenamento (compatível com S3):**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 com SSL:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## Autenticação

Todos os backends compatíveis com S3 requerem a autenticação AWS Signature Version 4 (ou v2):

**Chave de Acesso** - Identificador público (como nome de usuário)
**Chave Secreta** - Chave de assinatura privada (como senha)

O cliente Python da MinIO gerencia automaticamente todos os cálculos de assinatura.

### Criando Credenciais

**Para MinIO:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**Para o Ceph RGW:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**Para AWS S3:**
Crie um usuário IAM com permissões S3
Gere uma chave de acesso no Console da AWS

## Seleção da Biblioteca: Cliente Python MinIO

**Justificativa:**
Leve (~500KB vs ~50MB do boto3)
Compatível com S3 - funciona com qualquer endpoint de API S3
API mais simples que o boto3 para operações básicas
Já em uso, não é necessária migração
Testado em batalha com MinIO e outros sistemas S3

## Implementação do BlobStore

**Localização:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

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

## Benefícios Principais

1. **Sem Dependência de Fornecedor** - Funciona com qualquer armazenamento compatível com S3.
2. **Leve** - O cliente MinIO tem apenas ~500KB.
3. **Configuração Simples** - Apenas endpoint e credenciais.
4. **Sem Migração de Dados** - Substituição direta entre backends.
5. **Testado em Combate** - O cliente MinIO funciona com todas as principais implementações S3.

## Status da Implementação

Todo o código foi atualizado para usar nomes de parâmetros S3 genéricos:

✅ `blob_store.py` - Atualizado para aceitar `endpoint`, `access_key`, `secret_key`.
✅ `librarian.py` - Nomes de parâmetros atualizados.
✅ `service.py` - Argumentos da CLI e configuração atualizados.
✅ Documentação atualizada.

## Melhorias Futuras

1. **Suporte SSL/TLS** - Adicionar a flag `--s3-use-ssl` para HTTPS.
2. **Lógica de Repetição** - Implementar retrocesso exponencial para falhas transitórias.
3. **URLs Pré-assinadas** - Gerar URLs temporárias de upload/download.
4. **Suporte Multi-região** - Replicar blobs entre regiões.
5. **Integração CDN** - Servir blobs via CDN.
6. **Classes de Armazenamento** - Usar classes de armazenamento S3 para otimização de custos.
7. **Políticas de Ciclo de Vida** - Arquivamento/exclusão automática.
8. **Versionamento** - Armazenar múltiplas versões de blobs.

## Referências

Cliente Python MinIO: https://min.io/docs/minio/linux/developers/python/API.html
API S3 Ceph RGW: https://docs.ceph.com/en/latest/radosgw/s3/
Referência da API S3: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
