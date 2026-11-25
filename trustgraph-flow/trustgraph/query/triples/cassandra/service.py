
"""
Triples query service.  Input is a (s, p, o, g) quad pattern, some values may be
null.  Output is a list of quads.
"""

import asyncio
import logging
import json

from .... direct.cassandra_kg import (
    EntityCentricKnowledgeGraph, DEFAULT_GRAPH
)
from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import VersionEntry
from .... schema import Term, Triple, IRI, LITERAL, TRIPLE, BLANK
from .... base import TriplesQueryService
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-query"


def serialize_triple(triple):
    """Serialize a Triple object to JSON for querying (must match storage format)."""
    if triple is None:
        return None

    def term_to_dict(term):
        if term is None:
            return None
        result = {"type": term.type}
        if term.type == IRI:
            result["iri"] = term.iri
        elif term.type == LITERAL:
            result["value"] = term.value
            if term.datatype:
                result["datatype"] = term.datatype
            if term.language:
                result["language"] = term.language
        elif term.type == BLANK:
            result["id"] = term.id
        elif term.type == TRIPLE:
            result["triple"] = serialize_triple(term.triple)
        return result

    return json.dumps({
        "s": term_to_dict(triple.s),
        "p": term_to_dict(triple.p),
        "o": term_to_dict(triple.o),
    })


def get_term_value(term):
    """Extract the string value from a Term"""
    if term is None:
        return None
    if term.type == IRI:
        return term.iri
    elif term.type == LITERAL:
        return term.value
    elif term.type == TRIPLE:
        # Serialize nested triple to JSON (must match storage format)
        return serialize_triple(term.triple)
    else:
        # For blank nodes or other types, use id or value
        return term.id or term.value


def get_term_otype(term):
    """Map Term.type to storage otype code."""
    if term is None:
        return "u"
    if term.type == IRI or term.type == BLANK:
        return "u"
    elif term.type == LITERAL:
        return "l"
    elif term.type == TRIPLE:
        return "t"
    return "u"


def get_term_dtype(term):
    """Extract datatype from a Term (for literals)."""
    if term is None:
        return ""
    if term.type == LITERAL:
        return term.datatype or ""
    return ""


def get_term_lang(term):
    """Extract language tag from a Term (for literals)."""
    if term is None:
        return ""
    if term.type == LITERAL:
        return term.language or ""
    return ""


def deserialize_term(term_dict):
    """Deserialize a term from JSON structure."""
    if term_dict is None:
        return None
    term_type = term_dict.get("type", "")
    if term_type == IRI:
        return Term(type=IRI, iri=term_dict.get("iri", ""))
    elif term_type == LITERAL:
        return Term(
            type=LITERAL,
            value=term_dict.get("value", ""),
            datatype=term_dict.get("datatype", ""),
            language=term_dict.get("language", "")
        )
    elif term_type == TRIPLE:
        # Recursive for nested triples
        nested = term_dict.get("triple")
        if nested:
            return Term(
                type=TRIPLE,
                triple=Triple(
                    s=deserialize_term(nested.get("s")),
                    p=deserialize_term(nested.get("p")),
                    o=deserialize_term(nested.get("o")),
                )
            )
    # Fallback
    return Term(type=LITERAL, value=str(term_dict))


def create_term(value, term_type, datatype=None, language=None):
    """
    Create a Term from a string value and its storage type code.

    Args:
        value: The string value
        term_type: 'u' (IRI), 'l' (literal), 't' (triple) — required
        datatype: XSD datatype for literals
        language: Language tag for literals
    """
    if term_type == 'u':
        return Term(type=IRI, iri=value)
    elif term_type == 'l':
        return Term(
            type=LITERAL,
            value=value,
            datatype=datatype or "",
            language=language or ""
        )
    elif term_type == 't':
        # Triple/reification - parse JSON and create nested Triple
        try:
            triple_data = json.loads(value) if isinstance(value, str) else value
            if isinstance(triple_data, dict):
                return Term(
                    type=TRIPLE,
                    triple=Triple(
                        s=deserialize_term(triple_data.get("s")),
                        p=deserialize_term(triple_data.get("p")),
                        o=deserialize_term(triple_data.get("o")),
                    )
                )
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse triple JSON: {e}")
        # Fallback if parsing fails
        return Term(type=LITERAL, value=str(value))
    raise ValueError(f"term_type is required, got {term_type!r}")


