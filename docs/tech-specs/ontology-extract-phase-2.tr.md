---
layout: default
title: "Ontoloji Bilgi Çıkarma - 2. Aşama Yeniden Düzenleme"
parent: "Turkish (Beta)"
---

# Ontoloji Bilgi Çıkarma - 2. Aşama Yeniden Düzenleme

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Durum**: Taslak
**Yazar**: Analiz Oturumu 2025-12-03
**İlgili**: `ontology.md`, `ontorag.md`

## Genel Bakış

Bu belge, mevcut ontoloji tabanlı bilgi çıkarma sistemindeki tutarsızlıkları belirlemektedir ve LLM performansını iyileştirmek ve bilgi kaybını azaltmak için bir yeniden düzenleme önermektedir.

## Mevcut Uygulama

### Şu Anda Nasıl Çalışıyor

1. **Ontoloji Yükleme** (`ontology_loader.py`)
   `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"` gibi anahtarlara sahip ontoloji JSON'unu yükler.
   Sınıf kimlikleri, anahtar içinde namespace önekini içerir.
   `food.ontology`'dan bir örnek:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **İstem Oluşturma** (`extract.py:299-307`, `ontology-prompt.md`)
   Şablon, `classes`, `object_properties`, `datatype_properties` sözlüklerini alır.
   Şablon döngüye girer: `{% for class_id, class_def in classes.items() %}`
   LLM (Büyük Dil Modeli) şunları görür: `**fo/Recipe**: A Recipe is a combination...`
   Örnek çıktı formatı şöyledir:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **Yanıt Ayrıştırma** (`extract.py:382-428`)
   JSON dizisi beklenir: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   Ontoloji alt kümesine göre doğrulanır.
   URI'lar `expand_uri()` aracılığıyla genişletilir (extract.py:473-521).

4. **URI Genişletme** (`extract.py:473-521`)
   Değerin `ontology_subset.classes` sözlüğünde olup olmadığını kontrol eder.
   Bulunursa, URI sınıf tanımından çıkarılır.
   Bulunmazsa, URI oluşturulur: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### Veri Akışı Örneği

**Ontoloji JSON → Yükleyici → İstek:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**LLM → Ayrıştırıcı → Çıktı:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## Belirlenen Sorunlar

### 1. **İstemde Tutarsız Örnekler**

**Sorun**: İstem şablonu, sınıf kimliklerini öneklerle (`fo/Recipe`) gösterirken, örnek çıktı önek kullanılmayan sınıf adlarını kullanır (`Recipe`).

**Konum**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**Etki**: LLM, hangi formatı kullanması gerektiği konusunda çelişkili sinyaller alır.

### 2. **URI Genişletmesinde Bilgi Kaybı**

**Sorun**: LLM, örneğe uygun olarak önekli olmayan sınıf adları döndürdüğünde, `expand_uri()` bunları ontoloji sözlüğünde bulamaz ve yedek URI'ler oluşturur, böylece orijinal doğru URI'ler kaybolur.

**Konum**: `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**Etki:**
Orijinal URI: `http://purl.org/ontology/fo/Recipe`
Oluşturulmuş URI: `https://trustgraph.ai/ontology/food#Recipe`
Anlamsal anlam kayboluyor, birlikte çalışabilirlik bozuluyor.

### 3. **Belirsiz Varlık Örneği Biçimi**

**Sorun:** Varlık örneği URI biçimi hakkında net bir rehberlik yok.

**İpuçlarındaki örnekler:**
`"recipe:cornish-pasty"` (namespace benzeri önek)
`"ingredient:flour"` (farklı önek)

**Gerçek davranış** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**Etki**: LLM'nin, herhangi bir ontoloji bağlamı olmadan, önekleme kuralını tahmin etmesi gerekir.

### 4. **Ada Alanı Önekleri Hakkında Rehberlik Yok**

**Sorun**: Ontoloji JSON dosyası, ada alanı tanımlarını içerir (food.ontology dosyasının 10-25. satırları):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

Ancak bunlar asla LLM'ye iletilmez. LLM şunları bilmez:
"fo" kelimesinin ne anlama geldiğini
Varlıklar için hangi öneklerin kullanılması gerektiğini
Hangi ad alanının hangi öğelere uygulandığını

