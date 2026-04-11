# TrustGraph Kayıt (Log) Stratejisi

## Genel Bakış

TrustGraph, tüm kayıt işlemlerinde Python'un yerleşik `logging` modülünü kullanır, merkezi yapılandırma ve kayıt toplama için isteğe bağlı Loki entegrasyonuna sahiptir. Bu, sistemin tüm bileşenleri için standartlaştırılmış, esnek bir kayıt yaklaşımı sağlar.

## Varsayılan Yapılandırma

### Kayıt Seviyesi
**Varsayılan Seviye**: `INFO`
**Yapılandırılabilir**: `--log-level` komut satırı argümanı aracılığıyla
**Seçenekler**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Çıkış Hedefleri
1. **Konsol (stdout)**: Her zaman etkindir - konteynerleştirilmiş ortamlarla uyumluluğu sağlar.
2. **Loki**: İsteğe bağlı, merkezi kayıt toplama (varsayılan olarak etkindir, devre dışı bırakılabilir).

## Merkezi Kayıt Modülü

Tüm kayıt yapılandırması, aşağıdaki özellikleri sağlayan `trustgraph.base.logging` modülü tarafından yönetilir:
`add_logging_args(parser)` - Standart kayıt komut satırı argümanlarını ekler.
`setup_logging(args)` - Ayrıştırılmış argümanlardan kaydı yapılandırır.

Bu modül, tüm sunucu tarafı bileşenleri tarafından kullanılır:
AsyncProcessor tabanlı hizmetler
API Ağ Geçidi
MCP Sunucusu

## Uygulama Yönergeleri

### 1. Kayıt Oluşturucu Başlatma

Her modül, modülün `__name__`'ını kullanarak kendi kayıt oluşturucusunu oluşturmalıdır:

```python
import logging

logger = logging.getLogger(__name__)
```

Kayıt günlüğünün adı, Loki'de filtreleme ve arama için otomatik olarak bir etiket olarak kullanılır.

### 2. Hizmet Başlatma

Tüm sunucu tarafı hizmetleri, merkezi modül aracılığıyla otomatik olarak günlük yapılandırması alır:

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # Add standard logging arguments (includes Loki configuration)
    add_logging_args(parser)

    # Add your service-specific arguments
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # Setup logging early in startup
    setup_logging(args)

    # Rest of your service initialization
    logger = logging.getLogger(__name__)
    logger.info("Service starting...")
```

### 3. Komut Satırı Argümanları

Tüm hizmetler bu günlük kaydı argümanlarını destekler:

**Günlük Seviyesi:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**Loki Yapılandırması:**
```bash
--loki-enabled              # Enable Loki (default)
--no-loki-enabled           # Disable Loki
--loki-url URL              # Loki push URL (default: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # Optional authentication
--loki-password PASSWORD    # Optional authentication
```

**Örnekler:**
```bash
# Default - INFO level, Loki enabled
./my-service

# Debug mode, console only
./my-service --log-level DEBUG --no-loki-enabled

# Custom Loki server with auth
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. Ortam Değişkenleri

Loki yapılandırması, ortam değişkeni geri dönüşlerini destekler:

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

Komut satırı argümanları, ortam değişkenlerine göre önceliklidir.

### 5. Kayıt (Logging) İçin En İyi Uygulamalar

#### Kayıt Seviyelerinin Kullanımı
**DEBUG**: Sorunları teşhis etmek için detaylı bilgiler (değişken değerleri, fonksiyon giriş/çıkış)
**INFO**: Genel bilgilendirici mesajlar (hizmet başlatıldı, yapılandırma yüklendi, işlem aşamaları)
**WARNING**: Potansiyel olarak tehlikeli durumlara yönelik uyarı mesajları (kullanımdan kaldırılmış özellikler, düzeltilebilir hatalar)
**ERROR**: Ciddi sorunlara yönelik hata mesajları (başarısız işlemler, istisnalar)
**CRITICAL**: Acil müdahale gerektiren sistem arızalarına yönelik kritik mesajlar

#### Mesaj Formatı
```python
# Good - includes context
logger.info(f"Processing document: {doc_id}, size: {doc_size} bytes")
logger.error(f"Failed to connect to database: {error}", exc_info=True)

# Avoid - lacks context
logger.info("Processing document")
logger.error("Connection failed")
```

#### Performans Hususları
```python
# Use lazy formatting for expensive operations
logger.debug("Expensive operation result: %s", expensive_function())

# Check log level for very expensive debug operations
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"Debug data: {debug_data}")
```

### 6. Loki ile Yapılandırılmış Günlüğe Kayıt

Karmaşık veriler için, Loki için ek etiketlerle yapılandırılmış günlüğe kaydı kullanın:

```python
logger.info("Request processed", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'success'
    }
})
```

Bu etiketler, otomatik etiketlerin yanı sıra, Loki'de aranabilir etiketler haline gelir:
`severity` - Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
`logger` - Modül adı (`__name__`'den)

### 7. İstisna Kaydı

İstisnalar için her zaman yığın izlerini ekleyin:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"Failed to process data: {e}", exc_info=True)
    raise
```

### 8. Asenkron Kayıt (Logging) Hususları

Kayıt sistemi, Loki için engellemeyen, kuyruklu işleyiciler kullanır:
Konsol çıktısı senkron (hızlıdır)
Loki çıktısı, 500 mesajlık bir arabellekle kuyruğa alınır
Arka plan iş parçacığı, Loki iletimini yönetir
Ana uygulama kodunun engellenmesi olmaz

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    # Logging is thread-safe and won't block async operations
    logger.info(f"Starting async operation in task: {asyncio.current_task().get_name()}")
```

## Loki Entegrasyonu

