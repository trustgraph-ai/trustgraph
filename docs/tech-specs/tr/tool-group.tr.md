---
layout: default
title: "TrustGraph Araç Grubu Sistemi"
parent: "Turkish (Beta)"
---

# TrustGraph Araç Grubu Sistemi

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.
## Teknik Özellikler v1.0

### Yönetici Özeti

Bu özellik, TrustGraph ajanları için, belirli istekler için hangi araçların kullanılabilir olduğuna ince ayar yapılmasına olanak tanıyan bir araç gruplama sistemi tanımlar. Sistem, yapılandırma ve istek düzeyinde belirtme yoluyla, grup tabanlı araç filtrelemesi sunarak, daha iyi güvenlik sınırları, kaynak yönetimi ve ajan yeteneklerinin işlevsel ayrımı sağlar.

### 1. Genel Bakış

#### 1.1 Problem Tanımı

Şu anda, TrustGraph ajanları, istek bağlamı veya güvenlik gereksinimlerinden bağımsız olarak, yapılandırılmış tüm araçlara erişebilir. Bu, çeşitli zorluklara yol açmaktadır:

**Güvenlik Riski**: Hassas araçlar (örneğin, veri değişikliği), yalnızca okuma istekleri için bile kullanılabilir.
**Kaynak İsrafı**: Karmaşık araçlar, basit istekler için gerekli olmadığında bile yüklenir.
**İşlevsel Karmaşa**: Ajanlar, daha basit alternatifler varken, uygun olmayan araçları seçebilir.
**Çok Kiracılı İzolasyon**: Farklı kullanıcı gruplarının farklı araç setlerine erişmesi gerekir.

#### 1.2 Çözümün Genel Bakışı

Araç grubu sistemi aşağıdaki özellikleri sunar:

1. **Grup Sınıflandırması**: Araçlar, yapılandırma sırasında grup üyelikleriyle etiketlenir.
2. **İstek Düzeyinde Filtreleme**: AgentRequest, hangi araç gruplarının izinli olduğunu belirtir.
3. **Çalışma Zamanı Uygulaması**: Ajanlar, yalnızca istenen gruplarla eşleşen araçlara erişebilir.
4. **Esnek Gruplandırma**: Araçlar, karmaşık senaryolar için birden fazla gruba ait olabilir.

### 2. Şema Değişiklikleri

#### 2.1 Araç Yapılandırma Şeması Geliştirmesi

Mevcut araç yapılandırması, bir `group` alanı ile geliştirilmiştir:

**Önce:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query", 
  "description": "Query the knowledge graph"
}
```

**Sonra:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"]
}
```

**Grup Alanı Tanımlaması:**
`group`: Array(String) - Bu aracın ait olduğu grupların listesi
**İsteğe Bağlı:** Grup alanı olmayan araçlar, "varsayılan" gruba aittir
**Çoklu Üyelik:** Araçlar, birden fazla gruba ait olabilir
**Büyük/Küçük Harf Duyarlılığı:** Grup adları, tam string eşleşmeleridir

#### 2.1.2 Araç Durum Geçişi Geliştirmesi

Araçlar, isteğe bağlı olarak durum geçişlerini ve duruma bağlı kullanılabilirliği belirtebilir:

```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"],
  "state": "analysis",
  "available_in_states": ["undefined", "research"]
}
```

**Durum Alanı Tanımlaması:**
`state`: String - **İsteğe bağlı** - Başarılı araç çalıştırması sonrasında geçilecek durum
`available_in_states`: Array(String) - **İsteğe bağlı** - Bu aracın mevcut olduğu durumlar
**Varsayılan davranış:** `available_in_states` değeri olmayan araçlar, tüm durumlarda kullanılabilir
**Durum geçişi:** Sadece başarılı araç çalıştırması sonrasında gerçekleşir

#### 2.2 AgentRequest Şema Geliştirmesi

`trustgraph-base/trustgraph/schema/services/agent.py` içindeki `AgentRequest` şeması geliştirilmiştir:

**Mevcut AgentRequest:**
`question`: String - Kullanıcı sorgusu
`plan`: String - Çalıştırma planı (kaldırılabilir)
`state`: String - Ajan durumu
`history`: Array(AgentStep) - Çalıştırma geçmişi

