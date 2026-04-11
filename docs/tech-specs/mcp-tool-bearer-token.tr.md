# MCP Aracı Taşıyıcı (Bearer) Token Doğrulama Özelliği Belirtimi

> **⚠️ ÖNEMLİ: YALNIZCA TEK-KİRACI (SINGLE-TENANT) ORTAMLAR İÇİN**
>
> Bu belirtim, MCP araçları için temel, hizmet seviyesinde bir doğrulama mekanizmasını açıklamaktadır. Bu, **TAMAMLANMIŞ** bir doğrulama çözümü değildir ve aşağıdaki durumlar için **UYGUN DEĞİL**:
> - Çok kullanıcılı ortamlar
> - Çok kiracılı (multi-tenant) dağıtımlar
> - Federasyonlu doğrulama
> - Kullanıcı bağlamı yayılımı
> - Kullanıcı bazlı yetkilendirme
>
> Bu özellik, her MCP aracı için **tek bir statik token** sağlar ve bu token tüm kullanıcılar ve oturumlar arasında paylaşılır. Kullanıcı bazlı veya kiracı bazlı doğrulama gerekiyorsa, bu çözüm uygun değildir.

## Genel Bakış
**Özellik Adı**: MCP Aracı Taşıyıcı (Bearer) Token Doğrulama Desteği
**Yazar**: Claude Code Assistant
**Tarih**: 2025-11-11
**Durum**: Geliştirme Aşamasında

### Yönetici Özeti

MCP araçlarının, korumalı MCP sunucularıyla kimlik doğrulaması yapmak için isteğe bağlı taşıyıcı (bearer) token'lar belirtmesine olanak tanıyın. Bu, TrustGraph'ın, kimlik doğrulaması gerektiren sunucularda barındırılan MCP araçlarını, aracının veya araç çağrı arayüzlerinin değiştirilmesi olmadan güvenli bir şekilde çağırmasını sağlar.

**ÖNEMLİ**: Bu, tek kiracılı, hizmetten hizmete doğrulama senaryoları için tasarlanmış temel bir doğrulama mekanizmasıdır. Aşağıdaki durumlar için **UYGUN DEĞİL**:
Farklı kullanıcıların farklı kimlik bilgilerine ihtiyaç duyduğu çok kullanıcılı ortamlar
Kiracı başına izolasyon gerektiren çok kiracılı dağıtımlar
Federasyonlu doğrulama senaryoları
Kullanıcı seviyesinde doğrulama veya yetkilendirme
Dinamik kimlik bilgisi yönetimi veya token yenileme

Bu özellik, her MCP aracı yapılandırması için statik, sistem genelinde bir taşıyıcı (bearer) token sağlar ve bu token, o aracın tüm kullanıcıları ve çağrıları tarafından paylaşılır.

### Sorun Tanımı

Şu anda, MCP araçları yalnızca herkese açık olarak erişilebilir MCP sunucularına bağlanabilir. Birçok üretim MCP dağıtımı, güvenlik için taşıyıcı (bearer) token'lar aracılığıyla kimlik doğrulaması gerektirir. Kimlik doğrulama desteği olmadan:
MCP araçları, güvenli MCP sunucularına bağlanamaz
Kullanıcılar ya MCP sunucularını herkese açık hale getirmeli ya da ters vekil (reverse proxy) uygulamalıdır
MCP bağlantılarına kimlik bilgilerini iletmenin standart bir yolu yoktur
MCP uç noktalarında güvenlik en iyi uygulamaları uygulanamaz

### Hedefler

[ ] MCP araç yapılandırmalarının isteğe bağlı `auth-token` parametresini belirtmesine izin verin
[ ] MCP araç hizmetini, MCP sunucularına bağlanırken taşıyıcı (bearer) token'ları kullanacak şekilde güncelleyin
[ ] CLI araçlarını, kimlik doğrulama token'larını ayarlama/görüntüleme özelliğini destekleyecek şekilde güncelleyin
[ ] Kimlik doğrulaması olmayan MCP yapılandırmalarıyla geriye dönük uyumluluğu koruyun
[ ] Token depolama için güvenlik hususlarını belgeleyin

