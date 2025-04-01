
from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer

from . topic import topic
from . types import Error, RowSchema

############################################################################

# Prompt services, abstract the prompt generation
class ConfigRequest(Record):
    operation = String() # get, list, getall, delete, put, dump
    type = String()
    key = String()
    value = String()

class ConfigResponse(Record):
    version = Integer()
    value = String()
    directory = Array(String())
    values = Map(String())
    config = Map(Map(String()))
    error = Error()

class ConfigPush(Record):
    version = Integer()
    config = Map(Map(String()))

config_request_queue = topic(
    'config', kind='non-persistent', namespace='request'
)
config_response_queue = topic(
    'config', kind='non-persistent', namespace='response'
)
config_push_queue = topic(
    'config', kind='persistent', namespace='config'
)

############################################################################

