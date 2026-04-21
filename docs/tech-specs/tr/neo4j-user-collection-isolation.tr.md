---
layout: default
title: "Neo4j Kullanıcı/Koleksiyon İzolasyonu Desteği"
parent: "Turkish (Beta)"
---

# Neo4j Kullanıcı/Koleksiyon İzolasyonu Desteği

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Problem Tanımı

Mevcut Neo4j üçlü depolama ve sorgu uygulaması, kullanıcı/koleksiyon izolasyonu eksikliği nedeniyle çoklu kiracılık güvenliği sorunlarına yol açmaktadır. Tüm üçlüler, kullanıcıların diğer kullanıcıların verilerine erişmesini veya koleksiyonları karıştırmasını engelleyen herhangi bir mekanizma olmadan aynı grafik alanında saklanmaktadır.

TrustGraph'taki diğer depolama arka uçlarından farklı olarak:
**Cassandra**: Her kullanıcı için ayrı anahtarlar ve her koleksiyon için tablolar kullanır.
**Vektör depoları** (Milvus, Qdrant, Pinecone): Koleksiyona özgü ad alanlarını kullanır.
**Neo4j**: Şu anda tüm verileri tek bir grafik alanında paylaşır (güvenlik açığı).

## Mevcut Mimari

### Veri Modeli
**Düğümler**: `:Node` etiketi ile `uri` özelliği, `:Literal` etiketi ile `value` özelliği.
**İlişkiler**: `:Rel` etiketi ile `uri` özelliği.
**Dizinler**: `Node.uri`, `Literal.value`, `Rel.uri`.

### Mesaj Akışı
`Triples` mesajları `metadata.user` ve `metadata.collection` alanlarını içerir.
Depolama hizmeti kullanıcı/koleksiyon bilgilerini alır, ancak bunları yoksayar.
Sorgu hizmeti `TriplesQueryRequest` içinde `user` ve `collection`'i bekler, ancak bunları yoksayar.

### Mevcut Güvenlik Sorunu
```cypher
# Any user can query any data - no isolation
MATCH (src:Node)-[rel:Rel]->(dest:Node) 
RETURN src.uri, rel.uri, dest.uri
```

## Önerilen Çözüm: Özellik Tabanlı Filtreleme (Önerilen)

### Genel Bakış
Tüm düğümlere ve ilişkilerlere `user` ve `collection` özelliklerini ekleyin, ardından tüm işlemleri bu özelliklere göre filtreleyin. Bu yaklaşım, güçlü bir izolasyon sağlarken sorgu esnekliğini ve geriye dönük uyumluluğu korur.

### Veri Modeli Değişiklikleri

#### Gelişmiş Düğüm Yapısı
```cypher
// Node entities
CREATE (n:Node {
  uri: "http://example.com/entity1",
  user: "john_doe", 
  collection: "production_v1"
})

// Literal entities  
CREATE (n:Literal {
  value: "literal value",
  user: "john_doe",
  collection: "production_v1" 
})
```

#### Gelişmiş İlişki Yapısı
```cypher
// Relationships with user/collection properties
CREATE (src)-[:Rel {
  uri: "http://example.com/predicate1",
  user: "john_doe",
  collection: "production_v1"
}]->(dest)
```

#### Güncellenmiş İndeksler
```cypher
// Compound indexes for efficient filtering
CREATE INDEX node_user_collection_uri FOR (n:Node) ON (n.user, n.collection, n.uri);
CREATE INDEX literal_user_collection_value FOR (n:Literal) ON (n.user, n.collection, n.value);
CREATE INDEX rel_user_collection_uri FOR ()-[r:Rel]-() ON (r.user, r.collection, r.uri);

// Maintain existing indexes for backwards compatibility (optional)
CREATE INDEX Node_uri FOR (n:Node) ON (n.uri);
CREATE INDEX Literal_value FOR (n:Literal) ON (n.value);
CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri);
```

### Uygulama Değişiklikleri

#### Depolama Hizmeti (`write.py`)

**Mevcut Kod:**
```python
def create_node(self, uri):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri})",
        uri=uri, database_=self.db,
    ).summary
```

