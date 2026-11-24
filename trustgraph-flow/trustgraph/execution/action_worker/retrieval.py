
import json
import logging

from trustgraph.schema import TraversalStep

from . common import (
    ActionHandler, HandlerError,
    term_to_str, schema_term_to_dict, term_dict_to_str,
)

logger = logging.getLogger(__name__)


class ConceptExtractionHandler(ActionHandler):

    inputs = {
        "query": {"artifact-type": "TextBlobArtifact"},
    }
    outputs = {
        "keywords": {"artifact-type": "KeywordsArtifact"},
    }

    async def execute(self, inputs, flow):

        query = inputs["query"]["text"]

        logger.info(f"Concept extraction: {query[:80]}...")

        concept_extraction = flow("concept-extraction-request")

        concepts = await concept_extraction.extract(
            query, timeout=300,
        )

        return {
            "keywords": {
                "keywords": concepts,
                "query": query,
            }
        }


class KnowledgeRetrievalHandler(ActionHandler):

    inputs = {
        "keywords": {
            "artifact-type": "KeywordsArtifact", "optional": True,
        },
        "concepts": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "entities": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "collection": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "entity-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "triple-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "max-path-length": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "edge-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "max-reranker-input": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "languages": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "graph": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "subgraph": {"artifact-type": "SubgraphArtifact"},
    }

    async def execute(self, inputs, flow):

        if "keywords" in inputs:
            concepts = inputs["keywords"].get("keywords", [])
        elif "concepts" in inputs:
            concepts = [
                c.strip()
                for c in inputs["concepts"]["text"].split(",")
                if c.strip()
            ]
        else:
            concepts = []

        if "entities" in inputs:
            entities = [
                e.strip()
                for e in inputs["entities"]["text"].split(",")
                if e.strip()
            ]
        else:
            entities = []

        if not concepts and not entities:
            raise HandlerError(
                "knowledge-retrieval requires at least one of: "
                "'keywords', 'concepts', or 'entities'"
            )

        def _int(name, default):
            if name in inputs:
                return int(inputs[name]["text"])
            return default

        def _text(name, default=""):
            if name in inputs:
                return inputs[name]["text"]
            return default

        def _list(name):
            if name in inputs:
                return [
                    v.strip()
                    for v in inputs[name]["text"].split(",")
                    if v.strip()
                ]
            return []

        collection = _text("collection", "default")
        entity_limit = _int("entity-limit", 50)
        triple_limit = _int("triple-limit", 30)
        max_path_length = _int("max-path-length", 2)
        edge_limit = _int("edge-limit", 25)
        max_reranker_input = _int("max-reranker-input", 350)
        languages = _list("languages")
        graph = _text("graph")

        logger.info(
            f"Knowledge retrieval: {len(concepts)} concepts, "
            f"{len(entities)} seed entities, "
            f"collection={collection}"
        )

        knowledge_retrieval = flow("knowledge-retrieval-request")

        response = await knowledge_retrieval.retrieve(
            concepts=concepts or None,
            entities=entities or None,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_path_length=max_path_length,
            edge_limit=edge_limit,
            max_reranker_input=max_reranker_input,
            languages=languages or None,
            graph=graph,
            timeout=300,
        )

        triples = [
            {
                "s": {"type": "iri", "iri": e.s},
                "p": {"type": "iri", "iri": e.p},
                "o": {"type": "iri", "iri": e.o},
                "s_label": e.s_label, "p_label": e.p_label,
                "o_label": e.o_label,
                "score": e.score, "concept": e.concept,
            }
            for e in response.edges
        ]

        return {
            "subgraph": {
                "triples": triples,
                "seed_entities": response.seed_entities,
            }
        }


