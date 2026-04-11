# MCP Aracı Argümanları Belirtimi

## Genel Bakış
**Özellik Adı**: MCP Aracı Argümanları Desteği
**Yazar**: Claude Code Assistant
**Tarih**: 2025-08-21
**Durum**: Tamamlandı

### Yönetici Özeti

ReACT ajanlarının, argüman belirtimi desteğini MCP (Model Bağlam Protokolü) araç yapılandırmalarına ekleyerek,
doğru şekilde tanımlanmış argümanlarla MCP araçlarını çağırmasına olanak sağlayın; bu, mevcut istem şablonu araçlarının
nasıl çalıştığına benzer şekilde.


### Problem Tanımı


Şu anda, ReACT ajan çerçevesindeki MCP araçları, beklenen argümanlarını belirleyememektedir. `McpToolImpl.get_arguments()` metodu
boş bir liste döndürmektedir, bu da LLM'lerin (Büyük Dil Modelleri) yalnızca araç adlarına ve açıklamalarına dayanarak
doğru parametre yapısını tahmin etmesini gerektirmektedir. Bu, aşağıdaki sorunlara yol açmaktadır:
Parametre tahminine bağlı olarak güvenilir olmayan araç çağrıları
Yanlış argümanlar nedeniyle araçların başarısız olması durumunda kötü kullanıcı deneyimi
Yürütmeden önce araç parametrelerinin doğrulanmaması
Ajan istemlerindeki eksik parametre dokümantasyonu

### Hedefler

[ ] MCP araç yapılandırmalarının beklenen argümanları (ad, tür, açıklama) belirtmesine izin verin.
[ ] Ajan yöneticisini, MCP araç argümanlarını istemler aracılığıyla LLM'lere sunacak şekilde güncelleyin.
[ ] Mevcut MCP araç yapılandırmalarıyla geriye dönük uyumluluğu koruyun.
[ ] İstem şablonu araçlarına benzer şekilde argüman doğrulamasını destekleyin.

### Kapsam Dışı Hedefler
MCP sunucularından dinamik argüman keşfi (gelecek iyileştirme)
Temel yapı dışındaki argüman türü doğrulaması
Karmaşık argüman şemaları (iç içe nesneler, diziler)

## Arka Plan ve Bağlam

