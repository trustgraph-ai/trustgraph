# OntoRAG: Ontolojiye Dayalı Bilgi Çıkarma ve Sorgulama Teknik Özellikleri

## Genel Bakış

OntoRAG, yapılandırılmamış metinden bilgi üçlülerinin çıkarılması ve elde edilen bilgi grafiğinin sorgulanması sırasında sıkı semantik tutarlılığı sağlayan, ontoloji odaklı bir bilgi çıkarma ve sorgulama sistemidir. GraphRAG'e benzer, ancak resmi ontoloji kısıtlamalarıyla, OntoRAG, çıkarılan tüm üçlülerin önceden tanımlanmış ontolojik yapılara uygun olmasını sağlar ve semantik olarak bilinçli sorgulama yetenekleri sunar.

Sistem, hem çıkarma hem de sorgulama işlemlerinde ilgili ontoloji alt kümelerini dinamik olarak seçmek için vektör benzerliği eşleştirmesi kullanır, bu da odaklı ve bağlamsal olarak uygun işleme sağlarken semantik geçerliliği korur.

**Servis Adı**: `kg-extract-ontology`

## Hedefler

**Ontolojiye Uygun Çıkarma**: Çıkarılan tüm üçlülerin yüklenen ontolojilere kesinlikle uygun olmasını sağlamak
**Dinamik Bağlam Seçimi**: Her parça için ilgili ontoloji alt kümelerini seçmek için gömülmeleri kullanmak
**Semantik Tutarlılık**: Sınıf hiyerarşilerini, özellik alanlarını/aralıklarını ve kısıtlamaları korumak
**Verimli İşleme**: Hızlı ontoloji öğesi eşleştirmesi için bellek içi vektör depoları kullanmak
**Ölçeklenebilir Mimari**: Farklı alanlara sahip çoklu eşzamanlı ontolojileri desteklemek

## Arka Plan

Mevcut bilgi çıkarma hizmetleri (`kg-extract-definitions`, `kg-extract-relationships`), resmi kısıtlamalar olmadan çalışır ve potansiyel olarak tutarsız veya uyumsuz üçlüler üretebilir. OntoRAG, bunu şunları yaparak ele alır:

1. Geçerli sınıfları ve özellikleri tanımlayan resmi ontolojileri yüklemek
2. Metin içeriğini ilgili ontoloji öğeleriyle eşleştirmek için gömülmeleri kullanmak
3. Çıkarma işleminin yalnızca ontolojiye uygun üçlüler üretmesini sağlamak
4. Çıkarılan bilginin semantik olarak doğrulanmasını sağlamak

Bu yaklaşım, sinirsel çıkarmanın esnekliğini, resmi bilgi gösteriminin titizliğiyle birleştirir.

## Teknik Tasarım

### Mimari

OntoRAG sistemi aşağıdaki bileşenlerden oluşur:

```
┌─────────────────┐
│  Configuration  │
│    Service      │
└────────┬────────┘
         │ Ontologies
         ▼
┌─────────────────┐      ┌──────────────┐
│ kg-extract-     │────▶│  Embedding   │
│   ontology      │      │   Service    │
└────────┬────────┘      └──────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐      ┌──────────────┐
│   In-Memory     │◀────│   Ontology   │
│  Vector Store   │      │   Embedder   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Sentence     │────▶│   Chunker    │
│    Splitter     │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Ontology     │────▶│   Vector     │
│    Selector     │      │   Search     │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Prompt       │────▶│   Prompt     │
│   Constructor   │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  Triple Output  │
└─────────────────┘
```

### Bileşen Detayları

#### 1. Ontoloji Yükleyici

**Amaç**: Ontoloji yapılandırmalarını olay odaklı güncellemeler kullanarak yapılandırma hizmetinden alır ve ayrıştırır.

**Uygulama**:
Ontoloji Yükleyici, olay odaklı ontoloji yapılandırma güncellemelerini almak için TrustGraph'in ConfigPush kuyruğunu kullanır. "ontoloji" türünde bir yapılandırma öğesi eklendiğinde veya değiştirildiğinde, yükleyici yapılandırma-güncelleme kuyrusu aracılığıyla güncellemeyi alır ve meta veriler, sınıflar, nesne özellikleri ve veri türü özellikleri içeren JSON yapısını ayrıştırır. Bu ayrıştırılmış ontolojiler, çıkarma işlemi sırasında verimli bir şekilde erişilebilen yapılandırılmış nesneler olarak bellekte saklanır.

**Temel İşlemler**:
Ontoloji türündeki yapılandırmalar için config-update kuyruğuna abone olun
JSON ontoloji yapılarını OntologyClass ve OntologyProperty nesnelerine ayrıştırın
Ontoloji yapısını ve tutarlılığını doğrulayın
Ayrıştırılmış ontolojileri hızlı erişim için bellekte önbelleğe alın
Akışa özgü vektör depolarıyla akışa özel işleme yapın

**Uygulama Konumu**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_loader.py`

#### 2. Ontoloji Gömücüsü

**Amaç**: Tüm ontoloji öğeleri için vektör gömüleri oluşturarak semantik benzerlik eşleştirmesini etkinleştirir.

**Uygulama**:
Ontoloji Gömücüsü, yüklenen ontolojilerdeki her öğeyi (sınıflar, nesne özellikleri ve veri türü özellikleri) işler ve EmbeddingsClientSpec hizmetini kullanarak vektör gömüleri oluşturur. Her öğe için, öğenin tanımlayıcısını, etiketlerini ve açıklamasını (yorum) birleştirerek bir metin gösterimi oluşturur. Bu metin daha sonra, semantik anlamını yakalayan yüksek boyutlu bir vektör gömüsüne dönüştürülür. Bu gömüler, öğe türü, kaynak ontoloji ve tam tanım hakkında meta verilerle birlikte, akışa özel bir bellek içi FAISS vektör deposunda saklanır. Gömücü, ilk gömü yanıtından gömü boyutunu otomatik olarak algılar.

**Temel İşlemler**:
Öğenin kimliklerinden, etiketlerinden ve yorumlarından metin gösterimleri oluşturun
Toplu işleme için asyncio.gather kullanarak EmbeddingsClientSpec aracılığıyla gömüler oluşturun
Gömüleri kapsamlı meta verilerle FAISS vektör deposunda saklayın
Verimli erişim için ontolojiye, öğe türüne ve öğe kimliğine göre indeksleyin
Vektör deposu başlatması için gömü boyutlarını otomatik olarak algılayın
Bağımsız vektör depolarıyla akışa özel gömü modelleriyle çalışın

**Uygulama Konumu**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_embedder.py`

#### 3. Metin İşleyici (Cümle Ayırıcı)

**Amaç**: Ontoloji eşleştirmesi için hassas bir şekilde metin parçalarını ince taneli segmentlere ayırır.

**Uygulama**:
Metin İşleyici, gelen metin parçalarını cümlelere ayırmak ve POS etiketlemesi yapmak için NLTK'yi kullanır. NLTK sürüm uyumluluğunu, `punkt_tab` ve `averaged_perceptron_tagger_eng`'i indirmeye çalışarak ve gerekirse eski sürümlere geri dönerek yönetir. Her metin parçası, ontoloji öğeleriyle bağımsız olarak eşleştirilebilen ayrı cümlelere bölünür.

