# RAG Akış Desteği Teknik Özellikleri

## Genel Bakış

Bu özellik, GraphRAG ve DocumentRAG hizmetlerine akış desteği eklemeyi tanımlar. Bu, bilgi grafiği ve belge sorguları için gerçek zamanlı, token bazlı yanıtlar sağlar. Bu, LLM metin tamamlama, istem ve ajan hizmetleri için zaten uygulanan mevcut akış mimarisini genişletir.

## Hedefler

**Tutarlı akış kullanıcı deneyimi**: Tüm TrustGraph hizmetlerinde aynı akış deneyimini sağlayın.
**Minimum API değişiklikleri**: Akış desteğini, yerleşik kalıpları izleyerek tek bir `streaming` bayrağıyla ekleyin.
**Geriye dönük uyumluluk**: Mevcut, akış olmayan davranışı varsayılan olarak koruyun.
**Mevcut altyapıyı yeniden kullanın**: Zaten uygulanan PromptClient akışını kullanın.
**Gateway desteği**: İstemci uygulamaları için websocket gateway üzerinden akışı etkinleştirin.

## Arka Plan

Şu anda uygulanan akış hizmetleri:
**LLM metin tamamlama hizmeti**: 1. Aşama - LLM sağlayıcılardan akış.
**İstem hizmeti**: 2. Aşama - istem şablonları aracılığıyla akış.
**Ajan hizmeti**: 3.-4. Aşama - ReAct yanıtlarını, artımlı düşünce/gözlem/cevap parçalarıyla akış.

RAG hizmetleri için mevcut sınırlamalar:
GraphRAG ve DocumentRAG yalnızca engellenen yanıtları destekler.
Kullanıcılar, herhangi bir çıktı görmeden önce LLM'den gelen tamamlanmış yanıtı beklemelidir.
Bilgi grafiği veya belge sorgularından gelen uzun yanıtlar için kötü kullanıcı deneyimi.
Diğer TrustGraph hizmetlerine kıyasla tutarsız deneyim.

Bu özellik, GraphRAG ve DocumentRAG'a akış desteği ekleyerek bu boşlukları giderir. Token bazlı yanıtları etkinleştirerek, TrustGraph şunları yapabilir:
Tüm sorgu türleri için tutarlı bir akış kullanıcı deneyimi sağlayın.
RAG sorguları için algılanan gecikmeyi azaltın.
Uzun süren sorgular için daha iyi ilerleme geri bildirimi sağlayın.
İstemci uygulamalarında gerçek zamanlı görüntülemeyi destekleyin.

## Teknik Tasarım

### Mimari

RAG akış uygulaması, mevcut altyapıyı kullanır:

1. **PromptClient Akışı** (Zaten uygulandı)
   `kg_prompt()` ve `document_prompt()` zaten `streaming` ve `chunk_callback` parametrelerini kabul eder.
   Bunlar dahili olarak akış desteğiyle `prompt()`'ı çağırır.
   PromptClient'ta herhangi bir değişiklik yapılmasına gerek yoktur.

   Modül: `trustgraph-base/trustgraph/base/prompt_client.py`

2. **GraphRAG Hizmeti** (Akış parametresi geçişi gereklidir)
   `query()` yöntemine `streaming` parametresini ekleyin.
   Akış bayrağını ve geri çağırmaları `prompt_client.kg_prompt()`'a geçirin.
   GraphRagRequest şemasının `streaming` alanına ihtiyacı vardır.

   Modüller:
   `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
   `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (İşlemci)
   `trustgraph-base/trustgraph/schema/graph_rag.py` (İstek şeması)
   `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (Gateway)

3. **DocumentRAG Hizmeti** (Akış parametresi geçişi gereklidir)
   `query()` yöntemine `streaming` parametresini ekleyin.
   Akış bayrağını ve geri çağırmaları `prompt_client.document_prompt()`'a geçirin.
   DocumentRagRequest şemasının `streaming` alanına ihtiyacı vardır.

   Modüller:
   `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
   `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (İşlemci)
   `trustgraph-base/trustgraph/schema/document_rag.py` (İstek şeması)
   `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (Gateway)

