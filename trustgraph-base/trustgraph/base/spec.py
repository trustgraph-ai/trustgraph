
class Spec:

    async def register(self, flow, processor, definition):
        self.add(flow, processor, definition)
        return None

    def add(self, flow, processor, definition):
        pass


class TimeoutSpec:
    # Mixin for specs that create a client. An explicit constructor value
    # wins over the processor attribute named by timeout_param, which wins
    # over the class default.
    timeout_param = None
    default_timeout = None
    timeout = None

    def resolve_timeout(self, processor):
        # Reads a plain attribute: a Mock processor yields a Mock, not None.
        if self.timeout is not None:
            return self.timeout
        if self.timeout_param is not None:
            value = getattr(processor, self.timeout_param, None)
            if value is not None:
                return value
        return self.default_timeout
