# Vektör Depolama Yaşam Döngüsü Yönetimi

## Genel Bakış

Bu belge, TrustGraph'ın farklı arka uç uygulamaları (Qdrant, Pinecone, Milvus) arasında vektör depolama koleksiyonlarını nasıl yönettiğini açıklamaktadır. Tasarım, sabit boyut değerleri kullanmadan farklı boyutlara sahip gömülmeleri destekleme zorluğunu ele almaktadır.

## Problem Tanımı

Vektör depoları, koleksiyonlar/indeksler oluşturulurken gömme boyutunun belirtilmesini gerektirir. Ancak:
Farklı gömme modelleri farklı boyutlar üretir (örneğin, 384, 768, 1536).
Boyut, ilk gömme oluşturulana kadar bilinmemektedir.
Tek bir TrustGraph koleksiyonu, birden fazla modelden gömmeler alabilir.
Bir boyutu (örneğin, 384) sabit kodlamak, diğer gömme boyutlarıyla uyumsuzluğa neden olur.

## Tasarım İlkeleri

1. **Gecikmeli Oluşturma**: Koleksiyonlar, koleksiyon yönetimi işlemlerinin aksine, ilk yazma sırasında talep üzerine oluşturulur.
2. **Boyut Tabanlı İsimlendirme**: Koleksiyon adları, gömme boyutunu bir sonek olarak içerir.
3. **Nazik Bozulma**: Var olmayan koleksiyonlara yapılan sorgular, hatalar yerine boş sonuçlar döndürür.
4. **Çok Boyutlu Destek**: Tek bir mantıksal koleksiyon, birden fazla fiziksel koleksiyona (her biri bir boyut için bir tane) sahip olabilir.

## Mimari

### Koleksiyon İsimlendirme Kuralı

Vektör depolama koleksiyonları, birden fazla gömme boyutunu desteklemek için boyut soneklerini kullanır:

**Belge Gömme:**
Qdrant: `d_{user}_{collection}_{dimension}`
Pinecone: `d-{user}-{collection}-{dimension}`
Milvus: `doc_{user}_{collection}_{dimension}`

**Graf Gömme:**
Qdrant: `t_{user}_{collection}_{dimension}`
Pinecone: `t-{user}-{collection}-{dimension}`
Milvus: `entity_{user}_{collection}_{dimension}`

Örnekler:
`d_alice_papers_384` - 384 boyutlu gömmelere sahip Alice'in makale koleksiyonu
`d_alice_papers_768` - Aynı mantıksal koleksiyon, 768 boyutlu gömmelerle
`t_bob_knowledge_1536` - 1536 boyutlu gömmelere sahip Bob'un bilgi grafiği

### Yaşam Döngüsü Aşamaları

#### 1. Koleksiyon Oluşturma İsteği

**İstek Akışı:**
```
User/System → Librarian → Storage Management Topic → Vector Stores
```

**Davranış:**
Kütüphaneci, `create-collection` isteklerini tüm depolama arka uçlarına yayınlar.
Vektör depolama işlemcileri isteği kabul eder, ancak **fiziksel koleksiyonlar oluşturmaz**.
Yanıt, başarıyla birlikte hemen döndürülür.
Gerçek koleksiyon oluşturma, ilk yazma işlemine kadar ertelenir.

**Gerekçe:**
Boyut, oluşturma zamanında bilinmemektedir.
Yanlış boyutlara sahip koleksiyonların oluşturulması engellenir.
Koleksiyon yönetimi mantığını basitleştirir.

#### 2. Yazma İşlemleri (Gecikmeli Oluşturma)

**Yazma Akışı:**
```
Data → Storage Processor → Check Collection → Create if Needed → Insert
```

**Davranış:**
1. Vektörden gömme boyutunu çıkarın: `dim = len(vector)`
2. Boyut sonekiyle koleksiyon adını oluşturun
3. Belirli o boyuta sahip koleksiyonun var olup olmadığını kontrol edin
4. Yoksa:
   Doğru boyuta sahip bir koleksiyon oluşturun
   Kaydı tutun: `"Lazily creating collection {name} with dimension {dim}"`
5. Gömme değerini, boyutuna özel koleksiyona ekleyin