### 5. **İpuçunda Kullanılmayan Etiketler**

**Sorun**: Her sınıfın `rdfs:label` alanları vardır (örneğin, `{"value": "Recipe", "lang": "en-gb"}`), ancak ipucu şablonu bunları kullanmaz.

**Mevcut durum**: Sadece `class_id` ve `comment` gösteriliyor.
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**Kullanılabilir ancak kullanılmayan:**
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**Etki**: Teknik kimliklerin yanı sıra insan tarafından okunabilir isimler sağlayabilir.

## Önerilen Çözümler

### Seçenek A: Önek Olmayan Kimliklere Normalleştirme

**Yaklaşım**: Sınıf kimliklerinden önekleri, LLM'ye göstermeden önce kaldırın.

**Değişiklikler**:
1. `build_extraction_variables()`'ı, anahtarları dönüştürmek için değiştirin:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. İstem örneğini, (zaten önek kullanmayan) mevcut duruma uygun hale getirin.

3. `expand_uri()`'ı, her iki formatı da işleyebilecek şekilde değiştirin:
   ```python
   # Try exact match first
   if value in ontology_subset.classes:
       return ontology_subset.classes[value]['uri']

   # Try with prefix
   for prefix in ['fo/', 'rdf:', 'rdfs:']:
       prefixed = f"{prefix}{value}"
       if prefixed in ontology_subset.classes:
           return ontology_subset.classes[prefixed]['uri']
   ```

