"""
RDF namespace constants for provenance.

Includes PROV-O, Dublin Core, and TrustGraph namespace URIs.
"""

# PROV-O namespace (W3C Provenance Ontology)
PROV = "http://www.w3.org/ns/prov#"
PROV_ENTITY = PROV + "Entity"
PROV_ACTIVITY = PROV + "Activity"
PROV_AGENT = PROV + "Agent"
PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"
PROV_WAS_GENERATED_BY = PROV + "wasGeneratedBy"
PROV_USED = PROV + "used"
PROV_WAS_ASSOCIATED_WITH = PROV + "wasAssociatedWith"
PROV_STARTED_AT_TIME = PROV + "startedAtTime"

# Dublin Core namespace
DC = "http://purl.org/dc/elements/1.1/"
DC_TITLE = DC + "title"
DC_SOURCE = DC + "source"
DC_DATE = DC + "date"
DC_CREATOR = DC + "creator"

# RDF/RDFS namespace (also in rdf.py, but included here for completeness)
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDF_TYPE = RDF + "type"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
RDFS_LABEL = RDFS + "label"

# TrustGraph namespace for custom predicates
TG = "https://trustgraph.ai/ns/"
TG_REIFIES = TG + "reifies"
TG_PAGE_COUNT = TG + "pageCount"
TG_MIME_TYPE = TG + "mimeType"
TG_PAGE_NUMBER = TG + "pageNumber"
TG_CHUNK_INDEX = TG + "chunkIndex"
TG_CHAR_OFFSET = TG + "charOffset"
TG_CHAR_LENGTH = TG + "charLength"
TG_CHUNK_SIZE = TG + "chunkSize"
TG_CHUNK_OVERLAP = TG + "chunkOverlap"
TG_COMPONENT_VERSION = TG + "componentVersion"
TG_LLM_MODEL = TG + "llmModel"
TG_ONTOLOGY = TG + "ontology"
TG_EMBEDDING_MODEL = TG + "embeddingModel"
TG_SOURCE_TEXT = TG + "sourceText"
TG_SOURCE_CHAR_OFFSET = TG + "sourceCharOffset"
TG_SOURCE_CHAR_LENGTH = TG + "sourceCharLength"