**Örnek Senaryo:**
```
1. User creates collection "papers"
   → No physical collections created yet

2. First document with 384-dim embedding arrives
   → Creates d_user_papers_384
   → Inserts data

3. Second document with 768-dim embedding arrives
   → Creates d_user_papers_768
   → Inserts data

Result: Two physical collections for one logical collection
```

#### 3. Sorgu İşlemleri

**Sorgu Akışı:**
```
Query Vector → Determine Dimension → Check Collection → Search or Return Empty
```

**Davranış:**
1. Sorgu vektöründen boyutu çıkarın: `dim = len(vector)`
2. Boyut sonekiyle koleksiyon adını oluşturun
3. Koleksiyonun var olup olmadığını kontrol edin
4. Varsa:
   Benzerlik araması yapın
   Sonuçları döndürün
5. Yoksa:
   Kaydı tutun: `"Collection {name} does not exist, returning empty results"`
   Boş bir liste döndürün (hata yükseltilmez)

**Aynı Sorguda Birden Fazla Boyut:**
Sorgu farklı boyutlardaki vektörler içeriyorsa
Her boyut, ilgili koleksiyonunu sorgular
Sonuçlar birleştirilir
Eksik koleksiyonlar atlanır (hata olarak değerlendirilmez)

**Gerekçe:**
Boş bir koleksiyonu sorgulamak geçerli bir kullanım durumudur
Boş sonuçlar döndürmek anlamsal olarak doğrudur
Sistem başlatılırken veya veri yüklemesinden önce hataları önler

#### 4. Koleksiyon Silme

**Silme Akışı:**
```
Delete Request → List All Collections → Filter by Prefix → Delete All Matches
```

**Davranış:**
1. Önek kalıbını oluştur: `d_{user}_{collection}_` (sonundaki alt çizgiye dikkat edin)
2. Vektör deposundaki tüm koleksiyonları listele
3. Öneğe uyan koleksiyonları filtrele
4. Tüm eşleşen koleksiyonları sil
5. Her silme işlemini kaydet: `"Deleted collection {name}"`
6. Özet günlük: `"Deleted {count} collection(s) for {user}/{collection}"`

**Örnek:**
```
Collections in store:
- d_alice_papers_384
- d_alice_papers_768
- d_alice_reports_384
- d_bob_papers_384

Delete "papers" for alice:
→ Deletes: d_alice_papers_384, d_alice_papers_768
→ Keeps: d_alice_reports_384, d_bob_papers_384
```

**Gerekçe:**
Tüm boyut varyantlarının tamamen temizlenmesini sağlar.
Desen eşleştirme, yanlışlıkla ilgili olmayan koleksiyonların silinmesini önler.
Kullanıcı açısından atomik bir işlem (tüm boyutlar birlikte silinir).

## Davranışsal Özellikler

### Normal İşlemler

**Koleksiyon Oluşturma:**
✓ Hemen başarı döndürür.
✓ Herhangi bir fiziksel depolama alanı ayrılmaz.
✓ Hızlı işlem (arka uç G/Ç yok).

**İlk Yazma:**
✓ Doğru boyuta sahip koleksiyon oluşturur.
✓ Koleksiyon oluşturma ek yükü nedeniyle biraz daha yavaştır.
✓ Aynı boyuta yapılan sonraki yazmalar hızlıdır.

**Herhangi Bir Yazmadan Önce Sorgular:**
✓ Boş sonuçlar döndürür.
✓ Herhangi bir hata veya istisna oluşmaz.
✓ Sistem kararlı kalır.

**Farklı Boyutlara Yazma:**
✓ Otomatik olarak her boyut için ayrı koleksiyonlar oluşturur.
✓ Her boyut kendi koleksiyonunda izole edilir.
✓ Herhangi bir boyut çakışması veya şema hatası oluşmaz.

**Koleksiyon Silme:**
✓ Tüm boyut varyantlarını kaldırır.
✓ Tam temizleme.
✓ Herhangi bir yetim koleksiyon kalmaz.

### Sınır Durumlar

**Çoklu Gömülü Model:**
```
Scenario: User switches from model A (384-dim) to model B (768-dim)
Behavior:
- Both dimensions coexist in separate collections
- Old data (384-dim) remains queryable with 384-dim vectors
- New data (768-dim) queryable with 768-dim vectors
- Cross-dimension queries return results only for matching dimension
```