**Artıları:**
Daha temiz, daha insan tarafından okunabilir
Mevcut örnek istemlerle eşleşir
Büyük dil modelleri (LLM'ler), daha basit belirteçlerle daha iyi çalışır

**Eksileri:**
Birden fazla ontolojinin aynı sınıf adına sahip olması durumunda sınıf adı çakışmaları
Ad alanı bilgilerini kaybettirir
Arama işlemlerinde yedekleme mantığı gerektirir

### B Seçeneği: Tam Önekli Kimlikleri Tutarlı Bir Şekilde Kullanın

**Yaklaşım:** Örnekleri, sınıf listesinde gösterilenlerle eşleşen önekli kimlikleri kullanacak şekilde güncelleyin.

**Değişiklikler:**
1. Örnek istemi güncelleyin (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. İstemde (prompt) ad alanı açıklamasını ekleyin:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. `expand_uri()`'ı olduğu gibi tutun (eşleşmeler bulunduğunda doğru şekilde çalışır).

**Avantajları:**
Giriş = Çıkış tutarlılığı
Bilgi kaybı yok
Ada alanı semantiğini korur
Birden fazla ontoloji ile çalışır

**Dezavantajları:**
LLM için daha ayrıntılı belirteçler
LLM'nin önekleri takip etmesini gerektirir

### Seçenek C: Hibrit - Hem Etiketi Hem de Kimliği Gösterin

**Yaklaşım:** İnsan tarafından okunabilir etiketleri ve teknik kimlikleri göstermek için istemi geliştirin.

**Değişiklikler:**
1. İstem şablonunu güncelleyin:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   Örnek çıktı:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. Güncelleme talimatları:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**Avantajları**:
LLM için en anlaşılır olanı
Tüm bilgileri korur
Ne kullanılması gerektiği konusunda açık

**Dezavantajları**:
Daha uzun bir istem
Daha karmaşık bir şablon

## Uygulanan Yaklaşım

**Basitleştirilmiş Varlık-İlişki-Özellik Formatı** - eski üçlü tabanlı formatın tamamen yerini alır.

Bu yeni yaklaşım aşağıdaki nedenlerle seçilmiştir:

1. **Bilgi Kaybı Yok**: Orijinal URI'ler doğru şekilde korunur
2. **Daha Basit Mantık**: Dönüştürmeye gerek yoktur, doğrudan sözlük aramaları çalışır
3. **Ad Alanı Güvenliği**: Çakışmalar olmadan birden fazla ontolojiyi işler
4. **Anlamsal Doğruluk**: RDF/OWL semantiğini korur

## Uygulama Tamamlandı

### Oluşturulanlar:

1. **Yeni İstek Şablonu** (`prompts/ontology-extract-v2.txt`)
   ✅ Açık bölümler: Varlık Türleri, İlişkiler, Özellikler
   ✅ Tam tür tanımlayıcılarını kullanan örnek (`fo/Recipe`, `fo/has_ingredient`)
   ✅ Şemadan tam tanımlayıcıları kullanma talimatları
   ✅ Varlıklar/ilişkiler/özellikler dizileri içeren yeni JSON formatı

2. **Varlık Normalizasyonu** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - İsimleri URI'ye uygun formata dönüştürür
   ✅ `normalize_type_identifier()` - Türlerdeki eğik çizgileri işler (`fo/Recipe` → `fo-recipe`)
   ✅ `build_entity_uri()` - (isim, tür) tuple'ını kullanarak benzersiz URI'ler oluşturur
   ✅ `EntityRegistry` - Tekrarlamayı önlemek için varlıkları takip eder

3. **JSON Ayrıştırıcı** (`simplified_parser.py`)
   ✅ Yeni formatı ayrıştırır: `{entities: [...], relationships: [...], attributes: [...]}`
   ✅ kebab-case ve snake_case alan adlarını destekler
   ✅ Yapılandırılmış veri sınıfları döndürür
   ✅ Günlükleme ile zarif hata işleme

4. **Üçlü Dönüştürücü** (`triple_converter.py`)
   ✅ `convert_entity()` - Tür + etiket üçlülerini otomatik olarak oluşturur
   ✅ `convert_relationship()` - Varlık URI'lerini özellikler aracılığıyla bağlar
   ✅ `convert_attribute()` - Literal değerleri ekler
   ✅ Ontoloji tanımlarından tam URI'leri alır

5. **Güncellenmiş Ana İşlemci** (`extract.py`)
   ✅ Eski üçlü tabanlı çıkarma kodunu kaldırdı
   ✅ `extract_with_simplified_format()` yöntemini ekledi
   ✅ Artık yalnızca yeni, basitleştirilmiş formatı kullanır
   ✅ İstemleri `extract-with-ontologies-v2` kimliğiyle çağırır

## Test Senaryoları

### Test 1: URI Korunması
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### Test 2: Çoklu Ontoloji Çakışması
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### Test 3: Varlık Örneği Formatı
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## Açık Sorular

1. **Varlık örnekleri namespace önekleri kullanmalı mı?**
   Mevcut durum: `"recipe:cornish-pasty"` (keyfi)
   Alternatif: Ontoloji önekini kullanın `"fo:cornish-pasty"`?
   Alternatif: Önek yok, URI'da genişletin `"cornish-pasty"` → tam URI?

2. **Alan/kapsam (domain/range) nasıl işlenmeli?**
   Şu anda gösterilen: `(Recipe → Food)`
   Şu şekilde olmalı mı: `(fo/Recipe → fo/Food)`?

3. **Alan/kapsam kısıtlamalarını doğrulamalı mıyız?**
   TODO yorumu extract.py:470 satırında
   Daha fazla hata yakalanır, ancak daha karmaşık olur

4. **Ters özellikler ve eşdeğerlikler hakkında ne düşünülmeli?**
   Ontolojide `owl:inverseOf`, `owl:equivalentClass` bulunmaktadır
   Şu anda çıkarımda kullanılmıyor
   Kullanılmalı mı?

## Başarı Metrikleri

✅ Sıfır URI bilgisi kaybı (orijinal URI'lerin %100 korunması)
✅ LLM çıktısı formatı, giriş formatıyla eşleşiyor
✅ Girişte belirsiz örnek yok
✅ Birden fazla ontolojiyle testler geçiliyor
✅ İyileştirilmiş çıkarım kalitesi (geçerli üçlü yüzdesi ile ölçülür)

## Alternatif Yaklaşım: Basitleştirilmiş Çıkarım Formatı

### Felsefe

LLM'den RDF/OWL semantiğini anlamasını istemek yerine, LLM'nin iyi olduğu şeyi yapmasını isteyin: **metindeki varlıkları ve ilişkileri bulun**.

URI oluşturma, RDF'ye dönüştürme ve semantik web formalitelerini kodun halletmesine izin verin.

### Örnek: Varlık Sınıflandırması

**Giriş Metni:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**Ontoloji Şeması (LLM'ye gösterilen):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**LLM'nin Döndürdükleri (Basit JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    }
  ]
}
```

**Kodun Ürettiği Şeyler (RDF Üçlüleri):**
```python
# 1. Normalize entity name + type to ID (type prevents collisions)
entity_id = "recipe-cornish-pasty"  # normalize("Cornish pasty", "Recipe")
entity_uri = "https://trustgraph.ai/food/recipe-cornish-pasty"

# Note: Same name, different type = different URI
# "Cornish pasty" (Recipe) → recipe-cornish-pasty
# "Cornish pasty" (Food) → food-cornish-pasty

# 2. Generate triples
triples = [
    # Type triple
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),
    # Label triple (automatic)
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
        o=Value(value="Cornish pasty", is_uri=False)
    )
]
```

### Faydalar

1. **LLM'nin (Büyük Dil Modeli) yapması gerekmiyor:**
   URI sözdizimini anlamak
   Tanımlayıcı önekleri oluşturmak (`recipe:`, `ingredient:`)
   `rdf:type` veya `rdfs:label` hakkında bilgi sahibi olmak
   Semantik web tanımlayıcıları oluşturmak

2. **LLM'nin sadece yapması gerekiyor:**
   Metindeki varlıkları bulmak
   Bunları ontoloji sınıflarına eşlemek
   İlişkileri ve özellikleri çıkarmak

3. **Kod şunları yönetir:**
   URI normalizasyonu ve oluşturulması
   RDF üçlü üretimi
   Otomatik etiket ataması
   İsim alanı yönetimi

### Neden Bu Daha İyi Çalışıyor

**Daha basit istem** = daha az kafa karışıklığı = daha az hata
**Tutarlı kimlikler** = kod, normalizasyon kurallarını kontrol eder
**Otomatik olarak oluşturulan etiketler** = eksik rdfs:label üçlüleri yok
**LLM, çıkarma üzerine odaklanır** = aslında iyi olduğu şey

### Örnek: Varlık İlişkileri

**Giriş Metni:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**Ontoloji Şeması (LLM'ye gösterilen):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**LLM'nin Döndürdükleri (Basit JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ]
}
```