### Mevcut Durum
MCP araçları, ReACT ajan sisteminde minimum düzeyde meta veriyle yapılandırılmaktadır:
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance",
  "description": "Get bank account balance",
  "mcp-tool": "get_bank_balance"
}
```

`McpToolImpl.get_arguments()` metodu `[]` değerini döndürür, bu nedenle LLM'ler, istemlerinde argüman rehberliği almaz.

### Sınırlamalar

1. **Argüman belirtimi yok**: MCP araçları, beklenen
   parametreleri tanımlayamaz.

2. **LLM parametre tahmini**: Ajanlar, parametreleri araç
   adlarından/açıklamalarından çıkarım yoluyla belirlemelidir.

3. **Eksik istem bilgisi**: Ajan istemleri, MCP araçları için argüman
   ayrıntılarını göstermez.

4. **Doğrulama yok**: Geçersiz parametreler, yalnızca MCP araç
   yürütme zamanında tespit edilir.

### İlgili Bileşenler
**trustgraph-flow/agent/react/service.py**: Araç yapılandırması yükleme ve AgentManager oluşturma.
**trustgraph-flow/agent/react/tools.py**: McpToolImpl uygulaması.
**trustgraph-flow/agent/react/agent_manager.py**: Araç argümanlarıyla birlikte istem oluşturma.
**trustgraph-cli**: MCP araç yönetimi için komut satırı araçları.
**Workbench**: Ajan araç yapılandırması için harici kullanıcı arayüzü.

## Gereksinimler

### Fonksiyonel Gereksinimler

1. **MCP Araç Yapılandırma Argümanları**: MCP araç yapılandırmaları, isteğe bağlı bir `arguments` dizisiyle (ad, tür ve açıklama alanları) desteklemelidir.
2. **Argüman Açıklaması**: `McpToolImpl.get_arguments()`, boş bir liste yerine yapılandırılmış argümanları döndürmelidir.
3. **İstem Entegrasyonu**: Ajan istemleri, argümanlar belirtildiğinde MCP araç argümanı ayrıntılarını içermelidir.
4. **Geriye Dönük Uyumluluk**: Argümanlar olmadan mevcut MCP araç yapılandırmaları çalışmaya devam etmelidir.
5. **Komut Satırı Desteği**: Mevcut `tg-invoke-mcp-tool` komut satırı araçları, argümanları destekler (zaten uygulanmıştır).

### Fonksiyonel Olmayan Gereksinimler
1. **Geriye Dönük Uyumluluk**: Mevcut MCP araç yapılandırmaları için hiçbir bozucu değişiklik olmamalıdır.
2. **Performans**: Ajan istemi oluşturma üzerinde önemli bir performans etkisi olmamalıdır.
3. **Tutarlılık**: Argüman işleme, istem şablonu araç kalıplarıyla eşleşmelidir.

### Kullanıcı Hikayeleri

1. Bir **ajan geliştirici** olarak, LLM'lerin doğru parametrelerle araçları çağırması için MCP araç argümanlarını yapılandırmada belirtmek istiyorum.
2. Bir **workbench kullanıcısı** olarak, ajanların araçları doğru şekilde kullanması için MCP araç argümanlarını kullanıcı arayüzünde yapılandırmak istiyorum.
3. Bir **ReACT ajanı içindeki bir LLM** olarak, doğru parametreler sağlamak için istemlerdeki araç argümanı özelliklerini görmek istiyorum.

## Tasarım

### Yüksek Seviyeli Mimari
MCP araç yapılandırmasını, istem şablonu kalıbıyla eşleşecek şekilde aşağıdaki adımlarla genişletin:
1. MCP araç yapılandırmalarına isteğe bağlı bir `arguments` dizisi ekleyin.
2. `McpToolImpl`'nin yapılandırılmış argümanları kabul etmesini ve döndürmesini sağlayın.
3. MCP araç argümanlarını işlemek için araç yapılandırması yüklemeyi güncelleyin.
4. Ajan istemlerinin MCP araç argümanı bilgilerini içermesini sağlayın.

### Yapılandırma Şeması
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance", 
  "description": "Get bank account balance",
  "mcp-tool": "get_bank_balance",
  "arguments": [
    {
      "name": "account_id",
      "type": "string", 
      "description": "Bank account identifier"
    },
    {
      "name": "date",
      "type": "string",
      "description": "Date for balance query (optional, format: YYYY-MM-DD)"
    }
  ]
}
```

### Veri Akışı
1. **Yapılandırma Yükleme**: `on_tools_config()` ile birlikte MCP aracı yapılandırması yüklenir.
2. **Araç Oluşturma**: Argümanlar ayrıştırılır ve `McpToolImpl`'e oluşturucu aracılığıyla iletilir.
3. **İstem Oluşturma**: `agent_manager.py`, LLM istemlerine dahil etmek için `tool.arguments`'i çağırır.
4. **Araç Çağrısı**: LLM, MCP hizmetine değiştirilmeden parametreler sağlar.

### API Değişiklikleri
Harici API değişiklikleri yok - bu tamamen içsel yapılandırma ve argüman işleme ile ilgilidir.

### Bileşen Detayları

#### Bileşen 1: service.py (Araç Yapılandırma Yükleme)
**Amaç**: MCP araç yapılandırmalarını ayrıştırın ve araç örnekleri oluşturun.
**Gerekli Değişiklikler**: MCP araçları için argüman ayrıştırması ekleyin (istem araçlarına benzer şekilde).
**Yeni İşlevsellik**: MCP araç yapılandırmasından `arguments` dizisini çıkarın ve `Argument` nesneleri oluşturun.

#### Bileşen 2: tools.py (McpToolImpl)
**Amaç**: MCP araç uygulaması sarmalayıcısı.
**Gerekli Değişiklikler**: Oluşturucuda argümanları kabul edin ve bunları `get_arguments()`'den döndürün.
**Yeni İşlevsellik**: Boş bir liste döndürmek yerine yapılandırılmış argümanları saklayın ve sergileyin.

