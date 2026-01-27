#!/usr/bin/env python3

import _pulsar

from .. schema import TriplesQueryRequest, TriplesQueryResponse, Term, IRI, LITERAL
from .. schema import triples_request_queue
from .. schema import triples_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class TriplesQueryClient(BaseClient):

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        if input_queue == None:
            input_queue = triples_request_queue

        if output_queue == None:
            output_queue = triples_response_queue

        super(TriplesQueryClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_api_key=pulsar_api_key,
            pulsar_host=pulsar_host,
            input_schema=TriplesQueryRequest,
            output_schema=TriplesQueryResponse,
        )

    def create_value(self, ent):

        if ent == None: return None

        if ent.startswith("http://") or ent.startswith("https://"):
            return Term(type=IRI, iri=ent)

        return Term(type=LITERAL, value=ent)

    def request(
            self, 
            s, p, o,
            user="trustgraph", collection="default",
            limit=10, timeout=120,
    ):
        return self.call(
            s=self.create_value(s),
            p=self.create_value(p),
            o=self.create_value(o),
            user=user,
            collection=collection,
            limit=limit,
            timeout=timeout,
        ).triples

