# Dondoo la Maarifa la Ontolojia - Awamu ya 2 ya Urekebishaji

**Hali**: Rasimu
**Mwandishi**: Mkutano wa Uchambuzi wa 2025-12-03
**Inahusiana na**: `ontology.md`, `ontorag.md`

## Muhtasari

Hati hii inataja kutofautiana katika mfumo wa sasa wa dondoo la maarifa unaotegemea ontolojia na inapendekeza urekebishaji ili kuboresha utendaji wa LLM na kupunguza upotevu wa habari.

## Utendaji wa Sasa

### Inavyofanya Sasa

1. **Kupakia Ontolojia** (`ontology_loader.py`)
   Inapakia JSON ya ontolojia na vitufe kama `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"`
   Nambari za darasa zina jalizi la nafasi katika kitufe yenyewe
   Mfano kutoka `food.ontology`:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **Uundaji wa Maagizo** (`extract.py:299-307`, `ontology-prompt.md`)
   Kiolezo kinapokea dictionaries `classes`, `object_properties`, `datatype_properties`
   Kiolezo huchanganua: `{% for class_id, class_def in classes.items() %}`
   LLM inaona: `**fo/Recipe**: A Recipe is a combination...`
   Muundo wa mfano wa matokeo unaonyesha:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **Uchambuzi wa Majibu** (`extract.py:382-428`)
   Inatarajia safu ya JSON: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   Inathibitisha dhidi ya sehemu ya ontolojia
   Inapanua URI kupitia `expand_uri()` (extract.py:473-521)

4. **Upanuzi wa URI** (`extract.py:473-521`)
   Inangalia ikiwa thamani iko katika kamusi `ontology_subset.classes`
   Ikiwa imepatikana, inatoa URI kutoka kwenye ufafanuzi wa darasa
   Ikiwa haijapatikana, inaunda URI: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### Mfano wa Mtiririko wa Data

**Ontolojia ya JSON → Mpakuzi → Ombi:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**LLM → Mfumo wa Uchambuzi → Matokeo:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## Matatizo Yaliyobainika

### 1. **Mfano Usiofuata Kanuni katika Maagizo**

**Tatizo**: Kiolezo cha maagizo huonyesha vitambulisho vya darasa na mabainisha (`fo/Recipe`) lakini matokeo ya mfano hutumia majina ya darasa yasiyo na mabainisha (`Recipe`).

**Mahali**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**Athari**: Mfumo wa lugha (LLM) hupokea ishara tofauti kuhusu muundo ambao unapaswa kutumika.

### 2. **Upatanishi wa Habari katika Upanuzi wa URI**

**Tatizo**: Wakati LLM hurudisha majina ya darasa ambayo hayana alama ya mbele, kama ilivyoelezwa katika mfano, `expand_uri()` hayawezi kuyakuta katika kamusi ya ontolojia na huunda URI za dharura, na kusababisha kupoteza URI za asili.

**Mahali**: `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**Athari**:
URI asili: `http://purl.org/ontology/fo/Recipe`
URI iliyoundwa: `https://trustgraph.ai/ontology/food#Recipe`
Maana ya kielelezo yamepotea, husababisha kutofanya kazi kwa pamoja.

### 3. **Muundo Usio Wazi wa Eneo la Kitu**

**Tatizo**: Hakuna mwongozo wazi kuhusu muundo wa URI ya eneo la kitu.

**Mfano katika maagizo**:
`"recipe:cornish-pasty"` (kielezi kama kielezi)
`"ingredient:flour"` (kielezi tofauti)

**Tabia halisi** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**Athari**: Mfumo wa lugha (LLM) lazima ajue mbinu ya kuweka alama (prefixing) bila kuwa na msingi wa elimu (ontology).

### 4. **Hakuna Maelekezo ya Mbele ya Nafasi (Namespace)**

**Tatizo**: Faili ya JSON ya elimu ina maelezo ya nafasi (namespace) (kwa mstari wa 10-25 katika food.ontology):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

Lakini mistari hii haionyeshwi kwa mfumo wa lugha (LLM). MFUMO WA LUGHA (LLM) haujua:
Maana ya "fo"
Njia gani ya kutumia kwa vitu
Nafasi gani inayotumika kwa vipengele

### 5. **Lebo Ambazo Hazitumiki katika Swali**

**Tatizo**: Kila darasa lina sehemu za `rdfs:label` (k.m., `{"value": "Recipe", "lang": "en-gb"}`), lakini kigezo cha swali haziitumii.