**Geliştirilmiş AgentRequest:**
`question`: String - Kullanıcı sorgusu
`state`: String - Ajan çalıştırma durumu (artık araç filtreleme için aktif olarak kullanılıyor)
`history`: Array(AgentStep) - Çalıştırma geçmişi
`group`: Array(String) - **YENİ** - Bu istek için izin verilen araç grupları

**Şema Değişiklikleri:**
**Kaldırıldı:** `plan` alanı artık gerekli değildir ve kaldırılabilir (başlangıçta araç belirtimi için tasarlanmıştı)
**Eklendi:** Araç grubu belirtimi için `group` alanı
**Geliştirildi:** `state` alanı artık çalıştırma sırasında araç kullanılabilirliğini kontrol eder

**Alan Davranışları:**

**Grup Alanı:**
**İsteğe bağlı:** Belirtilmezse, varsayılan olarak ["default"] değerini alır
**Kesişim:** Sadece en az bir belirtilen grupla eşleşen araçlar kullanılabilir
**Boş dizi:** Hiçbir araç kullanılamaz (ajan yalnızca dahili akıl yürütmeyi kullanabilir)
**Yıldız işareti:** Özel "*" grubu, tüm araçlara erişim sağlar

**Durum Alanı:**
**İsteğe bağlı:** Belirtilmezse, varsayılan olarak "undefined" değerini alır
**Durum tabanlı filtreleme:** Yalnızca mevcut durumda bulunan araçlar uygun olabilir
**Varsayılan durum:** "undefined" durumu, tüm araçlara izin verir (grup filtrelemesine tabidir)
**Durum geçişleri:** Araçlar, başarılı çalıştırmadan sonra durumu değiştirebilir

### 3. Özel Grup Örnekleri

Kuruluşlar, alanla ilgili özel gruplar tanımlayabilir:

```json
{
  "financial-tools": ["stock-query", "portfolio-analysis"],
  "medical-tools": ["diagnosis-assist", "drug-interaction"],
  "legal-tools": ["contract-analysis", "case-search"]
}
```

### 4. Uygulama Detayları

#### 4.1 Araç Yükleme ve Filtreleme

**Yapılandırma Aşaması:**
1. Tüm araçlar, grup atamalarıyla birlikte yapılandırmadan yüklenir.
2. Açık bir grup atanmamış araçlar, "varsayılan" gruba atanır.
3. Grup üyeliği doğrulanır ve araç kaydında saklanır.

**İstek İşleme Aşaması:**
1. İsteğe bağlı grup belirtimiyle birlikte AgentRequest gelir.
2. Agent, mevcut araçları grup kesişimi temelinde filtreler.
3. Yalnızca eşleşen araçlar, agent yürütme bağlamına iletilir.
4. Agent, istek yaşam döngüsü boyunca filtrelenmiş araç kümesiyle çalışır.

#### 4.2 Araç Filtreleme Mantığı

**Birleştirilmiş Grup ve Durum Filtreleme:**

```
For each configured tool:
  tool_groups = tool.group || ["default"]
  tool_states = tool.available_in_states || ["*"]  // Available in all states
  
For each request:
  requested_groups = request.group || ["default"]
  current_state = request.state || "undefined"
  
Tool is available if:
  // Group filtering
  (intersection(tool_groups, requested_groups) is not empty OR "*" in requested_groups)
  AND
  // State filtering  
  (current_state in tool_states OR "*" in tool_states)
```

**Durum Geçişi Mantığı:**

```
After successful tool execution:
  if tool.state is defined:
    next_request.state = tool.state
  else:
    next_request.state = current_request.state  // No change
```

#### 4.3 Ajan Entegrasyon Noktaları

**ReAct Ajanı:**
Araç filtrelemesi, araç kaydı oluşturulurken agent_manager.py dosyasında gerçekleşir.
Kullanılabilir araçlar listesi, plan oluşturulmadan önce hem grup hem de duruma göre filtrelenir.
Durum geçişleri, başarılı araç çalıştırması sonrasında AgentRequest.state alanını günceller.
Bir sonraki yineleme, araç filtrelemesi için güncellenmiş durumu kullanır.

**Güvenilirlik Tabanlı Ajan:**
Araç filtrelemesi, plan oluşturulurken planner.py dosyasında gerçekleşir.
ExecutionStep doğrulama, yalnızca grup+durum uygun araçların kullanıldığından emin olur.
Akış denetleyicisi, çalışma zamanında araç kullanılabilirliğini zorlar.
Durum geçişleri, adımlar arasında Akış Denetleyicisi tarafından yönetilir.

