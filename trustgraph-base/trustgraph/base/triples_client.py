
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import TriplesQueryRequest, TriplesQueryResponse, Value
from .. knowledge import Uri, Literal, Triple

def to_value(x):
    if x.is_uri: return Uri(x.value)
    return Literal(x.value)

def from_value(x):
    if x is None: return None
    if isinstance(x, Uri):
        return Value(value=str(x), is_uri=True)
    else:
        return Value(value=str(x), is_uri=False)

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

        return [
            Triple(to_value(v.s), to_value(v.p), to_value(v.o))
            for v in resp.triples
        ]

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

