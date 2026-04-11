# Cassandra Yapılandırma Birleştirme: Teknik Özellikler

**Durum:** Taslak
**Yazar:** Yardımcı
**Tarih:** 2024-09-03

## Genel Bakış

Bu özellik, TrustGraph kod tabanındaki Cassandra bağlantı parametreleri için tutarsız adlandırma ve yapılandırma kalıplarını ele almaktadır. Şu anda, iki farklı parametre adlandırma şeması bulunmaktadır (`cassandra_*` ve `graph_*`), bu da kafa karışıklığına ve bakım karmaşıklığına yol açmaktadır.

## Sorun Tanımı

Kod tabanı şu anda iki farklı Cassandra yapılandırma parametre seti kullanmaktadır:

1. **Bilgi/Yapılandırma/Kütüphane modülleri** aşağıdaki parametreleri kullanır:
   `cassandra_host` (sunucu listesi)
   `cassandra_user`
   `cassandra_password`

2. **Grafik/Depolama modülleri** aşağıdaki parametreleri kullanır:
   `graph_host` (tek bir sunucu, bazen listeye dönüştürülür)
   `graph_username`
   `graph_password`

3. **Tutarsız komut satırı kullanımı**:
   Bazı işleme birimleri (örneğin, `kg-store`), Cassandra ayarlarını komut satırı argümanları olarak sunmaz
   Diğer işleme birimleri bunları farklı adlar ve formatlarla sunar
   Yardım metni, ortam değişkeni varsayılanlarını yansıtmaz

Her iki parametre seti de aynı Cassandra kümesine bağlanır, ancak farklı adlandırma kuralları kullanır, bu da şunlara neden olur:
Kullanıcılar için yapılandırma karışıklığı
Artan bakım yükü
Tutarsız dokümantasyon
Yanlış yapılandırma riski
Bazı işleme birimlerinde ayarları komut satırı aracılığıyla geçersiz kılma imkansızlığı

## Önerilen Çözüm

### 1. Parametre Adlarını Standartlaştırın

Tüm modüller, tutarlı `cassandra_*` parametre adlarını kullanacaktır:
`cassandra_host` - Sunucu listesi (içeride liste olarak saklanır)
`cassandra_username` - Kimlik doğrulama için kullanıcı adı
`cassandra_password` - Kimlik doğrulama için parola

### 2. Komut Satırı Argümanları

TÜM işleme birimleri, Cassandra yapılandırmasını komut satırı argümanları aracılığıyla sunmalıdır:
`--cassandra-host` - Virgülle ayrılmış sunucu listesi
`--cassandra-username` - Kimlik doğrulama için kullanıcı adı
`--cassandra-password` - Kimlik doğrulama için parola

### 3. Ortam Değişkeni Geri Düşüşü

Komut satırı parametreleri açıkça sağlanmadığında, sistem ortam değişkenlerini kontrol edecektir:
`CASSANDRA_HOST` - Virgülle ayrılmış sunucu listesi
`CASSANDRA_USERNAME` - Kimlik doğrulama için kullanıcı adı
`CASSANDRA_PASSWORD` - Kimlik doğrulama için parola

### 4. Varsayılan Değerler

Ne komut satırı parametreleri ne de ortam değişkenleri belirtilmediğinde:
`cassandra_host`, `["cassandra"]`'e varsayılan olarak ayarlanır
`cassandra_username`, `None`'e (kimlik doğrulama yok) varsayılan olarak ayarlanır
`cassandra_password`, `None`'e (kimlik doğrulama yok) varsayılan olarak ayarlanır

### 5. Yardım Metni Gereksinimleri

`--help` çıktısı şunları içermelidir:
Ortam değişkeni değerleri ayarlandığında, bunları varsayılan değerler olarak göstermelidir
Parola değerlerini asla göstermemelidir (bunun yerine `****` veya `<set>` göstermelidir)
Çözüm sırasını yardım metninde açıkça belirtmelidir

Örnek yardım çıktısı:
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## Uygulama Detayları

### Parametre Çözümleme Sırası

Her Cassandra parametresi için, çözümleme sırası aşağıdaki olacaktır:
1. Komut satırı argümanı değeri
2. Ortam değişkeni (`CASSANDRA_*`)
3. Varsayılan değer

### Ana Bilgisayar Parametreleri Yönetimi

`cassandra_host` parametresi:
Komut satırı, virgülle ayrılmış bir dize kabul eder: `--cassandra-host "host1,host2,host3"`
Ortam değişkeni, virgülle ayrılmış bir dize kabul eder: `CASSANDRA_HOST="host1,host2,host3"`
İçeride her zaman bir liste olarak saklanır: `["host1", "host2", "host3"]`
Tek bir ana bilgisayar: `"localhost"` → `["localhost"]`'e dönüştürülür
Zaten bir liste: `["host1", "host2"]` → olduğu gibi kullanılır

### Kimlik Doğrulama Mantığı

Kimlik doğrulama, hem `cassandra_username` hem de `cassandra_password` sağlandığında kullanılacaktır:
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## Değiştirilecek Dosyalar

### `graph_*` parametrelerini kullanan modüller (değiştirilecek):
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### `cassandra_*` parametrelerini kullanan modüller (ortam değişkeni geri dönüşü ile güncellenecek):
`trustgraph-flow/trustgraph/tables/config.py`
`trustgraph-flow/trustgraph/tables/knowledge.py`
`trustgraph-flow/trustgraph/tables/library.py`
`trustgraph-flow/trustgraph/storage/knowledge/store.py`
`trustgraph-flow/trustgraph/cores/knowledge.py`
`trustgraph-flow/trustgraph/librarian/librarian.py`
`trustgraph-flow/trustgraph/librarian/service.py`
`trustgraph-flow/trustgraph/config/service/service.py`
`trustgraph-flow/trustgraph/cores/service.py`

