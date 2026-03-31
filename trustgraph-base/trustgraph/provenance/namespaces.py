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

# Schema.org namespace
SCHEMA = "https://schema.org/"
SCHEMA_DIGITAL_DOCUMENT = SCHEMA + "DigitalDocument"
SCHEMA_DESCRIPTION = SCHEMA + "description"
SCHEMA_KEYWORDS = SCHEMA + "keywords"
SCHEMA_NAME = SCHEMA + "name"

# SKOS namespace
SKOS = "http://www.w3.org/2004/02/skos/core#"
SKOS_DEFINITION = SKOS + "definition"

# TrustGraph namespace for custom predicates
TG = "https://trustgraph.ai/ns/"
TG_CONTAINS = TG + "contains"
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

# Query-time provenance predicates (GraphRAG)
TG_QUERY = TG + "query"
TG_CONCEPT = TG + "concept"
TG_ENTITY = TG + "entity"
TG_EDGE_COUNT = TG + "edgeCount"
TG_SELECTED_EDGE = TG + "selectedEdge"
TG_EDGE = TG + "edge"
TG_REASONING = TG + "reasoning"
TG_DOCUMENT = TG + "document"  # Reference to document in librarian

# Query-time provenance predicates (DocumentRAG)
TG_CHUNK_COUNT = TG + "chunkCount"
TG_SELECTED_CHUNK = TG + "selectedChunk"

# Extraction provenance entity types
TG_DOCUMENT_TYPE = TG + "Document"
TG_PAGE_TYPE = TG + "Page"
TG_SECTION_TYPE = TG + "Section"
TG_CHUNK_TYPE = TG + "Chunk"
TG_IMAGE_TYPE = TG + "Image"
TG_SUBGRAPH_TYPE = TG + "Subgraph"

# Universal decoder metadata predicates
TG_ELEMENT_TYPES = TG + "elementTypes"
TG_TABLE_COUNT = TG + "tableCount"
TG_IMAGE_COUNT = TG + "imageCount"

# Explainability entity types (shared)
TG_QUESTION = TG + "Question"
TG_GROUNDING = TG + "Grounding"
TG_EXPLORATION = TG + "Exploration"
TG_FOCUS = TG + "Focus"
TG_SYNTHESIS = TG + "Synthesis"
TG_ANALYSIS = TG + "Analysis"
TG_CONCLUSION = TG + "Conclusion"

# Orchestrator entity types
TG_DECOMPOSITION = TG + "Decomposition"  # Supervisor decomposed into sub-goals
TG_FINDING = TG + "Finding"              # Subagent result
TG_PLAN_TYPE = TG + "Plan"               # Plan-then-execute plan
TG_STEP_RESULT = TG + "StepResult"       # Plan step result

# Unifying types for answer and intermediate commentary
TG_ANSWER_TYPE = TG + "Answer"          # Final answer (Synthesis, Conclusion, Finding, StepResult)
TG_REFLECTION_TYPE = TG + "Reflection"  # Intermediate commentary (Thought, Observation)
TG_THOUGHT_TYPE = TG + "Thought"        # Agent reasoning
TG_OBSERVATION_TYPE = TG + "Observation" # Agent tool result

# Question subtypes (to distinguish retrieval mechanism)
TG_GRAPH_RAG_QUESTION = TG + "GraphRagQuestion"
TG_DOC_RAG_QUESTION = TG + "DocRagQuestion"
TG_AGENT_QUESTION = TG + "AgentQuestion"

# Agent provenance predicates
TG_THOUGHT = TG + "thought"        # Links iteration to thought sub-entity
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation" # Links iteration to observation sub-entity
TG_SUBAGENT_GOAL = TG + "subagentGoal"  # Goal string on Decomposition/Finding
TG_PLAN_STEP = TG + "planStep"          # Step goal string on Plan/StepResult

# Named graph URIs for RDF datasets
# These separate different types of data while keeping them in the same collection
GRAPH_DEFAULT = ""                       # Core knowledge facts (triples extracted from documents)
GRAPH_SOURCE = "urn:graph:source"        # Extraction provenance (which document/chunk a triple came from)
GRAPH_RETRIEVAL = "urn:graph:retrieval"  # Query-time explainability (question, exploration, focus, synthesis)