**Temel İşlemler**:
NLTK cümle ayrıştırması kullanarak metni cümlelere ayırın
NLTK sürüm uyumluluğunu yönetin (punkt_tab vs punkt)
Metin ve konum bilgileriyle TextSegment nesneleri oluşturun
Hem tam cümleleri hem de ayrı parçaları destekleyin

**Uygulama Konumu**: `trustgraph-flow/trustgraph/extract/kg/ontology/text_processor.py`

#### 4. Ontoloji Seçici

**Amaç**: Mevcut metin parçası için en alakalı ontoloji öğesi alt kümesini belirler.

**Uygulama**:
Ontoloji Seçici, metin segmentleri ile ontoloji öğeleri arasında semantik eşleştirme yapmak için FAISS vektör benzerlik araması kullanır. Metin parçasındaki her cümle için, bir gömü oluşturur ve vektör deposunda en benzer ontoloji öğelerini yapılandırılabilir bir eşik değeri (varsayılan 0,3) ile kosinüs benzerliği kullanarak arar. Tüm ilgili öğeler toplandıktan sonra, kapsamlı bir bağımlılık çözümlemesi yapılır: bir sınıf seçilirse, üst sınıfları dahil edilir; bir özellik seçilirse, etki alanı ve aralık sınıfları eklenir. Ek olarak, seçilen her sınıf için, **o sınıfa referans veren tüm özellikleri** (etki alanı veya aralık olarak) otomatik olarak dahil eder. Bu, çıkarmanın ilgili tüm ilişki özelliklerine erişmesini sağlar.

**Temel İşlemler**:
Her metin parçasının (cümlelerin) gömülme değerlerini oluşturun.
FAISS vektör deposunda k-en yakın komşu araması yapın (top_k=10, eşik=0.3).
Zayıf eşleşmeleri filtrelemek için benzerlik eşiği uygulayın.
Bağımlılıkları çözün (üst sınıflar, etki alanları, aralıklar).
**Seçilen sınıflarla ilgili tüm özellikleri otomatik olarak dahil edin** (etki alanı/aralık eşleşmesi).
Tüm gerekli ilişkilerle tutarlı bir ontoloji alt kümesi oluşturun.
Birden çok kez görünen öğeleri yinelenenleri kaldırın.

**Uygulama Konumu**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_selector.py`

#### 5. İstek Oluşturma

**Amaç**: LLM'yi yalnızca ontolojiye uygun üçlüleri çıkarması için yönlendiren yapılandırılmış istekler oluşturur.

**Uygulama**:
Çıkarma hizmeti, `ontology-prompt.md`'dan yüklenen bir Jinja2 şablonu kullanır ve bu şablon, ontoloji alt kümesini ve LLM tarafından çıkarım için kullanılan metni biçimlendirir. Şablon, Jinja2 sözdizimini kullanarak sınıflar, nesne özellikleri ve veri türü özellikleri üzerinde dinamik olarak yineleme yapar ve her birini açıklamaları, etki alanları, aralıkları ve hiyerarşik ilişkileriyle birlikte sunar. İstek, yalnızca sağlanan ontoloji öğelerinin kullanılması konusunda kesin kurallar içerir ve tutarlı ayrıştırma için JSON çıktı biçimi talep eder.

**Temel İşlemler**:
Ontoloji öğeleri üzerinde döngüler içeren Jinja2 şablonunu kullanın.
Üst sınıf ilişkileri (subclass_of) ve yorumlarla sınıfları biçimlendirin.
Etki alanı/aralık kısıtlamaları ve yorumlarla özellikleri biçimlendirin.
Açık çıkarma kuralları ve çıktı biçimi gereksinimleri ekleyin.
"extract-with-ontologies" şablonuyla istek hizmetini çağırın.

**Şablon Konumu**: `ontology-prompt.md`
**Uygulama Konumu**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py` (build_extraction_variables metodu)

#### 6. Ana Çıkarma Hizmeti

**Amaç**: Uçtan uca, ontolojiye dayalı üçlü çıkarma işlemini gerçekleştirmek için tüm bileşenleri koordine eder.

**Uygulama**:
Ana Çıkarma Hizmeti (KgExtractOntology), eksiksiz çıkarma iş akışını yöneten orkestrasyon katmanıdır. Her akış için bileşen başlatmayı kullanan TrustGraph'ın FlowProcessor kalıbını kullanır. Bir ontoloji yapılandırma güncellemesi geldiğinde, akışa özgü bileşenleri (ontoloji yükleyici, gömücü, metin işlemcisi, seçici) başlatır veya günceller. Bir metin parçası işlenmek üzere geldiğinde, aşağıdaki adımları koordine eder: metni segmentlere ayırmak, vektör araması yoluyla ilgili ontoloji öğelerini bulmak, kısıtlı bir istek oluşturmak, istek hizmetini çağırmak, yanıtı ayrıştırmak ve doğrulamak, ontoloji tanım üçlüleri oluşturmak ve hem içerik üçlülerini hem de varlık bağlamlarını yayınlamak.

**Çıkarma İş Akışı**:
1. Metin parçasını chunks-input kuyruğu aracılığıyla alın.
2. Gerekirse akış bileşenlerini başlatın (ilk parça veya yapılandırma güncellemesinde).
3. Metni NLTK kullanarak cümlelere ayırın.
4. İlgili ontoloji kavramlarını bulmak için FAISS vektör deposunda arama yapın.
5. Otomatik özellik dahil etme ile ontoloji alt kümesini oluşturun.
6. Jinja2 şablonlu istek değişkenlerini oluşturun.
7. extract-with-ontologies şablonuyla istek hizmetini çağırın.
8. JSON yanıtını yapılandırılmış üçlülere ayrıştırın.
9. Üçlüleri doğrulayın ve URI'ları tam ontoloji URI'lerine genişletin.
10. Sınıflar ve özellikler (etiketler/yorumlar/etki alanları/aralıklar) ile ontoloji tanım üçlülerini oluşturun.
11. Tüm üçlülerden varlık bağlamlarını oluşturun.
12. Üçlüleri ve varlık-bağlamlarını kuyruklara yayınlayın.

**Temel Özellikler**:
Farklı gömme modellerini destekleyen akış içi vektör depoları.
config-update kuyruğu aracılığıyla olay odaklı ontoloji güncellemeleri.
Ontoloji URI'lerini kullanarak otomatik URI genişletme.
Ontoloji öğeleri, tüm meta verilerle birlikte bilgi grafiğine eklenir.
Varlık bağlamları hem içerik hem de ontoloji öğelerini içerir.

**Uygulama Konumu**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`

### Yapılandırma

Bu hizmet, komut satırı argümanlarıyla TrustGraph'ın standart yapılandırma yaklaşımını kullanır:

```bash
kg-extract-ontology \
  --id kg-extract-ontology \
  --pulsar-host localhost:6650 \
  --input-queue chunks \
  --config-input-queue config-update \
  --output-queue triples \
  --entity-contexts-output-queue entity-contexts