#### Bileşen 3: Workbench (Harici Depo)
**Amaç**: Aracılar için kullanıcı arayüzü yapılandırma.
**Gerekli Değişiklikler**: MCP araçları için argüman belirtme kullanıcı arayüzü ekleyin.
**Yeni İşlevsellik**: Kullanıcıların MCP araçları için argümanları eklemesine/düzenlemesine/kaldırmasına izin verin.

#### Bileşen 4: CLI Araçları
**Amaç**: Komut satırı aracı yönetimi.
**Gerekli Değişiklikler**: MCP araç oluşturma/güncelleme komutlarında argüman belirtimini destekleyin.
**Yeni İşlevsellik**: Araç yapılandırma komutlarında argüman parametresini kabul edin.

## Uygulama Planı

### 1. Aşama: Temel Ajan Çerçevesi Değişiklikleri
[ ] `McpToolImpl` oluşturucusunu `arguments` parametresini kabul edecek şekilde güncelleyin.
[ ] `McpToolImpl.get_arguments()`'ın saklanan argümanları döndürmesi için değiştirin.
[ ] `service.py` MCP araç yapılandırma ayrıştırmasını argümanları işleyecek şekilde değiştirin.
[ ] MCP araç argüman işleme için birim testleri ekleyin.
[ ] Ajan istemlerinin MCP araç argümanlarını içerdiğini doğrulayın.

### 2. Aşama: Harici Araç Desteği
[ ] CLI araçlarını MCP araç argüman belirtimini destekleyecek şekilde güncelleyin.
[ ] Kullanıcılar için argüman yapılandırma biçimini belgeleyin.
[ ] Workbench kullanıcı arayüzünü MCP araç argüman yapılandırmasını destekleyecek şekilde güncelleyin.
[ ] Örnekler ve belgeler ekleyin.

### Kod Değişiklikleri Özeti
| Dosya | Değişiklik Türü | Açıklama |
|------|------------|-------------|
| `tools.py` | Değiştirildi | `tools.py`'ı argümanları kabul edecek ve saklayacak şekilde güncelleyin |
| `service.py` | Değiştirildi | MCP araç yapılandırmasından argümanları ayrıştırın (satır 108-113) |
| `test_react_processor.py` | Değiştirildi | MCP araç argümanları için testler ekleyin |
| CLI araçları | Değiştirildi | Komutlarda argüman belirtimini destekleyin |
| Workbench | Değiştirildi | MCP araç argüman yapılandırması için bir kullanıcı arayüzü ekleyin |

## Test Stratejisi

### Birim Testleri
**MCP Araç Argüman Ayrıştırması**: `service.py`'ın MCP araç yapılandırmalarından argümanları doğru bir şekilde ayrıştırdığını test edin.
**McpToolImpl Argümanları**: `get_arguments()`'ın yapılandırılmış argümanları döndürdüğünü ve boş bir liste döndürmediğini test edin.
**Geriye Dönük Uyumluluk**: Argümanları olmayan MCP araçlarının çalışmaya devam ettiğini (boş bir liste döndürdüğünü) test edin.
**Ajan İstem Oluşturma**: Ajan istemlerinin MCP araç argümanı ayrıntılarını içerdiğini test edin.

### Entegrasyon Testleri
**Uçtan Uca Araç Çağrısı**: MCP araç argümanlarıyla test aracısı, araçları başarıyla çağırabilir.
**Yapılandırma Yükleme**: MCP araç argümanlarıyla test yapılandırma yükleme döngüsünü tamamlayın.
**Çoklu Bileşen**: Argümanların yapılandırmadan → araç oluşturmaya → istem oluşturmaya doğru doğru şekilde aktarılmasını test edin.

### Manuel Testler
**Ajan Davranışı**: LLM'nin ReACT döngülerinde argüman bilgilerini alıp kullandığını manuel olarak doğrulayın.
**CLI Entegrasyonu**: `tg-invoke-mcp-tool`'un yeni argüman yapılandırmalı MCP araçlarıyla çalıştığını test edin.
**Çalışma Ortamı Entegrasyonu**: Kullanıcı arayüzünün MCP araç argümanı yapılandırmasını desteklediğini test edin.

## Göç ve Dağıtım

