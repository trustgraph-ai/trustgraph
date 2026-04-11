---
layout: default
title: "Mbinu ya Uandikaji (Logging) ya TrustGraph"
parent: "Swahili (Beta)"
---

# Mbinu ya Uandikaji (Logging) ya TrustGraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

TrustGraph hutumia moduli iliyojumuishwa ya Python `logging` kwa operesheni zote za uandikaji, pamoja na usanidi uliokatikati na ujumuishaji wa Loki wa hiari kwa ukusanyaji wa matangazo. Hii hutoa mbinu iliyoendeshwa na kikao, inayobadilika kwa uandikaji katika vipengele vyote vya mfumo.

## Mpangilio Chaguwa

### Kigezo cha Uandikaji
**Kigezo Chaguwa**: `INFO`
**Inayoweza kusanidiwa kupitia**: hoja ya mstari wa amri `--log-level`
**Chaguo**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Vituo vya Matokeo
1. **Kikonsoli (stdout)**: Daima inaanzishwa - huhakikisha utangamano na mazingira yaliyofungwa.
2. **Loki**: Ukusanyaji wa matangazo uliokatikati wa hiari (inaanzishwa kwa chaguwa, inaweza kuzimwa).

## Moduli ya Uandikaji Iliyokatikati

Mpangilio wote wa uandikaji unadhibitiwa na moduli `trustgraph.base.logging`, ambayo hutoa:
`add_logging_args(parser)` - Inaongeza hoja za kawaida za CLI za uandikaji.
`setup_logging(args)` - Inasanidi uandikaji kutoka kwa hoja zilizochanganuliwa.

Moduli hii inatumika na vipengele vyote vya upande wa seva:
Huduma zinazotegemea AsyncProcessor
API Gateway
MCP Server

## Miongozo ya Utendaji

### 1. Uanzishaji wa Kichunguzi

Kila moduli inapaswa kuunda kichunguzi chake mwenyewe kwa kutumia moduli ya `__name__`:

```python
import logging

logger = logging.getLogger(__name__)
```

Jina la kichujio hutumika kiotomatiki kama lebo katika Loki kwa ajili ya kuchujua na kutafuta.

### 2. Uanzishaji wa Huduma

Huduma zote za upande wa seva hupokea kiotomatiki usanidi wa uandishi wa matukio kupitia moduli ya kituo:

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # Add standard logging arguments (includes Loki configuration)
    add_logging_args(parser)

    # Add your service-specific arguments
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # Setup logging early in startup
    setup_logging(args)

    # Rest of your service initialization
    logger = logging.getLogger(__name__)
    logger.info("Service starting...")
```

### 3. Vigezo vya Kamba ya Amri

Huduma zote zinaunga mkono vigezo hivi vya uandishi wa matukio:

**Kiwango cha Uandishi:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**Mipangilio ya Loki:**
```bash
--loki-enabled              # Enable Loki (default)
--no-loki-enabled           # Disable Loki
--loki-url URL              # Loki push URL (default: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # Optional authentication
--loki-password PASSWORD    # Optional authentication
```

**Mfano:**
```bash
# Default - INFO level, Loki enabled
./my-service

# Debug mode, console only
./my-service --log-level DEBUG --no-loki-enabled

# Custom Loki server with auth
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. Vigezo vya Mazingira

Usanidi wa Loki unaounga mkono utumizi wa vigezo vya mazingira kama chaguo-mbadala:

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

Vigezo vya mstari wa amana hupendelewa kuliko vigezo vya mazingira.

### 5. Mbinu Bora za Uandishi wa Matukio

#### Matumizi ya Viwango vya Matukio
**DEBUG**: Habari za kina kwa ajili ya utambuzi wa matatizo (maelezo ya vigezo, kuingia/kuacha kazi)
**INFO**: Jumbe za habari za jumla (huduma ilianza, usanidi ulipakuliwa, hatua muhimu za usindikaji)
**WARNING**: Jumbe za onyo kwa hali ambazo zinaweza kuwa hatari (vipengele vilivyomalizwa, makosa yanayoweza kutatuliwa)
**ERROR**: Jumbe za makosa kwa matatizo makubwa (operesheni zilizoendea, ukiukaji)
**CRITICAL**: Jumbe muhimu kwa ajili ya hitilafu za mfumo zinazohitaji uangalifu wa haraka

