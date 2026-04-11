# Ontoloji Yapısı Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph sistemindeki ontolojilerin yapısını ve biçimini tanımlar. Ontolojiler, sınıfları, özellikleri ve ilişkileri tanımlayan resmi bilgi modelleri sağlar ve akıl yürütme ve çıkarım yeteneklerini destekler. Sistem, OWL'den ilham alan bir yapılandırma biçimi kullanır ve bu, OWL/RDFS kavramlarını geniş ölçüde temsil ederken aynı zamanda TrustGraph'ın gereksinimleri için optimize edilmiştir.

**İsimlendirme Kuralları**: Bu proje, yılan_biçimi yerine tüm tanımlayıcılar (yapılandırma anahtarları, API uç noktaları, modül adları vb.) için kebab-case kullanır.

## Hedefler

**Sınıf ve Özellik Yönetimi**: OWL benzeri sınıfları, özellikleri, etki alanlarını, aralıkları ve tür kısıtlamalarını tanımlayın.
**Zengin Anlamsal Destek**: Etiketler, çoklu dil desteği ve resmi kısıtlamalar dahil olmak üzere kapsamlı RDFS/OWL özellikleri sağlayın.
**Çoklu Ontoloji Desteği**: Birden fazla ontolojinin birlikte var olmasına ve etkileşimde olmasına izin verin.
**Doğrulama ve Akıl Yürütme**: Ontolojilerin, tutarlılık kontrolü ve çıkarım desteği ile OWL benzeri standartlara uygun olduğundan emin olun.
**Standart Uyumluluğu**: İç optimizasyonu korurken standart formatlarda (Turtle, RDF/XML, OWL/XML) içe/dışa aktarma desteğini sağlayın.

## Arka Plan

TrustGraph, ontolojileri esnek bir anahtar-değer sisteminde yapılandırma öğeleri olarak saklar. Biçim OWL (Web Ontology Language) tarafından ilham alınmış olsa da, TrustGraph'ın belirli kullanım durumları için optimize edilmiştir ve tüm OWL özelliklerine kesin olarak uymamaktadır.

TrustGraph'taki ontolojiler şunları sağlar:
Resmi nesne türlerinin ve özelliklerinin tanımlanması
Özellik etki alanlarının, aralıklarının ve tür kısıtlamalarının belirtilmesi
Mantıksal akıl yürütme ve çıkarım
Karmaşık ilişkiler ve kardinalite kısıtlamaları
Uluslararasılaştırma için çoklu dil desteği

## Ontoloji Yapısı

### Yapılandırma Depolama

Ontolojiler, aşağıdaki kalıba sahip yapılandırma öğeleri olarak saklanır:
**Tür**: `ontology`
**Anahtar**: Benzersiz ontoloji tanımlayıcısı (örneğin, `natural-world`, `domain-model`)
**Değer**: JSON formatında eksiksiz ontoloji

### JSON Yapısı

Ontoloji JSON biçimi, dört ana bölümden oluşur:

#### 1. Meta Veriler

Ontoloji hakkında idari ve tanımlayıcı bilgiler içerir:

```json
{
  "metadata": {
    "name": "The natural world",
    "description": "Ontology covering the natural order",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "current-user",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  }
}
```

**Alanlar:**
`name`: Ontolojinin insan tarafından okunabilir adı
`description`: Ontolojinin amacının kısa açıklaması
`version`: Semantik sürüm numarası
`created`: Oluşturulma zamanının ISO 8601 zaman damgası
`modified`: Son değişiklik zamanının ISO 8601 zaman damgası
`creator`: Ontolojiyi oluşturan kullanıcı/sistemin kimliği
`namespace`: Ontoloji öğeleri için temel URI
`imports`: İçe aktarılan ontoloji URI'lerinin dizisi

#### 2. Sınıflar

Nesne türlerini ve hiyerarşik ilişkilerini tanımlar:

```json
{
  "classes": {
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Animal", "lang": "en"}],
      "rdfs:comment": "An animal",
      "rdfs:subClassOf": "lifeform",
      "owl:equivalentClass": ["creature"],
      "owl:disjointWith": ["plant"],
      "dcterms:identifier": "ANI-001"
    }
  }
}
```

**Desteklenen Özellikler:**
`uri`: Sınıfın tam URI'si
`type`: Her zaman `"owl:Class"`
`rdfs:label`: Dil etiketli etiketlerin dizisi
`rdfs:comment`: Sınıfın açıklaması
`rdfs:subClassOf`: Üst sınıf tanımlayıcısı (tekli miras)
`owl:equivalentClass`: Eşdeğer sınıf tanımlayıcılarının dizisi
`owl:disjointWith`: Ayrık sınıf tanımlayıcılarının dizisi
`dcterms:identifier`: İsteğe bağlı harici referans tanımlayıcısı

#### 3. Nesne Özellikleri

Örnekleri diğer örneklere bağlayan özellikler:

```json
{
  "objectProperties": {
    "has-parent": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#has-parent",
      "type": "owl:ObjectProperty",
      "rdfs:label": [{"value": "has parent", "lang": "en"}],
      "rdfs:comment": "Links an animal to its parent",
      "rdfs:domain": "animal",
      "rdfs:range": "animal",
      "owl:inverseOf": "parent-of",
      "owl:functionalProperty": false
    }
  }
}
```