### Veri Akışı

**Engellenmeyen (mevcut)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Prompt Service → LLM
                                   ↓
                                Complete response
                                   ↓
Client ← Gateway ← RAG Service ←  Response
```

**Akış (önerilen)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Prompt Service → LLM (streaming)
                                   ↓
                                Chunk → callback → RAG Response (chunk)
                                   ↓                       ↓
Client ← Gateway ← ────────────────────────────────── Response stream
```

### API'ler

**GraphRAG Değişiklikleri**:

1. **GraphRag.query()** - Akış parametreleri eklendi.
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NEW
):
    # ... existing entity/triple retrieval ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2. **GraphRagRequest şeması** - Akış alanı ekleyin.
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NEW
```

3. **GraphRagResponse şeması** - Akış alanlarını ekleyin (Agent modelini takip edin).
```python
class GraphRagResponse(Record):
    response = String()    # Legacy: complete response
    chunk = String()       # NEW: streaming chunk
    end_of_stream = Boolean()  # NEW: indicates last chunk
```

4. **İşlemci** - Veriyi sürekli akış halinde ilet.
```python
async def handle(self, msg):
    # ... existing code ...

    async def send_chunk(chunk):
        await self.respond(GraphRagResponse(
            chunk=chunk,
            end_of_stream=False,
            response=None
        ))

    if request.streaming:
        full_response = await self.rag.query(
            query=request.query,
            user=request.user,
            collection=request.collection,
            streaming=True,
            chunk_callback=send_chunk
        )
        # Send final message
        await self.respond(GraphRagResponse(
            chunk=None,
            end_of_stream=True,
            response=full_response
        ))
    else:
        # Existing non-streaming path
        response = await self.rag.query(...)
        await self.respond(GraphRagResponse(response=response))
```

**DocumentRAG Değişiklikleri**:

GraphRAG ile aynı yapı:
1. `streaming` ve `chunk_callback` parametrelerini `DocumentRag.query()`'ye ekleyin.
2. `streaming` alanını `DocumentRagRequest`'e ekleyin.
3. `chunk` ve `end_of_stream` alanlarını `DocumentRagResponse`'ye ekleyin.
4. İşlemciyi, geri çağırmalarla akışı işleyebilecek şekilde güncelleyin.

**Gateway Değişiklikleri**:

Hem `graph_rag.py` hem de `document_rag.py`, gateway/dispatch içinde, akış parçacıklarını websocket'e iletebilmesi için güncellenmelidir:

```python
async def handle(self, message, session, websocket):
    # ... existing code ...

    if request.streaming:
        async def recipient(resp):
            if resp.chunk:
                await websocket.send(json.dumps({
                    "id": message["id"],
                    "response": {"chunk": resp.chunk},
                    "complete": resp.end_of_stream
                }))
            return resp.end_of_stream

        await self.rag_client.request(request, recipient=recipient)
    else:
        # Existing non-streaming path
        resp = await self.rag_client.request(request)
        await websocket.send(...)