class GraphRagQueryHandler(ActionHandler):

    inputs = {
        "query": {"artifact-type": "TextBlobArtifact"},
        "collection": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "entity-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "triple-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "max-subgraph-size": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "max-path-length": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "edge-score-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "edge-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "max-reranker-input": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "grounding-seeds": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "graph-seeds": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "languages": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "traversal-instructions": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "graph": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "response": {"artifact-type": "TextBlobArtifact"},
    }

    async def execute(self, inputs, flow):

        query = inputs["query"]["text"]

        def _int(name, default):
            if name in inputs:
                return int(inputs[name]["text"])
            return default

        def _text(name, default=""):
            if name in inputs:
                return inputs[name]["text"]
            return default

        def _list(name):
            if name in inputs:
                return [
                    v.strip()
                    for v in inputs[name]["text"].split(",")
                    if v.strip()
                ]
            return []

        collection = _text("collection", "default")
        entity_limit = _int("entity-limit", 0)
        triple_limit = _int("triple-limit", 0)
        max_subgraph_size = _int("max-subgraph-size", 0)
        max_path_length = _int("max-path-length", 0)
        edge_score_limit = _int("edge-score-limit", 0)
        edge_limit = _int("edge-limit", 0)
        max_reranker_input = _int("max-reranker-input", 0)
        grounding_seeds = _list("grounding-seeds")
        graph_seeds = _list("graph-seeds")
        languages = _list("languages")
        graph = _text("graph") or None

        traversal_instructions = None
        if "traversal-instructions" in inputs:
            raw = json.loads(inputs["traversal-instructions"]["text"])
            traversal_instructions = []
            for i, item in enumerate(raw):
                if not isinstance(item, dict):
                    raise HandlerError(
                        f"traversal-instructions[{i}] must be "
                        f"an object"
                    )
                traversal_instructions.append(TraversalStep(
                    types=item.get("types", []),
                    relationships=item.get("relationships", []),
                    graphs=item.get("graphs", []),
                ))

        logger.info(
            f"Graph RAG query: {query[:80]}... "
            f"collection={collection}"
        )

        graph_rag = flow("graph-rag-request")

        response = await graph_rag.rag(
            query=query,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length,
            edge_score_limit=edge_score_limit,
            edge_limit=edge_limit,
            max_reranker_input=max_reranker_input,
            grounding_seeds=grounding_seeds or None,
            graph_seeds=graph_seeds or None,
            languages=languages or None,
            traversal_instructions=traversal_instructions,
            graph=graph,
            timeout=300,
        )

        return {
            "response": {
                "text": response,
                "query": query,
            }
        }


class GraphEmbeddingsQueryHandler(ActionHandler):

    inputs = {
        "query": {"artifact-type": "TextBlobArtifact"},
        "limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "collection": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "rdf-type": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "attributes": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "entities": {"artifact-type": "EntityListArtifact"},
    }

    async def execute(self, inputs, flow):

        query = inputs["query"]["text"]
        limit = (
            int(inputs["limit"]["text"]) if "limit" in inputs else 20
        )
        collection = (
            inputs["collection"]["text"]
            if "collection" in inputs else "default"
        )
        rdf_type = (
            inputs["rdf-type"]["text"]
            if "rdf-type" in inputs else ""
        )
        attributes = None
        if "attributes" in inputs:
            attributes = json.loads(inputs["attributes"]["text"])

        logger.info(
            f"Graph embeddings query: {query[:80]}... "
            f"collection={collection}"
        )

        embeddings = flow("embeddings-request")
        vectors = await embeddings.embed([query], timeout=300)

        if not vectors:
            raise HandlerError("Embeddings service returned no vectors")

        graph_embeddings = flow("graph-embeddings-request")
        entities = await graph_embeddings.query(
            vector=vectors[0],
            limit=limit,
            collection=collection,
            rdf_type=rdf_type,
            attributes=attributes,
            timeout=300,
        )

        results = [
            {
                "entity": term_to_str(e.entity) if e.entity else "",
                "score": e.score,
                "rdf_type": e.rdf_type,
                "attributes": e.attributes,
            }
            for e in entities
        ]

        logger.info(
            f"Graph embeddings query: {len(results)} matches"
        )

        return {
            "entities": {
                "entities": results,
                "query": query,
            }
        }