```

**Temel Yapılandırma Parametreleri**:
`similarity_threshold`: 0.3 (varsayılan, kod içinde yapılandırılabilir)
`top_k`: 10 (her segment için alınacak ontoloji öğelerinin sayısı)
`vector_store`: Otomatik olarak algılanan boyutlara sahip Per-flow FAISS IndexFlatIP
`text_processor`: NLTK ile punkt_tab cümle tokenizasyonu
`prompt_template`: "extract-with-ontologies" (Jinja2 şablonu)

**Ontoloji Yapılandırması**:
Ontolojiler, "ontology" türü ile yapılandırma güncelleme kuyruğu aracılığıyla dinamik olarak yüklenir.

### Veri Akışı

1. **Başlangıç Aşaması** (her akış için):
   Yapılandırma güncelleme kuyruğu aracılığıyla ontoloji yapılandırmasını alın
   Ontoloji JSON'unu OntologyClass ve OntologyProperty nesnelerine ayrıştırın
   Tüm ontoloji öğeleri için EmbeddingsClientSpec kullanarak gömülme oluşturun
   Gömülmeleri her akış için FAISS vektör deposunda saklayın
   İlk yanıttan gömülme boyutlarını otomatik olarak algılayın

2. **Çıkarma Aşaması** (her parça için):
   chunks-input kuyruğundan bir parça alın
   Parçayı NLTK kullanarak cümlelere bölün
   Her cümle için gömülmeler hesaplayın
   İlgili ontoloji öğelerini bulmak için FAISS vektör deposunda arama yapın
   Otomatik özellik eklemeli ontoloji alt kümesi oluşturun
   Metin ve ontoloji ile Jinja2 şablon değişkenlerini oluşturun
   extract-with-ontologies şablonu ile istem hizmetini çağırın
   JSON yanıtını ayrıştırın ve üçlüleri doğrulayın
   URI'ları ontoloji URI'lerini kullanarak genişletin
   Ontoloji tanım üçlülerini oluşturun
   Tüm üçlülerden varlık bağlamlarını oluşturun
   üçlüler ve varlık-bağlamları kuyruklarına yayınlayın

### Bellek İçi Vektör Deposu

**Amaç**: Ontoloji öğesi eşleştirmesi için hızlı, bellek tabanlı benzerlik araması sağlar.

**Uygulama: FAISS**

Sistem, tam kosinüs benzerliği araması için **FAISS (Facebook AI Similarity Search)** ve IndexFlatIP kullanır. Temel özellikler:

**IndexFlatIP**: İç çarpım kullanarak tam kosinüs benzerliği araması
**Otomatik algılama**: Boyut, ilk gömülme yanıtından belirlenir
**Per-flow depoları**: Her akış, farklı gömülme modelleri için bağımsız bir vektör deposuna sahiptir
**Normalleştirme**: Tüm vektörler dizine eklenmeden önce normalleştirilir
**Toplu işlemler**: Başlangıç ontoloji yüklemesi için verimli toplu ekleme

**Uygulama Konumu**: `trustgraph-flow/trustgraph/extract/kg/ontology/vector_store.py`

### Ontoloji Alt Kümesi Seçim Algoritması

**Amaç**: Her metin parçası için ontolojinin ilgili en küçük bölümünü dinamik olarak seçer.

**Detaylı Algoritma Adımları**:

1. **Metin Segmentasyonu**:
   Giriş parçasını NLP cümle algılama kullanarak cümlelere bölün
   Her cümleden isim öbeklerini, fiil öbeklerini ve adlandırılmış varlıkları çıkarın
   Bağlamı koruyan hiyerarşik bir segmentler yapısı oluşturun

2. **Gömülme Oluşturma**:
   Her metin segmenti (cümleler ve öbekler) için vektör gömülmeleri oluşturun
   Ontoloji öğeleri için kullanılan aynı gömülme modelini kullanın
   Tekrarlayan segmentler için performansı artırmak için gömülmeleri önbelleğe alın

3. **Benzerlik Araması**:
   Her metin segmenti gömülmesi için vektör deposunda arama yapın
   En benzer ontoloji öğelerinin en üst N tanesini (örneğin, 10) alın
   Zayıf eşleşmeleri filtrelemek için bir benzerlik eşiği (örneğin, 0.7) uygulayın
   Tüm segmentler genelinde sonuçları toplayın ve eşleşme sıklıklarını izleyin

4. **Bağımlılık Çözümü**:
   Seçilen her sınıf için, köke kadar tüm üst sınıfları yinelemeli olarak dahil edin
   Seçilen her özellik için, alan ve aralık sınıflarını dahil edin
   Ters özellikler için, her iki yönü de dahil edin
   Ontolojide mevcutsa, eşdeğer sınıfları ekleyin

5. **Alt Küme Oluşturma**:
   Toplanan öğeleri ilişkileri korurken yinelenenleri kaldırın
   Sınıflara, nesne özelliklerine ve veri türü özelliklerine göre düzenleyin
   Tüm kısıtlamaların ve ilişkilerin korunmasını sağlayın
   Geçerli ve eksiksiz olan kendi kendine yeterli bir mini-ontoloji oluşturun

**Örnek İnceleme**:
Verilen metin: "Kahverengi köpek, beyaz kedinin ağacın tepesine doğru koştuğunu gördü."
Segmentler: ["kahverengi köpek", "beyaz kedi", "ağaç", "koştu"]
Eşleşen öğeler: [köpek (sınıf), kedi (sınıf), hayvan (üst sınıf), koşar (özellik)]
Bağımlılıklar: [hayvan (köpek ve kedinin üst sınıfı), canlı (hayvanın üst sınıfı)]
Sonuç alt kümesi: Hayvan hiyerarşisi ve koşma ilişkisi ile eksiksiz mini-ontoloji

### Üçlü Doğrulama

**Amaç**: Çıkarılan tüm üçlülerin ontoloji kısıtlamalarına kesinlikle uygun olduğundan emin olun.

**Doğrulama Algoritması**:

1. **Sınıf Doğrulama**:
   Konuların, ontoloji alt kümesinde tanımlanan sınıfların örnekleri olduğundan emin olun.
   Nesne özellikleri için, nesnelerin de geçerli sınıf örnekleri olduğundan emin olun.
   Sınıf adlarını, ontolojinin sınıf sözlüğü ile karşılaştırın.
   Sınıf hiyerarşilerini işleyin - alt sınıfların örnekleri, üst sınıf kısıtlamaları için geçerlidir.

2. **Özellik Doğrulama**:
   Öncüllerin, ontoloji alt kümesindeki özelliklerle eşleştiğinden emin olun.
   Varlıklar arası nesne özellikleri ile varlıklardan literal değerlere olan veri tipi özellikleri arasındaki farkı belirtin.
   Özellik adlarının tam olarak eşleştiğinden emin olun (varsa ad alanını dikkate alın).

3. **Alan/Aralık Kontrolü**:
   Kullanılan her özellik için, alanını ve aralığını alın.
   Konunun türünün, özelliğin alanıyla eşleştiğinden veya ondan türediğinden emin olun.
   Nesnenin türünün, özelliğin aralığıyla eşleştiğinden veya ondan türediğinden emin olun.
   Veri tipi özellikleri için, nesnenin doğru XSD türünde bir literal olduğundan emin olun.
Veri tipi özellikleri için, nesnenin doğru XSD türünde bir literal olduğundan emin olun
4. **Kardinalite Doğrulama**:
   Her konu için özellik kullanım sayılarını takip edin.
   Minimum kardinaliteyi kontrol edin - gerekli özelliklerin mevcut olduğundan emin olun.
   Maksimum kardinaliteyi kontrol edin - özelliğin çok fazla kullanılmadığından emin olun.
   Fonksiyonel özellikler için, her konu için en fazla bir değer olduğundan emin olun.

5. **Veri Tipi Doğrulama**:
   Literal değerleri, bildirilen XSD türlerine göre ayrıştırın.
   Tamsayıların geçerli sayılar olduğundan, tarihlerinin doğru biçimlendirildiğinden emin olun, vb.
   Regex kısıtlamaları tanımlanmışsa, dize kalıplarını kontrol edin.
   URI'lerin xsd:anyURI türleri için doğru biçimlendirildiğinden emin olun.

**Doğrulama Örneği**:
Üçlü: ("Buddy", "has-owner", "John")
"Buddy"nin, "has-owner" özelliğine sahip olabilen bir sınıf olarak tanımlandığından emin olun.
"has-owner" özelliğinin ontolojide olduğundan emin olun.
Alan kısıtlamasını doğrulayın: konu, "Pet" türünde veya bir alt türünde olmalıdır.
Aralık kısıtlamasını doğrulayın: nesne, "Person" türünde veya bir alt türünde olmalıdır.
Geçerliyse, çıktıya ekleyin; geçersizse, ihlali günlüğe kaydedin ve atlayın.

## Performans Hususları

### Optimizasyon Stratejileri

1. **Gömülü Önbellekleme**: Sık kullanılan metin segmentleri için gömülmeleri önbelleğe alın.
2. **Toplu İşleme**: Birden fazla segmenti paralel olarak işleyin.
3. **Vektör Deposu İndeksleme**: Büyük ontolojiler için yaklaşık en yakın komşu algoritmalarını kullanın.
4. **İstem Optimizasyonu**: Yalnızca gerekli ontoloji öğelerini dahil ederek istem boyutunu en aza indirin.
5. **Sonuç Önbellekleme**: Aynı parçalar için çıkarma sonuçlarını önbelleğe alın.

### Ölçeklenebilirlik

**Yatay Ölçekleme**: Paylaşılan ontoloji önbelleğine sahip çoklu çıkarıcı örneği.
**Ontoloji Bölümleme**: Büyük ontolojileri alanlara göre bölün.
**Akışlı İşleme**: Parçalara toplu olarak işlem yapmadan geldikçe işleyin.
**Bellek Yönetimi**: Kullanılmayan gömülmelerin periyodik olarak temizlenmesi.

## Hata Yönetimi

### Başarısızlık Senaryoları

1. **Eksik Ontolojiler**: Kısıtlanmamış çıkarma işlemine geri dönün.
2. **Gömme Hizmeti Hatası**: Önbelleğe alınmış gömülmeleri kullanın veya semantik eşleşmeyi atlayın.
3. **İstem Hizmeti Zaman Aşımı**: Üstel geri alma ile yeniden deneyin.
4. **Geçersiz Üçlü Biçimi**: Hatalı üçlüleri günlüğe kaydedin ve atlayın.
5. **Ontoloji Tutarsızlıkları**: Çakışmaları bildirin ve en spesifik geçerli öğeleri kullanın.

### İzleme

İzlenecek temel ölçütler:

Ontoloji yükleme süresi ve bellek kullanımı
Gömme oluşturma gecikmesi
Vektör arama performansı
İstem hizmeti yanıt süresi
Üçlü çıkarma doğruluğu
Ontoloji uyumluluk oranı

## Geçiş Yolu

### Mevcut Çıkarıcılardan

1. **Paralel Çalışma**: Başlangıçta mevcut çıkarıcılarla birlikte çalıştırın.
2. **Aşamalı Dağıtım**: Belirli belge türleriyle başlayın.
3. **Kalite Karşılaştırması**: Çıktı kalitesini mevcut çıkarıcılarla karşılaştırın.
4. **Tam Geçiş**: Kalite doğrulandığında mevcut çıkarıcıları değiştirin.

### Ontoloji Geliştirme

1. **Mevcut Bilgilerden Başlatma**: Başlangıç ontolojilerini mevcut bilgilerden oluşturun.
2. **Yinelemeli İyileştirme**: Çıkarma kalıplarına göre iyileştirin.
3. **Alan Uzmanı İncelemesi**: Konu uzmanlarıyla doğrulayın.
4. **Sürekli İyileştirme**: Çıkarma geri bildirimine göre güncelleyin.

## Ontolojiye Duyarlı Sorgu Hizmeti

### Genel Bakış

Ontolojiye duyarlı sorgu hizmeti, farklı arka uç grafik depolarını desteklemek için çoklu sorgu yolu sağlar. Cassandra (SPARQL aracılığıyla) ve Cypher tabanlı grafik depoları (Neo4j, Memgraph, FalkorDB) için hem hassas hem de semantik olarak bilinçli soru yanıtlama için ontoloji bilgisini kullanır.

**Hizmet Bileşenleri**:
`onto-query-sparql`: Doğal dili, Cassandra için SPARQL'e dönüştürür.
`sparql-cassandra`: Cassandra için rdflib kullanarak SPARQL sorgu katmanı.
`onto-query-cypher`: Doğal dili, grafik veritabanları için Cypher'a dönüştürür.
`cypher-executor`: Neo4j, Memgraph, FalkorDB için Cypher sorgu katmanı.

### Mimari

```
                    ┌─────────────────┐
                    │   User Query    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Question      │────▶│   Sentence   │
                    │   Analyser      │      │   Splitter   │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Ontology      │────▶│   Vector     │
                    │   Matcher       │      │    Store     │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Backend Router  │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ onto-query-     │          │ onto-query-     │
    │    sparql       │          │    cypher       │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   SPARQL        │          │   Cypher        │
    │  Generator      │          │  Generator      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ sparql-         │          │ cypher-         │
    │ cassandra       │          │ executor        │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   Cassandra     │          │ Neo4j/Memgraph/ │
    │                 │          │   FalkorDB      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └────────────┬───────────────┘
                          │
                          ▼
                 ┌─────────────────┐      ┌──────────────┐
                 │   Answer        │────▶│   Prompt     │
                 │  Generator      │      │   Service    │
                 └────────┬────────┘      └──────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Final Answer   │
                 └─────────────────┘