### 5. Yapılandırma Örnekleri

#### 5.1 Gruplar ve Durumlarla Araç Yapılandırması

```yaml
tool:
  knowledge-query:
    type: knowledge-query
    name: "Knowledge Graph Query"
    description: "Query the knowledge graph for entities and relationships"
    group: ["read-only", "knowledge", "basic"]
    state: "analysis"
    available_in_states: ["undefined", "research"]
    
  graph-update:
    type: graph-update
    name: "Graph Update"
    description: "Add or modify entities in the knowledge graph"
    group: ["write", "knowledge", "admin"]
    available_in_states: ["analysis", "modification"]
    
  text-completion:
    type: text-completion
    name: "Text Completion"
    description: "Generate text using language models"
    group: ["read-only", "text", "basic"]
    state: "undefined"
    # No available_in_states = available in all states
    
  complex-analysis:
    type: mcp-tool
    name: "Complex Analysis Tool"
    description: "Perform complex data analysis"
    group: ["advanced", "compute", "expensive"]
    state: "results"
    available_in_states: ["analysis"]
    mcp_tool_id: "analysis-server"
    
  reset-workflow:
    type: mcp-tool
    name: "Reset Workflow"
    description: "Reset to initial state"
    group: ["admin"]
    state: "undefined"
    available_in_states: ["analysis", "results"]
```

#### 5.2 Durum İş Akışlarıyla Birlikte İstek Örnekleri

**Başlangıç Araştırma İsteği:**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"],
  "state": "undefined"
}
```
*Mevcut araçlar: knowledge-query, text-completion*
*knowledge-query işleminden sonra: durum → "analiz"*

**Analiz Aşaması:**
```json
{
  "question": "Continue analysis based on previous results",
  "group": ["advanced", "compute", "write"],
  "state": "analysis"
}
```
*Mevcut araçlar: karmaşık analiz, grafik güncelleme, iş akışı sıfırlama*
*Karmaşık analizden sonra: durum → "sonuçlar"*

**Sonuçlar Aşaması:**
```json
{
  "question": "What should I do with these results?",
  "group": ["admin"],
  "state": "results"
}
```
*Mevcut araçlar: yalnızca reset-workflow*
*reset-workflow'dan sonra: durum → "undefined"*

**İş Akışı Örneği - Tam Akış:**
1. **Başlangıç (undefined):** knowledge-query kullanın → "analysis" durumuna geçiş yapar.
2. **Analiz durumu:** complex-analysis kullanın → "results" durumuna geçiş yapar.
3. **Sonuç durumu:** reset-workflow kullanın → "undefined" durumuna geri döner.
4. **Başlangıca dönüş:** Tüm başlangıç araçları tekrar kullanılabilir.

### 6. Güvenlik Hususları

#### 6.1 Erişim Kontrolü Entegrasyonu

**Ağ Geçidi Seviyesinde Filtreleme:**
Ağ geçidi, kullanıcı izinlerine göre grup kısıtlamalarını uygulayabilir.
İstek manipülasyonu yoluyla yetki yükseltmesini engelleyin.
Denetim kaydı, istenen ve verilen araç gruplarını içerir.

**Örnek Ağ Geçidi Mantığı:**
```
user_permissions = get_user_permissions(request.user_id)
allowed_groups = user_permissions.tool_groups
requested_groups = request.group

# Validate request doesn't exceed permissions
if not is_subset(requested_groups, allowed_groups):
    reject_request("Insufficient permissions for requested tool groups")
