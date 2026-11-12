"""
Ontology service. Manages ontology parsing, validation, embedding, and
subset selection. Accepts ontologies in JSON-LD format via config events,
and serves ontology context to consumers over pub/sub.
"""

import asyncio
import json
import logging
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import rdflib
from rdflib import RDF, RDFS, OWL, XSD

from .. schema import (
    OntologyRequest, OntologyResponse, OntologyInfo, Error,
)
from .. base import FlowProcessor, ConsumerSpec, ProducerSpec
from .. base import EmbeddingsClientSpec

from .. extract.kg.ontology.vector_store import InMemoryVectorStore

logger = logging.getLogger(__name__)

default_ident = "ontology"
default_concurrency = 10


@dataclass
class OntologyElement:
    element_id: str
    element_type: str  # "class", "objectProperty", "datatypeProperty"
    uri: str
    labels: list = field(default_factory=list)
    comment: str = ""
    subclass_of: str = ""
    domain: str = ""
    range: str = ""
    inverse_of: str = ""
    functional: bool = False

    def to_dict(self):
        return {
            "uri": self.uri,
            "labels": self.labels,
            "comment": self.comment,
            "subclass_of": self.subclass_of,
            "domain": self.domain,
            "range": self.range,
            "inverse_of": self.inverse_of,
            "functional": self.functional,
        }


@dataclass
class ParsedOntology:
    ontology_id: str
    namespace: str
    classes: Dict[str, OntologyElement] = field(default_factory=dict)
    object_properties: Dict[str, OntologyElement] = field(
        default_factory=dict
    )
    datatype_properties: Dict[str, OntologyElement] = field(
        default_factory=dict
    )

    @property
    def total_elements(self):
        return (
            len(self.classes)
            + len(self.object_properties)
            + len(self.datatype_properties)
        )


@dataclass
class OntologyState:
    ontology: ParsedOntology
    state: str = "loading"  # "loading", "ready", "error"
    elements_embedded: int = 0
    error_message: str = ""


