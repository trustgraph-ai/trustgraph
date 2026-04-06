# Ajan Açıklanabilirliği: Kaynak Kaydı

## Genel Bakış

Ajan oturumlarının izlenebilmesi ve GraphRAG ile aynı açıklanabilirlik altyapısı kullanılarak hata ayıklanabilmesi için, React ajan döngüsüne kaynak kaydı ekleyin.

**Tasarım Kararları:**
- `urn:graph:retrieval`'a yazın (genel açıklanabilirlik grafiği)
- Şu anda doğrusal bağımlılık zinciri (analiz N → wasDerivedFrom → analiz N-1)
- Araçlar, kayıt alınmayan, opak kara kutulardır (sadece girdi/çıktı kaydedilir)
- DAG desteği, gelecekteki bir yinelemeye ertelenmiştir

## Varlık Türleri

Hem GraphRAG hem de Agent, TrustGraph'e özgü alt türlere sahip olan PROV-O'yu temel ontoloji olarak kullanır:

### GraphRAG Türleri
| Varlık | PROV-O Türü | TG Türleri | Açıklama |
|--------|-------------|----------|-------------|
| Soru | `prov:Activity` | `tg:Question`, `tg:GraphRagQuestion` | Kullanıcının sorgusu |
| Keşif | `prov:Entity` | `tg:Exploration` | Bilgi grafiğinden alınan kenarlar |
| Odak | `prov:Entity` | `tg:Focus` | Akıl yürütmeyle seçilen kenarlar |
| Sentez | `prov:Entity` | `tg:Synthesis` | Sonuç |

### Ajan Türleri
| Varlık | PROV-O Türü | TG Türleri | Açıklama |
|--------|-------------|----------|-------------|
| Soru | `prov:Activity` | `tg:Question`, `tg:AgentQuestion` | Kullanıcının sorgusu |
| Analiz | `prov:Entity` | `tg:Analysis` | Her düşünme/eylem/gözlem döngüsü |
| Sonuç | `prov:Entity` | `tg:Conclusion` | Sonuç |

### Belge RAG Türleri
| Varlık | PROV-O Türü | TG Türleri | Açıklama |
|--------|-------------|----------|-------------|
| Soru | `prov:Activity` | `tg:Question`, `tg:DocRagQuestion` | Kullanıcının sorgusu |
| Keşif | `prov:Entity` | `tg:Exploration` | Belge deposundan alınan parçalar |
| Sentez | `prov:Entity` | `tg:Synthesis` | Sonuç |

**Not:** Belge RAG, GraphRAG'ın türlerinin bir alt kümesini kullanır (kenar seçimi/akıl yürütme aşaması olmadığından Odak adımı yoktur).

### Soru Alt Türleri

Tüm Soru varlıkları `tg:Question`'ı temel tür olarak paylaşır, ancak geri alma mekanizmasını tanımlamak için özel bir alt türe sahiptir:

| Alt Tür | URI Kalıbı | Mekanizma |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | Bilgi grafiği RAG |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | Belge/parça RAG |
| `tg:AgentQuestion` | `urn:trustgraph:agent:{uuid}` | ReAct ajanı |

Bu, tüm soruların `tg:Question` aracılığıyla sorgulanabilmesini sağlarken, alt tür aracılığıyla belirli bir mekanizma ile filtrelenmesini sağlar.

## Kaynak Modeli

```
Question (urn:trustgraph:agent:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasDerivedFrom
    │
Analysis1 (urn:trustgraph:agent:{uuid}/i1)
    │
    │  tg:thought = "I need to query the knowledge base..."
    │  tg:action = "knowledge-query"
    │  tg:arguments = {"question": "..."}
    │  tg:observation = "Result from tool..."
    │  rdf:type = prov:Entity, tg:Analysis
    │
    ↓ prov:wasDerivedFrom
    │
Analysis2 (urn:trustgraph:agent:{uuid}/i2)
    │  ...
    ↓ prov:wasDerivedFrom
    │
Conclusion (urn:trustgraph:agent:{uuid}/final)
    │
    │  tg:answer = "The final response..."
    │  rdf:type = prov:Entity, tg:Conclusion
```

### Belge RAG (Retrieval-Augmented Generation) Kaynak Modeli

```
Question (urn:trustgraph:docrag:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasGeneratedBy
    │
Exploration (urn:trustgraph:docrag:{uuid}/exploration)
    │
    │  tg:chunkCount = 5
    │  tg:selectedChunk = "chunk-id-1"
    │  tg:selectedChunk = "chunk-id-2"
    │  ...
    │  rdf:type = prov:Entity, tg:Exploration
    │
    ↓ prov:wasDerivedFrom
    │
Synthesis (urn:trustgraph:docrag:{uuid}/synthesis)
    │
    │  tg:content = "The synthesized answer..."
    │  rdf:type = prov:Entity, tg:Synthesis
```

## Gerekli Değişiklikler

### 1. Şema Değişiklikleri

**Dosya:** `trustgraph-base/trustgraph/schema/services/agent.py`

`AgentRequest`'ye `session_id` ve `collection` alanlarını ekleyin:
```python
@dataclass
class AgentRequest:
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    user: str = ""
    collection: str = "default"  # NEW: Collection for provenance traces
    streaming: bool = False
    session_id: str = ""         # NEW: For provenance tracking across iterations
```

**Dosya:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

Çeviriciyi, `session_id` ve `collection`'i hem `to_pulsar()` hem de `from_pulsar()` içinde işleyebilecek şekilde güncelleyin.

### 2. Ajan Hizmetine Açıklanabilirlik Üreticisini Ekle