```

#### 6.2 Denetim ve İzleme

**Gelişmiş Denetim Kayıtları:**
İstenen araç gruplarını ve her istek için başlangıç durumunu kaydet.
Grup üyeliği tarafından durum geçişlerini ve araç kullanımını izle.
Yetkisiz grup erişim girişimlerini ve geçersiz durum geçişlerini izle.
Olağandışı grup kullanım kalıplarını veya şüpheli durum iş akışlarını tespit etme konusunda uyarı ver.

### 7. Geçiş Stratejisi

#### 7.1 Geriye Dönük Uyumluluk

**1. Aşama: Eklemeler**
Araç yapılandırmalarına isteğe bağlı `group` alanı ekle.
AgentRequest şemasına isteğe bağlı `group` alanı ekle.
Varsayılan davranış: Tüm mevcut araçlar "varsayılan" grubuna aittir.
Grup alanı olmayan mevcut istekler "varsayılan" grubunu kullanır.

**Mevcut Davranış Korunmuştur:**
Grup yapılandırması olmayan araçlar çalışmaya devam eder (varsayılan grup).
Durum yapılandırması olmayan araçlar tüm durumlarda kullanılabilir.
Grup belirtimi olmayan istekler tüm araçlara erişebilir (varsayılan grup).
Durum belirtimi olmayan istekler "belirsiz" durumu kullanır (tüm araçlar kullanılabilir).
Mevcut dağıtımlarda herhangi bir değişiklik yapılmamıştır.

### 8. İzleme ve Gözlemlenebilirlik

#### 8.1 Yeni Metrikler

**Araç Grubu Kullanımı:**
`agent_tool_group_requests_total` - Grup başına istek sayısı.
`agent_tool_group_availability` - Grup başına kullanılabilir araç sayısı.
`agent_filtered_tools_count` - Grup+durum filtrelemesinden sonraki araç sayısı histogramı.

**Durum İş Akışı Metrikleri:**
`agent_state_transitions_total` - Araç başına durum geçişleri sayısı.
`agent_workflow_duration_seconds` - Her durumda geçirilen süre histogramı.
`agent_state_availability` - Durum başına kullanılabilir araç sayısı.

**Güvenlik Metrikleri:**
`agent_group_access_denied_total` - Yetkisiz grup erişim sayısı.
`agent_invalid_state_transition_total` - Geçersiz durum geçişleri sayısı.
`agent_privilege_escalation_attempts_total` - Şüpheli istekler sayısı.

#### 8.2 Kayıt Güncellemeleri

**İstek Kayıtları:**
```json
{
  "request_id": "req-123",
  "requested_groups": ["read-only", "knowledge"],
  "initial_state": "undefined",
  "state_transitions": [
    {"tool": "knowledge-query", "from": "undefined", "to": "analysis", "timestamp": "2024-01-01T10:00:01Z"}
  ],
  "available_tools": ["knowledge-query", "text-completion"],
  "filtered_by_group": ["graph-update", "admin-tool"],
  "filtered_by_state": [],
  "execution_time": "1.2s"
}
```

### 9. Test Stratejisi

#### 9.1 Birim Testleri

**Araç Filtreleme Mantığı:**
Test grubu kesişimi hesaplamaları
Test durumu tabanlı filtreleme mantığı
Varsayılan grup ve durum atamasını doğrulayın
Test joker karakterli grup davranışını
Boş grup işleme doğrulamasını
Test birleştirilmiş grup+durum filtreleme senaryolarını

**Yapılandırma Doğrulama:**
Test farklı grup ve durum yapılandırmalarıyla araç yüklemeyi
Geçersiz grup ve durum tanımları için şema doğrulamasını
Test mevcut yapılandırmalarla geriye dönük uyumluluğu
Durum geçişi tanımlarını ve döngülerini doğrulayın

#### 9.2 Entegrasyon Testleri

**Ajan Davranışı:**
Ajanların yalnızca grup+durumla filtrelenmiş araçları gördüğünü doğrulayın
Test farklı grup kombinasyonlarıyla istek yürütmeyi
Ajan yürütülmesi sırasında durum geçişlerini test edin
Kullanılabilir araç olmadığında hata işleme doğrulamasını
Test çoklu durumlar aracılığıyla iş akışı ilerlemesini

**Güvenlik Testleri:**
Test ayrıcalık yükseltme önlemini
Denetim kaydı doğruluğunu doğrulayın
Kullanıcı izinleriyle ağ geçidi entegrasyonunu test edin

#### 9.3 Uçtan Uca Senaryolar

**Durum İş Akışlarıyla Çok Kiracılı Kullanım:**
```
Scenario: Different users with different tool access and workflow states
Given: User A has "read-only" permissions, state "undefined"
  And: User B has "write" permissions, state "analysis"
When: Both request knowledge operations
Then: User A gets read-only tools available in "undefined" state
  And: User B gets write tools available in "analysis" state
  And: State transitions are tracked per user session
  And: All usage and transitions are properly audited