```

### Uygulama Detayları

**Uygulama sırası**:
1. Şema alanlarını ekleyin (Hem RAG hizmetleri için İstek + Yanıt)
2. GraphRag.query() ve DocumentRag.query() yöntemlerini güncelleyin
3. Akışı işlemek için İşleyicileri güncelleyin
4. Ağ geçidi yönlendirme işleyicilerini güncelleyin
5. `--no-streaming` bayraklarını `tg-invoke-graph-rag` ve `tg-invoke-document-rag`'ye ekleyin (akış varsayılan olarak etkindir, ajan CLI kalıbını takip eder)

**Geri çağırma kalıbı**:
Ajan akışında oluşturulan aynı asenkron geri çağırma kalıbını izleyin:
İşleyici, `async def send_chunk(chunk)` geri çağrısını tanımlar
Geri çağrıyı RAG hizmetine iletir
RAG hizmeti, geri çağrıyı PromptClient'a iletir
PromptClient, her LLM parçası için geri çağrıyı çağırır
İşleyici, her parça için akış yanıt mesajını gönderir

**Hata işleme**:
Akış sırasında oluşan hatalar, `end_of_stream=True` ile hata yanıtı göndermelidir
Ajan akışından mevcut hata yayılım kalıplarını izleyin

## Güvenlik Hususları

Mevcut RAG hizmetlerinin ötesinde yeni güvenlik hususları yoktur:
Akış yanıtları, aynı kullanıcı/toplam izolasyonunu kullanır
Kimlik doğrulama veya yetkilendirmede herhangi bir değişiklik yoktur
Parça sınırları, hassas verileri ortaya çıkarmaz

## Performans Hususları

**Faydaları**:
Algılanan gecikmenin azaltılması (ilk belirteçler daha hızlı gelir)
Uzun yanıtlar için daha iyi kullanıcı deneyimi
Daha düşük bellek kullanımı (tam yanıtı tamponlamaya gerek yoktur)

**Olası endişeler**:
Akış yanıtları için daha fazla Pulsar mesajı
Parçalama/geri çağırma ek yükü için biraz daha yüksek CPU
Akış, isteğe bağlıdır, varsayılan olarak akış etkin değildir, bu nedenle bu sorunlar hafifletilmiştir

**Test hususları**:
Çok sayıda üçlü içeren büyük bilgi grafikleriyle test edin
Çok sayıda alınmış belgeyle test edin
Akışın ve akış dışı durumun ek yükünü ölçün

## Test Stratejisi

**Birim testleri**:
GraphRag.query()'yi streaming=True/False ile test edin
DocumentRag.query()'yi streaming=True/False ile test edin
Geri çağırma çağrılarını doğrulamak için PromptClient'ı taklit edin

**Entegrasyon testleri**:
Tam GraphRAG akışını test edin (mevcut ajan akış testlerine benzer)
Tam DocumentRAG akışını test edin
Ağ geçidi akış yönlendirmesini test edin
CLI akış çıktısını test edin

**Manuel testler**:
`tg-invoke-graph-rag -q "What is machine learning?"` (akış varsayılan olarak etkindir)
`tg-invoke-document-rag -q "Summarize the documents about AI"` (akış varsayılan olarak etkindir)
`tg-invoke-graph-rag --no-streaming -q "..."` (akış dışı modu test edin)
Akış modunda kademeli çıktının göründüğünü doğrulayın

## Geçiş Planı

Herhangi bir geçişe gerek yoktur:
Akış, `streaming` parametresi aracılığıyla isteğe bağlıdır (varsayılan olarak False)
Mevcut istemciler, herhangi bir değişiklik olmadan çalışmaya devam eder
Yeni istemciler, akışı kullanabilir

## Zaman Çizelgesi

Tahmini uygulama süresi: 4-6 saat
1. Aşama (2 saat): GraphRAG akış desteği
2. Aşama (2 saat): DocumentRAG akış desteği
3. Aşama (1-2 saat): Ağ geçidi güncellemeleri ve CLI bayrakları
Test: Her aşamaya entegre edilmiştir

## Açık Sorular

NLP Sorgu hizmetine de akış desteği eklemeli miyiz?
Ara adımları (örneğin, "Varlıkların alınması...", "Grafiğin sorgulanması...") mi yoksa sadece LLM çıktısını mı akışa vermeliyiz?
GraphRAG/DocumentRAG yanıtları, parça meta verilerini (örneğin, parça numarası, toplam beklenen) içermeli mi?

## Referanslar

Mevcut uygulama: `docs/tech-specs/streaming-llm-responses.md`
Ajan akışı: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
PromptClient akışı: `trustgraph-base/trustgraph/base/prompt_client.py`