**Güncellenmiş Kod:**
```python
def create_node(self, uri, user, collection):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
        uri=uri, user=user, collection=collection, database_=self.db,
    ).summary
```

**Geliştirilmiş `store_triples` Metodu:**
```python
async def store_triples(self, message):
    user = message.metadata.user
    collection = message.metadata.collection
    
    for t in message.triples:
        self.create_node(t.s.value, user, collection)
        
        if t.o.is_uri:
            self.create_node(t.o.value, user, collection)  
            self.relate_node(t.s.value, t.p.value, t.o.value, user, collection)
        else:
            self.create_literal(t.o.value, user, collection)
            self.relate_literal(t.s.value, t.p.value, t.o.value, user, collection)
```

#### Sorgu Hizmeti (`service.py`)

**Mevcut Kod:**
```python
records, summary, keys = self.io.execute_query(
    "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) "
    "RETURN dest.uri as dest",
    src=query.s.value, rel=query.p.value, database_=self.db,
)
```

**Güncellenmiş Kod:**
```python
records, summary, keys = self.io.execute_query(
    "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
    "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
    "(dest:Node {user: $user, collection: $collection}) "
    "RETURN dest.uri as dest",
    src=query.s.value, rel=query.p.value, 
    user=query.user, collection=query.collection,
    database_=self.db,
)
```

### Göç Stratejisi

#### 1. Aşama: Yeni Verilere Özellikler Ekleme
1. Kullanıcı/koleksiyon özelliklerini yeni üçlülere eklemek için depolama hizmetini güncelleyin.
2. Geriye dönük uyumluluğu korumak için sorgularda özelliklerin gerekli olmaması.
3. Mevcut veriler erişilebilir durumda kalır, ancak izole edilmez.

#### 2. Aşama: Mevcut Verilerin Taşınması
```cypher
// Migrate existing nodes (requires default user/collection assignment)
MATCH (n:Node) WHERE n.user IS NULL
SET n.user = 'legacy_user', n.collection = 'default_collection';

MATCH (n:Literal) WHERE n.user IS NULL  
SET n.user = 'legacy_user', n.collection = 'default_collection';

MATCH ()-[r:Rel]->() WHERE r.user IS NULL
SET r.user = 'legacy_user', r.collection = 'default_collection';
```

#### 3. Aşama: İzolasyonu Sağlama
1. Sorgu hizmetini, kullanıcı/koleksiyon filtrelemesini gerektirecek şekilde güncelleyin.
2. Doğru kullanıcı/koleksiyon bağlamı olmadan yapılan sorguları reddedecek doğrulama ekleyin.
3. Eski veri erişim yollarını kaldırın.

### Güvenlik Hususları

#### Sorgu Doğrulama
```python
async def query_triples(self, query):
    # Validate user/collection parameters
    if not query.user or not query.collection:
        raise ValueError("User and collection must be specified")
    
    # All queries must include user/collection filters
    # ... rest of implementation
```

#### Parametre Enjeksiyonunu Önleme
Yalnızca parametreli sorguları kullanın
Kullanıcı/toplam değerlerini izin verilen kalıplara karşı doğrulayın
Neo4j özellik adı gereksinimleri için sanitizasyonu göz önünde bulundurun

#### Denetim Kaydı
```python
logger.info(f"Query executed - User: {query.user}, Collection: {query.collection}, "
           f"Pattern: {query.s}/{query.p}/{query.o}")
```

## Alternatif Yaklaşımlar

### Seçenek 2: Etiket Tabanlı İzolasyon

**Yaklaşım**: Dinamik etiketler kullanın, örneğin `User_john_Collection_prod`

**Avantajları:**
Etiket filtreleme yoluyla güçlü izolasyon
Etiket indeksleriyle verimli sorgu performansı
Açık veri ayrımı

**Dezavantajları:**
Neo4j'nin etiket sayısı konusunda pratik sınırlamaları vardır (~1000'ler)
Karmaşık etiket adı oluşturma ve temizleme
Gerekli olduğunda koleksiyonlar arasında sorgu yapmak zordur