**Dosya:** `trustgraph-flow/trustgraph/agent/react/service.py`

Bir "açıklanabilirlik" üreticisi kaydedin (GraphRAG ile aynı yapı):
```python
from ... base import ProducerSpec
from ... schema import Triples

# In __init__:
self.register_specification(
    ProducerSpec(
        name = "explainability",
        schema = Triples,
    )
)
```

### 3. Kaynak Üçlü Oluşturma

**Dosya:** `trustgraph-base/trustgraph/provenance/agent.py`

Yardımcı fonksiyonlar oluşturun (GraphRAG'in `question_triples`, `exploration_triples`, vb. gibi):
```python
def agent_session_triples(session_uri, query, timestamp):
    """Generate triples for agent Question."""
    return [
        Triple(s=session_uri, p=RDF_TYPE, o=PROV_ACTIVITY),
        Triple(s=session_uri, p=RDF_TYPE, o=TG_QUESTION),
        Triple(s=session_uri, p=TG_QUERY, o=query),
        Triple(s=session_uri, p=PROV_STARTED_AT_TIME, o=timestamp),
    ]

def agent_iteration_triples(iteration_uri, parent_uri, thought, action, arguments, observation):
    """Generate triples for one Analysis step."""
    return [
        Triple(s=iteration_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=iteration_uri, p=RDF_TYPE, o=TG_ANALYSIS),
        Triple(s=iteration_uri, p=TG_THOUGHT, o=thought),
        Triple(s=iteration_uri, p=TG_ACTION, o=action),
        Triple(s=iteration_uri, p=TG_ARGUMENTS, o=json.dumps(arguments)),
        Triple(s=iteration_uri, p=TG_OBSERVATION, o=observation),
        Triple(s=iteration_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]

def agent_final_triples(final_uri, parent_uri, answer):
    """Generate triples for Conclusion."""
    return [
        Triple(s=final_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=final_uri, p=RDF_TYPE, o=TG_CONCLUSION),
        Triple(s=final_uri, p=TG_ANSWER, o=answer),
        Triple(s=final_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]
```

### 4. Tür Tanımları

**Dosya:** `trustgraph-base/trustgraph/provenance/namespaces.py`

Açıklanabilirlik varlık türlerini ve ajan özniteliklerini ekleyin:
```python
# Explainability entity types (used by both GraphRAG and Agent)
TG_QUESTION = TG + "Question"
TG_EXPLORATION = TG + "Exploration"
TG_FOCUS = TG + "Focus"
TG_SYNTHESIS = TG + "Synthesis"
TG_ANALYSIS = TG + "Analysis"
TG_CONCLUSION = TG + "Conclusion"

# Agent predicates
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_ANSWER = TG + "answer"
```

## Değiştirilen Dosyalar

| Dosya | Değişiklik |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | AgentRequest'e session_id ve collection eklendi |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | Yeni alanlar için çevirici güncellendi |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Varlık türleri, ajan önişlemleri ve Document RAG önişlemleri eklendi |
| `trustgraph-base/trustgraph/provenance/triples.py` | GraphRAG üçlü oluşturucularına TG türleri eklendi, Document RAG üçlü oluşturucuları eklendi |
| `trustgraph-base/trustgraph/provenance/uris.py` | Document RAG URI oluşturucuları eklendi |
| `trustgraph-base/trustgraph/provenance/__init__.py` | Yeni türler, önişlemler ve Document RAG fonksiyonları dışa aktarıldı |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | DocumentRagResponse'a explain_id ve explain_graph eklendi |
| `trustgraph-base/trustgraph/messaging/translators/retrieval.py` | Açıklanabilirlik alanları için DocumentRagResponseTranslator güncellendi |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Açıklanabilirlik üretici + kayıt mantığı eklendi |
| `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` | Açıklanabilirlik geri çağırması eklendi ve kaynak üçlüleri yayıldı |
| `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` | Açıklanabilirlik üretici eklendi ve geri çağırma ile bağlandı |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Ajan izleme türleri işlendi |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | Ajan oturumları, GraphRAG ile birlikte listelendi |

## Oluşturulan Dosyalar

| Dosya | Amaç |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | Ajan özel üçlü oluşturucuları |

## CLI Güncellemeleri

**Algılama:** Hem GraphRAG hem de Ajan Soruları `tg:Question` türündedir. Aşağıdakilerle ayırt edilir:
1. URI kalıbı: `urn:trustgraph:agent:` vs `urn:trustgraph:question:`
2. Türetilen varlıklar: `tg:Analysis` (ajan) vs `tg:Exploration` (GraphRAG)

**`list_explain_traces.py`:**
- Tür sütununu (Ajan vs GraphRAG) gösterir

**`show_explain_trace.py`:**
- İzleme türünü otomatik olarak algılar
- Ajan işleme, şu öğeleri gösterir: Soru → Analiz adımı(ları) → Sonuç

## Geriye Dönük Uyumluluk

- `session_id` varsayılan olarak `""`'dir - eski istekler çalışır, ancak kaynak bilgisi olmayacaktır
- `collection` varsayılan olarak `"default"`'dir - makul bir yedekleme
- CLI, her iki izleme türünü de sorunsuz bir şekilde işler

## Doğrulama

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## Gelecek Çalışmalar (Bu PR'de Değil)

- DAG bağımlılıkları (analiz N, birden fazla önceki analizden sonuçları kullandığında)
- Araçlara özel köken bağlantısı (KnowledgeQuery → GraphRAG izi)
- Akışlı köken yayını (sonunda toplu olarak değil, işlem sırasında yayınla)