class EntityTriplesQueryHandler(ActionHandler):

    inputs = {
        "entity-list": {
            "artifact-type": "EntityListArtifact", "optional": True,
        },
        "entity": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "entities": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "direction": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "collection": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "graph": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "subgraph": {"artifact-type": "SubgraphArtifact"},
    }

    async def execute(self, inputs, flow):

        entity_uris = []

        if "entity-list" in inputs:
            entity_uris = [
                e.get("entity", "")
                for e in inputs["entity-list"].get("entities", [])
                if e.get("entity")
            ]
        else:
            if "entity" in inputs:
                entity_uris.append(inputs["entity"]["text"].strip())
            if "entities" in inputs:
                entity_uris.extend(
                    e.strip()
                    for e in inputs["entities"]["text"].split(",")
                    if e.strip()
                )

        if not entity_uris:
            raise HandlerError(
                "entity-triples-query requires at least one of: "
                "'entity-list', 'entity', or 'entities'"
            )

        limit = (
            int(inputs["limit"]["text"]) if "limit" in inputs else 50
        )
        direction = (
            inputs["direction"]["text"]
            if "direction" in inputs else "both"
        )
        collection = (
            inputs["collection"]["text"]
            if "collection" in inputs else "default"
        )
        g = (
            inputs["graph"]["text"] if "graph" in inputs else None
        )

        logger.info(
            f"Entity triples query: {len(entity_uris)} entities, "
            f"limit={limit}, direction={direction}, "
            f"collection={collection}"
        )

        triples_client = flow("triples-request")
        seen = set()
        triples = []

        for entity_uri in entity_uris:
            if direction in ("outbound", "both"):
                results = await triples_client.query_terms(
                    s=entity_uri, limit=limit,
                    collection=collection, g=g,
                    timeout=300,
                )
                for t in results:
                    key = (term_to_str(t.s), term_to_str(t.p),
                           term_to_str(t.o))
                    if key not in seen:
                        seen.add(key)
                        triples.append({
                            "s": schema_term_to_dict(t.s),
                            "p": schema_term_to_dict(t.p),
                            "o": schema_term_to_dict(t.o),
                        })

            if direction in ("inbound", "both"):
                results = await triples_client.query_terms(
                    o=entity_uri, limit=limit,
                    collection=collection, g=g,
                    timeout=300,
                )
                for t in results:
                    key = (term_to_str(t.s), term_to_str(t.p),
                           term_to_str(t.o))
                    if key not in seen:
                        seen.add(key)
                        triples.append({
                            "s": schema_term_to_dict(t.s),
                            "p": schema_term_to_dict(t.p),
                            "o": schema_term_to_dict(t.o),
                        })

        logger.info(
            f"Entity triples query: {len(triples)} unique triples"
        )

        return {
            "subgraph": {
                "triples": triples,
                "seed_entities": entity_uris,
            }
        }


class DocumentRagQueryHandler(ActionHandler):

    inputs = {
        "query": {"artifact-type": "TextBlobArtifact"},
        "collection": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "doc-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "fetch-limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "response": {"artifact-type": "TextBlobArtifact"},
    }

    async def execute(self, inputs, flow):

        query = inputs["query"]["text"]
        collection = (
            inputs["collection"]["text"]
            if "collection" in inputs else "default"
        )
        doc_limit = (
            int(inputs["doc-limit"]["text"])
            if "doc-limit" in inputs else 0
        )
        fetch_limit = (
            int(inputs["fetch-limit"]["text"])
            if "fetch-limit" in inputs else 0
        )

        logger.info(
            f"Document RAG query: {query[:80]}... "
            f"collection={collection}"
        )

        doc_rag = flow("document-rag-request")

        response = await doc_rag.rag(
            query=query,
            collection=collection,
            doc_limit=doc_limit,
            fetch_limit=fetch_limit,
            timeout=300,
        )

        return {
            "response": {
                "text": response,
                "query": query,
            }
        }


class TriplesQueryHandler(ActionHandler):

    inputs = {
        "s": {"artifact-type": "TextBlobArtifact", "optional": True},
        "p": {"artifact-type": "TextBlobArtifact", "optional": True},
        "o": {"artifact-type": "TextBlobArtifact", "optional": True},
        "limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "collection": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "graph": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "languages": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "subgraph": {"artifact-type": "SubgraphArtifact"},
    }

    async def execute(self, inputs, flow):

        s = inputs["s"]["text"] if "s" in inputs else None
        p = inputs["p"]["text"] if "p" in inputs else None
        o = inputs["o"]["text"] if "o" in inputs else None

        if not s and not p and not o:
            raise HandlerError(
                "triples-query requires at least one of: "
                "'s', 'p', or 'o'"
            )

        limit = (
            int(inputs["limit"]["text"]) if "limit" in inputs else 50
        )
        collection = (
            inputs["collection"]["text"]
            if "collection" in inputs else "default"
        )
        g = inputs["graph"]["text"] if "graph" in inputs else None
        languages = []
        if "languages" in inputs:
            languages = [
                v.strip()
                for v in inputs["languages"]["text"].split(",")
                if v.strip()
            ]

        logger.info(
            f"Triples query: s={s}, p={p}, o={o}, "
            f"limit={limit}, collection={collection}"
        )

        triples_client = flow("triples-request")

        results = await triples_client.query_terms(
            s=s, p=p, o=o,
            limit=limit,
            collection=collection,
            g=g,
            timeout=300,
        )

        triples = []
        for t in results:
            if languages:
                o_term = t.o
                if o_term and o_term.type == 'l' and o_term.language:
                    if o_term.language not in languages:
                        continue

            triples.append({
                "s": schema_term_to_dict(t.s),
                "p": schema_term_to_dict(t.p),
                "o": schema_term_to_dict(t.o),
            })

        logger.info(
            f"Triples query: {len(triples)} triples"
            + (f" (filtered by languages: {languages})"
               if languages else "")
        )

        return {
            "subgraph": {
                "triples": triples,
            }
        }