```

### Sorgu İşleme Hattı

#### 1. Soru Analizörü

**Amaç**: Kullanıcı sorularını, ontoloji eşleştirmesi için anlamsal bileşenlere ayırır.

**Algoritma Açıklaması**:
Soru Analizörü, gelen doğal dil sorgusunu alır ve çıkarma hattında kullanılan aynı cümle bölme yaklaşımıyla anlamlı segmentlere böler. Soruda bahsedilen temel varlıkları, ilişkileri ve kısıtlamaları belirler. Her segment, soru türü (olaysal, toplama, karşılaştırma vb.) ve beklenen cevap formatı açısından analiz edilir. Bu ayrıştırma, soruyu yanıtlamak için ontolojinin hangi bölümlerinin en alakalı olduğunu belirlemeye yardımcı olur.

**Temel İşlemler**:
Soruyu cümlelere ve ifadelere ayırın
Soru türünü ve amacını belirleyin
Bahsedilen varlıkları ve ilişkileri çıkarın
Sorudaki kısıtlamaları ve filtreleri tespit edin
Beklenen cevap formatını belirleyin

#### 2. Sorgular İçin Ontoloji Eşleştirici

**Amaç**: Soruyu yanıtlamak için gereken ilgili ontoloji alt kümesini belirler.

**Algoritma Açıklaması**:
Çıkarma hattının Ontoloji Seçici'sine benzer, ancak soru yanıtlama için optimize edilmiştir. Eşleştirici, soru segmentleri için gömülme değerleri oluşturur ve ilgili ontoloji öğelerini vektör deposunda arar. Ancak, sorgu oluşturma için yararlı olacak kavramları bulmaya odaklanır, çıkarma işlemine değil. Grafiği keşfederken bahsedilmeyen ancak ilgili olabilecek ilgili özellikleri de seçime dahil eder. Örneğin, "çalışanlar" hakkında bir soru sorulursa, çalışan bilgileri bulmak için ilgili olabilecek "çalışır", "yönetir" ve "rapor verir" gibi özellikleri de içerebilir.

**Eşleştirme Stratejisi**:
Soru segmentlerini gömülme değerlerine dönüştürün
Doğrudan bahsedilen ontoloji kavramlarını bulun
Bahsedilen sınıfları birbirine bağlayan özellikleri dahil edin
Gezinme için ters ve ilgili özellikleri ekleyin
Hiyerarşik sorgular için üst/alt sınıfları dahil edin
Sorgu odaklı bir ontoloji bölümü oluşturun

#### 3. Arka Uç Yönlendirici

**Amaç**: Sorguları, yapılandırmaya göre uygun arka uç özel sorgu yoluna yönlendirir.

**Algoritma Açıklaması**:
Arka Uç Yönlendirici, sistem yapılandırmasını inceleyerek hangi grafik arka ucunun (Cassandra veya Cypher tabanlı) etkin olduğunu belirler. Soruyu ve ontoloji bölümünü uygun sorgu oluşturma hizmetine yönlendirir. Yönlendirici, birincil arka uç kullanılamıyorsa, aynı zamanda birden fazla arka uç arasında yük dengeleme veya yedekleme mekanizmalarını da destekleyebilir.

**Yönlendirme Mantığı**:
Sistem ayarlarından yapılandırılmış arka uç türünü kontrol edin
Cassandra arka uçları için `onto-query-sparql`'a yönlendirin
Neo4j/Memgraph/FalkorDB için `onto-query-cypher`'a yönlendirin
Sorgu dağıtımı ile çoklu arka uç yapılandırmalarını destekleyin
Arıza ve yük dengeleme senaryolarını işleyin

#### 4. SPARQL Sorgu Oluşturma (`onto-query-sparql`)

**Amaç**: Doğal dil sorularını, Cassandra üzerinde yürütme için SPARQL sorgularına dönüştürür.

**Algoritma Açıklaması**:
SPARQL sorgu oluşturucu, soruyu ve ontoloji bölümünü alır ve Cassandra arka ucu üzerinde yürütülmek üzere optimize edilmiş bir SPARQL sorgusu oluşturur. RDF/OWL semantiğini içeren, SPARQL'e özel bir şablon kullanan bir istem hizmeti kullanır. Oluşturucu, Cassandra işlemleriyle verimli bir şekilde çevrilebilen özellik yolları, isteğe bağlı ifadeler ve filtreler gibi SPARQL kalıplarını anlar.

**SPARQL Oluşturma İstem Şablonu**:
```
Generate a SPARQL query for the following question using the provided ontology.

