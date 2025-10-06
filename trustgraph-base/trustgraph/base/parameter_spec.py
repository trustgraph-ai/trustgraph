
from . spec import Spec

class Parameter:
    def __init__(self, value):
        self.value = value
    async def start():
        pass
    async def stop():
        pass
        
class ParameterSpec(Spec):
    def __init__(self, name):
        self.name = name

    def add(self, flow, processor, definition):

        value = definition.get(self.name, None)

        flow.parameter[self.name] = Parameter(value)

