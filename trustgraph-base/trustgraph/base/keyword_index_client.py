
import logging

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import KeywordIndexRequest, KeywordIndexResponse

# Module logger
logger = logging.getLogger(__name__)

class KeywordIndexClient(RequestResponse):
    async def query(self, query, limit=20, collection="default", timeout=30):

        resp = await self.request(
            KeywordIndexRequest(
                query = query,
                limit = limit,
                collection = collection
            ),
            timeout=timeout
        )

        logger.debug("Keyword index response: %s", resp)

        if resp.error:
            raise RuntimeError(resp.error.message)

        # Return ChunkMatch objects with chunk_id and score
        return resp.chunks

class KeywordIndexClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(KeywordIndexClientSpec, self).__init__(
            request_name = request_name,
            request_schema = KeywordIndexRequest,
            response_name = response_name,
            response_schema = KeywordIndexResponse,
            impl = KeywordIndexClient,
            # Flow definitions predating the keyword index don't declare
            # these topics; bind only where they exist so one stale
            # definition can't wedge the processor.
            optional = True,
        )