### Mimari

Günlük sistemi, engellemeyen Loki entegrasyonu için Python'un yerleşik `QueueHandler` ve `QueueListener` özelliklerini kullanır:

1. **QueueHandler**: Günlükler, 500 mesajlık bir kuyruğa (engellemesiz) yerleştirilir.
2. **Arka Plan İş Parçacığı**: QueueListener, günlükleri Loki'ye asenkron olarak gönderir.
3. **Usulüne Uygun Bozulma**: Loki kullanılamıyorsa, konsol günlüğü devam eder.

### Otomatik Etiketler

Loki'ye gönderilen her günlük şunları içerir:
`processor`: İşlemci kimliği (örneğin, `config-svc`, `text-completion`, `embeddings`)
`severity`: Günlük seviyesi (DEBUG, INFO, vb.)
`logger`: Modül adı (örneğin, `trustgraph.gateway.service`, `trustgraph.agent.react.service`)

### Özel Etiketler

Özel etiketleri `extra` parametresi aracılığıyla ekleyin:

```python
logger.info("User action", extra={
    'tags': {
        'user_id': user_id,
        'action': 'document_upload',
        'collection': collection_name
    }
})
```

### Loki'de Logları Sorgulama

```logql
# All logs from a specific processor (recommended - matches Prometheus metrics)
{processor="config-svc"}
{processor="text-completion"}
{processor="embeddings"}

# Error logs from a specific processor
{processor="config-svc", severity="ERROR"}

# Error logs from all processors
{severity="ERROR"}

# Logs from a specific processor with text filter
{processor="text-completion"} |= "Processing"

# All logs from API gateway
{processor="api-gateway"}

# Logs from processors matching pattern
{processor=~".*-completion"}

# Logs with custom tags
{processor="api-gateway"} | json | user_id="12345"
```

### Zarif Bozulma

Eğer Loki kullanılamıyorsa veya `python-logging-loki` yüklü değilse:
Uyarı mesajı konsola yazdırılır
Konsol kaydı normal şekilde devam eder
Uygulama çalışmaya devam eder
Loki bağlantısı için tekrar deneme mantığı yoktur (hızlı bir şekilde başarısız olun, zarif bir şekilde bozulun)

## Test

Testler sırasında, farklı bir kayıt yapılandırması kullanmayı düşünün:

```python
# In test setup
import logging

# Reduce noise during tests
logging.getLogger().setLevel(logging.WARNING)

# Or disable Loki for tests
setup_logging({'log_level': 'WARNING', 'loki_enabled': False})
```

## İzleme Entegrasyonu

### Standart Format
Tüm günlükler tutarlı bir formata sahiptir:
```
2025-01-09 10:30:45,123 - trustgraph.gateway.service - INFO - Request processed
```

Biçim öğeleri:
Zaman damgası (milisaniyelerle birlikte ISO formatı)
Kayıt yöneticisi adı (modül yolu)
Kayıt düzeyi
Mesaj

### İzleme için Loki Sorguları

Yaygın izleme sorguları:

```logql
# Error rate by processor
rate({severity="ERROR"}[5m]) by (processor)

# Top error-producing processors
topk(5, count_over_time({severity="ERROR"}[1h]) by (processor))

# Recent errors with processor name
{severity="ERROR"} | line_format "{{.processor}}: {{.message}}"

# All agent processors
{processor=~".*agent.*"} |= "exception"

# Specific processor error count
count_over_time({processor="config-svc", severity="ERROR"}[1h])
```

## Güvenlik Hususları

**Hassas bilgileri asla kaydetmeyin** (şifreler, API anahtarları, kişisel veriler, token'lar)
**Kayıt işleminden önce kullanıcı girişini temizleyin**
**Hassas alanlar için yer tutucular kullanın**: `user_id=****1234`
**Loki kimlik doğrulaması**: Güvenli dağıtımlar için `--loki-username` ve `--loki-password`'i kullanın
**Güvenli taşıma**: Üretimde Loki URL'si için HTTPS kullanın: `https://loki.prod:3100/loki/api/v1/push`

## Bağımlılıklar

Merkezi günlük kaydı modülü şunları gerektirir:
`python-logging-loki` - Loki entegrasyonu için (isteğe bağlı, eksikse sorunsuz bir şekilde çalışır)

Zaten `trustgraph-base/pyproject.toml` ve `requirements.txt` içinde bulunmaktadır.

## Geçiş Yolu

Mevcut kod için:

1. **AsyncProcessor kullanan hizmetler**: Herhangi bir değişiklik gerekmez, Loki desteği otomatik olarak sağlanır
2. **AsyncProcessor kullanmayan hizmetler** (api-gateway, mcp-server): Zaten güncellenmiştir
3. **CLI araçları**: Kapsam dışındadır - print() veya basit günlük kaydını kullanmaya devam edin

### print()'ten günlük kaydına:
```python
# Before
print(f"Processing document {doc_id}")

# After
logger = logging.getLogger(__name__)
logger.info(f"Processing document {doc_id}")
```

## Yapılandırma Özeti

| Argüman | Varsayılan Değer | Ortam Değişkeni | Açıklama |
|----------|---------|---------------------|-------------|
| `--log-level` | `INFO` | - | Konsol ve Loki log seviyesi |
| `--loki-enabled` | `True` | - | Loki log kaydını etkinleştir |
| `--loki-url` | `http://loki:3100/loki/api/v1/push` | `LOKI_URL` | Loki push endpoint'i |
| `--loki-username` | `None` | `LOKI_USERNAME` | Loki kimlik doğrulama kullanıcı adı |
| `--loki-password` | `None` | `LOKI_PASSWORD` | Loki kimlik doğrulama parolası |
