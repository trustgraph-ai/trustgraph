
from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer

from . topic import topic
from . types import Error

############################################################################

# Config service:
#   get(keys) -> (version, values)
#   list(type) -> (version, values)
#   getvalues(type) -> (version, values)
#   put(values) -> ()
#   delete(keys) -> ()
#   config() -> (version, config)
class ConfigKey(Record):
    type = String()
    key = String()

class ConfigValue(Record):
    type = String()
    key = String()
    value = String()

# Prompt services, abstract the prompt generation
class ConfigRequest(Record):

    operation = String() # get, list, getvalues, delete, put, config

    # get, delete
    keys = Array(ConfigKey())

    # list, getvalues
    type = String()

    # put
    values = Array(ConfigValue())

class ConfigResponse(Record):

    # get, list, getvalues, config
    version = Integer()

    # get, getvalues
    values = Array(ConfigValue())

    # list
    directory = Array(String())

    # config
    config = Map(Map(String()))

    # Everything
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