### Güncellenecek Test Dosyaları:
`tests/unit/test_cores/test_knowledge_manager.py`
`tests/unit/test_storage/test_triples_cassandra_storage.py`
`tests/unit/test_query/test_triples_cassandra_query.py`
`tests/integration/test_objects_cassandra_integration.py`

## Uygulama Stratejisi

### Aşama 1: Ortak Yapılandırma Yardımcı Programı Oluşturma
Tüm işlemcilerde Cassandra yapılandırmasını standartlaştırmak için yardımcı işlevler oluşturun:

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### 2. Aşama: `graph_*` Parametrelerini Kullanan Modülleri Güncelleme
1. Parametre adlarını `graph_*`'dan `cassandra_*`'e değiştirin.
2. Özel `add_args()` yöntemlerini standart `add_cassandra_args()` yöntemleriyle değiştirin.
3. Ortak yapılandırma yardımcı fonksiyonlarını kullanın.
4. Dokümantasyon metinlerini güncelleyin.

Örnek dönüşüm:
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### 3. Aşama: `cassandra_*` Parametrelerini Kullanarak Modülleri Güncelleme
1. Eksik olan yerlerde komut satırı argümanı desteğini ekleyin (örneğin, `kg-store`)
2. Mevcut argüman tanımlarını `add_cassandra_args()` ile değiştirin
3. Tutarlı çözümleme için `resolve_cassandra_config()`'ı kullanın
4. Tutarlı ana bilgisayar listesi işleme sağlayın

### 4. Aşama: Testleri ve Belgeleri Güncelleme
1. Tüm test dosyalarını yeni parametre adlarını kullanacak şekilde güncelleyin
2. Komut satırı (CLI) belgelerini güncelleyin
3. API belgelerini güncelleyin
4. Ortam değişkeni belgelerini ekleyin

## Geriye Dönük Uyumluluk

Geçiş sırasında geriye dönük uyumluluğu korumak için:

1. `graph_*` parametreleri için **kullanımdan kaldırma uyarıları**
2. **Parametre takma adları** - başlangıçta hem eski hem de yeni adları kabul edin
3. **Aşamalı dağıtım** birden fazla sürümde
4. **Belge güncellemeleri** ve geçiş kılavuzu

Örnek geriye dönük uyumluluk kodu:
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## Test Stratejisi

1. **Birim testleri**, yapılandırma çözümleme mantığı için
2. **Entegrasyon testleri**, çeşitli yapılandırma kombinasyonlarıyla
3. **Ortam değişkeni testleri**
4. **Geriye dönük uyumluluk testleri**, kullanımdan kaldırılmış parametrelerle
5. **Docker compose testleri**, ortam değişkenleriyle

## Dokümantasyon Güncellemeleri

1. Tüm CLI komutu dokümantasyonunu güncelleyin
2. API dokümantasyonunu güncelleyin
3. Geçiş kılavuzu oluşturun
4. Docker compose örneklerini güncelleyin
5. Yapılandırma referans dokümantasyonunu güncelleyin

## Riskler ve Azaltma

| Risk | Etki | Azaltma |
|------|--------|------------|
| Kullanıcılar için bozucu değişiklikler | Yüksek | Geriye dönük uyumluluk süresi uygulayın |
| Geçiş sırasında yapılandırma karışıklığı | Orta | Açık dokümantasyon ve kullanımdan kaldırma uyarıları |
| Test hataları | Orta | Kapsamlı test güncellemeleri |
| Docker dağıtım sorunları | Yüksek | Tüm Docker compose örneklerini güncelleyin |

## Başarı Kriterleri

[ ] Tüm modüller, tutarlı `cassandra_*` parametre adlarını kullanır
[ ] Tüm işlemciler, Cassandra ayarlarını komut satırı argümanları aracılığıyla sunar
[ ] Komut satırı yardım metni, ortam değişkeni varsayılanlarını gösterir
[ ] Parola değerleri, yardım metninde asla görüntülenmez
[ ] Ortam değişkeni yedeklemesi doğru şekilde çalışır
[ ] `cassandra_host`, dahili olarak tutarlı bir şekilde bir liste olarak işlenir
[ ] Geriye dönüştürülebilirlik, en az 2 sürüm için korunur
[ ] Tüm testler, yeni yapılandırma sistemiyle geçer
[ ] Dokümantasyon tamamen güncellenmiştir
[ ] Docker compose örnekleri, ortam değişkenleriyle çalışır

## Zaman Çizelgesi

**1. Hafta:** Ortak yapılandırma yardımcı programını uygulayın ve `graph_*` modüllerini güncelleyin
**2. Hafta:** Mevcut `cassandra_*` modüllerine ortam değişkeni desteği ekleyin
**3. Hafta:** Testleri ve dokümantasyonu güncelleyin
**4. Hafta:** Entegrasyon testi ve hata düzeltmeleri

## Gelecek Hususlar

Bu kalıbı diğer veritabanı yapılandırmalarına (örneğin, Elasticsearch) genişletmeyi düşünün
Yapılandırma doğrulama ve daha iyi hata mesajları uygulayın
Cassandra bağlantı havuzu yapılandırması desteği ekleyin
Yapılandırma dosyası desteği eklemeyi düşünün (.env dosyaları)