#### Muundo wa Jumbe
```python
# Good - includes context
logger.info(f"Processing document: {doc_id}, size: {doc_size} bytes")
logger.error(f"Failed to connect to database: {error}", exc_info=True)

# Avoid - lacks context
logger.info("Processing document")
logger.error("Connection failed")
```

#### Mawazo ya Utendaji
```python
# Use lazy formatting for expensive operations
logger.debug("Expensive operation result: %s", expensive_function())

# Check log level for very expensive debug operations
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"Debug data: {debug_data}")
```

### 6. Uandikaji Maelezo Ulio Pamoja na Muundo Ukitumia Loki

Kwa data ngumu, tumia uandikaji maelezo uliopangwa na lebo za ziada kwa ajili ya Loki:

```python
logger.info("Request processed", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'success'
    }
})
```

Alama hizi zinakuwa lebo zinazoweza kutafutwa katika Loki, pamoja na lebo za kiotomatiki:
`severity` - Kiwango cha matukio (DEBUG, INFO, WARNING, ERROR, CRITICAL)
`logger` - Jina la moduli (kutoka `__name__`)

### 7. Uandikaji wa Matukio ya Aina ya Makosa

Daima jumuisha maandishi ya mfuatano wa mazingira kwa matukio ya aina ya makosa:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"Failed to process data: {e}", exc_info=True)
    raise
```

### 8. Mambo ya Kuzingatia Kuhusu Uandikaji wa Matukio (Logging) ya Aina ya Async

Mfumo wa uandikaji wa matukio hutumia vichuja (handlers) visivyozuia (non-blocking) vilivyopangwa kwa Loki:
Matokeo ya konseli ni ya aina moja kwa moja (haraka)
Matokeo ya Loki yanapangwa na buffer ya ujumbe 500
Mfumo wa nyuma hushughulikia usambazaji wa Loki
Hakuna kuzuiliwa kwa msimbo mkuu wa programu

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    # Logging is thread-safe and won't block async operations
    logger.info(f"Starting async operation in task: {asyncio.current_task().get_name()}")
```

## Uunganisho wa Loki

### Muundo

Mfumo wa uandikaji matumizi hutumia `QueueHandler` na `QueueListener` zilizojumuishwa katika Python kwa uunganisho wa Loki usiozuia:

1. **QueueHandler**: Matukio yanawekwa kwenye folyo ya ujumbe 500 (hayazuilii)
2. **Mfululizo wa Nyuma**: QueueListener hutuma matukio kwa Loki kwa njia isiyo ya moja kwa moja
3. **Upunguzaji wa Kawaida**: Ikiwa Loki haipatikani, uandikaji matukio kwenye konsi unaendelea

### Laha za Otomatiki

Kila tukio linalotumwa kwa Loki linajumuisha:
`processor`: Kitambulisho cha kichakata (k.m., `config-svc`, `text-completion`, `embeddings`)
`severity`: Kiwango cha matukio (DEBUG, INFO, n.k.)
`logger`: Jina la moduli (k.m., `trustgraph.gateway.service`, `trustgraph.agent.react.service`)

### Laha za Msingi

Ongeza laha za msingi kupitia parameter ya `extra`:

```python
logger.info("User action", extra={
    'tags': {
        'user_id': user_id,
        'action': 'document_upload',
        'collection': collection_name
    }
})
```

### Kuuliza Kumbukumbu katika Loki

```logql
# All logs from a specific processor (recommended - matches Prometheus metrics)
{processor="config-svc"}
{processor="text-completion"}
{processor="embeddings"}

# Error logs from a specific processor
{processor="config-svc", severity="ERROR"}

# Error logs from all processors
{severity="ERROR"}

# Logs from a specific processor with text filter
{processor="text-completion"} |= "Processing"

# All logs from API gateway
{processor="api-gateway"}

# Logs from processors matching pattern
{processor=~".*-completion"}

# Logs with custom tags
{processor="api-gateway"} | json | user_id="12345"
```

### Upunguzaji wa Athari (Graceful Degradation)

