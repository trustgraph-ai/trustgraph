
"""
Triples query service.  Input is a (s, p, o, g) quad pattern, some values may be
null.  Output is a list of quads.
"""

import logging

import json
from cassandra.query import SimpleStatement

from .... direct.cassandra_kg import (
    EntityCentricKnowledgeGraph, GRAPH_WILDCARD, DEFAULT_GRAPH
)
from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
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


def create_term(value, term_type=None, datatype=None, language=None):
    """
    Create a Term from a string value, optionally using type metadata.

    Args:
        value: The string value
        term_type: 'u' (IRI), 'l' (literal), 't' (triple)
        datatype: XSD datatype for literals
        language: Language tag for literals

    If term_type is provided, uses it to determine Term type.
    Otherwise falls back to URL detection heuristic for object values.
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
    elif term_type is not None:
        # Unknown term_type, fall back to heuristic
        pass

    # Heuristic fallback for backwards compatibility (object values only)
    if value.startswith("http://") or value.startswith("https://"):
        return Term(type=IRI, iri=value)
    else:
        return Term(type=LITERAL, value=value)


class Processor(TriplesQueryService):

    def __init__(self, **params):

        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace = resolve_cassandra_config(
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
        self.table = None

    def ensure_connection(self, user):
        """Ensure we have a connection to the correct keyspace."""
        if user != self.table:
            KGClass = EntityCentricKnowledgeGraph

            if self.cassandra_username and self.cassandra_password:
                self.tg = KGClass(
                    hosts=self.cassandra_host,
                    keyspace=user,
                    username=self.cassandra_username,
                    password=self.cassandra_password
                )
            else:
                self.tg = KGClass(
                    hosts=self.cassandra_host,
                    keyspace=user,
                )
            self.table = user

    async def query_triples(self, query):

        try:

            self.ensure_connection(query.user)

            # Extract values from query
            s_val = get_term_value(query.s)
            p_val = get_term_value(query.p)
            o_val = get_term_value(query.o)
            g_val = query.g  # Already a string or None

            def get_object_metadata(row):
                """Extract term type metadata from result row"""
                return (
                    getattr(row, 'otype', None),
                    getattr(row, 'dtype', None),
                    getattr(row, 'lang', None),
                )

            quads = []

            # Route to appropriate query method based on which fields are specified
            if s_val is not None:
                if p_val is not None:
                    if o_val is not None:
                        # SPO specified - find matching graphs
                        resp = self.tg.get_spo(
                            query.collection, s_val, p_val, o_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((s_val, p_val, o_val, g, term_type, datatype, language))
                    else:
                        # SP specified
                        resp = self.tg.get_sp(
                            query.collection, s_val, p_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((s_val, p_val, t.o, g, term_type, datatype, language))
                else:
                    if o_val is not None:
                        # SO specified
                        resp = self.tg.get_os(
                            query.collection, o_val, s_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((s_val, t.p, o_val, g, term_type, datatype, language))
                    else:
                        # S only
                        resp = self.tg.get_s(
                            query.collection, s_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((s_val, t.p, t.o, g, term_type, datatype, language))
            else:
                if p_val is not None:
                    if o_val is not None:
                        # PO specified
                        resp = self.tg.get_po(
                            query.collection, p_val, o_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((t.s, p_val, o_val, g, term_type, datatype, language))
                    else:
                        # P only
                        resp = self.tg.get_p(
                            query.collection, p_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((t.s, p_val, t.o, g, term_type, datatype, language))
                else:
                    if o_val is not None:
                        # O only
                        resp = self.tg.get_o(
                            query.collection, o_val, g=g_val,
                            limit=query.limit
                        )
                        for t in resp:
                            g = t.g if hasattr(t, 'g') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((t.s, t.p, o_val, g, term_type, datatype, language))
                    else:
                        # Nothing specified - get all
                        resp = self.tg.get_all(
                            query.collection,
                            limit=query.limit
                        )
                        for t in resp:
                            # Note: quads_by_collection uses 'd' for graph field
                            g = t.d if hasattr(t, 'd') else DEFAULT_GRAPH
                            term_type, datatype, language = get_object_metadata(t)
                            quads.append((t.s, t.p, t.o, g, term_type, datatype, language))

            # Convert to Triple objects (with g field)
            # s and p are always IRIs in RDF
            # Object uses term_type/datatype/language metadata from database
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

    async def query_triples_stream(self, query):
        """
        Streaming query - yields (batch, is_final) tuples.
        Uses Cassandra's paging to fetch results incrementally.
        """
        try:
            self.ensure_connection(query.user)

            batch_size = query.batch_size if query.batch_size > 0 else 20
            limit = query.limit if query.limit > 0 else 10000

            # Extract query pattern
            s_val = get_term_value(query.s)
            p_val = get_term_value(query.p)
            o_val = get_term_value(query.o)
            g_val = query.g

            def get_object_metadata(row):
                """Extract term type metadata from result row"""
                return (
                    getattr(row, 'otype', None),
                    getattr(row, 'dtype', None),
                    getattr(row, 'lang', None),
                )

            # For streaming, we need to execute with fetch_size
            # Use the collection table for get_all queries (most common streaming case)

            # Determine which query to use based on pattern
            if s_val is None and p_val is None and o_val is None:
                # Get all - use collection table with paging
                cql = f"SELECT d, s, p, o, otype, dtype, lang FROM {self.tg.collection_table} WHERE collection = %s"
                params = [query.collection]
            else:
                # For specific patterns, fall back to non-streaming
                # (these typically return small result sets anyway)
                async for batch, is_final in self._fallback_stream(query, batch_size):
                    yield batch, is_final
                return

            # Create statement with fetch_size for true streaming
            statement = SimpleStatement(cql, fetch_size=batch_size)
            result_set = self.tg.session.execute(statement, params)

            batch = []
            count = 0

            for row in result_set:
                if count >= limit:
                    break

                g = row.d if hasattr(row, 'd') else DEFAULT_GRAPH
                term_type, datatype, language = get_object_metadata(row)

                # s and p are always IRIs in RDF
                triple = Triple(
                    s=create_term(row.s, term_type='u'),
                    p=create_term(row.p, term_type='u'),
                    o=create_term(row.o, term_type=term_type, datatype=datatype, language=language),
                    g=g if g != DEFAULT_GRAPH else None
                )
                batch.append(triple)
                count += 1

                # Yield batch when full (never mark as final mid-stream)
                if len(batch) >= batch_size:
                    yield batch, False
                    batch = []

            # Always yield final batch to signal completion
            # This handles: remaining rows, empty result set, or exact batch boundary
            yield batch, True

        except Exception as e:
            logger.error(f"Exception in streaming query: {e}", exc_info=True)
            raise e

    async def _fallback_stream(self, query, batch_size):
        """Fallback to non-streaming query with post-hoc batching."""
        triples = await self.query_triples(query)

        for i in range(0, len(triples), batch_size):
            batch = triples[i:i + batch_size]
            is_final = (i + batch_size >= len(triples))
            yield batch, is_final

        if len(triples) == 0:
            yield [], True

    @staticmethod
    def add_args(parser):

        TriplesQueryService.add_args(parser)
        add_cassandra_args(parser)


def run():

    Processor.launch(default_ident, __doc__)