**Hali ya sasa**: Inaonyesha tu `class_id` na `comment`
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**Inapatikana lakini haitumiki:**
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**Athari**: Inaweza kutoa majina ambayo yanaweza kueleweka kwa binadamu pamoja na vitambulisho vya kiufundi.

## Suluhisho Zilizopendekezwa

### Chaguo A: Kuweka Vipengele sawa na Vitambulisho visivyo na Mbele

**Mbinu**: Ondoa mbele kutoka kwa vitambulisho vya darasa kabla ya kuviwasha kwa mfumo wa akili bandia (LLM).

**Mabadiliko**:
1. Badilisha `build_extraction_variables()` ili kubadilisha funguo:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. Sasisha mfano wa maagizo ili ufanane (tayari hutumia majina yasiyo na alama).

3. Badilisha `expand_uri()` ili iweze kushughulikia aina zote mbili:
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

**Faida:**
Safi zaidi, rahisi zaidi kusoma na kuelewa.
Inafanana na mifano iliyopo ya maagizo.
Mifumo ya lugha kubwa (LLMs) hufanya kazi vizuri zaidi na alama (tokens) rahisi.

**Hasara:**
Migongano ya majina ya madarasa ikiwa ontolojia nyingi zina jina sawa la darasa.
Inapoteza habari ya nafasi (namespace).
Inahitaji mantiki ya dharura kwa utafutaji.

### Chaguo B: Tumia Kitambulisho Kamili Chenye Alama (Prefix) kwa Ufanisi

**Mbinu:** Sasisha mifano ili kutumia kitambulisho chenye alama kinacholingana na kile kinachoonyeshwa katika orodha ya madarasa.