class Processor(TriplesQueryService):

    async def _resolve_version(self, tg, collection, named_graph, version_str):
        if not version_str:
            return None

        if named_graph is None:
            raise ValueError(
                "Version filtering requires a specific graph — "
                "versions are per-graph and have no cross-graph meaning"
            )

        try:
            return int(version_str)
        except (ValueError, TypeError):
            pass

        log = await tg.async_get_version_log(collection, named_graph)
        for entry in log:
            if entry["names"] and version_str in entry["names"]:
                return entry["version"]

        raise ValueError(
            f"Unknown version name '{version_str}' "
            f"for graph {named_graph}"
        )

    def __init__(self, **params):

        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace, _ = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password
        )

        super(Processor, self).__init__(
            **params | {
                "cassandra_host": ','.join(hosts),
                "cassandra_username": username,
            }
        )

        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password

        self._connections = {}
        self._conn_lock = asyncio.Lock()

    async def _get_connection(self, workspace):
        async with self._conn_lock:
            if workspace not in self._connections:
                if self.cassandra_username and self.cassandra_password:
                    tg = await asyncio.to_thread(
                        EntityCentricKnowledgeGraph,
                        hosts=self.cassandra_host,
                        keyspace=workspace,
                        username=self.cassandra_username,
                        password=self.cassandra_password,
                    )
                else:
                    tg = await asyncio.to_thread(
                        EntityCentricKnowledgeGraph,
                        hosts=self.cassandra_host,
                        keyspace=workspace,
                    )
                self._connections[workspace] = tg
            return self._connections[workspace]

    async def query_triples(self, workspace, query):

        try:

            s_val = get_term_value(query.s)
            p_val = get_term_value(query.p)
            o_val = get_term_value(query.o)
            g_val = query.g

            tg = await self._get_connection(workspace)

            v = await self._resolve_version(
                tg, query.collection, g_val, query.version
            )

            def get_object_metadata(row):
                return (
                    getattr(row, 'otype', None),
                    getattr(row, 'dtype', None),
                    getattr(row, 'lang', None),
                )

            quads = []

            if s_val is not None:
                if p_val is not None:
                    if o_val is not None:
                        resp = await tg.async_get_spo(
                            query.collection, s_val, p_val, o_val,
                            g=g_val, version=v, limit=query.limit,
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((s_val, p_val, o_val, g, term_type, datatype, language))
                    else:
                        resp = await tg.async_get_sp(
                            query.collection, s_val, p_val,
                            g=g_val, version=v, limit=query.limit,
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((s_val, p_val, t.o, g, term_type, datatype, language))
                else:
                    if o_val is not None:
                        resp = await tg.async_get_os(
                            query.collection, o_val, s_val,
                            g=g_val, version=v, limit=query.limit,
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((s_val, t.p, o_val, g, term_type, datatype, language))
                    else:
                        resp = await tg.async_get_s(
                            query.collection, s_val,
                            g=g_val, version=v, limit=query.limit,
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((s_val, t.p, t.o, g, term_type, datatype, language))
            else:
                if p_val is not None:
                    if o_val is not None:
                        resp = await tg.async_get_po(
                            query.collection, p_val, o_val,
                            g=g_val, version=v, limit=query.limit,
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((t.s, p_val, o_val, g, term_type, datatype, language))
                    else:
                        resp = await tg.async_get_p(
                            query.collection, p_val,
                            g=g_val, version=v, limit=query.limit,
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((t.s, p_val, t.o, g, term_type, datatype, language))
                else:
                    if o_val is not None:
                        resp = await tg.async_get_o(
                            query.collection, o_val,
                            g=g_val, version=v, limit=query.limit,
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((t.s, t.p, o_val, g, term_type, datatype, language))
                    else:
                        resp = await tg.async_get_all(
                            query.collection,
                            g=g_val, version=v, limit=query.limit,
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((t.s, t.p, t.o, g, term_type, datatype, language))

            triples = [
                Triple(
                    s=create_term(q[0], term_type='u'),
                    p=create_term(q[1], term_type='u'),
                    o=create_term(q[2], term_type=q[4], datatype=q[5], language=q[6]),
                    g=q[3] if q[3] != DEFAULT_GRAPH else None
                )
                for q in quads
            ]

            return triples

        except Exception as e:

            logger.error(f"Exception querying triples: {e}", exc_info=True)
            raise e

    async def query_triples_stream(self, workspace, query):
        """
        Streaming query - yields (batch, is_final) tuples.
        Uses Cassandra's paging to fetch results incrementally.
        """
        try:

            batch_size = query.batch_size if query.batch_size > 0 else 20
            limit = query.limit if query.limit > 0 else 10000

            s_val = get_term_value(query.s)
            p_val = get_term_value(query.p)
            o_val = get_term_value(query.o)
            g_val = query.g

            def get_object_metadata(row):
                return (
                    getattr(row, 'otype', None),
                    getattr(row, 'dtype', None),
                    getattr(row, 'lang', None),
                )

            if s_val is None and p_val is None and o_val is None:

                tg = await self._get_connection(workspace)
                v = await self._resolve_version(
                    tg, query.collection, g_val, query.version,
                )

                def to_triple(row):
                    g = row.g if hasattr(row, 'g') else DEFAULT_GRAPH
                    term_type, datatype, language = get_object_metadata(row)
                    return Triple(
                        s=create_term(row.s, term_type='u'),
                        p=create_term(row.p, term_type='u'),
                        o=create_term(
                            row.o, term_type=term_type,
                            datatype=datatype, language=language,
                        ),
                        g=g if g != DEFAULT_GRAPH else None,
                    )

                # Stream resolved manifest batches with one-batch look-ahead
                # so we can tag the last batch as is_final=True.
                pending = None
                async for raw_batch in tg.async_stream_manifest(
                    query.collection,
                    g=g_val, version=v,
                    limit=limit, batch_size=batch_size,
                ):
                    triples = [to_triple(r) for r in raw_batch]
                    if not triples:
                        continue
                    if pending is not None:
                        yield pending, False
                    pending = triples

                if pending is not None:
                    yield pending, True
                else:
                    yield [], True
                return

            else:
                async for batch, is_final in self._fallback_stream(workspace, query, batch_size):
                    yield batch, is_final
                return

        except Exception as e:
            logger.error(f"Exception in streaming query: {e}", exc_info=True)
            raise e

    async def _fallback_stream(self, workspace, query, batch_size):
        """Fallback to non-streaming query with post-hoc batching."""
        triples = await self.query_triples(workspace, query)

        for i in range(0, len(triples), batch_size):
            batch = triples[i:i + batch_size]
            is_final = (i + batch_size >= len(triples))
            yield batch, is_final

        if len(triples) == 0:
            yield [], True

    async def handle_version_bump(self, workspace, request):
        tg = await self._get_connection(workspace)

        named_graph = request.named_graph
        new_version = await tg.async_bump_graph_version(
            request.collection, named_graph
        )

        logger.info(
            f"Bumped version for {request.collection}/{named_graph} "
            f"to v{new_version}"
        )

        return TriplesQueryResponse(version=new_version)

    async def handle_version_map(self, workspace, request):
        tg = await self._get_connection(workspace)

        version_map = await tg.async_get_version_map(request.collection)

        return TriplesQueryResponse(version_map=version_map)

    async def handle_version_list(self, workspace, request):
        tg = await self._get_connection(workspace)

        named_graph = request.named_graph
        log = await tg.async_get_version_log(
            request.collection, named_graph
        )

        entries = [
            VersionEntry(
                version=entry["version"],
                created_at=str(entry["created_at"]) if entry["created_at"] else "",
                names=list(entry["names"]) if entry["names"] else [],
                description=entry["description"] or "",
            )
            for entry in log
        ]

        return TriplesQueryResponse(version_log=entries)

    async def handle_version_label(self, workspace, request):
        tg = await self._get_connection(workspace)

        named_graph = request.named_graph
        if not request.version:
            return TriplesQueryResponse(
                error=Error(
                    type="version-label-error",
                    message="version is required for version-label",
                ),
            )

        if not request.name:
            return TriplesQueryResponse(
                error=Error(
                    type="version-label-error",
                    message="name is required for version-label",
                ),
            )

        version = await self._resolve_version(
            tg, request.collection, named_graph, request.version
        )

        await tg.async_label_version(
            request.collection, named_graph, version, request.name
        )

        logger.info(
            f"Labelled {request.collection}/{named_graph} "
            f"v{request.version} as '{request.name}'"
        )

        return TriplesQueryResponse()

    def _quad_tuples_to_triples(self, quads):
        """Convert a set of (s, p, o, g, otype, dtype, lang) tuples to Triple objects."""
        return [
            Triple(
                s=create_term(q[0], term_type='u'),
                p=create_term(q[1], term_type='u'),
                o=create_term(q[2], term_type=q[4], datatype=q[5], language=q[6]),
                g=q[3] if q[3] != DEFAULT_GRAPH else None,
            )
            for q in quads
        ]

    async def handle_diff(self, workspace, request):
        tg = await self._get_connection(workspace)

        named_graph = request.named_graph
        if not request.v1 or not request.v2:
            return TriplesQueryResponse(
                error=Error(
                    type="diff-error",
                    message="v1 and v2 are required for diff",
                ),
            )

        added, removed = await tg.async_diff_versions(
            request.collection, named_graph, request.v1, request.v2
        )

        logger.info(
            f"Diff {request.collection}/{named_graph} "
            f"v{request.v1}..v{request.v2}: "
            f"{len(added)} added, {len(removed)} removed"
        )

        return TriplesQueryResponse(
            added=self._quad_tuples_to_triples(added),
            removed=self._quad_tuples_to_triples(removed),
        )

    async def handle_revert(self, workspace, request):
        tg = await self._get_connection(workspace)

        named_graph = request.named_graph
        if not request.version:
            return TriplesQueryResponse(
                error=Error(
                    type="revert-error",
                    message="version is required for revert",
                ),
            )

        version = await self._resolve_version(
            tg, request.collection, named_graph, request.version
        )

        new_version = await tg.async_revert_to_version(
            request.collection, named_graph, version
        )

        logger.info(
            f"Reverted {request.collection}/{named_graph} "
            f"to v{version} (now v{new_version})"
        )

        return TriplesQueryResponse(version=new_version)

    async def handle_delete(self, workspace, request):
        tg = await self._get_connection(workspace)

        named_graph = request.named_graph
        version_cache = {}

        async def get_version(graph):
            if graph not in version_cache:
                version_cache[graph] = (
                    await tg.async_bootstrap_graph_version(
                        request.collection, graph
                    )
                )
            return version_cache[graph]

        if request.triples:
            # Explicit triple deletion — blind insert markers
            count = 0
            for triple in request.triples:
                s_val = get_term_value(triple.s)
                p_val = get_term_value(triple.p)
                o_val = get_term_value(triple.o)
                g_val = triple.g if triple.g is not None else named_graph

                if s_val is None or p_val is None or o_val is None:
                    continue

                version = await get_version(g_val)
                await tg.async_insert(
                    request.collection, s_val, p_val, o_val,
                    g_val, version, True,
                    otype=get_term_otype(triple.o),
                    dtype=get_term_dtype(triple.o),
                    lang=get_term_lang(triple.o),
                )
                count += 1

            logger.info(
                f"Deleted {count} explicit triples from "
                f"{request.collection}/{named_graph}"
            )

        else:
            # Pattern-based deletion — query then mark deleted
            query = request
            triples = await self.query_triples(workspace, query)
            count = 0
            for triple in triples:
                s_val = get_term_value(triple.s)
                p_val = get_term_value(triple.p)
                o_val = get_term_value(triple.o)
                g_val = triple.g if triple.g is not None else named_graph

                version = await get_version(g_val)
                await tg.async_insert(
                    request.collection, s_val, p_val, o_val,
                    g_val, version, True,
                    otype=get_term_otype(triple.o),
                    dtype=get_term_dtype(triple.o),
                    lang=get_term_lang(triple.o),
                )
                count += 1

            logger.info(
                f"Deleted {count} triples by pattern from "
                f"{request.collection}/{named_graph}"
            )

        return TriplesQueryResponse()

    async def handle_write(self, workspace, request):
        tg = await self._get_connection(workspace)

        named_graph = request.named_graph
        if not request.triples:
            return TriplesQueryResponse(
                error=Error(
                    type="write-error",
                    message="triples list is required for write",
                ),
            )

        version_cache = {}

        async def get_version(graph):
            if graph not in version_cache:
                version_cache[graph] = (
                    await tg.async_bootstrap_graph_version(
                        request.collection, graph
                    )
                )
            return version_cache[graph]

        count = 0
        for triple in request.triples:
            s_val = get_term_value(triple.s)
            p_val = get_term_value(triple.p)
            o_val = get_term_value(triple.o)
            g_val = triple.g if triple.g is not None else named_graph

            if s_val is None or p_val is None or o_val is None:
                continue

            version = await get_version(g_val)
            await tg.async_insert(
                request.collection, s_val, p_val, o_val,
                g_val, version, False,
                otype=get_term_otype(triple.o),
                dtype=get_term_dtype(triple.o),
                lang=get_term_lang(triple.o),
            )
            count += 1

        logger.info(
            f"Wrote {count} triples to "
            f"{request.collection}/{named_graph}"
        )

        return TriplesQueryResponse()

    @staticmethod
    def add_args(parser):

        TriplesQueryService.add_args(parser)
        add_cassandra_args(parser)


def run():

    Processor.launch(default_ident, __doc__)