ONTOLOGY CLASSES:
{classes}

ONTOLOGY PROPERTIES:
{properties}

RULES:
- Use proper RDF/OWL semantics
- Include relevant prefixes
- Use property paths for hierarchical queries
- Add FILTER clauses for constraints
- Optimise for Cassandra backend

QUESTION: {question}

SPARQL QUERY:
```

#### 5. Şifre Sorgu Üretimi (`onto-query-cypher`)

**Amaç**: Doğal dil sorularını, grafik veritabanları için Şifre sorgularına dönüştürür.

**Algoritma Açıklaması**:
Şifre sorgu üreticisi, Neo4j, Memgraph ve FalkorDB için optimize edilmiş yerel Şifre sorguları oluşturur. Ontoloji sınıflarını düğüm etiketlerine ve özellikleri ilişkilerle eşler, Şifre'nin desen eşleştirme sözdizimini kullanır. Üretici, ilişki yönü ipuçları, indeks kullanımı ve sorgu planlama ipuçları gibi Şifre'ye özgü optimizasyonları içerir.

**Şifre Üretim İstem Şablonu**:
```
Generate a Cypher query for the following question using the provided ontology.

NODE LABELS (from classes):
{classes}

RELATIONSHIP TYPES (from properties):
{properties}

RULES:
- Use MATCH patterns for graph traversal
- Include WHERE clauses for filters
- Use aggregation functions when needed
- Optimise for graph database performance
- Consider index hints for large datasets

QUESTION: {question}