### Hedef Dışı Kalanlar
Dinamik token yenileme veya OAuth akışları (yalnızca statik token'lar)
Depolanmış token'ların şifrelenmesi (yapılandırma sistemi güvenliği kapsam dışındadır)
Alternatif doğrulama yöntemleri (Temel kimlik doğrulama, API anahtarları, vb.)
Token doğrulama veya son kullanma kontrolü
**Kullanıcı başına doğrulama**: Bu özellik, kullanıcıya özel kimlik bilgilerini desteklemez
**Kiracı izolasyonu**: Bu özellik, kiracı başına token yönetimi sağlamaz
**Federasyonlu doğrulama**: Bu özellik, kimlik sağlayıcılarıyla (SSO, OAuth, SAML, vb.) entegre olmaz
**Bağlama duyarlı doğrulama**: Token'lar, kullanıcı bağlamına veya oturuma göre iletilmez

## Arka Plan ve Bağlam

### Mevcut Durum
MCP araç yapılandırmaları, `mcp` yapılandırma grubunda aşağıdaki yapıya sahip olarak saklanır:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

MCP aracı hizmeti, `streamablehttp_client(url)` kullanarak sunuculara bağlanır ve herhangi bir kimlik doğrulama başlığı kullanmaz.

### Sınırlamalar

**Mevcut Sistem Sınırlamaları:**
1. **Kimlik doğrulama desteği yok:** Güvenli MCP sunucularına bağlanılamaz.
2. **Güvenlik açığı:** MCP sunucuları, yalnızca ağ seviyesinde güvenlik kullanılarak genel olarak erişilebilir olmalıdır.
3. **Üretim dağıtım sorunları:** API uç noktaları için güvenlik en iyi uygulamalarını takip edilemez.

**Bu Çözümün Sınırlamaları:**
1. **Yalnızca tek kiracı:** Her MCP aracı için tek bir statik belirteç, tüm kullanıcılar arasında paylaşılır.
2. **Kullanıcı başına kimlik bilgileri yok:** Farklı kullanıcılar olarak kimlik doğrulaması yapılamaz veya kullanıcı bağlamı geçirilemez.
3. **Çok kiracılı destek yok:** Kimlik bilgilerini kiracı veya kuruluş başına izole etmek mümkün değildir.
4. **Yalnızca statik belirteçler:** Belirteç yenileme, döndürme veya son kullanma süresi yönetimi desteği yoktur.
5. **Hizmet seviyesi kimlik doğrulaması:** Bireysel kullanıcılar yerine TrustGraph hizmetini doğrular.
6. **Paylaşılan güvenlik bağlamı:** Bir MCP aracının tüm çağrıları aynı kimlik bilgisini kullanır.

### Kullanım Alanı Uygunluğu

**✅ Uygun Kullanım Alanları:**
Tek kiracılı TrustGraph dağıtımları
Hizmetten hizmete kimlik doğrulama (TrustGraph → MCP Sunucusu)
Geliştirme ve test ortamları
TrustGraph sistemi tarafından erişilen dahili MCP araçları
Tüm kullanıcıların aynı MCP aracı erişim düzeyini paylaştığı senaryolar
Statik, uzun ömürlü hizmet kimlik bilgileri

**❌ Uygun Olmayan Kullanım Alanları:**
Kullanıcı başına kimlik doğrulama gerektiren çok kullanıcılı sistemler
Kiracı izolasyonu gereksinimleri olan çok kiracılı SaaS dağıtımları
Federasyon kimlik doğrulama senaryoları (SSO, OAuth, SAML)
MCP sunucularına kullanıcı bağlamının iletilmesi gereken sistemler
Dinamik belirteç yenileme veya kısa ömürlü belirteçler gerektiren ortamlar
Farklı kullanıcıların farklı izin düzeylerine ihtiyaç duyduğu uygulamalar
Kullanıcı seviyesinde denetim izleri için uyumluluk gereksinimleri

**Örnek Uygun Senaryo:**
Tüm çalışanların aynı dahili MCP aracını (örneğin, şirket veritabanı sorgusu) kullandığı tek organizasyonlu bir TrustGraph dağıtımı. MCP sunucusunun harici erişimi önlemek için kimlik doğrulama gerektirmesi, ancak tüm dahili kullanıcıların aynı erişim düzeyine sahip olması.

**Örnek Uygun Olmayan Senaryo:**
Kiracı A ve Kiracı B'nin her birinin ayrı kimlik bilgileriyle kendi izole MCP sunucularına erişmesi gereken çok kiracılı bir TrustGraph SaaS platformu. Bu özellik, kiracı başına belirteç yönetimi DEĞİLDİR.

### İlgili Bileşenler
**trustgraph-flow/trustgraph/agent/mcp_tool/service.py**: MCP aracı çağrı hizmeti
**trustgraph-cli/trustgraph/cli/set_mcp_tool.py**: MCP yapılandırmalarını oluşturmak/güncellemek için CLI aracı
**trustgraph-cli/trustgraph/cli/show_mcp_tools.py**: MCP yapılandırmalarını görüntülemek için CLI aracı
**MCP Python SDK**: `streamablehttp_client` from `mcp.client.streamable_http`

## Gereksinimler

### Fonksiyonel Gereksinimler

1. **MCP Yapılandırma Kimlik Doğrulama Belirteci**: MCP aracı yapılandırmaları, isteğe bağlı bir `auth-token` alanı DESTEKLEMELİDİR.
2. **Bearer Belirteç Kullanımı**: MCP aracı hizmeti, kimlik doğrulama belirteci yapılandırıldığında `Authorization: Bearer {token}` başlığını GÖNDERMELİDİR.
3. **CLI Desteği**: `tg-set-mcp-tool`, isteğe bağlı bir `--auth-token` parametresi KABUL ETMELİDİR.
4. **Belirteç Görüntüleme**: `tg-show-mcp-tools`, kimlik doğrulama belirtecinin yapılandırıldığını GÖSTERMELİDİR (güvenlik için gizlenmiş).
5. **Geriye Dönük Uyumluluk**: Kimlik doğrulama belirteci olmayan mevcut MCP aracı yapılandırmaları çalışmaya DEVAM ETMELİDİR.

### Fonksiyonel Olmayan Gereksinimler
1. **Geriye Dönük Uyumluluk**: Mevcut MCP aracı yapılandırmaları için hiçbir bozucu değişiklik olmamalıdır.
2. **Performans**: MCP aracı çağrısı üzerinde önemli bir performans etkisi olmamalıdır.
3. **Güvenlik**: Belirteçler yapılandırmada saklanır (güvenlik etkilerini belgeleyin).

### Kullanıcı Hikayeleri

1. Bir **DevOps mühendisi** olarak, MCP sunucusu uç noktalarını güvence altına almak için MCP araçları için taşıyıcı belirteçleri yapılandırmak istiyorum.
2. Bir **CLI kullanıcısı** olarak, korumalı sunuculara bağlanabilmem için MCP araçları oluştururken kimlik doğrulama belirteçleri ayarlamak istiyorum.
3. Bir **sistem yöneticisi** olarak, hangi MCP araçlarının kimlik doğrulamasının yapılandırıldığını görmek istiyorum, böylece güvenlik ayarlarını denetleyebilirim.

## Tasarım

### Yüksek Seviyeli Mimari
Taşıyıcı belirteç kimlik doğrulaması desteği için MCP aracı yapılandırmasını ve hizmetini genişletin:
1. MCP aracı yapılandırma şemasına isteğe bağlı bir `auth-token` alanı ekleyin.
2. Kimlik doğrulama belirteci yapılandırıldığında, MCP aracı hizmetinin kimlik doğrulama belirteci okuyup HTTP istemcisine iletmesini sağlayın.
3. Kimlik doğrulama belirteçleri ayarlamak ve görüntülemek için CLI araçlarını güncelleyin.
4. Güvenlik hususlarını ve en iyi uygulamaları belgeleyin.

### Yapılandırma Şeması

**Mevcut Şema**:
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

**Yeni Şema** (isteğe bağlı kimlik doğrulama jetonu ile):
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api",
  "auth-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Alan Açıklamaları**:
`remote-name` (isteğe bağlı): MCP sunucusu tarafından kullanılan isim (varsayılan olarak yapılandırma anahtarı)
`url` (gerekli): MCP sunucusu uç noktası URL'si
`auth-token` (isteğe bağlı): Kimlik doğrulama için kullanılan taşıyıcı belirteci

### Veri Akışı

1. **Yapılandırma Depolama**: Kullanıcı `tg-set-mcp-tool --id my-tool --tool-url http://server/api --auth-token xyz123`'ı çalıştırır
2. **Yapılandırma Yükleme**: MCP aracı hizmeti, `on_mcp_config()` geri çağırması aracılığıyla yapılandırma güncellemelerini alır
3. **Araç Çağrısı**: Araç çağrıldığında:
   Hizmet, yapılandırmadan `auth-token`'ı okur (varsa)
   Başlıklar sözlüğünü oluşturur: `{"Authorization": "Bearer {token}"}`
   Başlıkları `streamablehttp_client(url, headers=headers)`'a iletir
   MCP sunucusu belirteci doğrular ve isteği işler

### API Değişiklikleri
Harici API değişiklikleri yok - yalnızca yapılandırma şeması uzantısı.

### Bileşen Detayları

#### Bileşen 1: service.py (MCP Aracı Hizmeti)
**Dosya**: `trustgraph-flow/trustgraph/agent/mcp_tool/service.py`

**Amaç**: Uzak sunuculardaki MCP araçlarını çağırmak

**Gerekli Değişiklikler** (`invoke_tool()` yönteminde):
1. `auth-token`'ın `self.mcp_services[name]` yapılandırmasında olup olmadığını kontrol edin
2. Belirteç varsa, Authorization başlığıyla başlıklar sözlüğünü oluşturun
3. Başlıkları `streamablehttp_client(url, headers=headers)`'a iletin

**Mevcut Kod** (42-89 satırları):
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server
        async with streamablehttp_client(url) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method
```

**Değiştirilmiş Kod:**
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        # Build headers with optional bearer token
        headers = {}
        if "auth-token" in self.mcp_services[name]:
            token = self.mcp_services[name]["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server with headers
        async with streamablehttp_client(url, headers=headers) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method (unchanged)
```

#### Bileşen 2: set_mcp_tool.py (CLI Yapılandırma Aracı)
**Dosya**: `trustgraph-cli/trustgraph/cli/set_mcp_tool.py`

**Amaç**: MCP aracı yapılandırmalarını oluşturma/güncelleme

**Gerekli Değişiklikler**:
1. `--auth-token` isteğe bağlı argümanı argparse'a ekleyin
2. Sağlandığında, `auth-token`'yi yapılandırma JSON'una dahil edin

**Mevcut Argümanlar**:
`--id` (gerekli): MCP aracı tanımlayıcısı
`--remote-name` (isteğe bağlı): Uzak MCP aracı adı
`--tool-url` (gerekli): MCP aracı URL uç noktası
`-u, --api-url` (isteğe bağlı): TrustGraph API URL'si

**Yeni Argüman**:
`--auth-token` (isteğe bağlı): Kimlik doğrulama için taşıyıcı belirteci

**Değiştirilmiş Yapılandırma Oluşturma**:
```python
# Build configuration object
config = {
    "url": args.tool_url,
}

if args.remote_name:
    config["remote-name"] = args.remote_name

if args.auth_token:
    config["auth-token"] = args.auth_token

# Store configuration
api.config().put([
    ConfigValue(type="mcp", key=args.id, value=json.dumps(config))
])
```

#### Bileşen 3: show_mcp_tools.py (CLI Görüntüleme Aracı)
**Dosya**: `trustgraph-cli/trustgraph/cli/show_mcp_tools.py`

**Amaç**: MCP araç yapılandırmalarını görüntülemek

**Gerekli Değişiklikler**:
1. Çıktı tablosuna "Auth" sütununu ekleyin
2. "auth-token" varlığına bağlı olarak "Evet" veya "Hayır" görüntüleyin
3. Gerçek token değerini görüntülemeyin (güvenlik)

**Mevcut Çıktı**:
```
ID          Remote Name    URL
----------  -------------  ------------------------
my-tool     my-tool        http://server:3000/api
```

**Yeni Çıktı**:
```
ID          Remote Name    URL                      Auth
----------  -------------  ------------------------ ------
my-tool     my-tool        http://server:3000/api   Yes
other-tool  other-tool     http://other:3000/api    No
```

#### Bileşen 4: Belgeler
**Dosya**: `docs/cli/tg-set-mcp-tool.md`

**Gerekli Değişiklikler**:
1. Yeni `--auth-token` parametresini belgeleyin
2. Kimlik doğrulama ile örnek kullanım sağlayın
3. Güvenlik hususlarını belgeleyin

## Uygulama Planı

### Aşama 1: Teknik Özellikleri Oluşturma
[x] Tüm değişiklikleri belgeleyen kapsamlı bir teknik özellik yazın

### Aşama 2: MCP Araç Hizmetini Güncelleme
[ ] `service.py` içindeki `invoke_tool()`'ı, auth-token'ı yapılandırmadan okumak için değiştirin
[ ] Başlıklar sözlüğünü oluşturun ve `streamablehttp_client`'a iletin
[ ] Kimliği doğrulanmış bir MCP sunucusuyla test edin

### Aşama 3: CLI Araçlarını Güncelleme
[ ] `set_mcp_tool.py`'e `--auth-token` argümanını ekleyin
[ ] auth-token'ı yapılandırma JSON'unda dahil edin
[ ] `show_mcp_tools.py` çıktısına "Auth" sütununu ekleyin
[ ] CLI araç değişikliklerini test edin

### Aşama 4: Belgeleri Güncelleme
[ ] `tg-set-mcp-tool.md` içindeki `--auth-token` parametresini belgeleyin
[ ] Güvenlik hususları bölümünü ekleyin
[ ] Örnek kullanım sağlayın

### Aşama 5: Test
[ ] MCP aracının auth-token ile başarıyla bağlandığını test edin
[ ] Geriye dönük uyumluluğu test edin (auth-token olmadan çalışan araçlar)
[ ] CLI araçlarının auth-token'ı doğru şekilde kabul ettiğini ve depoladığını test edin
[ ] "show" komutunun auth durumunu doğru şekilde gösterdiğini test edin

### Kod Değişiklikleri Özeti
| Dosya | Değişiklik Türü | Satırlar | Açıklama |
|------|------------|-------|-------------|
| `service.py` | Değiştirildi | ~52-66 | auth-token okuma ve başlık oluşturma ekleyin |
| `set_mcp_tool.py` | Değiştirildi | ~30-60 | --auth-token argümanı ve yapılandırma depolama ekleyin |
| `show_mcp_tools.py` | Değiştirildi | ~40-70 | Görüntüleme için "Auth" sütununu ekleyin |
| `tg-set-mcp-tool.md` | Değiştirildi | Çeşitli | Yeni parametreyi belgeleyin |

## Test Stratejisi

### Birim Testleri
**Auth Token Okuma**: `invoke_tool()`'ın auth-token'ı yapılandırmadan doğru şekilde okuduğunu test edin
**Başlık Oluşturma**: Authorization başlığının Bearer öneki ile doğru şekilde oluşturulduğunu test edin
**Geriye Dönük Uyumluluk**: auth-token olmadan çalışan araçların değişmeden çalıştığını test edin
**CLI Argümanı Ayrıştırma**: `--auth-token` argümanının doğru şekilde ayrıştırıldığını test edin

### Entegrasyon Testleri
**Kimliği Doğrulanmış Bağlantı**: MCP araç hizmetinin kimliği doğrulanmış bir sunucuya bağlandığını test edin
**Uçtan Uca**: CLI → yapılandırma depolama → auth token ile hizmet çağrısını test edin
**Token Gerekli Değil**: Kimliği doğrulanmamış bir sunucuya bağlantının hala çalıştığını test edin

### Manuel Testler
**Gerçek MCP Sunucusu**: bearer token kimlik doğrulaması gerektiren gerçek bir MCP sunucusuyla test edin
**CLI İş Akışı**: Tam iş akışını test edin: aracı auth ile yapılandır → aracı çağır → başarıyı doğrulayın
**Görüntü Maskeleme**: auth durumunun gösterildiğini ancak token değerinin görünmediğini doğrulayın

## Göç ve Dağıtım

### Göç Stratejisi
Göç gerektirmez - bu tamamen ek bir işlevsellik:
`auth-token` içermeyen mevcut MCP araç yapılandırmaları çalışmaya devam eder
Yeni yapılandırmalar isteğe bağlı olarak `auth-token` alanını içerebilir
CLI araçları `--auth-token` parametresini kabul eder, ancak gerektirmez

### Dağıtım Planı
1. **Aşama 1**: Temel hizmet değişikliklerini geliştirme/hazırlık ortamına dağıtın
2. **Aşama 2**: CLI araç güncellemelerini dağıtın
3. **Aşama 3**: Belgeleri güncelleyin
4. **Aşama 4**: İzleme ile üretim dağıtımı

### Geri Alma Planı
Temel değişiklikler geriye dönük uyumludur - mevcut araçlar etkilenmez
Sorunlar ortaya çıkarsa, auth-token işleme, başlık oluşturma mantığını kaldırarak devre dışı bırakılabilir
CLI değişiklikleri bağımsızdır ve ayrı olarak geri alınabilir

## Güvenlik Hususları

### ⚠️ Kritik Sınırlama: Yalnızca Tek Kiracılı Kimlik Doğrulama

**Bu kimlik doğrulama mekanizması, çok kullanıcılı veya çok kiracılı ortamlar için UYGUN DEĞİLDİR.**

**Paylaşılan kimlik bilgiler**: Tüm kullanıcılar ve çağrılar, her MCP aracı için aynı token'ı paylaşır
**Kullanıcı bağlamı yok**: MCP sunucusu, farklı TrustGraph kullanıcıları arasında ayrım yapamaz
**Kiracı yalıtımı yok**: Tüm kiracılar, her MCP aracı için aynı kimlik bilgilerini paylaşır
**Denetim izi sınırlaması**: MCP sunucusu, aynı kimlik bilgilerinden gelen tüm istekleri günlüğe kaydeder
**İzin kapsamı**: Farklı kullanıcılara farklı izin seviyeleri uygulanamaz

**Bu özelliği KULLANMAYIN eğer:**
TrustGraph dağıtımınız birden fazla kuruluşu (çok kiracılı) hizmet veriyorsa
Hangi kullanıcının hangi MCP aracına eriştiğini izlemeniz gerekiyorsa
Farklı kullanıcıların farklı izin seviyelerine ihtiyacı varsa
Kullanıcı düzeyinde denetim gereksinimlerine uymanız gerekiyorsa
MCP sunucunuz kullanıcı başına hız sınırlamaları veya kotaları uyguluyorsa

**Çok kullanıcılı/çok kiracılı senaryolar için alternatif çözümler:**
Özel başlıklar aracılığıyla kullanıcı bağlamı yayılımını uygulayın
Her kiracı için ayrı TrustGraph örnekleri dağıtın
Ağ seviyesinde izolasyon kullanın (VPC'ler, hizmet ağları)
Her kullanıcı için kimlik doğrulamayı yöneten bir ara katman uygulayın

### Token Depolama
**Risk**: Kimlik doğrulama jetonları yapılandırma sisteminde düz metin olarak saklanır

**Giderilmesi Gereken Durum:**
Jetonların şifrelenmeden saklandığını belgeleyin
Mümkün olduğunda kısa ömürlü jetonlar kullanılması önerin
Yapılandırma depolaması için uygun erişim kontrolü kullanılması önerin
Şifrelenmiş jeton depolama için gelecekteki bir iyileştirmeyi düşünün

### Jetonun Açığa Çıkarılması
**Risk**: Jetonlar günlüklerde veya CLI çıktısında açığa çıkabilir

**Giderilmesi Gereken Durum:**
Jeton değerlerini kaydetmeyin (sadece "kimlik doğrulama yapılandırıldı: evet/hayır" kaydını tutun)
CLI göster komutu yalnızca maskelenmiş durumu gösterir, gerçek jetonu göstermez
Jetonları hata mesajlarında dahil etmeyin

### Ağ Güvenliği
**Risk**: Jetonlar şifrelenmemiş bağlantılar üzerinden iletilir

**Giderilmesi Gereken Durum:**
MCP sunucuları için HTTPS URL'lerinin kullanılması önerisi belgelendirilmelidir
HTTP ile düz metin iletim riskine ilişkin kullanıcılara uyarı verilmelidir

### Yapılandırma Erişimi
**Risk**: Yapılandırma sistemine yetkisiz erişim, jetonları açığa çıkarır

**Giderilmesi Gereken Durum:**
Yapılandırma sistemi erişiminin güvenliğinin önemini belgeleyin
Yapılandırma erişimi için en az ayrıcalık ilkesi önerin
Yapılandırma değişiklikleri için denetim günlüğü almayı düşünün (gelecekteki iyileştirme)

### Çok Kullanıcılı Ortamlar
**Risk**: Çok kullanıcılı dağıtımlarda, tüm kullanıcılar aynı MCP kimlik bilgilerini paylaşır

**Riskin Anlaşılması:**
Kullanıcı A ve Kullanıcı B, bir MCP aracını kullanırken aynı jetonu kullanır
MCP sunucusu, farklı TrustGraph kullanıcıları arasında ayrım yapamaz
Kullanıcı başına izinleri veya hız sınırlamalarını uygulama imkanı yoktur
MCP sunucusundaki denetim günlükleri, aynı kimlik bilgilerinden gelen tüm istekleri gösterir
Bir kullanıcının oturumu tehlikeye girerse, saldırganın tüm kullanıcılar kadar aynı MCP erişimi vardır

**Bu bir hata DEĞİLDİR - bu tasarımın temel bir sınırlamasıdır.**

## Performans Etkisi
**Minimum ek yük**: Başlık oluşturma, ihmal edilebilir bir işlem süresi ekler
**Ağ etkisi**: Ek HTTP başlığı, istek başına yaklaşık 50-200 bayt ekler
**Bellek kullanımı**: Yapılandırmada jeton dizesini depolamak için ihmal edilebilir bir artış

## Belgeler

### Kullanıcı Belgeleri
[ ] `tg-set-mcp-tool.md`'ı `--auth-token` parametresiyle güncelleyin
[ ] Güvenlik hususları bölümü ekleyin
[ ] Bir örnek kullanım senaryosuyla birlikte taşıyıcı jetonu sağlayın
[ ] Jeton depolama etkilerini belgeleyin

### Geliştirici Belgeleri
[ ] `service.py` içindeki kimlik doğrulama jetonu işleme için satır içi yorumlar ekleyin
[ ] Başlık oluşturma mantığını belgeleyin
[ ] MCP aracı yapılandırma şeması belgelerini güncelleyin

## Açık Sorular
1. **Jeton şifreleme**: Yapılandırma sisteminde şifrelenmiş jeton depolamayı uygulamalı mıyız?
2. **Jeton yenileme**: OAuth yenileme akışları veya jeton rotasyonu için gelecekteki destek?
3. **Alternatif kimlik doğrulama yöntemleri**: Temel kimlik doğrulama, API anahtarları veya diğer yöntemleri desteklemeli miyiz?

## Değerlendirilen Alternatifler

1. **Jetonlar için ortam değişkenleri**: Jetonları yapılandırma yerine ortam değişkenlerinde saklayın
   **Reddedildi**: Dağıtımı ve yapılandırma yönetimini karmaşıklaştırır

2. **Ayrı gizli anahtar deposu**: Özel bir gizli anahtar yönetim sistemi kullanın
   **Erteleme**: Başlangıç uygulaması kapsamı dışındadır, gelecekteki bir iyileştirme olarak düşünün

3. **Çoklu kimlik doğrulama yöntemleri**: Temel, API anahtarı, OAuth vb. destekleyin
   **Reddedildi**: Taşıyıcı jetonlar çoğu kullanım durumunu kapsar, başlangıç uygulamasını basit tutun

4. **Şifrelenmiş jeton depolama**: Jetonları yapılandırma sisteminde şifreleyin
   **Erteleme**: Yapılandırma sistemi güvenliği daha geniş bir endişedir, gelecekteki çalışmalara bırakın

5. **Her çağrı için jetonlar**: Jetonların çağrı zamanında geçirilmesine izin verin
   **Reddedildi**: Endişe ayrımını ihlal eder, aracının kimlik bilgilerini işlemesi gerekmez

## Referanslar
[MCP Protokolü Özellikleri](https://github.com/modelcontextprotocol/spec)
[HTTP Taşıyıcı Kimlik Doğrulaması (RFC 6750)](https://tools.ietf.org/html/rfc6750)
[Mevcut MCP Aracı Hizmeti](../trustgraph-flow/trustgraph/agent/mcp_tool/service.py)
[MCP Aracı Argümanları Özellikleri](./mcp-tool-arguments.md)

## Ek

### Örnek Kullanım

**Kimlik doğrulama ile MCP aracının yapılandırılması:**
```bash
tg-set-mcp-tool \
  --id secure-tool \
  --tool-url https://secure-server.example.com/mcp \
  --auth-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**MCP araçlarını göster:**
```bash
tg-show-mcp-tools

ID            Remote Name   URL                                    Auth
-----------   -----------   ------------------------------------   ------
secure-tool   secure-tool   https://secure-server.example.com/mcp  Yes
public-tool   public-tool   http://localhost:3000/mcp              No
```

### Yapılandırma Örneği

**Yapılandırma sisteminde saklanır**:
```json
{
  "type": "mcp",
  "key": "secure-tool",
  "value": "{\"url\": \"https://secure-server.example.com/mcp\", \"auth-token\": \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\"}"
}
```

### Güvenlik En İyi Uygulamaları

1. **HTTPS Kullanımı**: Kimlik doğrulama ile çalışan MCP sunucuları için her zaman HTTPS URL'lerini kullanın.
2. **Kısa Ömürlü Token'lar**: Mümkün olduğunda, son kullanma tarihine sahip token'lar kullanın.
3. **En Az Yetki**: Token'lara, yalnızca gerekli olan minimum izinleri verin.
4. **Erişim Kontrolü**: Yapılandırma sistemine erişimi kısıtlayın.
5. **Token Döndürme**: Token'ları düzenli olarak değiştirin.
6. **Denetim Kayıtları**: Güvenlik olayları için yapılandırma değişikliklerini izleyin.