**Desteklenen Özellikler:**
`uri`: Özelliğin tam URI'si
`type`: Her zaman `"owl:ObjectProperty"`
`rdfs:label`: Dil etiketli etiketlerin dizisi
`rdfs:comment`: Özelliğin açıklaması
`rdfs:domain`: Bu özelliğe sahip sınıf tanımlayıcısı
`rdfs:range`: Özellik değerleri için sınıf tanımlayıcısı
`owl:inverseOf`: Ters özelliğin tanımlayıcısı
`owl:functionalProperty`: En fazla bir değer olduğunu gösteren boolean değeri
`owl:inverseFunctionalProperty`: Benzersiz tanımlayıcı özellikleri için boolean değeri

#### 4. Veri Tipi Özellikleri

Örnekleri, literal değerlere bağlayan özellikler:

```json
{
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "number of legs", "lang": "en"}],
      "rdfs:comment": "Count of number of legs of the animal",
      "rdfs:domain": "animal",
      "rdfs:range": "xsd:nonNegativeInteger",
      "owl:functionalProperty": true,
      "owl:minCardinality": 0,
      "owl:maxCardinality": 1
    }
  }
}
```

**Desteklenen Özellikler:**
`uri`: Özelliğin tam URI'si
`type`: Her zaman `"owl:DatatypeProperty"`
`rdfs:label`: Dil etiketli etiketlerin dizisi
`rdfs:comment`: Özelliğin açıklaması
`rdfs:domain`: Bu özelliğe sahip sınıf tanımlayıcısı
`rdfs:range`: Özellik değerleri için XSD veri türü
`owl:functionalProperty`: En fazla bir değer olduğunu gösteren boolean değeri
`owl:minCardinality`: Minimum değer sayısı (isteğe bağlı)
`owl:maxCardinality`: Maksimum değer sayısı (isteğe bağlı)
`owl:cardinality`: Tam değer sayısı (isteğe bağlı)

### Desteklenen XSD Veri Türleri

Aşağıdaki XML Şema veri türleri, veri türü özellik aralıkları için desteklenmektedir:

`xsd:string` - Metin değerleri
`xsd:integer` - Tamsayılar
`xsd:nonNegativeInteger` - Negatif olmayan tamsayılar
`xsd:float` - Ondalık sayılar
`xsd:double` - Çift hassasiyetli sayılar
`xsd:boolean` - Doğru/yanlış değerleri
`xsd:dateTime` - Tarih ve saat değerleri
`xsd:date` - Tarih değerleri
`xsd:anyURI` - URI referansları

### Dil Desteği

Etiketler ve yorumlar, W3C dil etiketi biçimini kullanarak çoklu dilleri destekler:

```json
{
  "rdfs:label": [
    {"value": "Animal", "lang": "en"},
    {"value": "Tier", "lang": "de"},
    {"value": "Animal", "lang": "es"}
  ]
}
```

## Örnek Ontoloji

İşte basit bir ontolojinin eksiksiz bir örneği:

```json
{
  "metadata": {
    "name": "The natural world",
    "description": "Ontology covering the natural order",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "current-user",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  },
  "classes": {
    "lifeform": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#lifeform",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Lifeform", "lang": "en"}],
      "rdfs:comment": "A living thing"
    },
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Animal", "lang": "en"}],
      "rdfs:comment": "An animal",
      "rdfs:subClassOf": "lifeform"
    },
    "cat": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#cat",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Cat", "lang": "en"}],
      "rdfs:comment": "A cat",
      "rdfs:subClassOf": "animal"
    },
    "dog": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#dog",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Dog", "lang": "en"}],
      "rdfs:comment": "A dog",
      "rdfs:subClassOf": "animal",
      "owl:disjointWith": ["cat"]
    }
  },
  "objectProperties": {},
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "number-of-legs", "lang": "en"}],
      "rdfs:comment": "Count of number of legs of the animal",
      "rdfs:range": "xsd:nonNegativeInteger",
      "rdfs:domain": "animal"
    }
  }
}
```

## Doğrulama Kuralları

### Yapısal Doğrulama

1. **URI Tutarlılığı**: Tüm URI'ler `{namespace}#{identifier}` kalıbını takip etmelidir.
2. **Sınıf Hiyerarşisi**: `rdfs:subClassOf` içinde döngüsel miras ilişkisi olmamalıdır.
3. **Özellik Alanları/Aralıkları**: Mevcut sınıflara veya geçerli XSD türlerine başvurmalıdır.
4. **Ayrık Sınıflar**: Birbirinin alt sınıfı olamazlar.
5. **Ters Özellikler**: Belirtilmişse, çift yönlü olmalıdır.

### Anlamsal Doğrulama

1. **Benzersiz Tanımlayıcılar**: Sınıf ve özellik tanımlayıcıları, bir ontoloji içinde benzersiz olmalıdır.
2. **Dil Etiketleri**: BCP 47 dil etiketi formatını takip etmelidir.
3. **Kardinalite Kısıtlamaları**: Hem belirtilmişse, `minCardinality` ≤ `maxCardinality` olmalıdır.
4. **Fonksiyonel Özellikler**: `maxCardinality` > 1 olamaz.

## İçe/Dışa Aktarma Formatı Desteği

İç format JSON olmasına rağmen, sistem standart ontoloji formatlarına dönüştürmeyi destekler:

**Turtle (.ttl)** - RDF'nin kompakt seri hale getirilmesi
**RDF/XML (.rdf, .owl)** - W3C standardı formatı
**OWL/XML (.owx)** - OWL'e özel XML formatı
**JSON-LD (.jsonld)** - Bağlı Veri için JSON

## Referanslar

[OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
[RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
[XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/)
[BCP 47 Language Tags](https://tools.ietf.org/html/bcp47)