**Kodun Ürettiği Şeyler (RDF Üçlüleri):**
```python
# Normalize entity names to URIs
cornish_pasty_uri = "https://trustgraph.ai/food/cornish-pasty"
beef_uri = "https://trustgraph.ai/food/beef"
potatoes_uri = "https://trustgraph.ai/food/potatoes"

# Look up relation URI from ontology
has_ingredient_uri = "http://purl.org/ontology/fo/ingredients"  # from fo/has_ingredient

triples = [
    # Entity type triples (as before)
    Triple(s=cornish_pasty_uri, p=rdf_type, o="http://purl.org/ontology/fo/Recipe"),
    Triple(s=cornish_pasty_uri, p=rdfs_label, o="Cornish pasty"),

    Triple(s=beef_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=beef_uri, p=rdfs_label, o="beef"),

    Triple(s=potatoes_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=potatoes_uri, p=rdfs_label, o="potatoes"),

    # Relationship triples
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=beef_uri, is_uri=True)
    ),
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=potatoes_uri, is_uri=True)
    )
]
```

**Önemli Noktalar:**
LLM, doğal dil varlık isimlerini döndürür: `"Cornish pasty"`, `"beef"`, `"potatoes"`
LLM, anlam belirsizliğini gidermek için türleri içerir: `subject-type`, `object-type`
LLM, şemadan ilişki adını kullanır: `"has_ingredient"`
Kod, (isim, tür) kullanarak tutarlı kimlikler türetir: `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
Kod, ontolojiden ilişki URI'sini arar: `fo/has_ingredient` → tam URI
Aynı (isim, tür) ikilisi her zaman aynı URI'yi alır (çiftleme önleme)

### Örnek: Varlık İsimlerinin Anlam Belirsizliğinin Giderilmesi

**Sorun:** Aynı isim, farklı varlık türlerini ifade edebilir.

**Gerçek dünya örneği:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**Nasıl İşlendiği:**

LLM, her ikisini de ayrı varlıklar olarak döndürür:
```json
{
  "entities": [
    {"entity": "Cornish pasty", "type": "Recipe"},
    {"entity": "Cornish pasty", "type": "Food"}
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "produces",
      "object": "Cornish pasty",
      "object-type": "Food"
    }
  ]
}
```

**Kod Çözümleme:**
```python
# Different types → different URIs
recipe_uri = normalize("Cornish pasty", "Recipe")
# → "https://trustgraph.ai/food/recipe-cornish-pasty"