```

**İş Akışı Durumu İlerlemesi:**
```
Scenario: Complete workflow execution
Given: Request with groups ["knowledge", "compute"] and state "undefined"
When: Agent executes knowledge-query tool (transitions to "analysis")
  And: Agent executes complex-analysis tool (transitions to "results")
  And: Agent executes reset-workflow tool (transitions to "undefined")
Then: Each step has correctly filtered available tools
  And: State transitions are logged with timestamps
  And: Final state allows initial workflow to repeat
```

### 10. Performans Hususları

#### 10.1 Araç Yükleme Etkisi

**Yapılandırma Yükleme:**
Grup ve durum meta verileri, başlatmada yalnızca bir kez yüklenir.
Her araç için minimum bellek yükü (ek alanlar).
Araç başlatma süresi üzerinde herhangi bir etkisi yoktur.

**İstek İşleme:**
Grup+durum filtrelemesi, her istek için yalnızca bir kez yapılır.
Yapılandırılmış araç sayısına (n) bağlı olarak O(n) karmaşıklığı.
Durum geçişleri, minimum bir yük ekler (dize ataması).
Tipik araç sayıları (< 100) için ihmal edilebilir bir etki.

#### 10.2 Optimizasyon Stratejileri

**Önceden Hesaplanan Araç Kümeleri:**
Araç kümelerini grup+durum kombinasyonuna göre önbelleğe alın.
Yaygın grup/durum kalıpları için tekrarlanan filtrelemeyi önleyin.
Sık kullanılan kombinasyonlar için bellek ve hesaplama arasında bir denge.

**Gecikmeli Yükleme:**
Araç uygulamalarını yalnızca ihtiyaç duyulduğunda yükleyin.
Birçok araca sahip dağıtımların başlatma süresini azaltın.
Grup gereksinimlerine göre dinamik araç kaydı.

### 11. Gelecekteki Geliştirmeler

#### 11.1 Dinamik Grup Ataması

**Bağlam Farkındalığına Sahip Gruplandırma:**
Araçları, istek bağlamına göre gruplara atayın.
Zaman tabanlı grup kullanılabilirliği (sadece iş saatleri).
Yük tabanlı grup kısıtlamaları (düşük kullanımda pahalı araçlar).

#### 11.2 Grup Hiyerarşileri

**İç İçe Geçmiş Grup Yapısı:**
```json
{
  "knowledge": {
    "read": ["knowledge-query", "entity-search"],
    "write": ["graph-update", "entity-create"]
  }
}
```

#### 11.3 Araç Önerileri

**Grup Tabanlı Öneriler:**
İstek türleri için en uygun araç gruplarını önerin
Önerileri iyileştirmek için kullanım kalıplarından öğrenin
Tercih edilen araçlar kullanılamadığında yedek gruplar sağlayın

### 12. Açık Sorular

1. **Grup Doğrulama**: İstehlerdeki geçersiz grup adları, sert hatalara mı yoksa uyarı mesajlarına mı neden olmalıdır?

2. **Grup Keşfi**: Sistem, mevcut grupları ve araçlarını listelemek için bir API sağlamalı mıdır?

3. **Dinamik Gruplar**: Gruplar, çalışma zamanında mı yoksa yalnızca başlangıçta mı yapılandırılabilir olmalıdır?

4. **Grup Mirası**: Araçlar, grup bilgilerini ebeveyn kategorilerinden veya uygulamalarından mı miras almalıdır?

5. **Performans İzleme**: Grup tabanlı araç kullanımını etkili bir şekilde izlemek için hangi ek metrikler gereklidir?

### 13. Sonuç

Araç grubu sistemi şunları sağlar:

**Güvenlik**: Aracılar üzerindeki yetenekler için ayrıntılı erişim kontrolü
**Performans**: Araç yükleme ve seçim üzerindeki ek yükün azaltılması
**Esneklik**: Çok boyutlu araç sınıflandırması
**Uyumluluk**: Mevcut araç mimarileriyle sorunsuz entegrasyon

Bu sistem, TrustGraph dağıtımlarının araç erişimini daha iyi yönetmesini, güvenlik sınırlarını iyileştirmesini ve mevcut yapılandırmalar ve isteklerle tam uyumluluğu korurken kaynak kullanımını optimize etmesini sağlar.
