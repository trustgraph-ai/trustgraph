"""
NL-to-SPARQL translation service. Takes a natural language question,
uses ontology context for schema awareness and typed graph embeddings
for entity resolution, then calls an LLM to generate SPARQL.
"""

import json
import logging

from ... schema import (
    QuestionToSparqlRequest, QuestionToSparqlResponse,
    ResolvedEntity, Error, IRI,
    OntologyRequest, OntologyResponse,
)
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import GraphEmbeddingsClientSpec, RequestResponseSpec

logger = logging.getLogger(__name__)

default_ident = "nl-sparql"
default_concurrency = 10


class Processor(FlowProcessor):

    def __init__(self, **params):
        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", default_concurrency)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "concurrency": concurrency,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=QuestionToSparqlRequest,
                handler=self.on_message,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=QuestionToSparqlResponse,
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name="embeddings-request",
                response_name="embeddings-response",
            )
        )

        self.register_specification(
            GraphEmbeddingsClientSpec(
                request_name="graph-embeddings-request",
                response_name="graph-embeddings-response",
            )
        )

        self.register_specification(
            RequestResponseSpec(
                request_name="ontology-request",
                response_name="ontology-response",
                request_schema=OntologyRequest,
                response_schema=OntologyResponse,
            )
        )

        self.entity_limit = params.get("entity_limit", 5)

    async def on_message(self, msg, consumer, flow):
        try:
            request = msg.value()
            id = msg.properties()["id"]

            response = await self._translate(flow, request)

            await flow("response").send(
                response, properties={"id": id}
            )

        except Exception as e:
            logger.error(
                f"NL-to-SPARQL service error: {e}", exc_info=True
            )

    async def _translate(self, flow, request):
        question = request.question
        collection = request.collection or "default"
        limit = request.limit or 10

        # Step 1: Get ontology context
        ontology = await self._get_ontology_subset(flow, question)
        if ontology is None:
            return QuestionToSparqlResponse(
                error=Error(
                    type="no-ontology",
                    message="No ontology available for this workspace",
                ),
            )

        # Step 2: Extract entity mentions from the question
        entities = await self._extract_entities(
            flow, question, ontology
        )
        logger.info(
            f"Extracted {len(entities)} entity mentions from question"
        )

        # Step 3: Resolve entities via typed graph embeddings
        resolved = await self._resolve_entities(
            flow, entities, collection, ontology
        )
        logger.info(
            f"Resolved {len(resolved)} entities to URIs"
        )

        # Step 4: Generate SPARQL
        sparql = await self._generate_sparql(
            flow, question, ontology, resolved, limit
        )

        return QuestionToSparqlResponse(
            sparql=sparql,
            resolved_entities=resolved,
        )

    async def _get_ontology_subset(self, flow, text):
        try:
            response = await flow("ontology-request").request(
                OntologyRequest(
                    operation="subset",
                    text=text,
                )
            )

            if response.error:
                logger.warning(
                    f"Ontology service error: {response.error.message}"
                )
                return None

            if not response.classes and not response.object_properties:
                logger.warning("Ontology service returned empty subset")
                return None

            return response

        except Exception as e:
            logger.error(f"Ontology request failed: {e}")
            return None

    async def _extract_entities(self, flow, question, ontology):
        """Use LLM to extract entity mentions and their expected types."""
        try:
            classes = self._ontology_classes_for_prompt(ontology)

            result = await flow("prompt-request").prompt(
                "sparql-extract-entities",
                variables={
                    "question": question,
                    "classes": classes,
                }
            )

            parsed = result.object
            if parsed is None:
                logger.warning(
                    "Entity extraction returned no structured data"
                )
                return []

            entities = parsed.get("entities", [])
            return [
                e for e in entities
                if isinstance(e, dict) and "mention" in e
            ]

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def _resolve_class_uri(self, ontology, class_id):
        """Look up full URI for a class ID from the ontology response."""
        class_json = ontology.classes.get(class_id)
        if class_json is None:
            return class_id

        defn = (
            json.loads(class_json)
            if isinstance(class_json, str)
            else class_json
        )
        return defn.get("uri", class_id)

    async def _resolve_entities(self, flow, entities, collection,
                                ontology):
        """Resolve entity mentions to knowledge graph URIs."""
        resolved = []

        embeddings_client = flow("embeddings-request")
        graph_client = flow("graph-embeddings-request")

        for entity in entities:
            mention = entity.get("mention", "")
            rdf_type = entity.get("type", "")

            if not mention:
                continue

            # Resolve class ID to full URI for graph embeddings filter
            rdf_type_uri = self._resolve_class_uri(
                ontology, rdf_type
            ) if rdf_type else ""

            try:
                vectors = await embeddings_client.embed([mention])
                if not vectors or not vectors[0]:
                    continue

                matches = await graph_client.query(
                    vector=vectors[0],
                    limit=self.entity_limit,
                    collection=collection,
                    rdf_type=rdf_type_uri,
                )

                if matches:
                    best = matches[0]
                    entity_uri = ""
                    if best.entity:
                        if best.entity.type == IRI:
                            entity_uri = best.entity.iri
                        else:
                            entity_uri = best.entity.value

                    if entity_uri:
                        resolved.append(ResolvedEntity(
                            mention=mention,
                            uri=entity_uri,
                            rdf_type=rdf_type,
                            score=best.score,
                        ))

            except Exception as e:
                logger.warning(
                    f"Failed to resolve entity '{mention}': {e}"
                )

        return resolved

    async def _generate_sparql(
        self, flow, question, ontology, resolved_entities, limit
    ):
        """Call LLM to generate SPARQL from ontology context and entities."""
        try:
            classes = self._ontology_classes_for_prompt(ontology)
            object_properties = self._ontology_obj_props_for_prompt(
                ontology
            )
            datatype_properties = self._ontology_dt_props_for_prompt(
                ontology
            )

            entities_for_prompt = [
                {
                    "mention": e.mention,
                    "uri": e.uri,
                    "type": e.rdf_type,
                }
                for e in resolved_entities
            ]

            result = await flow("prompt-request").prompt(
                "sparql-generate",
                variables={
                    "question": question,
                    "namespace": ontology.namespace,
                    "classes": classes,
                    "object_properties": object_properties,
                    "datatype_properties": datatype_properties,
                    "resolved_entities": entities_for_prompt,
                    "limit": limit,
                }
            )

            sparql = result.text.strip()

            # Strip markdown code fences if present
            if sparql.startswith("```"):
                lines = sparql.split("\n")
                lines = lines[1:]  # drop opening fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                sparql = "\n".join(lines).strip()

            return sparql

        except Exception as e:
            logger.error(f"SPARQL generation failed: {e}")
            return ""

    def _ontology_classes_for_prompt(self, ontology):
        """Convert ontology classes to structured list for prompt."""
        result = []
        for class_id, class_json in ontology.classes.items():
            defn = (
                json.loads(class_json)
                if isinstance(class_json, str)
                else class_json
            )
            entry = {"id": class_id, "uri": defn.get("uri", "")}
            if defn.get("comment"):
                entry["description"] = defn["comment"]
            if defn.get("subclass_of"):
                entry["subclass_of"] = defn["subclass_of"]
            result.append(entry)
        return result

    def _ontology_obj_props_for_prompt(self, ontology):
        """Convert object properties to structured list for prompt."""
        result = []
        for prop_id, prop_json in ontology.object_properties.items():
            defn = (
                json.loads(prop_json)
                if isinstance(prop_json, str)
                else prop_json
            )
            entry = {"id": prop_id, "uri": defn.get("uri", "")}
            if defn.get("comment"):
                entry["description"] = defn["comment"]
            if defn.get("domain"):
                entry["domain"] = defn["domain"]
            if defn.get("range"):
                entry["range"] = defn["range"]
            result.append(entry)
        return result

    def _ontology_dt_props_for_prompt(self, ontology):
        """Convert datatype properties to structured list for prompt."""
        result = []
        for prop_id, prop_json in ontology.datatype_properties.items():
            defn = (
                json.loads(prop_json)
                if isinstance(prop_json, str)
                else prop_json
            )
            entry = {"id": prop_id, "uri": defn.get("uri", "")}
            if defn.get("comment"):
                entry["description"] = defn["comment"]
            if defn.get("domain"):
                entry["domain"] = defn["domain"]
            if defn.get("range"):
                entry["range"] = defn["range"]
            result.append(entry)
        return result

    @staticmethod
    def add_args(parser):
        parser.add_argument(
            '--entity-limit',
            type=int,
            default=5,
            help='Max graph embedding matches per entity (default: 5)'
        )
        FlowProcessor.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
