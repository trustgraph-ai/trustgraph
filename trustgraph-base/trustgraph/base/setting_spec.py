
from . spec import Spec

class Setting:
    def __init__(self, value):
        self.value = value
    async def start():
        pass
    async def stop():
        pass
        
class SettingSpec(Spec):
    def __init__(self, name):
        self.name = name

    def add(self, flow, processor, definition):

        flow.config[self.name] = Setting(definition[self.name])