**Eşzamanlı İlk Yazma İşlemleri:**
```
Scenario: Multiple processes write to same collection simultaneously
Behavior:
- Each process checks for existence before creating
- Most vector stores handle concurrent creation gracefully
- If race condition occurs, second create is typically idempotent
- Final state: Collection exists and both writes succeed
```

**Boyutların Taşınması:**
```
Scenario: User wants to migrate from 384-dim to 768-dim embeddings
Behavior:
- No automatic migration
- Old collection (384-dim) persists
- New collection (768-dim) created on first new write
- Both dimensions remain accessible
- Manual deletion of old dimension collections possible
```

**Boş Koleksiyon Sorguları:**
```
Scenario: Query a collection that has never received data
Behavior:
- Collection doesn't exist (never created)
- Query returns empty list
- No error state
- System logs: "Collection does not exist, returning empty results"
```

## Uygulama Notları

### Depolama Arka Ucu Özellikleri

**Qdrant:**
Varlık kontrolleri için `collection_exists()` kullanılır.
Silme sırasında listeleme için `get_collections()` kullanılır.
Koleksiyon oluşturma `VectorParams(size=dim, distance=Distance.COSINE)` gerektirir.

**Pinecone:**
Varlık kontrolleri için `has_index()` kullanılır.
Silme sırasında listeleme için `list_indexes()` kullanılır.
İndeks oluşturma, "hazır" durumunu bekleme gerektirir.
Sunucusuz yapılandırma, bulut/bölge ile yapılır.

**Milvus:**
Doğrudan sınıflar (`DocVectors`, `EntityVectors`), yaşam döngüsünü yönetir.
Performans için dahili önbellek `self.collections[(dim, user, collection)]`.
Koleksiyon adları, yalnızca alfanümerik ve alt çizgi içeren şekilde temizlenir.
Otomatik artan kimliklere sahip şema desteği.

### Performans Hususları

**İlk Yazma Gecikmesi:**
Koleksiyon oluşturma nedeniyle ek yük.
Qdrant: ~100-500ms
Pinecone: ~10-30 saniye (sunucusuz sağlama)
Milvus: ~500-2000ms (indekslemeyi içerir)

**Sorgu Performansı:**
Varlık kontrolü, minimum ek yük ekler (~1-10ms).
Koleksiyon mevcut olduğunda performans üzerinde etkisi yoktur.
Her boyut koleksiyonu, bağımsız olarak optimize edilir.

**Depolama Yükü:**
Her koleksiyon için minimum meta veri.
Ana yük, boyut başına depolamadır.
Dengeleme: Depolama alanı ile boyut esnekliği.

## Gelecek Hususlar

**Otomatik Boyut Birleştirme:**
Kullanılmayan boyut varyantlarını belirlemek ve birleştirmek için arka plan işlemi eklenebilir.
Yeniden gömme veya boyut azaltma gerektirecektir.

**Boyut Keşfi:**
Bir koleksiyon için kullanılan tüm boyutları listelemek için bir API açılabilir.
Yönetim ve izleme için kullanışlıdır.

**Varsayılan Boyut Tercihi:**
Her koleksiyon için "birincil" boyut izlenebilir.
Boyut bağlamı kullanılamadığında sorgular için kullanılır.

**Depolama Kotaları:**
Her koleksiyon için boyut limitleri gerekebilir.
Boyut varyantlarının yayılmasını önler.

## Geçiş Notları

**Ön Boyut-Sonek Sisteminden:**
Eski koleksiyonlar: `d_{user}_{collection}` (boyut soneki yok)
Yeni koleksiyonlar: `d_{user}_{collection}_{dim}` (boyut soneki ile)
Otomatik geçiş yok - eski koleksiyonlar erişilebilir durumda kalır.
Gerekirse, manuel bir geçiş betiği düşünülmelidir.
Her iki adlandırma şeması de aynı anda kullanılabilir.

## Referanslar

Koleksiyon Yönetimi: `docs/tech-specs/collection-management.md`
Depolama Şeması: `trustgraph-base/trustgraph/schema/services/storage.py`
Kütüphaneci Hizmeti: `trustgraph-flow/trustgraph/librarian/service.py`