**Uygulama Örneği:**
```cypher
CREATE (n:Node:User_john_Collection_prod {uri: "http://example.com/entity"})
MATCH (n:User_john_Collection_prod) WHERE n:Node RETURN n
```

### Seçenek 3: Kullanıcı Başına Veritabanı

**Yaklaşım:** Her kullanıcı veya kullanıcı/koleksiyon kombinasyonu için ayrı Neo4j veritabanları oluşturun.

**Avantajları:**
Tam veri izolasyonu
Çapraz bulaşma riski yok
Kullanıcı başına bağımsız ölçeklendirme

**Dezavantajları:**
Kaynak yükü (her veritabanı bellek tüketir)
Karmaşık veritabanı yaşam döngüsü yönetimi
Neo4j Community Edition veritabanı limitleri
Kullanıcılar arası analizler yapmak zordur.

### Seçenek 4: Bileşik Anahtar Stratejisi

**Yaklaşım:** Tüm URI'ları ve değerleri kullanıcı/koleksiyon bilgileriyle ön ekleyin.

**Avantajları:**
Mevcut sorgularla geriye dönük uyumluluk
Basit uygulama
Şema değişiklikleri gerektirmez

**Dezavantajları:**
URI kirliliği, veri anlamını etkiler
Daha az verimli sorgular (dize ön eki eşleştirme)
RDF/semantik web standartlarını ihlal eder

**Uygulama Örneği:**
```python
def make_composite_uri(uri, user, collection):
    return f"usr:{user}:col:{collection}:uri:{uri}"
```

## Uygulama Planı

### Aşama 1: Temel (1. Hafta)
1. [ ] Depolama hizmetini, kullanıcı/koleksiyon özelliklerini kabul edecek ve saklayacak şekilde güncelleyin.
2. [ ] Verimli sorgulama için bileşik indeksler ekleyin.
3. [ ] Geriye dönük uyumluluk katmanı uygulayın.
4. [ ] Yeni işlevler için birim testleri oluşturun.

### Aşama 2: Sorgu Güncellemeleri (2. Hafta)
1. [ ] Tüm sorgu kalıplarını, kullanıcı/koleksiyon filtrelerini içerecek şekilde güncelleyin.
2. [ ] Sorgu doğrulaması ve güvenlik kontrolleri ekleyin.
3. [ ] Entegrasyon testlerini güncelleyin.
4. [ ] Filtrelenmiş sorgularla performans testi yapın.

### Aşama 3: Göç ve Dağıtım (3. Hafta)
1. [ ] Mevcut Neo4j örnekleri için veri geçiş betikleri oluşturun.
2. [ ] Dağıtım belgeleri ve çalıştırma kılavuzları.
3. [ ] İzolasyon ihlalleri için izleme ve uyarı.
4. [ ] Çok sayıda kullanıcı/koleksiyonla uçtan uca testler yapın.

### Aşama 4: Güçlendirme (4. Hafta)
1. [ ] Eski uyumluluk modunu kaldırın.
2. [ ] Kapsamlı denetim kaydı ekleyin.
3. [ ] Güvenlik incelemesi ve sızma testi.
4. [ ] Performans optimizasyonu.

## Test Stratejisi

### Birim Testleri
```python
def test_user_collection_isolation():
    # Store triples for user1/collection1
    processor.store_triples(triples_user1_coll1)
    
    # Store triples for user2/collection2  
    processor.store_triples(triples_user2_coll2)
    
    # Query as user1 should only return user1's data
    results = processor.query_triples(query_user1_coll1)
    assert all_results_belong_to_user1_coll1(results)
    
    # Query as user2 should only return user2's data
    results = processor.query_triples(query_user2_coll2)
    assert all_results_belong_to_user2_coll2(results)
```

### Entegrasyon Testleri
Eş zamanlı veri içeren çok kullanıcılı senaryolar
Koleksiyonlar arası sorgular (başarısız olmalıdır)
Mevcut verilerle yapılan geçiş testleri
Büyük veri kümeleriyle yapılan performans ölçümleri

