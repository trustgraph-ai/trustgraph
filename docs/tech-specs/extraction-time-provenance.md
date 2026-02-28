# Extraction-Time Provenance: Source Layer

## Status

Notes - Not yet started

## Overview

This document captures notes on extraction-time provenance for future specification work. Extraction-time provenance records the "source layer" - where data came from originally, how it was extracted and transformed.

This is separate from query-time provenance (see `query-time-provenance.md`) which records agent reasoning.

## Current State

Source metadata is already partially stored in the knowledge graph (~40% solved):
- Documents have source URLs, timestamps
- Some extraction metadata exists

## Scope

Extraction-time provenance should capture:

### Source Layer (Origin)
- URL / file path
- Retrieval timestamp
- Funding sources
- Authorship / authority
- Document metadata (title, date, version)

### Transformation Layer (Extraction)
- Extraction tool used (e.g., PDF parser, table extractor)
- Extraction method / version
- Confidence scores
- Raw-to-structured mapping
- Parent-child relationships (PDF → table → row → fact)

## Key Questions for Future Spec

1. What metadata is already captured today?
2. What gaps exist?
3. How to structure the extraction DAG?
4. How does query-time provenance link to extraction-time nodes?
5. Storage format - RDF triples? Separate schema?

## References

- Query-time provenance: `docs/tech-specs/query-time-provenance.md`
- PROV-O standard for provenance modeling
- Existing source metadata in knowledge graph (needs audit)
