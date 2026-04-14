---
layout: default
title: "Происхождение извлечения: Модель подграфа"
parent: "Russian (Beta)"
---

# Происхождение извлечения: Модель подграфа

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Проблема

<<<<<<< HEAD
В настоящее время механизм отслеживания происхождения, работающий во время извлечения, создает полную реификацию для каждого
извлеченного тройства: уникальный `stmt_uri`, `activity_uri` и связанные
метаданные PROV-O для каждого отдельного факта знаний. Обработка одного блока
данных, который дает 20 отношений, приводит к появлению примерно 220 тройств отслеживания происхождения в дополнение к
примерно 20 тройствам знаний — это примерно 10:1 избыточности.

Это дорого (хранение, индексация, передача) и семантически
неточно. Каждый блок обрабатывается одним вызовом LLM, который создает
все свои тройства за одну транзакцию. Текущая модель, основанная на тройствах,
искажает это, создавая иллюзию 20 независимых событий извлечения.


Кроме того, два из четырех процессоров извлечения (kg-extract-ontology,
kg-extract-agent) вообще не имеют информации об отслеживании происхождения, что оставляет пробелы в журнале аудита.


## Решение

Заменить реификацию на уровне тройств на **модель подграфа**: одна запись отслеживания происхождения для каждого блока извлечения,
используемая для всех тройств, созданных из этого блока.

=======
В настоящее время механизм отслеживания происхождения, действующий во время извлечения, создает полную реификацию для каждого
извлеченного тройного набора: уникальный `stmt_uri`, `activity_uri` и связанные
метаданные PROV-O для каждого отдельного факта знаний. Обработка одного блока,
который дает 20 отношений, приводит к появлению примерно 220 тройных наборов отслеживания происхождения, помимо
примерно 20 тройных наборов знаний — это примерно 10:1 избыточности.

Это дорого (хранение, индексация, передача) и семантически
неточно. Каждый блок обрабатывается одним вызовом LLM, который создает
все свои тройные наборы за одну транзакцию. Текущая модель для каждого тройного набора
создает иллюзию 20 независимых событий извлечения.


Кроме того, два из четырех процессоров извлечения (kg-extract-ontology,
kg-extract-agent) вообще не имеют информации об отслеживании происхождения, что создает пробелы в
журнале аудита.

## Решение

Заменить реификацию для каждого тройного набора на **модель подграфа**: один
набор отслеживания происхождения для каждого извлеченного блока, который используется
для всех тройных наборов, созданных из этого блока.
>>>>>>> 82edf2d (New md files from RunPod)

### Изменение терминологии

| Старое | Новое |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1, идентичность) | `tg:contains` (1:много, содержательность) |

### Целевая структура

<<<<<<< HEAD
Все тройства отслеживания происхождения должны быть помещены в именованный граф `urn:graph:source`.
=======
Все тройные наборы отслеживания происхождения должны быть помещены в именованный граф `urn:graph:source`.
>>>>>>> 82edf2d (New md files from RunPod)

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### Сравнение объемов

Для блока, генерирующего N извлеченных троек:

| | Старый (на тройку) | Новый (подграф) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| Тройки активности | ~9 x N | ~9 |
| Тройки агентов | 2 x N | 2 |
| Метаданные утверждения/подграфа | 2 x N | 2 |
<<<<<<< HEAD
| **Всего троек происхождения** | **~13N** | **N + 13** |
=======
| **Общее количество троек происхождения** | **~13N** | **N + 13** |
>>>>>>> 82edf2d (New md files from RunPod)
| **Пример (N=20)** | **~260** | **33** |

## Область применения

<<<<<<< HEAD
### Модули для обновления (существующее происхождение, на тройку)
=======
### Процессоры для обновления (существующее происхождение, на тройку)
>>>>>>> 82edf2d (New md files from RunPod)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

В настоящее время вызывает `statement_uri()` + `triple_provenance_triples()` внутри
цикла для каждой сущности.

Изменения:
Переместить создание `subgraph_uri()` и `activity_uri()` перед циклом
Собирать тройки `tg:contains` внутри цикла
Выводить общий блок активности/агента/происхождения один раз после цикла

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

Та же схема, что и для сущностей. Те же изменения.

<<<<<<< HEAD
### Модули для добавления информации о происхождении (в настоящее время отсутствуют)
=======
### Процессоры для добавления происхождения (в настоящее время отсутствуют)
>>>>>>> 82edf2d (New md files from RunPod)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

<<<<<<< HEAD
В настоящее время генерируются тройки без указания источника. Добавить информацию об источнике подграфа,
используя ту же схему: один подграф для каждого фрагмента, `tg:contains` для каждой
извлеченной тройки.
=======
В настоящее время генерируются тройки данных без указания источника. Добавить информацию об источнике подграфа,
используя ту же схему: один подграф для каждого блока, `tg:contains` для каждой
извлеченной тройки данных.
>>>>>>> 82edf2d (New md files from RunPod)

**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

<<<<<<< HEAD
В настоящее время генерируются тройки без указания источника. Добавить информацию об источнике подграфа,
=======
В настоящее время генерируются тройки данных без указания источника. Добавить информацию об источнике подграфа,
>>>>>>> 82edf2d (New md files from RunPod)
используя ту же схему.

### Изменения в общей библиотеке отслеживания происхождения данных

**`trustgraph-base/trustgraph/provenance/triples.py`**

Заменить `triple_provenance_triples()` на `subgraph_provenance_triples()`
<<<<<<< HEAD
Новая функция принимает список извлеченных троек вместо одной
Генерирует один `tg:contains` для каждой тройки, общий блок активности/агента
=======
Новая функция принимает список извлеченных троек данных вместо одной
Генерирует один `tg:contains` для каждой тройки данных, общий блок активности/агента
>>>>>>> 82edf2d (New md files from RunPod)
Удалить старый `triple_provenance_triples()`

**`trustgraph-base/trustgraph/provenance/uris.py`**

Заменить `statement_uri()` на `subgraph_uri()`

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

Заменить `TG_REIFIES` на `TG_CONTAINS`

### Не входит в область действия

**kg-extract-topics**: устаревший процессор, в настоящее время не используется в
  стандартных процессах.
**kg-extract-rows**: генерирует строки, а не тройки, имеет другую модель
  происхождения.
**Происхождение во время запроса** (`urn:graph:retrieval`): отдельная задача,
  уже использует другую схему (вопрос/исследование/фокус/синтез).
**Происхождение документа/страницы/фрагмента** (декодер PDF, разбиение на фрагменты): уже использует
  `derived_entity_triples()`, который применяется к каждой сущности, а не к каждой тройке — нет
  проблемы избыточности.

## Замечания по реализации

### Реструктуризация цикла процессора

До (для каждой тройки, в отношениях):
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

После (подграфа):
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### Новая вспомогательная подпись

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### Существенное изменение

Это существенное изменение модели отслеживания происхождения. Отслеживание происхождения еще не было выпущено, поэтому миграция не требуется. Старый код ⟦CODE_0⟧ /
`tg:reifies` можно удалить безвозвратно.
Код `statement_uri` можно удалить полностью.