### Göç Stratejisi
Göç gerektirmez - bu tamamen ek bir işlevsellik:
``arguments`` içermeyen mevcut MCP araç yapılandırmaları, herhangi bir değişiklik olmadan çalışmaya devam eder.
``McpToolImpl.get_arguments()``, eski araçlar için boş bir liste döndürür.
Yeni yapılandırmalar isteğe bağlı olarak ``arguments`` dizisini içerebilir.

### Dağıtım Planı
1. **1. Aşama**: Çekirdek ajan çerçevesi değişikliklerini geliştirme/hazırlık ortamına dağıtın.
2. **2. Aşama**: CLI araç güncellemelerini ve belgeleri dağıtın.
3. **3. Aşama**: Argüman yapılandırması için çalışma ortamı kullanıcı arayüzü güncellemelerini dağıtın.
4. **4. Aşama**: İzleme ile üretim dağıtımı.

### Geri Alma Planı
Çekirdek değişiklikler geriye dönük uyumludur - işlevsellik için geri alma işlemine gerek yoktur.
Sorunlar ortaya çıkarsa, MCP araç yapılandırma yükleme mantığını geri alarak argüman ayrıştırmayı devre dışı bırakın.
Çalışma ortamı ve CLI değişiklikleri bağımsızdır ve ayrı olarak geri alınabilir.

## Güvenlik Hususları
**Yeni bir saldırı yüzeyi yok**: Argümanlar, yeni girdiler olmadan mevcut yapılandırma kaynaklarından ayrıştırılır.
**Parametre doğrulama**: Argümanlar MCP araçlarına değiştirilmeden iletilir - doğrulama MCP araç seviyesinde kalır.
**Yapılandırma bütünlüğü**: Argüman özellikleri araç yapılandırmasının bir parçasıdır - aynı güvenlik modeli uygulanır.

## Performans Etkisi
**Minimum ek yük**: Argüman ayrıştırması yalnızca yapılandırma yükleme sırasında, her istekte değil gerçekleşir.
**İstem boyutu artışı**: Ajan istemleri, MCP araç argümanı ayrıntılarını içerecek ve bu da token kullanımını biraz artıracaktır.
**Bellek kullanımı**: Argüman özelliklerinin araç nesnelerinde depolanması için ihmal edilebilir bir artış.

## Belgeler

### Kullanıcı Belgeleri
[ ] Argüman örnekleriyle MCP araç yapılandırma kılavuzunu güncelleyin.
[ ] CLI araç yardım metnine argüman belirtimi ekleyin.
[ ] Yaygın MCP araç argümanı kalıplarının örneklerini oluşturun.

### Geliştirici Belgeleri
[ ] `McpToolImpl` sınıfının belgelerini güncelleyin.
[ ] Argüman ayrıştırma mantığı için iç içe yorumlar ekleyin.
[ ] Sistem mimarisinde argüman akışını belgeleyin.

## Açık Sorular
1. **Argüman doğrulama**: Temel yapı kontrolünün ötesinde argüman türlerini/formatlarını doğrulamalı mıyız?
2. **Dinamik keşif**: Gelecekte MCP sunucularından araç şemalarını otomatik olarak sorgulamak için bir özellik mi?

## Göz Önünde Bulundurulan Alternatifler
1. **Dinamik MCP şema keşfi**: Çalışma zamanında araç argüman şemaları için MCP sunucularını sorgulayın - karmaşıklık ve güvenilirlik sorunları nedeniyle reddedildi.
2. **Ayrı argüman kaydı**: MCP araç argümanlarını ayrı bir yapılandırma bölümünde saklayın - başlangıç uygulamasının basit kalması için istem şablonu yaklaşımıyla tutarlılık nedeniyle reddedildi.
3. **Tip doğrulama**: Argümanlar için tam JSON şema doğrulaması - başlangıçta basit bir uygulama sağlamak için gelecekteki bir özellik olarak ertelendi.

## Referanslar
[MCP Protokolü Özellikleri](https://github.com/modelcontextprotocol/spec)
[İstem Şablonu Araç Uygulaması](./trustgraph-flow/trustgraph/agent/react/service.py#L114-129)
[Mevcut MCP Araç Uygulaması](./trustgraph-flow/trustgraph/agent/react/tools.py#L58-86)

## Ek
[Herhangi bir ek bilgi, diyagram veya örnek]
