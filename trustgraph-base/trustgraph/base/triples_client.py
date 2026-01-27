
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import TriplesQueryRequest, TriplesQueryResponse, Term, IRI, LITERAL
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
    """Convert Uri or Literal to schema Term."""
    if x is None:
        return None
    if isinstance(x, Uri):
        return Term(type=IRI, iri=str(x))
    else:
        return Term(type=LITERAL, value=str(x))

class TriplesClient(RequestResponse):
    async def query(self, s=None, p=None, o=None, limit=20,
                    user="trustgraph", collection="default",
                    timeout=30):

        resp = await self.request(
            TriplesQueryRequest(
                s = from_value(s),
                p = from_value(p),
                o = from_value(o),
                limit = limit,
                user = user,
                collection = collection,
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