food_uri = normalize("Cornish pasty", "Food")
# → "https://trustgraph.ai/food/food-cornish-pasty"

# Relationship connects them correctly
triple = Triple(
    s=recipe_uri,  # The Recipe
    p="http://purl.org/ontology/fo/produces",
    o=food_uri     # The Food
)
```

**Neden İşe Yarıyor:**
Tip, TÜM referanslarda (varlıklar, ilişkiler, özellikler) bulunur.
Kod, arama anahtarı olarak `(name, type)` tuple'ını kullanır.
Herhangi bir belirsizlik, herhangi bir çakışma yoktur.

### Örnek: Varlık Özellikleri

**Giriş Metni:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**Ontoloji Şeması (LLM'ye gösterilen):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**LLM'nin Döndürdükleri (Basit JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty recipe",
      "type": "Recipe"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4-6 people"
    },
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "preparation_time",
      "value": "45 minutes"
    }
  ]
}
```

**Kodun Ürettiği Şeyler (RDF Üçlüleri):**
```python
# Normalize entity name to URI
recipe_uri = "https://trustgraph.ai/food/cornish-pasty-recipe"

# Look up attribute URIs from ontology
serves_uri = "http://purl.org/ontology/fo/serves"  # from fo/serves
prep_time_uri = "http://purl.org/ontology/fo/preparation_time"  # from fo/preparation_time

triples = [
    # Entity type triple
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdf_type, is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),

    # Label triple (automatic)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdfs_label, is_uri=True),
        o=Value(value="Cornish pasty recipe", is_uri=False)
    ),

    # Attribute triples (objects are literals, not URIs)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=serves_uri, is_uri=True),
        o=Value(value="4-6 people", is_uri=False)  # Literal value!
    ),
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=prep_time_uri, is_uri=True),
        o=Value(value="45 minutes", is_uri=False)  # Literal value!
    )
]
```

**Önemli Noktalar:**
LLM, gerçek değerleri çıkarır: `"4-6 people"`, `"45 minutes"`
LLM, anlam ayrımı için varlık türünü içerir: `entity-type`
LLM, şemadan öznitelik adını kullanır: `"serves"`, `"preparation_time"`
Kod, öznitelik URI'sini ontoloji veri türü özelliklerinden arar
**Nesne bir literaldir** (`is_uri=False`), bir URI referansı değildir
Değerler, doğal metin olarak kalır, normalleştirmeye gerek yoktur

**İlişkilerden Farkı:**
İlişkiler: hem konu hem de nesne varlıklardır (URI'ler)
Öznitelikler: konu bir varlıktır (URI), nesne bir literal değerdir (dize/sayı)

### Tam Örnek: Varlıklar + İlişkiler + Öznitelikler

**Giriş Metni:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**LLM'nin Döndürdükleri:**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4 people"
    }
  ]
}
```

**Sonuç:** 11 RDF üçlüsü oluşturuldu:
3 varlık türü üçlüsü (rdf:type)
3 varlık etiket üçlüsü (rdfs:label) - otomatik
2 ilişki üçlüsü (has_ingredient)
1 özellik üçlüsü (serves)

Bunların hepsi, LLM tarafından yapılan basit, doğal dil çıkarımlarından elde edilmiştir!

## Referanslar

Mevcut uygulama: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
İstek şablonu: `ontology-prompt.md`
Test senaryoları: `tests/unit/test_extract/test_ontology/`
Örnek ontoloji: `e2e/test-data/food.ontology`