### Güvenlik Testleri
Diğer kullanıcıların verilerine erişme girişimleri
Kullanıcı/koleksiyon parametrelerine yönelik SQL enjeksiyonu tarzı saldırılar
Çeşitli sorgu kalıpları altında tam izolasyonu doğrulayın

## Performans Hususları

### İndeks Stratejisi
Optimum filtreleme için `(user, collection, uri)` üzerinde birleşik indeksler
Bazı koleksiyonların çok daha büyük olması durumunda, kısmi indeksleri göz önünde bulundurun
İndeks kullanımını ve sorgu performansını izleyin

### Sorgu Optimizasyonu
Filtrelenmiş sorgularda indeks kullanımını doğrulamak için EXPLAIN'i kullanın
Sık erişilen veriler için sorgu sonucu önbelleklemesini göz önünde bulundurun
Çok sayıda kullanıcı/koleksiyonla bellek kullanımını analiz edin

### Ölçeklenebilirlik
Her kullanıcı/koleksiyon kombinasyonu, ayrı veri adacıkları oluşturur
Veritabanı boyutunu ve bağlantı havuzu kullanımını izleyin
Gerekirse, yatay ölçeklendirme stratejilerini göz önünde bulundurun

## Güvenlik ve Uyumluluk

### Veri İzolasyon Garantileri
**Fiziksel**: Tüm kullanıcı verileri, açık kullanıcı/koleksiyon özellikleri ile saklanır
**Mantıksal**: Tüm sorgular, kullanıcı/koleksiyon bağlamıyla filtrelenir
**Erişim Kontrolü**: Hizmet seviyesindeki doğrulama, yetkisiz erişimi engeller

### Denetim Gereksinimleri
Tüm veri erişimlerini kullanıcı/koleksiyon bağlamıyla kaydedin
Geçiş etkinliklerini ve veri hareketlerini izleyin
İzolasyon ihlali girişimlerini izleyin

### Uyumluluk Hususları
GDPR: Kullanıcıya özel verileri bulma ve silme yeteneğinin geliştirilmesi
SOC2: Açık veri izolasyonu ve erişim kontrolleri
HIPAA: Sağlık verileri için güçlü kiracı izolasyonu

## Riskler ve Önlemler

| Risk | Etki | Olasılık | Önlem |
|------|--------|------------|------------|
| Sorguda eksik kullanıcı/koleksiyon filtresi | Yüksek | Orta | Zorunlu doğrulama, kapsamlı testler |
| Performans düşüşü | Orta | Düşük | İndeks optimizasyonu, sorgu analizi |
| Geçiş sırasında veri bozulması | Yüksek | Düşük | Yedekleme stratejisi, geri alma prosedürleri |
| Karmaşık, koleksiyonlar arası sorgular | Orta | Orta | Sorgu kalıplarını belgeleyin, örnekler sağlayın |

## Başarı Kriterleri

1. **Güvenlik**: Üretimde, kullanıcılar arası veri erişiminin sıfır olması
2. **Performans**: Filtrelenmemiş sorgulara kıyasla %10'dan düşük sorgu performans etkisi
3. **Geçiş**: Mevcut verilerin %100'ü, kayıp olmadan başarıyla geçirilmiştir
4. **Kullanılabilirlik**: Tüm mevcut sorgu kalıpları, kullanıcı/koleksiyon bağlamıyla çalışır
5. **Uyumluluk**: Kullanıcı/koleksiyon verilerine yapılan tüm erişimlerin tam denetim kaydı

## Sonuç

Özellik tabanlı filtreleme yaklaşımı, Neo4j'ye kullanıcı/koleksiyon izolasyonu eklemek için güvenlik, performans ve bakım açısından en iyi dengeyi sağlar. TrustGraph'ın mevcut çok kiracılık kalıplarıyla uyumludur ve aynı zamanda Neo4j'nin grafik sorgulama ve indeksleme konusundaki güçlü yönlerinden yararlanır.

Bu çözüm, TrustGraph'ın Neo4j arka ucunun, diğer depolama arka uçları ile aynı güvenlik standartlarını karşılamasını sağlar ve veri izolasyonu güvenlik açıklarını önlerken, grafik sorgularının esnekliğini ve gücünü korur.