CYPHER QUERY:
```

#### 6. SPARQL-Cassandra Sorgu Motoru (`sparql-cassandra`)

**Amaç**: Python rdflib kullanarak Cassandra'ya karşı SPARQL sorgularını yürütür.

**Algoritma Açıklaması**:
SPARQL-Cassandra motoru, Python'ın rdflib kütüphanesini ve özel bir Cassandra arka uç depolama alanını kullanan bir SPARQL işlemcisi uygular. SPARQL grafik desenlerini, birleştirmeleri, filtreleri ve toplama işlemlerini işleyerek uygun Cassandra CQL sorgularına dönüştürür. Motor, semantik yapıyı korurken Cassandra'nın sütun ailesi depolama modeline göre optimizasyon sağlayan bir RDF-Cassandra eşleme sürdürür.

**Uygulama Özellikleri**:
Cassandra için rdflib Store arayüzü uygulaması
Yaygın desenlerle SPARQL 1.1 sorgu desteği
Üçlü desenlerin CQL'ye verimli çevirisi
Özellik yolları ve hiyerarşik sorgular için destek
Büyük veri kümeleri için sonuç akışı
Bağlantı havuzu ve sorgu önbelleği

**Örnek Çeviri**:
```sparql
SELECT ?animal WHERE {
  ?animal rdf:type :Animal .
  ?animal :hasOwner "John" .
}
```
İndeksleri ve bölüm anahtarlarını kullanan, optimize edilmiş Cassandra sorgularına çevrilir.

#### 7. Cypher Sorgu Yürütücüsü (`cypher-executor`)

**Amaç**: Neo4j, Memgraph ve FalkorDB'ye karşı Cypher sorgularını yürütür.

**Algoritma Açıklaması**:
Cypher yürütücüsü, farklı grafik veritabanları arasında Cypher sorgularını yürütmek için birleşik bir arayüz sağlar. Veritabanına özgü bağlantı protokollerini, sorgu optimizasyonu ipuçlarını ve sonuç biçimi normalizasyonunu işler. Yürütücü, her veritabanı türü için uygun olan yeniden deneme mantığını, bağlantı havuzunu ve işlem yönetimini içerir.

**Çoklu Veritabanı Desteği**:
**Neo4j**: Bolt protokolü, işlem fonksiyonları, indeks ipuçları
**Memgraph**: Özel protokol, akışlı sonuçlar, analitik sorgular
**FalkorDB**: Redis protokolü adaptasyonu, bellek içi optimizasyonlar

**Yürütme Özellikleri**:
Veritabanından bağımsız bağlantı yönetimi
Sorgu doğrulaması ve sözdizimi kontrolü
Zaman aşımı ve kaynak limiti uygulama
Sonuç sayfalama ve akış
Veritabanı türüne göre performans izleme
Veritabanı örnekleri arasında otomatik geçiş

#### 8. Cevap Oluşturucu

**Amaç**: Sorgu sonuçlarından doğal bir dil cevabı oluşturur.

**Algoritma Açıklaması**:
Cevap Oluşturucu, yapılandırılmış sorgu sonuçlarını ve orijinal soruyu alır, ardından kapsamlı bir cevap oluşturmak için istem hizmetini kullanır. Basit şablon tabanlı yanıtlardan farklı olarak, grafik verilerini sorunun bağlamında yorumlamak için bir LLM kullanır, karmaşık ilişkileri, toplamaları ve çıkarımları işler. Oluşturucu, ontoloji yapısına ve grafikten alınan belirli üçlülere başvurarak akıl yürütmesini açıklayabilir.

**Cevap Oluşturma Süreci**:
Sorgu sonuçlarını yapılandırılmış bir bağlama dönüştürür
Açıklık için ilgili ontoloji tanımlarını ekler
Soru ve sonuçlarla bir istem oluşturur
LLM aracılığıyla doğal dil cevabı oluşturur
Cevabı sorgu amacına göre doğrular
Gerekirse belirli grafik varlıklarına alıntılar ekler

### Mevcut Hizmetlerle Entegrasyon

#### GraphRAG ile İlişki

**Tamamlayıcı**: onto-query semantik hassasiyet sağlarken, GraphRAG geniş kapsamlı bir kapsama sahiptir.
**Paylaşılan Altyapı**: Her ikisi de aynı bilgi grafiğini ve istem hizmetlerini kullanır.
**Sorgu Yönlendirmesi**: Sistem, sorunun türüne göre sorguları en uygun hizmete yönlendirebilir.
**Hibrit Mod**: Kapsamlı cevaplar için her iki yaklaşımı da birleştirebilir.

#### OntoRAG Çıkarma ile İlişki

**Paylaşılan Ontolojiler**: kg-extract-ontology tarafından yüklenen aynı ontoloji yapılandırmalarını kullanır.
**Paylaşılan Vektör Deposu**: Çıkarma hizmetinden alınan bellek içi gömülmeleri yeniden kullanır.
**Tutarlı Semantikler**: Sorgular, aynı ontolojik kısıtlamalarla oluşturulmuş grafikler üzerinde çalışır.

### Sorgu Örnekleri

#### Örnek 1: Basit Varlık Sorgusu
**Soru**: "Hangi hayvanlar memelidir?"
**Ontoloji Eşleşmesi**: [hayvan, memeli, subClassOf]
**Oluşturulan Sorgu**:
```cypher
MATCH (a:animal)-[:subClassOf*]->(m:mammal)
RETURN a.name
```

#### Örnek 2: İlişki Sorgusu
**Soru**: "Hangi belgeler John Smith tarafından yazılmıştır?"
**Ontoloji Eşleşmesi**: [belge, kişi, yazarıdır]
**Oluşturulan Sorgu**:
```cypher
MATCH (d:document)-[:has-author]->(p:person {name: "John Smith"})
RETURN d.title, d.date
```

#### Örnek 3: Toplama Sorgusu
**Soru**: "Kedilerin kaç tane bacağı vardır?"
**Ontoloji Eşleşmesi**: [kedi, bacak sayısı (veri tipi özelliği)]
**Oluşturulan Sorgu**:
```cypher
MATCH (c:cat)
RETURN c.name, c.number_of_legs
```

### Yapılandırma

```yaml
onto-query:
  embedding_model: "text-embedding-3-small"
  vector_store:
    shared_with_extractor: true  # Reuse kg-extract-ontology's store
  query_builder:
    model: "gpt-4"
    temperature: 0.1
    max_query_length: 1000
  graph_executor:
    timeout: 30000  # ms
    max_results: 1000
  answer_generator:
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 500
```

### Performans Optimizasyonları

#### Sorgu Optimizasyonu

**Ontoloji Budama**: Sadece gerekli ontoloji öğelerini istemlerde kullanın.
**Sorgu Önbelleği**: Sıkça sorulan soruları ve sorgularını önbelleğe alın.
**Sonuç Önbelleği**: Aynı sorgular için sonuçları belirli bir zaman aralığında saklayın.
**Toplu İşleme**: Birden fazla ilgili soruyu tek bir grafik geçişiyle işleyin.

#### Ölçeklenebilirlik Hususları

**Dağıtık Çalıştırma**: Alt sorguları grafik bölümlerine göre paralel hale getirin.
**Artan Sonuçlar**: Büyük veri kümeleri için sonuçları akış şeklinde gönderin.
**Yük Dengeleme**: Sorgu yükünü birden fazla hizmet örneğine dağıtın.
**Kaynak Havuzları**: Grafik veritabanlarına bağlantı havuzlarını yönetin.

### Hata Yönetimi

#### Hata Senaryoları

1. **Geçersiz Sorgu Oluşturma**: GraphRAG'e veya basit anahtar kelime aramasına geri dönün.
2. **Ontoloji Uyuşmazlığı**: Aramayı daha geniş bir ontoloji alt kümesine genişletin.
3. **Sorgu Zaman Aşımı**: Sorguyu basitleştirin veya zaman aşımı süresini artırın.
4. **Boş Sonuçlar**: Sorguyu yeniden formüle etmeyi veya ilgili soruları önerin.
5. **LLM Hizmeti Hatası**: Önbelleğe alınmış sorguları veya şablon tabanlı yanıtları kullanın.

### İzleme Metrikleri

Soru karmaşıklığı dağılımı
Ontoloji bölüm boyutları
Sorgu oluşturma başarı oranı
Grafik sorgu yürütme süresi
Cevap kalitesi puanları
Önbellek isabet oranları
Hata frekansları (türlere göre)

## Gelecek Geliştirmeler

1. **Ontoloji Öğrenimi**: Çıkarma kalıplarına göre ontolojileri otomatik olarak genişletin.
2. **Güvenilirlik Puanlama**: Çıkarılan üçlülere güvenilirlik puanları atayın.
3. **Açıklama Oluşturma**: Üçlü çıkarma için gerekçeler sağlayın.
4. **Aktif Öğrenme**: Belirsiz çıkarmalar için insan doğrulaması isteyin.

## Güvenlik Hususları

1. **İstem Enjeksiyonu Önleme**: İstem oluşturulmadan önce parça metnini temizleyin.
2. **Kaynak Limitleri**: Vektör deposu için bellek kullanımını sınırlayın.
3. **Hız Sınırlama**: İstem başına çıkarma isteklerini sınırlayın.
4. **Denetim Kaydı**: Tüm çıkarma isteklerini ve sonuçlarını izleyin.

## Test Stratejisi

### Birim Testleri

Çeşitli formatlarda ontoloji yükleyici
Gömme oluşturma ve depolama
Cümle bölme algoritmaları
Vektör benzerliği hesaplamaları
Üçlü ayrıştırma ve doğrulama

### Entegrasyon Testleri

Uçtan uca çıkarma hattı
Yapılandırma hizmeti entegrasyonu
İstem hizmeti etkileşimi
Eşzamanlı çıkarma işleme

### Performans Testleri

Büyük ontoloji işleme (1000+ sınıf)
Yüksek hacimli parça işleme
Yük altında bellek kullanımı
Gecikme ölçümleri

## Teslimat Planı

### Genel Bakış

OntoRAG sistemi, her fazda kademeli değer sağlayan ve tamamlanmış sisteme doğru ilerleyen dört ana fazda teslim edilecektir. Plan, öncelikle temel çıkarma yeteneklerini, ardından sorgu işlevselliğini ve ardından optimizasyonları ve gelişmiş özellikleri eklemeyi hedeflemektedir.

### 1. Faz: Temel ve Temel Çıkarma

**Hedef**: Basit vektör eşleştirmesiyle temel, ontoloji odaklı çıkarma hattını kurun.

#### 1. Adım: Ontoloji Yönetimi Temeli
Ontoloji yapılandırma yükleyici uygulayın (`OntologyLoader`).
Ontoloji JSON yapılarını ayrıştırın ve doğrulayın.
Bellekte ontoloji depolama ve erişim kalıplarını oluşturun.
Ontoloji yenileme mekanizmasını uygulayın.

**Başarı Kriterleri**:
Ontoloji yapılandırmalarını başarıyla yükleyin ve ayrıştırın.
Ontoloji yapısını ve tutarlılığını doğrulayın.
Birden fazla eşzamanlı ontolojiyi işleyin.

#### 2. Adım: Vektör Deposu Uygulaması
Başlangıç prototipi olarak basit NumPy tabanlı bir vektör deposu uygulayın.
FAISS vektör deposu uygulamasını ekleyin.
Vektör deposu arayüzü soyutlamasını oluşturun.
Yapılandırılabilir eşiklerle benzerlik araması uygulayın.

**Başarı Kriterleri**:
Gömme vektörlerini verimli bir şekilde depola ve geri yükle
<100ms gecikmeyle benzerlik araması yap
NumPy ve FAISS arka uçlarını destekle

#### 1.3 Adımı: Ontoloji Gömme İşlem Hattı
Gömme hizmetiyle entegre ol
`OntologyEmbedder` bileşenini uygula
Tüm ontoloji öğeleri için gömmeler oluştur
Vektör deposunda meta verilerle birlikte gömmeleri depola

**Başarı Kriterleri**:
Sınıflar ve özellikler için gömmeler oluştur
Uygun meta verilerle birlikte gömmeleri depola
Ontoloji güncellemelerinde gömmeleri yeniden oluştur

#### 1.4 Adımı: Metin İşleme Bileşenleri
NLTK/spaCy kullanarak cümle bölücü uygula
Cümleleri ve adlandırılmış varlıkları çıkar
Metin segmenti hiyerarşisi oluştur
Metin segmentleri için gömmeler oluştur

**Başarı Kriterleri**:
Metni doğru bir şekilde cümlelere böl
Anlamlı cümleleri çıkar
Bağlam ilişkilerini koru

#### 1.5 Adımı: Ontoloji Seçim Algoritması
Metin ve ontoloji arasındaki benzerlik eşleştirmesini uygula
Ontoloji öğeleri için bağımlılık çözümlemesi oluştur
Minimal, tutarlı ontoloji alt kümeleri oluştur
Alt küme oluşturma performansını optimize et

**Başarı Kriterleri**:
İlgili ontoloji öğelerini >%80 doğrulukla seç
Tüm gerekli bağımlılıkları dahil et
Alt kümeleri <500ms içinde oluştur

#### 1.6 Adımı: Temel Çıkarma Hizmeti
Çıkarma için istem oluşturma uygula
İstem hizmetiyle entegre ol
Üçlü yanıtları ayrıştır ve doğrula
`kg-extract-ontology` hizmet uç noktası oluştur

**Başarı Kriterleri**:
Ontolojiye uygun üçlüler çıkar
Tüm üçlüleri ontolojiye göre doğrula
Çıkarma hatalarını düzgün bir şekilde işle

### 2. Aşama: Sorgu Sistemi Uygulaması

**Amaç**: Çoklu arka uç desteğiyle ontolojiye duyarlı sorgu yetenekleri ekle.

#### 2.1 Adımı: Sorgu Temel Bileşenleri
Soru analizörünü uygula
Sorgular için ontoloji eşleştirici oluştur
Vektör aramayı sorgu bağlamı için uyarlayın
Arka uç yönlendirici bileşeni oluştur

**Başarı Kriterleri**:
Soruları anlamsal bileşenlere ayır
Soruları ilgili ontoloji öğelerine eşleştir
Sorguları uygun arka uca yönlendir

#### 2.2 Adımı: SPARQL Yolu Uygulaması
`onto-query-sparql` hizmetini uygula
LLM kullanarak SPARQL sorgu oluşturucu oluştur
SPARQL oluşturma için istem şablonları geliştir
Oluşturulan SPARQL sözdizimini doğrula

**Başarı Kriterleri**:
Geçerli SPARQL sorguları oluştur
Uygun SPARQL kalıplarını kullan
Karmaşık sorgu türlerini işle

#### 2.3 Adımı: SPARQL-Cassandra Motoru
Cassandra için rdflib Store arayüzünü uygula
CQL sorgu çevirmeni oluştur
Üçlü kalıp eşleştirmesini optimize et
SPARQL sonuç biçimlendirmesini işle

**Başarı Kriterleri**:
SPARQL sorgularını Cassandra üzerinde çalıştır
Yaygın SPARQL kalıplarını destekle
Sonuçları standart biçimde döndür

#### 2.4 Adımı: Cypher Yolu Uygulaması
`onto-query-cypher` hizmetini uygula
LLM kullanarak Cypher sorgu oluşturucu oluştur
Cypher oluşturma için istem şablonları geliştir
Oluşturulan Cypher sözdizimini doğrula

**Başarı Kriterleri**:
Geçerli Cypher sorguları oluştur
Uygun grafik kalıplarını kullan
Neo4j, Memgraph, FalkorDB'yi destekle

#### 2.5 Adımı: Cypher Yürütücü
Çoklu veritabanı Cypher yürütücüsünü uygulayın
Bolt protokolünü destekleyin (Neo4j/Memgraph)
Redis protokolünü destekleyin (FalkorDB)
Sonuç normalleştirmesini yönetin

**Başarı Kriterleri**:
Cypher'ı tüm hedef veritabanlarında çalıştırın
Veritabanına özgü farklılıkları ele alın
Bağlantı havuzlarını verimli bir şekilde koruyun

#### 2. Adım: Cevap Üretimi
Cevap üretici bileşenini uygulayın
Cevap sentezi için istemler oluşturun
Sorgu sonuçlarını LLM'nin kullanabileceği bir formata dönüştürün
Doğal dil cevapları oluşturun

**Başarı Kriterleri**:
Sorgu sonuçlarından doğru cevaplar üretin
Orijinal sorudan bağlamı koruyun
Açık, öz cevaplar sağlayın

### 3. Aşama: Optimizasyon ve Güvenilirlik

**Amaç**: Performansı optimize edin, önbellekleme ekleyin, hata yönetimini iyileştirin ve güvenilirliği artırın.

#### 3.1 Adım: Performans Optimizasyonu
Gömme önbelleklemesini uygulayın
Sorgu sonucu önbelleklemesini ekleyin
FAISS IVF indeksleriyle vektör aramayı optimize edin
Gömme işlemleri için toplu işleme uygulayın

**Başarı Kriterleri**:
Ortalama sorgu gecikmesini %50 azaltın
10 kat daha fazla eşzamanlı istek destekleyin
Saniyeden daha kısa yanıt sürelerini koruyun

#### 3.2 Adım: Gelişmiş Hata Yönetimi
Kapsamlı bir hata kurtarma mekanizması uygulayın
Sorgu yolları arasında yedekleme mekanizmaları ekleyin
Üstel geri çekilme ile yeniden deneme mantığı oluşturun
Hata günlüğünü ve tanılama bilgilerini iyileştirin

**Başarı Kriterleri**:
Tüm hata senaryolarını sorunsuz bir şekilde ele alın
Arka uçlar arasında otomatik geçiş
Hata ayıklama için ayrıntılı hata raporlama

#### 3.3 Adım: İzleme ve Gözlemlenebilirlik
Performans metrikleri toplama ekleyin
Sorgu izlemeyi uygulayın
Sağlık kontrol uç noktaları oluşturun
Kaynak kullanımı izlemeyi ekleyin

**Başarı Kriterleri**:
Tüm önemli performans göstergelerini izleyin
Engelleri hızlı bir şekilde belirleyin
Sistem sağlığını gerçek zamanlı olarak izleyin

#### 3.4 Adım: Yapılandırma Yönetimi
Dinamik yapılandırma güncellemelerini uygulayın
Yapılandırma doğrulama ekleyin
Yapılandırma şablonları oluşturun
Ortam özelinde ayarlara destek sağlayın

**Başarı Kriterleri**:
Yapılandırmayı yeniden başlatmadan güncelleyin
Tüm yapılandırma değişikliklerini doğrulayın
Birden çok dağıtım ortamını destekleyin

### 4. Aşama: Gelişmiş Özellikler

**Amaç**: Üretim dağıtımı ve gelişmiş işlevsellik için sofistike yetenekler ekleyin.

#### 4.1 Adım: Çoklu Ontoloji Desteği
Ontoloji seçimi mantığını uygulayın
Çapraz ontoloji sorgularını destekleyin
Ontoloji sürümlemesini yönetin
Ontoloji birleştirme yetenekleri oluşturun

**Başarı Kriterleri**:
Birden çok ontoloji üzerinde sorgu yapın
Ontoloji çakışmalarını ele alın
Ontoloji evrimini destekleyin

#### 4.2 Adım: Akıllı Sorgu Yönlendirme
Performans odaklı yönlendirme uygulayın
Sorgu karmaşıklığı analizini ekleyin
Adaptif yönlendirme algoritmaları oluşturun
Yollar için A/B testlerini destekleyin

**Başarı Kriterleri**:
Sorguları en uygun şekilde yönlendirin
Sorgu performansından öğrenin
Yönlendirmeyi zamanla iyileştirin

#### 4.3. Adım: Gelişmiş Çıkarma Özellikleri
Üçlüler için güvenilirlik puanı ekleyin
Açıklama oluşturma uygulayın
İyileştirme için geri bildirim döngüleri oluşturun
Artımlı öğrenmeyi destekleyin

**Başarı Kriterleri**:
Güvenilirlik puanları sağlayın
Çıkarma kararlarını açıklayın
Doğruluğu sürekli olarak iyileştirin

#### 4.4. Adım: Üretim Hazırlığı
Hız sınırlaması ekleyin
Kimlik doğrulama/yetkilendirme uygulayın
Dağıtım otomasyonu oluşturun
Yedekleme ve kurtarma ekleyin

**Başarı Kriterleri**:
Üretim için uygun güvenlik
Otomatikleştirilmiş dağıtım hattı
Afet kurtarma yeteneği

### Teslimat Aşamaları

1. **Aşama 1** (1. Aşamanın Sonu): Temel, ontoloji odaklı çıkarma işleminin çalışır durumda olması
2. **Aşama 2** (2. Aşamanın Sonu): Hem SPARQL hem de Cypher yollarına sahip tam sorgu sistemi
3. **Aşama 3** (3. Aşamanın Sonu): Optimize edilmiş, sağlam sistem, üretim ortamına hazır
4. **Aşama 4** (4. Aşamanın Sonu): Gelişmiş özelliklere sahip, üretim için hazır sistem

### Risk Azaltma

#### Teknik Riskler
**Vektör Depolama Ölçeklenebilirliği**: NumPy ile başlayın, FAISS'e kademeli olarak geçin
**Sorgu Oluşturma Doğruluğu**: Doğrulama ve yedekleme mekanizmaları uygulayın
**Arka Uç Uyumluluğu**: Her veritabanı türüyle kapsamlı bir şekilde test edin
**Performans Engelleri**: Erken ve sık sık profil oluşturun, yinelemeli olarak optimize edin

#### İşletim Riskleri
**Ontoloji Kalitesi**: Doğrulama ve tutarlılık kontrolü uygulayın
**Hizmet Bağımlılıkları**: Devre kesiciler ve yedeklemeler ekleyin
**Kaynak Kısıtlamaları**: İzleyin ve uygun limitler ayarlayın
**Veri Tutarlılığı**: Uygun işlem yönetimi uygulayın

### Başarı Metrikleri

#### 1. Aşama Başarı Metrikleri
Çıkarma doğruluğu: %90'ın üzerinde ontoloji uyumluluğu
İşleme hızı: Parça başına <1 saniye
Ontoloji yükleme süresi: <10 saniye
Vektör arama gecikmesi: <100 ms

#### 2. Aşama Başarı Metrikleri
Sorgu başarı oranı: %95'in üzerinde
Sorgu gecikmesi: Uçtan uca <2 saniye
Arka uç uyumluluğu: Hedef veritabanları için %100
Cevap doğruluğu: Mevcut verilere göre %85'in üzerinde

#### 3. Aşama Başarı Metrikleri
Sistem çalışma süresi: >%99.9
Hata kurtarma oranı: >%95
Önbellek isabet oranı: >%60
Eşzamanlı kullanıcılar: >100

#### 4. Aşama Başarı Metrikleri
Çoklu ontoloji sorguları: Tamamen destekleniyor
Yönlendirme optimizasyonu: Gecikmede %30 azalma
Güvenilirlik puanı doğruluğu: >%90
Üretim dağıtımı: Sıfır kesintiyle güncellemeler

## Referanslar

[OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
[GraphRAG Architecture](https://github.com/microsoft/graphrag)
[Sentence Transformers](https://www.sbert.net/)
[FAISS Vector Search](https://github.com/facebookresearch/faiss)
[spaCy NLP Library](https://spacy.io/)
[rdflib Documentation](https://rdflib.readthedocs.io/)
[Neo4j Bolt Protocol](https://neo4j.com/docs/bolt/current/)
