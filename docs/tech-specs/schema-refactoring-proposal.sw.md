# Pendekezo la Urekebishaji wa Saraka ya Mfumo

## Masuala Yanayoendelea

1. **Muundo tambarare** - Saraka moja inayokuwa na mifumo yote inafanya iwe ngumu kuelewa uhusiano.
2. **Mambo mchanganyikano** - Aina za msingi, vitu vya kikoa, na mikatiba ya API yote yamechanganywa.
3. **Majina yasiyo wazi** - Faili kama vile "object.py", "types.py", "topic.py" hazionyeshi wazi madhumuni yake.
4. **Hakuna tabaka wazi** - Haiwezekani kuona kwa urahisi nini kinategemea nini.

## Muundo Ulio Pendekezwa

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

## Mabadiliko Muhimu

1. **Mpangilio wa kimfumo** - Tofauti wazi kati ya aina kuu, modeli za maarifa, na mikatiba ya huduma.
2. **Majina bora zaidi**:
   `types.py` → `core/primitives.py` (lengo lililoboreshwa)
   `object.py` → Kugawanywa katika faili zinazofaa kulingana na yaliyomo halisi.
   `documents.py` → `knowledge/document.py` (moja, thabiti)
   `models.py` → `services/llm.py` (wazi zaidi ni aina gani ya modeli)
   `prompt.py` → Kugawanywa: sehemu za huduma hadi `services/prompt.py`, aina za data hadi `knowledge/nlp.py`

3. **Punguzo la mantiki**:
   Aina zote za kuingiza zimeunganishwa katika `knowledge/embeddings.py`
   Mikatiba yote ya huduma inayohusiana na LLM iko katika `services/llm.py`
   Tofauti wazi ya jozi za ombi/jibu katika saraka ya huduma.
   Aina za utoaji wa maarifa zimepangwa pamoja na modeli zingine za uwanja wa maarifa.

4. **Ufafanuzi wa utegemezi**:
   Aina kuu hazina utegemezi wowote.
   Modeli za maarifa hutegemea tu aina kuu.
   Mikatiba ya huduma inaweza kutegemea aina kuu na modeli za maarifa.

## Faida za Uhamisho

1. **Uramaji rahisi** - Wasanidi programu wanaweza kupata haraka kile wanachohitaji.
2. **Uunganishaji bora zaidi** - Mipaka wazi kati ya masuala tofauti.
3. **Uingizaji rahisi zaidi** - Njia za uingizaji ambazo ni za angavu zaidi.
4. **Inaweza kudumu kwa muda mrefu** - Rahisi kuongeza aina mpya za maarifa au huduma bila kusumbua.

## Mfano wa Mabadiliko ya Uingizaji

```python
# Before
from trustgraph.schema import Error, Triple, GraphEmbeddings, TextCompletionRequest

# After
from trustgraph.schema.core import Error, Triple
from trustgraph.schema.knowledge import GraphEmbeddings
from trustgraph.schema.services import TextCompletionRequest
```

## Maelezo ya Utendaji

1. Hakikisha utangamano wa zamani kwa kudumisha uingizaji wa faili katika sehemu kuu `__init__.py`
2. Hamisha faili hatua kwa hatua, na usasishe uingizaji wa faili kama inavyohitajika
3. Fikiria kuongeza `legacy.py` ambayo huingiza kila kitu kwa kipindi cha mpito
4. Sasisha nyaraka ili kuonyesha muundo mpya

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Fanyia uchunguzi muundo wa sasa wa saraka ya schema", "status": "imekamilika", "priority": "juu"}, {"id": "2", "content": "Changanua faili za schema na madhumuni yao", "status": "imekamilika", "priority": "juu"}, {"id": "3", "content": "Pendekeza jina na muundo uliobora", "status": "imekamilika", "priority": "juu"}]