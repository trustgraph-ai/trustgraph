
from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer

from . topic import topic
from . types import Error, RowSchema

############################################################################

# Prompt services, abstract the prompt generation

class ConfigItem(Record):
    key = String()
    value = String()

class ConfigItems(Record):
    items = Map(String())

class ConfigRequest(Record):
    type = String()
    key = String()
    operation = String() # get, list, getall, delete, put, dump

class ConfigResponse(Record):
    value = String()
    directory = Array(String())
    values = Map(String())
    config = Map(Map(String()))
    error = Error()

class ConfigPush(Record):
    config = Map(ConfigItems())

config_request_queue = topic(
    'prompt', kind='non-persistent', namespace='request'
)
config_response_queue = topic(
    'prompt', kind='non-persistent', namespace='response'
)
config_push_queue = topic(
    'prompt', kind='non-persistent', namespace='config'b
)

############################################################################

