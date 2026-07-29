from prometheus_client import Counter, Histogram
from trustgraph.base.metrics import BUCKETS_LLM

extraction_duration_metric = Histogram(
    'tg_extraction_duration_seconds',
    'Wall-clock time per chunk extraction',
    ["processor", "extractor"],
    buckets=BUCKETS_LLM,
)

extraction_triple_metric = Counter(
    'tg_extraction_triple_total',
    'Triples produced per extractor',
    ["processor", "extractor"],
)

extraction_entity_metric = Counter(
    'tg_extraction_entity_total',
    'Entities extracted',
    ["processor", "extractor"],
)

extraction_empty_metric = Counter(
    'tg_extraction_empty_total',
    'Chunks that yielded zero extractions',
    ["processor", "extractor"],
)
