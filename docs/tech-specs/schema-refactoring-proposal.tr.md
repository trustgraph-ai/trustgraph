# Şema Dizini Yeniden Düzenleme Önerisi

## Mevcut Sorunlar

1. **Düz yapı** - Tüm şemaların tek bir dizinde olması, ilişkileri anlamayı zorlaştırıyor.
2. **Karışık konular** - Temel tipler, alan nesneleri ve API sözleşmeleri bir arada bulunuyor.
3. **Belirsiz adlandırma** - "object.py", "types.py", "topic.py" gibi dosyalar, amaçlarını açıkça belirtmiyor.
4. **Açık katmanlama yok** - Neyin neye bağlı olduğunu kolayca görmek mümkün değil.

## Önerilen Yapı

```
trustgraph-base/trustgraph/schema/
├── __init__.py
├── core/              # Core primitive types used everywhere
│   ├── __init__.py
│   ├── primitives.py  # Error, Value, Triple, Field, RowSchema
│   ├── metadata.py    # Metadata record
│   └── topic.py       # Topic utilities
│
├── knowledge/         # Knowledge domain models and extraction
│   ├── __init__.py
│   ├── graph.py       # EntityContext, EntityEmbeddings, Triples
│   ├── document.py    # Document, TextDocument, Chunk
│   ├── knowledge.py   # Knowledge extraction types
│   ├── embeddings.py  # All embedding-related types (moved from multiple files)
│   └── nlp.py         # Definition, Topic, Relationship, Fact types
│
└── services/          # Service request/response contracts
    ├── __init__.py
    ├── llm.py         # TextCompletion, Embeddings, Tool requests/responses
    ├── retrieval.py   # GraphRAG, DocumentRAG queries/responses
    ├── query.py       # GraphEmbeddingsRequest/Response, DocumentEmbeddingsRequest/Response
    ├── agent.py       # Agent requests/responses
    ├── flow.py        # Flow requests/responses
    ├── prompt.py      # Prompt service requests/responses
    ├── config.py      # Configuration service
    ├── library.py     # Librarian service
    └── lookup.py      # Lookup service
```

## Temel Değişiklikler

1. **Hiyerarşik organizasyon** - Temel tipler, bilgi modelleri ve hizmet sözleşmeleri arasında net bir ayrım.
2. **Daha iyi adlandırma**:
   `types.py` → `core/primitives.py` (daha açık amaç)
   `object.py` → Gerçek içeriğe göre uygun dosyalara ayrım
   `documents.py` → `knowledge/document.py` (tekil, tutarlı)
   `models.py` → `services/llm.py` (hangi tür modeller olduğu daha açık)
   `prompt.py` → Ayrım: hizmet kısımları `services/prompt.py`'e, veri tipleri `knowledge/nlp.py`'ye

3. **Mantıksal gruplandırma**:
   Tüm gömme türleri `knowledge/embeddings.py` içinde toplandı.
   Tüm LLM ile ilgili hizmet sözleşmeleri `services/llm.py` içinde.
   Hizmetler dizininde istek/yanıt çiftlerinin net bir şekilde ayrılması.
   Bilgi çıkarma türleri, diğer bilgi alanı modelleriyle gruplandırıldı.

4. **Bağımlılık netliği**:
   Temel tiplerin hiçbir bağımlılığı yoktur.
   Bilgi modelleri yalnızca temel bağımlılıklarına sahiptir.
   Hizmet sözleşmeleri hem temel hem de bilgi modellerine bağımlı olabilir.

## Geçiş Faydaları

1. **Daha kolay gezinme** - Geliştiriciler ihtiyaç duyduklarını hızla bulabilir.
2. **Daha iyi modülerlik** - Farklı konular arasındaki sınırlar nettir.
3. **Daha basit içe aktarmalar** - Daha sezgisel içe aktarma yolları.
4. **Geleceğe yönelik** - Yeni bilgi türleri veya hizmetler eklemek, karmaşayı önleyecek şekilde kolaydır.

## Örnek İçe Aktarma Değişiklikleri

```python
# Before
from trustgraph.schema import Error, Triple, GraphEmbeddings, TextCompletionRequest

# After
from trustgraph.schema.core import Error, Triple
from trustgraph.schema.knowledge import GraphEmbeddings
from trustgraph.schema.services import TextCompletionRequest
```

## Uygulama Notları

1. Kök dizindeki `__init__.py` içindeki import'ları koruyarak geriye dönük uyumluluğu sağlayın.
2. Dosyaları kademeli olarak taşıyın ve gerektiğinde import'ları güncelleyin.
3. Geçiş dönemi için her şeyi import eden bir `legacy.py` eklemeyi düşünün.
4. Yeni yapıyı yansıtacak şekilde dokümantasyonu güncelleyin.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Mevcut şema dizin yapısını inceleyin", "status": "tamamlandı", "priority": "yüksek"}, {"id": "2", "content": "Şema dosyalarını ve amaçlarını analiz edin", "status": "tamamlandı", "priority": "yüksek"}, {"id": "3", "content": "Geliştirilmiş adlandırma ve yapı önerin", "status": "tamamlandı", "priority": "yüksek"}]