Ikiwa Loki haipatikani au `python-logging-loki` haijafunguliwa:
Ujumbe wa onyo huonyeshwa kwenye konsoli
Uandikaji kwenye konsoli unaendelea kama kawaida
Programu inaendelea kuendeshwa
Hakuna mfumo wa kujaribu tena muunganisho wa Loki (fainda haraka, punguza athari)

## Majaribio

Wakati wa majaribio, fikiria kutumia usanidi tofauti wa uandikaji:

```python
# In test setup
import logging

# Reduce noise during tests
logging.getLogger().setLevel(logging.WARNING)

# Or disable Loki for tests
setup_logging({'log_level': 'WARNING', 'loki_enabled': False})
```

## Ufuatiliaji wa Uunganishaji

### Muundo wa Kawaida
Matumizi yote ya rekodi hutumia muundo unaofuata sheria:
```
2025-01-09 10:30:45,123 - trustgraph.gateway.service - INFO - Request processed
```

Vipengele vya muundo:
Wakati (muundo wa ISO na milisekundi)
Jina la kisajili (njia ya moduli)
Kiwango cha kisajili
Ujumbe

### Maswali ya Loki kwa Ufuatiliaji

Maswali ya kawaida ya ufuatiliaji:

```logql
# Error rate by processor
rate({severity="ERROR"}[5m]) by (processor)

# Top error-producing processors
topk(5, count_over_time({severity="ERROR"}[1h]) by (processor))

# Recent errors with processor name
{severity="ERROR"} | line_format "{{.processor}}: {{.message}}"

# All agent processors
{processor=~".*agent.*"} |= "exception"

# Specific processor error count
count_over_time({processor="config-svc", severity="ERROR"}[1h])
```

## Mambo ya Kuzingatia Kuhusu Usalama

**Usisahirishe kamwe taarifa nyeti** (manenosi, funguo za API, data ya kibinafsi, alama)
**Safisha pembejeo za mtumiaji** kabla ya kuzisajili
**Tumia nafasi za kubadilika** kwa sehemu nyeti: `user_id=****1234`
**Uthibitishaji wa Loki**: Tumia `--loki-username` na `--loki-password` kwa matumizi salama
**Usafiri salama**: Tumia HTTPS kwa URL ya Loki katika mazingira ya uzalishaji: `https://loki.prod:3100/loki/api/v1/push`

## Utegemezi

Moduli ya uandikaji matukio ya kituo inahitaji:
`python-logging-loki` - Kwa ujumuishaji wa Loki (hiari, utendaji wa chini ikiwa haipo)

Tayari imejumuishwa katika `trustgraph-base/pyproject.toml` na `requirements.txt`.

## Njia ya Uhamishaji

Kwa programu zilizopo:

1. **Huduma ambazo tayari zinatumia AsyncProcessor**: Hakuna mabadiliko yanayohitajika, usaidizi wa Loki ni moja kwa moja
2. **Huduma ambazo hazitumii AsyncProcessor** (api-gateway, mcp-server): Tayari zimefanyiwa mabadiliko
3. **Zana za CLI**: Hayajajumuishwa - endelea kutumia print() au uandikaji matukio rahisi

### Kutoka print() hadi uandikaji matukio:
```python
# Before
print(f"Processing document {doc_id}")

# After
logger = logging.getLogger(__name__)
logger.info(f"Processing document {doc_id}")
```

## Muhtasari wa Usanidi

| Jina la hoja | Chaguizi | Kigezo cha mazingira | Maelezo |
|----------|---------|---------------------|-------------|
| `--log-level` | `INFO` | - | Kigezo cha uingishaji wa Loki na kituo cha uendeshaji |
| `--loki-enabled` | `True` | - | Wezesha uingishaji wa Loki |
| `--loki-url` | `http://loki:3100/loki/api/v1/push` | `LOKI_URL` | Kifaa cha utumaji cha Loki |
| `--loki-username` | `None` | `LOKI_USERNAME` | Jina la mtumiaji la uthibitishaji wa Loki |
| `--loki-password` | `None` | `LOKI_PASSWORD` | Nenosiri la uthibitishaji wa Loki |