class SparqlQueryHandler(ActionHandler):

    inputs = {
        "query": {"artifact-type": "TextBlobArtifact"},
        "variables": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "collection": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
        "limit": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "result": {
            "artifact-type": [
                "TextBlobArtifact",
                "SubgraphArtifact",
                "TabularArtifact",
            ],
        },
    }

    @staticmethod
    def _format_sparql_value(spec):
        if isinstance(spec, str):
            raise HandlerError(
                "SPARQL variable must be a typed object, "
                "not a bare string"
            )
        vtype = spec.get("type", "")
        value = spec.get("value", "")
        if vtype == "iri":
            escaped = value.replace("\\", "\\\\").replace(">", "\\>")
            return f"<{escaped}>"
        elif vtype == "literal":
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lang = spec.get("language", "")
            datatype = spec.get("datatype", "")
            if lang:
                return f'"{escaped}"@{lang}'
            elif datatype:
                dt_escaped = datatype.replace("\\", "\\\\").replace(
                    ">", "\\>",
                )
                return f'"{escaped}"^^<{dt_escaped}>'
            return f'"{escaped}"'
        else:
            raise HandlerError(
                f"SPARQL variable type must be 'iri' or 'literal', "
                f"got '{vtype}'"
            )

    @classmethod
    def _substitute_variables(cls, query, variables):
        for name, spec in variables.items():
            sparql_value = cls._format_sparql_value(spec)
            query = query.replace(f"${name}", sparql_value)
        return query

    async def execute(self, inputs, flow):

        query = inputs["query"]["text"]

        if "variables" in inputs:
            variables = json.loads(inputs["variables"]["text"])
            query = self._substitute_variables(query, variables)

        collection = (
            inputs["collection"]["text"]
            if "collection" in inputs else "default"
        )
        limit = (
            int(inputs["limit"]["text"])
            if "limit" in inputs else 10000
        )

        logger.info(
            f"SPARQL query: {query[:80]}... "
            f"collection={collection}, limit={limit}"
        )

        sparql = flow("sparql-request")
        response = await sparql.query(
            query=query,
            collection=collection,
            limit=limit,
            timeout=300,
        )

        if response.query_type == "ask":
            return {
                "result": {
                    "artifact-type": "TextBlobArtifact",
                    "artifact": {
                        "text": str(response.ask_result),
                    },
                }
            }

        if response.query_type in ("construct", "describe"):
            triples = [
                {
                    "s": schema_term_to_dict(t.s),
                    "p": schema_term_to_dict(t.p),
                    "o": schema_term_to_dict(t.o),
                }
                for t in response.triples
            ]
            return {
                "result": {
                    "artifact-type": "SubgraphArtifact",
                    "artifact": {"triples": triples},
                }
            }

        columns = [
            {"name": v, "type": "string"}
            for v in response.variables
        ]
        rows = []
        for binding in response.bindings:
            row = {}
            for var, val in zip(response.variables, binding.values):
                row[var] = term_to_str(val) if val else ""
            rows.append(row)

        logger.info(
            f"SPARQL query: {len(rows)} rows, "
            f"{len(columns)} columns"
        )

        return {
            "result": {
                "artifact-type": "TabularArtifact",
                "artifact": {
                    "columns": columns,
                    "rows": rows,
                },
            }
        }