class OntologyParser:

    @staticmethod
    def local_name(uri):
        s = str(uri)
        if "#" in s:
            return s.split("#")[-1]
        return s.rsplit("/", 1)[-1]

    @staticmethod
    def parse_jsonld(ontology_id: str, jsonld_str: str) -> ParsedOntology:
        g = rdflib.Graph()
        g.parse(data=jsonld_str, format="json-ld")

        namespace = ""
        for ns_prefix, ns_uri in g.namespaces():
            if ns_prefix == "" or ns_prefix == "base":
                namespace = str(ns_uri)
                break
        if not namespace:
            for s in g.subjects():
                namespace = str(s).rsplit("#", 1)[0] + "#"
                break

        ontology = ParsedOntology(
            ontology_id=ontology_id,
            namespace=namespace,
        )

        for s in g.subjects(RDF.type, OWL.Class):
            element_id = OntologyParser.local_name(s)
            labels = [
                {"value": str(o), "lang": o.language or "en"}
                for o in g.objects(s, RDFS.label)
            ]
            comment = str(next(g.objects(s, RDFS.comment), ""))
            subclass_of = ""
            for parent in g.objects(s, RDFS.subClassOf):
                if isinstance(parent, rdflib.URIRef):
                    subclass_of = OntologyParser.local_name(parent)
                    break

            ontology.classes[element_id] = OntologyElement(
                element_id=element_id,
                element_type="class",
                uri=str(s),
                labels=labels,
                comment=comment,
                subclass_of=subclass_of,
            )

        for s in g.subjects(RDF.type, OWL.ObjectProperty):
            element_id = OntologyParser.local_name(s)
            labels = [
                {"value": str(o), "lang": o.language or "en"}
                for o in g.objects(s, RDFS.label)
            ]
            comment = str(next(g.objects(s, RDFS.comment), ""))
            domain = ""
            for d in g.objects(s, RDFS.domain):
                if isinstance(d, rdflib.URIRef):
                    domain = OntologyParser.local_name(d)
                    break
            range_val = ""
            for r in g.objects(s, RDFS.range):
                if isinstance(r, rdflib.URIRef):
                    range_val = OntologyParser.local_name(r)
                    break
            inverse_of = ""
            for inv in g.objects(s, OWL.inverseOf):
                if isinstance(inv, rdflib.URIRef):
                    inverse_of = OntologyParser.local_name(inv)
                    break
            functional = (s, RDF.type, OWL.FunctionalProperty) in g

            ontology.object_properties[element_id] = OntologyElement(
                element_id=element_id,
                element_type="objectProperty",
                uri=str(s),
                labels=labels,
                comment=comment,
                domain=domain,
                range=range_val,
                inverse_of=inverse_of,
                functional=functional,
            )

        for s in g.subjects(RDF.type, OWL.DatatypeProperty):
            element_id = OntologyParser.local_name(s)
            labels = [
                {"value": str(o), "lang": o.language or "en"}
                for o in g.objects(s, RDFS.label)
            ]
            comment = str(next(g.objects(s, RDFS.comment), ""))
            domain = ""
            for d in g.objects(s, RDFS.domain):
                if isinstance(d, rdflib.URIRef):
                    domain = OntologyParser.local_name(d)
                    break
            range_val = ""
            for r in g.objects(s, RDFS.range):
                range_val = OntologyParser.local_name(r)
                break

            ontology.datatype_properties[element_id] = OntologyElement(
                element_id=element_id,
                element_type="datatypeProperty",
                uri=str(s),
                labels=labels,
                comment=comment,
                domain=domain,
                range=range_val,
            )

        return ontology


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
                schema=OntologyRequest,
                handler=self.on_message,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=OntologyResponse,
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name="embeddings-request",
                response_name="embeddings-response"
            )
        )

        self.register_config_handler(
            self.on_ontology_config, types=["ontology"]
        )

        self.top_k = params.get("top_k", 10)
        self.similarity_threshold = params.get(
            "similarity_threshold", 0.3
        )
        self.bypass_selector_below = params.get(
            "bypass_selector_below", 5
        )

        # Per-workspace state
        self.ontology_states: Dict[str, Dict[str, OntologyState]] = {}
        self.vector_stores: Dict[str, InMemoryVectorStore] = {}
        self.vector_dimensions: Dict[str, int] = {}

        # Loading readiness: event is set when loading is complete
        self.ready_events: Dict[str, asyncio.Event] = {}

    def _get_ready_event(self, workspace):
        if workspace not in self.ready_events:
            self.ready_events[workspace] = asyncio.Event()
        return self.ready_events[workspace]

    async def on_ontology_config(self, workspace, config, version):
        try:
            logger.info(
                f"Received ontology config update, "
                f"version={version} workspace={workspace}"
            )

            event = self._get_ready_event(workspace)
            event.clear()

            if "ontology" not in config:
                logger.warning(
                    f"No 'ontology' section in config for {workspace}"
                )
                event.set()
                return

            ontology_configs = config["ontology"]
            self.ontology_states[workspace] = {}

            for ont_id, ont_jsonld in ontology_configs.items():
                try:
                    parsed = OntologyParser.parse_jsonld(ont_id, ont_jsonld)
                    self.ontology_states[workspace][ont_id] = OntologyState(
                        ontology=parsed,
                        state="loading",
                    )
                    logger.info(
                        f"Parsed ontology '{ont_id}': "
                        f"{len(parsed.classes)} classes, "
                        f"{len(parsed.object_properties)} object properties, "
                        f"{len(parsed.datatype_properties)} datatype properties"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to parse ontology '{ont_id}': {e}",
                        exc_info=True
                    )
                    self.ontology_states[workspace][ont_id] = OntologyState(
                        ontology=ParsedOntology(
                            ontology_id=ont_id, namespace=""
                        ),
                        state="error",
                        error_message=str(e),
                    )

            # Embedding happens asynchronously so we don't block
            # the config handler
            asyncio.ensure_future(
                self._embed_workspace(workspace)
            )

        except Exception as e:
            logger.error(
                f"Failed to process ontology config: {e}",
                exc_info=True
            )
            self._get_ready_event(workspace).set()

    async def _embed_workspace(self, workspace):
        try:
            states = self.ontology_states.get(workspace, {})
            loadable = [
                s for s in states.values() if s.state == "loading"
            ]

            if not loadable:
                self._get_ready_event(workspace).set()
                return

            # Detect embedding dimension from first flow we can find
            dimension = self.vector_dimensions.get(workspace)
            if dimension is None:
                dimension = await self._detect_dimension(workspace)
                if dimension is None:
                    logger.error(
                        f"Cannot detect embedding dimension for {workspace}"
                    )
                    for s in loadable:
                        s.state = "error"
                        s.error_message = "Cannot detect embedding dimension"
                    self._get_ready_event(workspace).set()
                    return
                self.vector_dimensions[workspace] = dimension

            vector_store = InMemoryVectorStore(
                dimension=dimension, index_type='flat'
            )
            self.vector_stores[workspace] = vector_store

            for state in loadable:
                try:
                    count = await self._embed_ontology(
                        workspace, state, vector_store
                    )
                    state.state = "ready"
                    logger.info(
                        f"Ontology '{state.ontology.ontology_id}' ready, "
                        f"embedded {count} elements"
                    )
                except Exception as e:
                    state.state = "error"
                    state.error_message = str(e)
                    logger.error(
                        f"Failed to embed ontology "
                        f"'{state.ontology.ontology_id}': {e}",
                        exc_info=True
                    )

            self._get_ready_event(workspace).set()

        except Exception as e:
            logger.error(
                f"Workspace embedding failed: {e}", exc_info=True
            )
            self._get_ready_event(workspace).set()

    async def _detect_dimension(self, workspace):
        try:
            # We need a flow to call the embeddings service.
            # Use a placeholder — the embeddings client is registered
            # on the processor, not per-flow.
            # Try to embed a test string using any available flow.
            for flow in self._active_flows():
                embeddings_client = flow("embeddings-request")
                test_response = await embeddings_client.embed(["test"])
                return len(test_response[0])
        except Exception as e:
            logger.error(f"Dimension detection failed: {e}")
            return None

    def _active_flows(self):
        if hasattr(self, 'flows') and self.flows:
            return self.flows.values()
        return []

    async def _embed_ontology(self, workspace, state, vector_store):
        ontology = state.ontology
        batch_size = 50
        embedded = 0

        elements = []

        for cid, cls in ontology.classes.items():
            text = self._element_text(cid, cls)
            elements.append((
                f"{ontology.ontology_id}:class:{cid}",
                text,
                {
                    "type": "class",
                    "ontology": ontology.ontology_id,
                    "element": cid,
                    "definition": cls.to_dict(),
                }
            ))

        for pid, prop in ontology.object_properties.items():
            text = self._element_text(pid, prop)
            elements.append((
                f"{ontology.ontology_id}:objectProperty:{pid}",
                text,
                {
                    "type": "objectProperty",
                    "ontology": ontology.ontology_id,
                    "element": pid,
                    "definition": prop.to_dict(),
                }
            ))

        for pid, prop in ontology.datatype_properties.items():
            text = self._element_text(pid, prop)
            elements.append((
                f"{ontology.ontology_id}:datatypeProperty:{pid}",
                text,
                {
                    "type": "datatypeProperty",
                    "ontology": ontology.ontology_id,
                    "element": pid,
                    "definition": prop.to_dict(),
                }
            ))

        for i in range(0, len(elements), batch_size):
            batch = elements[i:i + batch_size]
            texts = [t for _, t, _ in batch]

            try:
                embeddings_response = None
                for flow in self._active_flows():
                    client = flow("embeddings-request")
                    embeddings_response = await client.embed(texts)
                    break

                if embeddings_response is None:
                    raise RuntimeError("No active flow for embeddings")

                vectors = np.array(embeddings_response)
                ids = [eid for eid, _, _ in batch]
                metadata = [m for _, _, m in batch]
                vector_store.add_batch(ids, vectors, metadata)
                embedded += len(batch)
                state.elements_embedded = embedded

            except Exception as e:
                logger.error(
                    f"Failed to embed batch for "
                    f"'{ontology.ontology_id}': {e}",
                    exc_info=True
                )

        return embedded

    @staticmethod
    def _element_text(element_id, element):
        parts = [element_id.replace('-', ' ').replace('_', ' ')]

        for label in element.labels:
            if isinstance(label, dict):
                parts.append(label.get('value', ''))
            else:
                parts.append(str(label))

        if element.comment:
            parts.append(element.comment)

        if element.element_type == 'class' and element.subclass_of:
            parts.append(f"subclass of {element.subclass_of}")
        elif element.element_type in ('objectProperty', 'datatypeProperty'):
            if element.domain:
                parts.append(f"domain: {element.domain}")
            if element.range:
                parts.append(f"range: {element.range}")

        return ' '.join(filter(None, parts))

    async def on_message(self, msg, consumer, flow):
        try:
            request = msg.value()
            id = msg.properties()["id"]

            if request.operation == "list":
                response = self._handle_list(flow)
            elif request.operation == "subset":
                response = await self._handle_subset(
                    flow, request
                )
            else:
                response = OntologyResponse(
                    error=Error(
                        type="invalid-operation",
                        message=f"Unknown operation: {request.operation}",
                    ),
                    operation=request.operation,
                )

            await flow("response").send(
                response, properties={"id": id}
            )

        except Exception as e:
            logger.error(
                f"Ontology service error: {e}", exc_info=True
            )

    def _handle_list(self, flow):
        workspace = flow.workspace
        states = self.ontology_states.get(workspace, {})

        ontologies = []
        for ont_id, state in states.items():
            ontologies.append(OntologyInfo(
                ontology_id=ont_id,
                state=state.state,
                classes_total=len(state.ontology.classes),
                properties_total=(
                    len(state.ontology.object_properties)
                    + len(state.ontology.datatype_properties)
                ),
                elements_embedded=state.elements_embedded,
                error_message=state.error_message,
            ))

        return OntologyResponse(
            operation="list",
            ontologies=ontologies,
        )

    async def _handle_subset(self, flow, request):
        workspace = flow.workspace

        # Block until ontologies are loaded
        event = self._get_ready_event(workspace)
        await event.wait()

        states = self.ontology_states.get(workspace, {})
        ready = {
            k: v for k, v in states.items() if v.state == "ready"
        }

        if not ready:
            return OntologyResponse(
                operation="subset",
                error=Error(
                    type="no-ontology",
                    message="No ontologies loaded for this workspace",
                ),
            )

        # Check if we should bypass the selector for small ontologies
        total_elements = sum(
            s.ontology.total_elements for s in ready.values()
        )

        if total_elements < self.bypass_selector_below:
            return self._full_subset_response(ready)

        # Vector similarity search
        vector_store = self.vector_stores.get(workspace)
        if vector_store is None or vector_store.size() == 0:
            return self._full_subset_response(ready)

        top_k = request.top_k or self.top_k
        threshold = request.similarity_threshold or self.similarity_threshold

        # Embed the query text
        embedding = None
        try:
            client = flow("embeddings-request")
            resp = await client.embed([request.text])
            embedding = np.array(resp[0])
        except Exception as e:
            logger.error(f"Failed to embed query text: {e}")

        if embedding is None:
            return OntologyResponse(
                operation="subset",
                error=Error(
                    type="embedding-failed",
                    message="Failed to embed query text",
                ),
            )

        results = vector_store.search(
            embedding=embedding, top_k=top_k, threshold=threshold,
        )

        if not results:
            return self._full_subset_response(ready)

        # Build subset from search results
        classes = {}
        object_properties = {}
        datatype_properties = {}
        ontology_id = ""
        namespace = ""

        for result in results:
            meta = result.metadata
            ont_id = meta["ontology"]
            elem_type = meta["type"]
            elem_id = meta["element"]
            definition = meta["definition"]

            if not ontology_id:
                ontology_id = ont_id
                state = ready.get(ont_id)
                if state:
                    namespace = state.ontology.namespace

            if elem_type == "class":
                classes[elem_id] = json.dumps(definition)
            elif elem_type == "objectProperty":
                object_properties[elem_id] = json.dumps(definition)
            elif elem_type == "datatypeProperty":
                datatype_properties[elem_id] = json.dumps(definition)

        # Resolve dependencies
        self._resolve_dependencies(
            ontology_id, classes, object_properties,
            datatype_properties, ready,
        )

        return OntologyResponse(
            operation="subset",
            ontology_id=ontology_id,
            classes=classes,
            object_properties=object_properties,
            datatype_properties=datatype_properties,
            namespace=namespace,
        )

    def _full_subset_response(self, ready_states):
        all_classes = {}
        all_obj_props = {}
        all_dt_props = {}
        ontology_id = ""
        namespace = ""

        for ont_id, state in ready_states.items():
            ont = state.ontology
            if not ontology_id:
                ontology_id = ont_id
                namespace = ont.namespace

            for cid, cls in ont.classes.items():
                all_classes[cid] = json.dumps(cls.to_dict())
            for pid, prop in ont.object_properties.items():
                all_obj_props[pid] = json.dumps(prop.to_dict())
            for pid, prop in ont.datatype_properties.items():
                all_dt_props[pid] = json.dumps(prop.to_dict())

        return OntologyResponse(
            operation="subset",
            ontology_id=ontology_id,
            classes=all_classes,
            object_properties=all_obj_props,
            datatype_properties=all_dt_props,
            namespace=namespace,
        )

    def _resolve_dependencies(
        self, ontology_id, classes, object_properties,
        datatype_properties, ready_states,
    ):
        state = ready_states.get(ontology_id)
        if not state:
            return

        ont = state.ontology
        classes_to_add = set()

        # Add parent classes
        for cid in list(classes.keys()):
            cls = ont.classes.get(cid)
            if cls and cls.subclass_of and cls.subclass_of not in classes:
                classes_to_add.add(cls.subclass_of)

        # Add domain/range classes for selected properties
        for pid in list(object_properties.keys()):
            prop = ont.object_properties.get(pid)
            if prop:
                if prop.domain and prop.domain not in classes:
                    classes_to_add.add(prop.domain)
                if prop.range and prop.range not in classes:
                    classes_to_add.add(prop.range)

        for pid in list(datatype_properties.keys()):
            prop = ont.datatype_properties.get(pid)
            if prop and prop.domain and prop.domain not in classes:
                classes_to_add.add(prop.domain)

        # Add inverse properties
        for pid in list(object_properties.keys()):
            prop = ont.object_properties.get(pid)
            if prop and prop.inverse_of:
                inv = ont.object_properties.get(prop.inverse_of)
                if inv and prop.inverse_of not in object_properties:
                    object_properties[prop.inverse_of] = json.dumps(
                        inv.to_dict()
                    )

        # Add properties related to selected classes
        for cid in list(classes.keys()):
            for pid, prop in ont.object_properties.items():
                if pid not in object_properties:
                    if prop.domain == cid or prop.range == cid:
                        object_properties[pid] = json.dumps(
                            prop.to_dict()
                        )
                        if prop.domain and prop.domain not in classes:
                            classes_to_add.add(prop.domain)
                        if prop.range and prop.range not in classes:
                            classes_to_add.add(prop.range)

            for pid, prop in ont.datatype_properties.items():
                if pid not in datatype_properties:
                    if prop.domain == cid:
                        datatype_properties[pid] = json.dumps(
                            prop.to_dict()
                        )

        for cid in classes_to_add:
            cls = ont.classes.get(cid)
            if cls:
                classes[cid] = json.dumps(cls.to_dict())

    @staticmethod
    def add_args(parser):
        parser.add_argument(
            '--top-k',
            type=int,
            default=10,
            help='Number of top ontology elements to retrieve (default: 10)'
        )
        parser.add_argument(
            '--similarity-threshold',
            type=float,
            default=0.3,
            help='Similarity threshold for matching (default: 0.3)'
        )
        parser.add_argument(
            '--bypass-selector-below',
            type=int,
            default=5,
            help='Bypass selector when total elements below this (default: 5)'
        )
        FlowProcessor.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