**Mabadiliko:**
1. Sasisha mfano wa agizo (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. Ongeza maelezo ya nafasi ya kazi kwenye swali:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. Acha `expand_uri()` kama ilivyo (hufanya kazi vizuri wakati mechi zinapopatikana).

**Faida:**
Ulinganisho kati ya ingizo na pato.
Hakuna upotevu wa habari.
Inahifadhi maana ya nafasi (namespace).
Inafanya kazi na ontolojia nyingi.

**Hasara:**
Alama (tokens) zaidi kwa LLM.
Inahitaji LLM kufuatilia alama za mbele (prefixes).

### Chaguo C: Mchanganyiko - Onyesha Lebo na Kitambulisho (ID)

**Mbinu:** Ongeza maagizo katika swali ili kuonyesha lebo zinazoweza kusomwa na binadamu na kitambulisho (ID) cha kiufundi.

**Mabadiliko:**
1. Sasisha mfumo wa swali:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   Matokeo ya mfano:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. Maelekezo ya sasisho:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**Faida:**
Inafaa zaidi kwa mifumo ya lugha kubwa (LLM).
Inahifadhi habari yote.
Inaeleza wazi ni nini kinachotakiwa kutumika.

**Hasara:**
Ombi refu zaidi.
Mfumo mgumu zaidi.

## Njia Iliyotekelezwa

**Muundo Ulioboreshwa wa Muhusiano wa Vitu na Sifa** - unaibadilisha kabisa mfumo wa zamani unaotegemea triplet.

Njia mpya ilichaguliwa kwa sababu:

1. **Hakuna Upotevu wa Habari:** Anwani za mtandaoni (URIs) za awali zinaendelea kuhifadhiwa kwa usahihi.
2. **Mantiki Rahisi:** Hakuna mabadiliko yanayohitajika, utafutaji wa moja kwa moja wa kamusi unafanya kazi.
3. **Usalama wa Nafasi:** Inashughulikia ontolojia nyingi bila migongano.
4. **Ukweli wa Kisia:** Inahifadhi maana ya RDF/OWL.

## Utendaji Uliofanyika

### Kilichojengwa:

1. **Mfumo Mpya wa Ombi** (`prompts/ontology-extract-v2.txt`)
   ✅ Sehemu zilizoelezwa wazi: Aina za Vitu, Mahusiano, Sifa.
   ✅ Mfano unaotumia kitambulisho kamili cha aina (`fo/Recipe`, `fo/has_ingredient`).
   ✅ Maelekezo ya kutumia kitambulisho halisi kutoka kwa schema.
   ✅ Muundo mpya wa JSON na safu za vitu/mahusiano/sifa.

2. **Urekebishaji wa Vitu** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - Inabadilisha majina kuwa muundo salama wa URI.
   ✅ `normalize_type_identifier()` - Inashughulikia alama za upande katika aina (`fo/Recipe` → `fo-recipe`).
   ✅ `build_entity_uri()` - Inaunda anwani za kipekee (URIs) kwa kutumia jozi (jina, aina).
   ✅ `EntityRegistry` - Inafuatilia vitu ili kuepuka marudia.

3. **Mchangamizi wa JSON** (`simplified_parser.py`)
   ✅ Inachanganua muundo mpya: `{entities: [...], relationships: [...], attributes: [...]}`.
   ✅ Inasaidia majina ya sehemu katika muundo wa kebab na muundo wa nyoka.
   ✅ Inarudisha madarasa ya data iliyopangwa.
   ✅ Usimamizi wa makosa kwa njia nzuri pamoja na uandishi wa matukio.

4. **Mabadilishaji wa Triplet** (`triple_converter.py`)
   ✅ `convert_entity()` - Inaunda triplet za aina + lebo moja kwa moja.
   ✅ `convert_relationship()` - Inaunganisha anwani za vitu (URIs) kupitia sifa.
   ✅ `convert_attribute()` - Inaongeza maadili ya moja kwa moja.
   ✅ Inatafuta anwani kamili kutoka kwa maelezo ya ontolojia.

5. **Mchakato Mkuu Uliosasishwa** (`extract.py`)
   ✅ Imeondoa msimbo wa zamani wa uondoaji wa triplet.
   ✅ Imeongeza `extract_with_simplified_format()`.
   ✅ Sasa inatumia tu muundo uliorahisishwa.
   ✅ Inaitisha ombi na kitambulisho `extract-with-ontologies-v2`.

## Majaribio

### Jaribio la 1: Uhifadhi wa URI
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### Mtihani wa 2: Mzozo wa Ontolojia Nyingi
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### Mtihani wa 3: Muundo wa Eneo la Mfano
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## Maswali ya Kufungua

1. **Je, vipozi vya mifano ya vitu vinapaswa kutumia mbele za nafasi?**
   Sasa: `"recipe:cornish-pasty"` (ya hiari)
   Mbadala: Je, kutumia mbele ya ontolojia `"fo:cornish-pasty"`?
   Mbadala: Hakuna mbele, kupanua katika URI `"cornish-pasty"` → URI kamili?

2. **Jinsi ya kushughulikia uwanja/jukumu katika swali?**
   Kwa sasa inaonyesha: `(Recipe → Food)`
   Je, inapaswa kuwa: `(fo/Recipe → fo/Food)`?

3. **Je, tunapaswa kuthibitisha vikwazo vya uwanja/jukumu?**
   TODO maoni katika extract.py:470
   Itakamata makosa zaidi lakini ni ngumu zaidi

4. **Hebu kuhusu sifa za kinyume na usawa?**
   Ontolojia ina `owl:inverseOf`, `owl:equivalentClass`
   Hasa haitumiki katika uondoaji
   Je, inapaswa kutumika?

## Viashiria vya Mafanikio

✅ Hakuna upotevu wa habari ya URI (uhifadhi wa 100% wa URI za awali)
✅ Muundo wa pato la LLM unalingana na muundo wa ingizo
✅ Hakuna mifano ya kusumbua katika swali
✅ Vipimo hufanikiwa na ontolojia nyingi
✅ Ubora wa uondoaji ulioboreshwa (uliofanywa na asilimia ya triple halali)

## Mbinu Mbadala: Muundo Ulioboreshwa wa Uondoaji

### Falsafa

Badala ya kuuliza LLM kuelewa maana ya RDF/OWL, waulize ifanye kile ambacho ni nzuri: **kutafuta vitu na uhusiano katika maandishi**.

Acha msimbo kushughulikia uundaji wa URI, ubadilishaji wa RDF, na mambo rasmi ya wavuti ya kiakili.

### Mfano: Uainishaji wa Vitu

**Maandishi ya Ingizo:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**Muundo wa Ontolojia (unaonyeshwa kwa mfumo wa lugha kubwa):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**Kinachorudishwa na Mfumo wa Lugha Kubwa (JSON Rahisi):**
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

**Ni Nini Ambo Inazalisha (Triple za RDF):**
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

### Faida

1. **LLM haihitaji:**
   Kuelewa sintaksia ya URI
   Kuunda mbele za kitambulisho (`recipe:`, `ingredient:`)
   Kujua kuhusu `rdf:type` au `rdfs:label`
   Kuunda kitambulisho cha mtandao wa maana

2. **LLM inahitaji tu:**
   Kupata vitu katika maandishi
   Kuviweka katika madarasa ya ontolojia
   Kuchukua uhusiano na sifa

3. **Msimbo hushughulikia:**
   Usanifu na uundaji wa URI
   Uzalishaji wa triple za RDF
   Uwekaji wa kiotomatiki wa lebo
   Usimamizi wa nafasi

### Kwa Nini Hii Inafanya Vyema

**Swali rahisi** = uchanganyifu mdogo = makosa machache
**Kitambulisho thabiti** = msimbo udhibiti sheria za usanifu
**Lebo zilizozalishwa kiotomatiki** = hakuna triple za rdfs:label zilizopotea
**LLM inazingatia uondoaji** = ambayo ni jambo ambalo inafaa

### Mfano: Uhusiano wa Vitu

**Maandishi ya Ingizo:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**Muundo wa Ontolojia (unaonyeshwa kwa LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**Kinachorudishwa na Mfumo wa Lugha Kubwa (JSON Rahisi):**
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

**Ni Nini Ambo Inazalisha (Triple za RDF):**
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

**Pointi Muhimu:**
LLM hurudia majina ya vitu katika lugha ya asili: `"Cornish pasty"`, `"beef"`, `"potatoes"`
LLM hujumuisha aina ili kufafanua: `subject-type`, `object-type`
LLM hutumia jina la uhusiano kutoka kwa schema: `"has_ingredient"`
Msimbo hutengeneza vitambulisho vinavyolingana kwa kutumia (jina, aina): `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
Msimbo hutafuta URI ya uhusiano kutoka kwa ontolojia: `fo/has_ingredient` → URI kamili
Jozi sawa (jina, aina) daima hupata URI sawa (kuondoa marudia)

### Mfano: Utambuzi wa Jina la Kitu

**Tatizo:** Jina lile lile linaweza kurejelea aina tofauti za vitu.

**Mfano halisi:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**Jinsi Inavyoshughuliwa:**

Mfumo wa lugha kubwa (LLM) hurudisha yote kama vitu tofauti:
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

**Suluhisho la Msimbo:**
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

**Kwa Nini Hifanya Kazi:**
Aina (type) imejumuishwa katika marejeleo yote (vitu, uhusiano, sifa).
Msimbo hutumia `(name, type)` kama ufunguo wa utafutaji.
Hakuna ukosefu wa uwazi, hakuna migongano.

### Mifano: Sifa za Vitu

**Nakala ya Ingizo:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**Muundo wa Ontolojia (unaonyeshwa kwa LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**Kinachorudishwa na Mfumo wa Lugha Kubwa (JSON Rahisi):**
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

**Ni Nini Ambo Inazalisha (Triple za RDF):**
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

**Pointi Muhimu:**
LLM huchukua maadili halisi: `"4-6 people"`, `"45 minutes"`
LLM hujumuisha aina ya kitu ili kuepusha utofauti: `entity-type`
LLM hutumia jina la sifa kutoka kwa schema: `"serves"`, `"preparation_time"`
Msimbo hutafuta URI ya sifa kutoka kwa sifa za aina ya ontology
**Kitu ni halali** (`is_uri=False`), si rejea la URI
Maadili husalia kama maandishi ya asili, hakuna haja ya urekebishaji

**Tofauti na Mahusiano:**
Mahusiano: kitu cha kwanza na cha pili ni vitu (URIs)
Sifa: kitu cha kwanza ni kitu (URI), kitu cha pili ni thamani halali (mstari/nambari)

### Mfano Kamili: Vitu + Mahusiano + Sifa

**Maandishi ya Ingizo:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**Hili Ni Lile Ambalo Mfumo wa Lugha Kubwa Hurudisha:**
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

**Matokeo:** Triple 11 za RDF zilizoundwa:
Triple 3 za aina ya kitu (rdf:type)
Triple 3 za lebo ya kitu (rdfs:label) - moja kwa moja
Triple 2 za uhusiano (ina_viungo)
Triple 1 ya sifa (inafaa)

Yote kutoka kwa uundaji rahisi, wa lugha ya asili na mfumo wa akili bandia (LLM)!

## Marejeleo

Utaratibu wa sasa: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
Mfumo wa swali: `ontology-prompt.md`
Majaribio: `tests/unit/test_extract/test_ontology/`
Ontolojia ya mfano: `e2e/test-data/food.ontology`
