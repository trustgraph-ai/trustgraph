
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import TriplesQueryRequest, TriplesQueryResponse, Term, IRI, LITERAL, TRIPLE
from .. knowledge import Uri, Literal


class Triple:
    def __init__(self, s, p, o):
        self.s = s
        self.p = p
        self.o = o


def to_value(x):
    """Convert schema Term to Uri or Literal."""
    if x.type == IRI:
        return Uri(x.iri)
    elif x.type == LITERAL:
        return Literal(x.value)
    # Fallback
    return Literal(x.value or x.iri)


def from_value(x):
    """Convert Uri, Literal, string, or Term to schema Term."""
    if x is None:
        return None
    if isinstance(x, Term):
        return x
    if isinstance(x, Uri):
        return Term(type=IRI, iri=str(x))
    elif isinstance(x, Literal):
        return Term(type=LITERAL, value=str(x))
    elif isinstance(x, str):
        # Detect IRIs by common prefixes
        if x.startswith("http://") or x.startswith("https://") or x.startswith("urn:"):
            return Term(type=IRI, iri=x)
        else:
            return Term(type=LITERAL, value=x)
    else:
        return Term(type=LITERAL, value=str(x))

class TriplesClient(RequestResponse):
    async def query(self, s=None, p=None, o=None, limit=20,
                    user="trustgraph", collection="default",
                    timeout=30, g=None):

        resp = await self.request(
            TriplesQueryRequest(
                s = from_value(s),
                p = from_value(p),
                o = from_value(o),
                limit = limit,
                user = user,
                collection = collection,
                g = g,
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        triples = [
            Triple(to_value(v.s), to_value(v.p), to_value(v.o))
            for v in resp.triples
        ]

        return triples

    async def query_stream(self, s=None, p=None, o=None, limit=20,
                           user="trustgraph", collection="default",
                           batch_size=20, timeout=30,
                           batch_callback=None, g=None):
        """
        Streaming triple query - calls callback for each batch as it arrives.

        Args:
            s, p, o: Triple pattern (None for wildcard)
            limit: Maximum total triples to return
            user: User/keyspace
            collection: Collection name
            batch_size: Triples per batch
            timeout: Request timeout in seconds
            batch_callback: Async callback(batch, is_final) called for each batch
            g: Graph filter. ""=default graph only, None=all graphs,
               or a specific graph IRI.

        Returns:
            List[Triple]: All triples (flattened) if no callback provided
        """
        all_triples = []

        async def recipient(resp):
            if resp.error:
                raise RuntimeError(resp.error.message)

            batch = [
                Triple(to_value(v.s), to_value(v.p), to_value(v.o))
                for v in resp.triples
            ]

            if batch_callback:
                await batch_callback(batch, resp.is_final)
            else:
                all_triples.extend(batch)

            return resp.is_final

        await self.request(
            TriplesQueryRequest(
                s=from_value(s),
                p=from_value(p),
                o=from_value(o),
                limit=limit,
                user=user,
                collection=collection,
                streaming=True,
                batch_size=batch_size,
                g=g,
            ),
            timeout=timeout,
            recipient=recipient,
        )

        if not batch_callback:
            return all_triples

class TriplesClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(TriplesClientSpec, self).__init__(
            request_name = request_name,
            request_schema = TriplesQueryRequest,
            response_name = response_name,
            response_schema = TriplesQueryResponse,
            impl = TriplesClient,
        )

